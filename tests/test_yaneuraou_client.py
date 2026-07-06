from __future__ import annotations

import stat
from pathlib import Path

import pytest

from kiou_eval.config import Settings
from kiou_eval.engine import EngineError, YaneuraOuClient
from kiou_eval.shogi import INITIAL_SFEN


def _fake_engine(tmp_path: Path) -> Path:
    path = tmp_path / "fake_engine.py"
    path.write_text(
        """#!/usr/bin/env python3
import sys
for raw in sys.stdin:
    command = raw.strip()
    if command == "usi":
        print("id name FakeEngine", flush=True)
        print("usiok", flush=True)
    elif command == "isready":
        print("readyok", flush=True)
    elif command.startswith("go "):
        print("info depth 12 multipv 2 score cp 30 nodes 80 pv 7g7f", flush=True)
        print("info depth 14 seldepth 20 multipv 1 score cp 235 "
              "nodes 100 nps 5000 pv 2g2f 8c8d", flush=True)
        print("bestmove 2g2f ponder 8c8d", flush=True)
    elif command == "quit":
        break
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_engine_path_error(tmp_path: Path) -> None:
    settings = Settings(engine_path=tmp_path / "missing-engine")
    with pytest.raises(EngineError, match="YANEAURAOU_ENGINE_PATH"):
        YaneuraOuClient(settings).start()


def test_engine_start_error_is_clear(tmp_path: Path) -> None:
    path = tmp_path / "broken-engine"
    path.write_text("実行できないファイル", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    settings = Settings(engine_path=path)
    with pytest.raises(EngineError, match="YaneuraOuを起動できませんでした"):
        YaneuraOuClient(settings).start()


def test_analyze_with_fake_engine(tmp_path: Path) -> None:
    settings = Settings(engine_path=_fake_engine(tmp_path), multipv=2, movetime_ms=10)
    with YaneuraOuClient(settings, command_timeout=2) as client:
        result = client.analyze(INITIAL_SFEN)
    assert result.eval_cp_sente == 235
    assert result.bestmove == "2g2f"
    assert result.depth == 14
    assert result.pv == ["2g2f", "8c8d"]
    assert len(result.lines) == 2


def test_white_turn_score_is_normalized(tmp_path: Path) -> None:
    settings = Settings(engine_path=_fake_engine(tmp_path), movetime_ms=10)
    sfen = INITIAL_SFEN.replace(" b - 1", " w - 1")
    with YaneuraOuClient(settings, command_timeout=2) as client:
        result = client.analyze(sfen)
    assert result.eval_cp_sente == -235
