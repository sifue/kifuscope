from __future__ import annotations

import cshogi

from kiou_eval.shogi import INITIAL_SFEN, BoardState, format_usi_move, format_usi_pv


def test_format_normal_move() -> None:
    state = BoardState.from_sfen(INITIAL_SFEN)
    assert format_usi_move(state, "7g7f") == "▲7六歩"


def test_format_white_move() -> None:
    board = cshogi.Board(INITIAL_SFEN)
    board.push_usi("7g7f")
    state = BoardState.from_sfen(board.sfen())
    assert format_usi_move(state, "3c3d") == "△3四歩"


def test_format_drop_move() -> None:
    state = BoardState.from_sfen("4k4/9/9/9/9/9/9/9/4K4 b B 1")
    assert format_usi_move(state, "B*5e") == "▲5五角打"


def test_format_promotion_move() -> None:
    state = BoardState.from_sfen("4k4/1B7/9/9/9/9/9/9/4K4 b - 1")
    assert format_usi_move(state, "8b2b+") == "▲2二角成"


def test_format_pv_advances_turns() -> None:
    state = BoardState.from_sfen(INITIAL_SFEN)
    assert format_usi_pv(state, ["7g7f", "3c3d"]) == ["▲7六歩", "△3四歩"]
