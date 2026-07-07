"""FastAPIアプリケーション。"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from kiou_eval.config import Settings
from kiou_eval.engine import EngineError, YaneuraOuClient
from kiou_eval.shogi import INITIAL_SFEN, PositionValidationError, SfenError

from .schemas import AnalyzeRequest, OverlayState, ResetRequest
from .websocket import EvaluationHub

if TYPE_CHECKING:
    from kiou_eval.runtime import RealtimeConfig

logger = logging.getLogger(__name__)
OVERLAY_DIR = Path(__file__).resolve().parent.parent / "overlay"


def _demo_state(value: int) -> OverlayState:
    return OverlayState(
        status="ok",
        message="デモ評価値",
        confidence=1.0,
        sfen=INITIAL_SFEN,
        turn="black",
        score_type="cp",
        eval_cp_sente=value,
        bestmove="2g2f",
        pv=["2g2f", "8c8d", "2f2e"],
        depth=14,
        nodes=123456,
        multipv=1,
    )


async def _run_demo(hub: EvaluationHub) -> None:
    values = [-320, -80, 0, 140, 430, 120]
    index = 0
    while True:
        await hub.publish(_demo_state(values[index % len(values)]))
        index += 1
        await asyncio.sleep(3)


def create_app(
    settings: Settings | None = None,
    *,
    demo: bool = False,
    realtime: RealtimeConfig | None = None,
) -> FastAPI:
    """依存を注入可能なFastAPIアプリを生成する。"""
    resolved = settings or Settings()
    hub = EvaluationHub()
    engine = YaneuraOuClient(resolved)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        demo_task = asyncio.create_task(_run_demo(hub)) if demo else None
        realtime_task = None
        if realtime is not None:
            from kiou_eval.runtime import RealtimeEvaluator

            _app.state.realtime_runner = RealtimeEvaluator(resolved, hub, engine, realtime)
            realtime_task = asyncio.create_task(_app.state.realtime_runner.run())
        try:
            yield
        finally:
            if realtime_task is not None:
                realtime_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await realtime_task
            if demo_task is not None:
                demo_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await demo_task
            await asyncio.to_thread(engine.close)

    app = FastAPI(
        title="Kifuscope API",
        description="配信・実況向けの将棋評価値API",
        version="0.3.0",
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.hub = hub
    app.state.engine = engine
    app.state.realtime_runner = None
    app.mount("/static", StaticFiles(directory=OVERLAY_DIR), name="overlay-static")

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/overlay")

    @app.get("/overlay", include_in_schema=False)
    async def overlay() -> FileResponse:
        return FileResponse(OVERLAY_DIR / "overlay.html")

    @app.get("/api/eval", response_model=OverlayState)
    async def get_evaluation() -> OverlayState:
        return await hub.current()

    @app.post("/api/analyze", response_model=OverlayState)
    async def analyze(request: AnalyzeRequest) -> OverlayState:
        await hub.publish(
            OverlayState(
                status="evaluating",
                message="評価中",
                confidence=1.0,
                sfen=request.sfen,
            )
        )
        try:
            result = await asyncio.to_thread(
                engine.analyze, request.sfen, movetime_ms=request.movetime_ms
            )
            state = OverlayState.model_validate(result.to_dict())
        except (SfenError, PositionValidationError) as exc:
            state = OverlayState(status="invalid_sfen", message=str(exc), confidence=0.0)
            await hub.publish(state)
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except EngineError as exc:
            logger.error("エンジン評価に失敗しました: %s", exc)
            state = OverlayState(status="engine_error", message=str(exc), confidence=0.0)
            await hub.publish(state)
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        await hub.publish(state)
        return state

    @app.post("/api/realtime/reset", response_model=OverlayState)
    async def reset_realtime(request: ResetRequest | None = None) -> OverlayState:
        runner = app.state.realtime_runner
        if runner is None:
            raise HTTPException(
                status_code=409,
                detail="リアルタイム認識は起動していません。serve-realtimeで起動してください。",
            )
        try:
            return await runner.reset(request.initial_sfen if request else None)
        except (SfenError, PositionValidationError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.websocket("/ws/eval")
    async def evaluation_websocket(websocket: WebSocket) -> None:
        await hub.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await hub.disconnect(websocket)

    return app


app = create_app()
