"""YaneuraOuをUSIサブプロセスとして制御する。"""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import TextIO

from kiou_eval.config import Settings
from kiou_eval.shogi import format_usi_move, format_usi_pv, validate_sfen_position

from .eval_result import EvalResult, PrincipalVariation
from .usi_parser import UsiInfo, normalize_score_for_sente, parse_info_line

logger = logging.getLogger(__name__)


class EngineError(RuntimeError):
    """エンジンの起動・通信・探索エラー。"""


class YaneuraOuClient:
    """1プロセスを逐次利用する同期USIクライアント。"""

    def __init__(self, settings: Settings, *, command_timeout: float = 15.0) -> None:
        self.settings = settings
        self.command_timeout = command_timeout
        self._process: subprocess.Popen[str] | None = None
        self._lines: queue.Queue[str | None] = queue.Queue()
        self._recent_output: deque[str] = deque(maxlen=5)
        self._reader_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        """エンジンプロセスが動作中か返す。"""
        return self._process is not None and self._process.poll() is None

    def _validate_engine_path(self) -> Path:
        path = self.settings.engine_path.expanduser()
        if not path.is_file():
            raise EngineError(
                "YaneuraOuが見つかりません。YANEAURAOU_ENGINE_PATHに"
                f"実行ファイルのパスを設定してください: {path}"
            )
        return path

    def start(self) -> None:
        """エンジンを起動し、USI初期化を完了する。"""
        with self._lock:
            if self.running:
                return
            path = self._validate_engine_path()
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            try:
                self._process = subprocess.Popen(
                    [str(path)],
                    cwd=path.parent,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=creationflags,
                )
            except OSError as exc:
                raise EngineError(f"YaneuraOuを起動できませんでした: {exc}") from exc

            assert self._process.stdout is not None
            self._reader_thread = threading.Thread(
                target=self._read_output,
                args=(self._process.stdout,),
                name="usi-output-reader",
                daemon=True,
            )
            self._reader_thread.start()
            try:
                self._send("usi")
                self._wait_for("usiok")
                self._send(f"setoption name USI_Hash value {self.settings.hash_mb}")
                self._send(f"setoption name Threads value {self.settings.threads}")
                self._send(f"setoption name MultiPV value {self.settings.multipv}")
                self._send("isready")
                self._wait_for("readyok")
                self._send("usinewgame")
            except Exception:
                self._terminate()
                raise
            logger.info("YaneuraOuへの接続が完了しました")

    def _read_output(self, stream: TextIO) -> None:
        try:
            for line in stream:
                stripped = line.rstrip("\r\n")
                self._recent_output.append(stripped)
                self._lines.put(stripped)
        finally:
            self._lines.put(None)

    def _send(self, command: str) -> None:
        process = self._process
        if process is None or process.poll() is not None or process.stdin is None:
            raise EngineError("YaneuraOuとの接続が切断されています")
        logger.debug("USI送信: %s", command)
        try:
            process.stdin.write(command + "\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise EngineError("YaneuraOuへのコマンド送信に失敗しました") from exc

    def _next_line(self, deadline: float) -> str:
        timeout = deadline - time.monotonic()
        if timeout <= 0:
            raise EngineError("YaneuraOuからの応答がタイムアウトしました")
        try:
            line = self._lines.get(timeout=timeout)
        except queue.Empty as exc:
            raise EngineError("YaneuraOuからの応答がタイムアウトしました") from exc
        if line is None:
            return_code = self._process.poll() if self._process else None
            detail = " / ".join(self._recent_output)
            suffix = f"。エンジン出力: {detail}" if detail else ""
            raise EngineError(
                f"YaneuraOuが予期せず終了しました（終了コード: {return_code}）{suffix}"
            )
        logger.debug("USI受信: %s", line)
        return line

    def _wait_for(self, expected: str) -> None:
        deadline = time.monotonic() + self.command_timeout
        while self._next_line(deadline) != expected:
            pass

    def check_connection(self) -> None:
        """起動済みエンジンへisreadyを送り、応答を確認する。"""
        self.start()
        with self._lock:
            self._send("isready")
            self._wait_for("readyok")

    def analyze(self, sfen: str, *, movetime_ms: int | None = None) -> EvalResult:
        """SFEN局面を評価し、先手視点に正規化した結果を返す。"""
        position = validate_sfen_position(sfen)
        self.start()
        think_time = movetime_ms or self.settings.movetime_ms
        if think_time < 1:
            raise ValueError("探索時間は1ミリ秒以上で指定してください")

        with self._lock:
            self._send(f"position sfen {sfen.strip()}")
            self._send(f"go movetime {think_time}")
            deadline = time.monotonic() + max(self.command_timeout, think_time / 1000 + 10)
            latest: dict[int, UsiInfo] = {}
            bestmove: str | None = None
            while bestmove is None:
                line = self._next_line(deadline)
                if line.startswith("info "):
                    info = parse_info_line(line)
                    if info is not None and info.score is not None:
                        latest[info.multipv] = info
                elif line.startswith("bestmove "):
                    parts = line.split()
                    bestmove = parts[1] if len(parts) > 1 else "none"

        if not latest:
            raise EngineError("YaneuraOuから評価値を取得できませんでした")
        primary = latest.get(1) or latest[min(latest)]
        lines = [self._to_pv(info, position.turn) for _, info in sorted(latest.items())]
        primary_pv = next((line for line in lines if line.multipv == primary.multipv), lines[0])
        return EvalResult(
            status="ok",
            sfen=sfen.strip(),
            turn="black" if position.turn == "b" else "white",
            score_type=primary_pv.score_type,
            eval_cp_sente=primary_pv.eval_cp_sente,
            mate_sente=primary_pv.mate_sente,
            bestmove=bestmove,
            pv=primary_pv.pv,
            depth=primary_pv.depth,
            seldepth=primary_pv.seldepth,
            nodes=primary_pv.nodes,
            nps=primary_pv.nps,
            multipv=primary_pv.multipv,
            lines=lines,
            bestmove_japanese=format_usi_move(position, bestmove),
            pv_japanese=format_usi_pv(position, primary_pv.pv),
        )

    @staticmethod
    def _to_pv(info: UsiInfo, turn: str) -> PrincipalVariation:
        assert info.score_type is not None and info.score is not None
        normalized = normalize_score_for_sente(info.score, turn)
        return PrincipalVariation(
            multipv=info.multipv,
            score_type=info.score_type,
            eval_cp_sente=normalized if info.score_type == "cp" else None,
            mate_sente=normalized if info.score_type == "mate" else None,
            depth=info.depth,
            seldepth=info.seldepth,
            nodes=info.nodes,
            nps=info.nps,
            pv=info.pv,
        )

    def stop_search(self) -> None:
        """進行中の探索へ停止要求を送る。"""
        if self.running:
            self._send("stop")

    def close(self) -> None:
        """エンジンを正常終了し、残存時は強制終了する。"""
        with self._lock:
            if not self.running:
                self._terminate()
                return
            try:
                self._send("quit")
                assert self._process is not None
                self._process.wait(timeout=3)
            except (EngineError, subprocess.TimeoutExpired):
                self._terminate()
            finally:
                self._process = None

    def _terminate(self) -> None:
        process = self._process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
        self._process = None

    def __enter__(self) -> YaneuraOuClient:
        self.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
