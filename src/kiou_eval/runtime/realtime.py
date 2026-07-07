"""棋桜画面のリアルタイム認識・評価ループ。"""

from __future__ import annotations

import asyncio
import contextlib
import logging
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
    capture_screen,
    capture_window,
    load_image,
)
from kiou_eval.server.schemas import OverlayState
from kiou_eval.server.websocket import EvaluationHub
from kiou_eval.shogi import INITIAL_SFEN, BoardState, StableLegalTracker

logger = logging.getLogger(__name__)
CaptureSource = Literal["window", "monitor", "images"]


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
        self.recognizer = ScreenRecognizer(calibration, TemplateLibrary(config.templates_path))
        self.tracker = StableLegalTracker(
            BoardState.from_sfen(config.initial_sfen),
            stable_frames=calibration.stable_frames,
            threshold=calibration.legal_match_threshold,
            margin=calibration.legal_margin,
        )
        self._image_index = 0
        self._last_requested_sfen: str | None = None
        self._last_published_sfen: str | None = None
        self._pending_evaluation: tuple[str, float] | None = None
        self._evaluation_task: asyncio.Task[None] | None = None

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
            await self.hub.publish(
                OverlayState(
                    status="recognition_failed",
                    message=f"画面キャプチャに失敗しました: {exc}",
                    confidence=0.0,
                )
            )
            return

        recognized = self.recognizer.recognize(
            frame, move_number=self.tracker.current.move_number
        )
        tracked = self.tracker.update(recognized.observation)
        if tracked.status == "recognition_failed":
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


def engine_analyze(engine: YaneuraOuClient, sfen: str) -> object:
    """asyncio.to_threadへ渡すための薄いラッパー。"""
    return engine.analyze(sfen)


def _turn_label(turn: str) -> Literal["black", "white"]:
    return "black" if turn == "b" else "white"
