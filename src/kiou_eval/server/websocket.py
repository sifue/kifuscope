"""評価状態とWebSocket購読者の管理。"""

from __future__ import annotations

import asyncio

from fastapi import WebSocket

from .schemas import OverlayState


class EvaluationHub:
    """最新状態を保持し、接続中クライアントへ配信する。"""

    def __init__(self) -> None:
        self._state = OverlayState()
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def current(self) -> OverlayState:
        async with self._lock:
            return self._state.model_copy(deep=True)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
            state = self._state.model_dump(mode="json")
        await websocket.send_json(state)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def publish(self, state: OverlayState) -> None:
        async with self._lock:
            self._state = state
            clients = tuple(self._clients)
        payload = state.model_dump(mode="json")
        failed: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_json(payload)
            except RuntimeError:
                failed.append(client)
        if failed:
            async with self._lock:
                self._clients.difference_update(failed)

