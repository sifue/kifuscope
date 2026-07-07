"""棋桜画面のリアルタイム認識・評価ループ。"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np

from kiou_eval.config import Settings
from kiou_eval.engine import EngineError, YaneuraOuClient
from kiou_eval.recognizer import (
    Calibration,
    ScreenRecognizer,
    TemplateLibrary,
    build_templates,
    capture_screen,
    capture_window,
    load_image,
)
from kiou_eval.server.schemas import OverlayState
from kiou_eval.server.websocket import EvaluationHub
from kiou_eval.shogi import INITIAL_SFEN, BoardState, StableLegalTracker

logger = logging.getLogger(__name__)
CaptureSource = Literal["window", "monitor", "images"]
_REBUILD_TEMPLATE_GROUPS = ("board", "hand", "turn")


@dataclass(frozen=True, slots=True)
class RealtimeConfig:
    """リアルタイム認識ループの設定。"""

    calibration_path: Path
    templates_path: Path
    initial_sfen: str = INITIAL_SFEN
    source: CaptureSource = "window"
    window_title: str = "KIOU"
    window_contains: bool = False
    monitor: int = 1
    images: tuple[Path, ...] = field(default_factory=tuple)
    interval_sec: float = 0.25
    evaluate: bool = True

    def __post_init__(self) -> None:
        if self.interval_sec <= 0:
            raise ValueError("キャプチャ間隔は0秒より大きくしてください")
        if self.source == "images" and not self.images:
            raise ValueError("images入力では画像パスを1つ以上指定してください")


class RealtimeEvaluator:
    """キャプチャ、認識、合法手追跡、評価配信を統合する。"""

    def __init__(
        self,
        settings: Settings,
        hub: EvaluationHub,
        engine: YaneuraOuClient,
        config: RealtimeConfig,
    ) -> None:
        self.settings = settings
        self.hub = hub
        self.engine = engine
        self.config = config
        calibration = Calibration.from_file(config.calibration_path)
        self.calibration = calibration
        self.recognizer = ScreenRecognizer(calibration, TemplateLibrary(config.templates_path))
        self.tracker = self._create_tracker(config.initial_sfen)
        self._lock = asyncio.Lock()
        self._image_index = 0
        self._last_requested_sfen: str | None = None
        self._last_published_sfen: str | None = None
        self._pending_evaluation: tuple[str, float] | None = None
        self._evaluation_task: asyncio.Task[None] | None = None
        self._has_stable_overlay = False

    async def run(self) -> None:
        """キャンセルされるまでリアルタイム認識を続ける。"""
        logger.info(
            "リアルタイム認識を開始します: source=%s, templates=%s, calibration=%s",
            self.config.source,
            self.config.templates_path,
            self.config.calibration_path,
        )
        await self.hub.publish(
            OverlayState(status="recognizing", message="棋桜画面を認識中", confidence=0.0)
        )
        try:
            while True:
                try:
                    await self._process_one_frame()
                except Exception as exc:
                    logger.exception("リアルタイム認識ループで例外が発生しました")
                    await self.hub.publish(
                        OverlayState(
                            status="realtime_error",
                            message=f"リアルタイム認識でエラーが発生しました: {exc}",
                            confidence=0.0,
                            sfen=self.tracker.current.to_sfen(),
                            turn=_turn_label(self.tracker.current.turn),
                        )
                    )
                await asyncio.sleep(self.config.interval_sec)
        except asyncio.CancelledError:
            await self._shutdown_evaluation()
            raise

    async def _process_one_frame(self) -> None:
        try:
            frame = await asyncio.to_thread(self._capture_frame)
        except Exception as exc:
            logger.warning("画面キャプチャに失敗しました: %s", exc)
            if not self._has_stable_overlay:
                await self.hub.publish(
                    OverlayState(
                        status="recognition_failed",
                        message=f"画面キャプチャに失敗しました: {exc}",
                        confidence=0.0,
                    )
                )
            return

        async with self._lock:
            recognized = self.recognizer.recognize(
                frame, move_number=self.tracker.current.move_number
            )
            if recognized.observation.top_side is not None:
                logger.debug(
                    "画面上側表示を認識しました: top_side=%s",
                    recognized.observation.top_side,
                )
            if recognized.observation.move_number_observed is not None:
                logger.debug(
                    "画面手数を認識しました: observed=%s tracker_current=%s",
                    recognized.observation.move_number_observed,
                    self.tracker.current.move_number,
                )
            tracked = self.tracker.update(recognized.observation)
        if tracked.status == "recognition_failed":
            logger.warning(
                "局面認識に失敗しました: message=%s confidence=%.3f current_sfen=%s",
                tracked.message,
                tracked.confidence,
                self.tracker.current.to_sfen(),
            )
            if not self._has_stable_overlay:
                await self.hub.publish(
                    OverlayState(
                        status="recognition_failed",
                        message=tracked.message,
                        confidence=tracked.confidence,
                        sfen=self.tracker.current.to_sfen(),
                        turn=_turn_label(self.tracker.current.turn),
                    )
                )
            return
        if tracked.status == "position_unconfirmed":
            logger.info(
                "局面はまだ未確定です: message=%s confidence=%.3f current_sfen=%s",
                tracked.message,
                tracked.confidence,
                self.tracker.current.to_sfen(),
            )
            if not self._has_stable_overlay:
                await self.hub.publish(
                    OverlayState(
                        status="position_unconfirmed",
                        message=tracked.message,
                        confidence=tracked.confidence,
                        sfen=self.tracker.current.to_sfen(),
                        turn=_turn_label(self.tracker.current.turn),
                    )
                )
            return

        sfen = tracked.state.to_sfen()
        if not self.config.evaluate:
            if sfen != self._last_published_sfen:
                self._last_published_sfen = sfen
                self._has_stable_overlay = True
                await self.hub.publish(
                    OverlayState(
                        status="ok",
                        message="局面を確定しました",
                        confidence=tracked.confidence,
                        sfen=sfen,
                        turn=_turn_label(tracked.state.turn),
                    )
                )
            return

        if sfen != self._last_requested_sfen:
            self._last_requested_sfen = sfen
            logger.info("局面を確定しました。評価を要求します: %s", sfen)
            await self._request_evaluation(sfen, tracked.confidence)

    def _capture_frame(self) -> np.ndarray:
        if self.config.source == "window":
            return capture_window(
                self.config.window_title,
                exact=not self.config.window_contains,
            ).image
        if self.config.source == "monitor":
            return capture_screen(self.config.monitor)
        image_path = self.config.images[self._image_index % len(self.config.images)]
        self._image_index += 1
        return load_image(image_path)

    async def _request_evaluation(self, sfen: str, confidence: float) -> None:
        self._pending_evaluation = (sfen, confidence)
        logger.info("評価を開始します: sfen=%s confidence=%.3f", sfen, confidence)
        if not self._has_stable_overlay:
            await self.hub.publish(
                OverlayState(
                    status="evaluating",
                    message="評価中",
                    confidence=confidence,
                    sfen=sfen,
                    turn=_turn_label(BoardState.from_sfen(sfen).turn),
                )
            )
        if self._evaluation_task is not None and not self._evaluation_task.done():
            await asyncio.to_thread(self._stop_search_safely)
            return
        self._evaluation_task = asyncio.create_task(self._evaluation_loop())

    async def _evaluation_loop(self) -> None:
        while self._pending_evaluation is not None:
            sfen, confidence = self._pending_evaluation
            self._pending_evaluation = None
            try:
                result = await asyncio.to_thread(engine_analyze, self.engine, sfen)
            except Exception as exc:
                logger.error("リアルタイム評価に失敗しました: %s", exc)
                await self.hub.publish(
                    OverlayState(
                        status="engine_error",
                        message=str(exc),
                        confidence=confidence,
                        sfen=sfen,
                        turn=_turn_label(BoardState.from_sfen(sfen).turn),
                    )
                )
                continue

            if self._pending_evaluation is not None:
                continue
            self._last_published_sfen = sfen
            self._has_stable_overlay = True
            await self.hub.publish(OverlayState.model_validate(result.to_dict()))

    def _stop_search_safely(self) -> None:
        with contextlib.suppress(EngineError):
            self.engine.stop_search()

    async def _shutdown_evaluation(self) -> None:
        if self._evaluation_task is None:
            return
        if not self._evaluation_task.done():
            await asyncio.to_thread(self._stop_search_safely)
            self._evaluation_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._evaluation_task

    async def reset(
        self,
        initial_sfen: str | None = None,
        *,
        rebuild_templates: bool = False,
    ) -> OverlayState:
        """追跡状態を初期局面へ戻す。"""
        sfen = initial_sfen or self.config.initial_sfen
        state = BoardState.from_sfen(sfen)
        state.validate()
        async with self._lock:
            await asyncio.to_thread(self._stop_search_safely)
            rebuilt = 0
            if rebuild_templates:
                frame = await asyncio.to_thread(self._capture_frame)
                rebuilt = await asyncio.to_thread(
                    self._rebuild_templates,
                    frame,
                    state,
                )
                self.recognizer = ScreenRecognizer(
                    self.calibration, TemplateLibrary(self.config.templates_path)
                )
            self.tracker = self._create_tracker(sfen)
            self._pending_evaluation = None
            self._last_requested_sfen = None
            self._last_published_sfen = None
            self._has_stable_overlay = False
            message = "追跡状態をリセットしました"
            if rebuilt:
                message = f"テンプレートを{rebuilt}枚再生成し、追跡状態をリセットしました"
            overlay = OverlayState(
                status="recognizing",
                message=message,
                confidence=0.0,
                sfen=state.to_sfen(),
                turn=_turn_label(state.turn),
            )
            await self.hub.publish(overlay)
            return overlay

    def _rebuild_templates(self, frame: np.ndarray, state: BoardState) -> int:
        """現在フレームから初期局面テンプレートを作り直す。"""
        templates_path = self.config.templates_path
        templates_path.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".rebuild-templates-", dir=templates_path
        ) as temporary:
            temporary_path = Path(temporary)
            written = build_templates(frame, state, self.calibration, temporary_path)
            for group in _REBUILD_TEMPLATE_GROUPS:
                source = temporary_path / group
                target = templates_path / group
                backup = templates_path / f".{group}.backup"
                if backup.exists():
                    shutil.rmtree(backup)
                if target.exists():
                    target.rename(backup)
                try:
                    if source.exists():
                        shutil.move(str(source), str(target))
                except Exception:
                    if target.exists():
                        shutil.rmtree(target)
                    if backup.exists():
                        backup.rename(target)
                    raise
                if backup.exists():
                    shutil.rmtree(backup)
            return written

    def _create_tracker(self, initial_sfen: str) -> StableLegalTracker:
        return StableLegalTracker(
            BoardState.from_sfen(initial_sfen),
            stable_frames=self.calibration.stable_frames,
            threshold=self.calibration.legal_match_threshold,
            margin=self.calibration.legal_margin,
        )


def engine_analyze(engine: YaneuraOuClient, sfen: str) -> object:
    """asyncio.to_threadへ渡すための薄いラッパー。"""
    return engine.analyze(sfen)


def _turn_label(turn: str) -> Literal["black", "white"]:
    return "black" if turn == "b" else "white"
