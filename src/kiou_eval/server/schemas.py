"""HTTP APIのスキーマ。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """局面評価リクエスト。"""

    sfen: str = Field(min_length=1)
    movetime_ms: int | None = Field(default=None, ge=1, le=300_000)


class ResetRequest(BaseModel):
    """リアルタイム追跡リセットリクエスト。"""

    initial_sfen: str | None = Field(default=None, min_length=1)


class OverlayState(BaseModel):
    """オーバーレイへ配信する共通状態。"""

    status: str = "waiting"
    message: str = "局面を待っています"
    confidence: float = 0.0
    sfen: str | None = None
    turn: Literal["black", "white"] | None = None
    score_type: Literal["cp", "mate"] | None = None
    eval_cp_sente: int | None = None
    mate_sente: int | None = None
    bestmove: str | None = None
    bestmove_japanese: str | None = None
    pv: list[str] = Field(default_factory=list)
    pv_japanese: list[str] = Field(default_factory=list)
    depth: int | None = None
    seldepth: int | None = None
    nodes: int | None = None
    nps: int | None = None
    multipv: int | None = None
    lines: list[dict[str, Any]] = Field(default_factory=list)
