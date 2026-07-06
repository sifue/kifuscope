"""評価結果の値オブジェクト。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


@dataclass(slots=True)
class PrincipalVariation:
    """MultiPVの1候補。"""

    multipv: int
    score_type: Literal["cp", "mate"]
    eval_cp_sente: int | None = None
    mate_sente: int | None = None
    depth: int | None = None
    seldepth: int | None = None
    nodes: int | None = None
    nps: int | None = None
    pv: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EvalResult:
    """外部APIへ渡す局面評価結果。"""

    status: str
    sfen: str
    turn: Literal["black", "white"]
    score_type: Literal["cp", "mate"]
    eval_cp_sente: int | None
    mate_sente: int | None
    bestmove: str
    pv: list[str]
    depth: int | None
    seldepth: int | None
    nodes: int | None
    nps: int | None
    multipv: int
    lines: list[PrincipalVariation]
    confidence: float = 1.0
    message: str = "評価完了"

    def to_dict(self) -> dict[str, object]:
        """JSON化可能な辞書へ変換する。"""
        return asdict(self)

