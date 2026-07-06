"""USIのinfo行パーサー。"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Literal


@dataclass(slots=True)
class UsiInfo:
    """解析に必要なinfo行のフィールド。"""

    score_type: Literal["cp", "mate"] | None = None
    score: int | None = None
    lowerbound: bool = False
    upperbound: bool = False
    depth: int | None = None
    seldepth: int | None = None
    nodes: int | None = None
    nps: int | None = None
    multipv: int = 1
    pv: list[str] = field(default_factory=list)


_INTEGER_FIELDS = {"depth", "seldepth", "nodes", "nps", "multipv"}


def parse_info_line(line: str) -> UsiInfo | None:
    """USI ``info`` 行を解析する。解析対象外ならNoneを返す。"""
    tokens = line.strip().split()
    if not tokens or tokens[0] != "info":
        return None

    info = UsiInfo()
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in _INTEGER_FIELDS and index + 1 < len(tokens):
            with contextlib.suppress(ValueError):
                setattr(info, token, int(tokens[index + 1]))
            index += 2
            continue
        if token == "score" and index + 2 < len(tokens):
            score_type = tokens[index + 1]
            if score_type in {"cp", "mate"}:
                info.score_type = score_type  # type: ignore[assignment]
                try:
                    info.score = int(tokens[index + 2])
                except ValueError:
                    info.score = None
                index += 3
                continue
        if token == "lowerbound":
            info.lowerbound = True
        elif token == "upperbound":
            info.upperbound = True
        elif token == "pv":
            info.pv = tokens[index + 1 :]
            break
        index += 1
    return info


def normalize_score_for_sente(score: int, turn: str) -> int:
    """手番視点のスコアを先手視点へ正規化する。"""
    if turn not in {"b", "w"}:
        raise ValueError("手番は'b'または'w'で指定してください")
    return score if turn == "b" else -score
