"""USI指し手を配信用の日本語表記へ変換する。"""

from __future__ import annotations

import cshogi

from .board_state import BoardState

_SIDE_MARK = {"b": "▲", "w": "△"}
_RANK_JA = {
    "a": "一",
    "b": "二",
    "c": "三",
    "d": "四",
    "e": "五",
    "f": "六",
    "g": "七",
    "h": "八",
    "i": "九",
}
_FILE_JA = {
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
}
_PIECE_JA = {
    "P": "歩",
    "L": "香",
    "N": "桂",
    "S": "銀",
    "G": "金",
    "B": "角",
    "R": "飛",
    "K": "玉",
    "+P": "と",
    "+L": "成香",
    "+N": "成桂",
    "+S": "成銀",
    "+B": "馬",
    "+R": "龍",
}


def format_usi_move(state: BoardState, move_usi: str) -> str:
    """1手のUSI表記を現在局面から日本語表記へ変換する。"""
    if move_usi in {"none", "resign", "win"}:
        return move_usi
    if len(move_usi) < 4:
        return move_usi

    side = _SIDE_MARK[state.turn]
    if move_usi[1] == "*":
        piece = _PIECE_JA.get(move_usi[0].upper(), move_usi[0])
        destination = _format_square(move_usi[2:4])
        return f"{side}{destination}{piece}打"

    source = move_usi[0:2]
    destination = _format_square(move_usi[2:4])
    piece = state.squares[_square_index(source)]
    if piece is None:
        return f"{side}{destination}{move_usi}"
    piece_key = piece.upper() if not piece.startswith("+") else "+" + piece[-1].upper()
    piece_name = _PIECE_JA.get(piece_key)
    if piece_name is None:
        piece_name = piece
    promotion = "成" if move_usi.endswith("+") else ""
    return f"{side}{destination}{piece_name}{promotion}"


def format_usi_pv(state: BoardState, pv: list[str]) -> list[str]:
    """PVを局面を進めながら日本語表記へ変換する。"""
    if not pv:
        return []
    board = cshogi.Board(state.to_sfen())
    current = state
    formatted: list[str] = []
    for move in pv:
        formatted.append(format_usi_move(current, move))
        try:
            board.push_usi(move)
        except Exception:
            break
        current = BoardState.from_sfen(board.sfen())
    return formatted


def _format_square(square: str) -> str:
    if len(square) != 2:
        return square
    file_text = _FILE_JA.get(square[0], square[0])
    rank_text = _RANK_JA.get(square[1], square[1])
    return f"{file_text}{rank_text}"


def _square_index(square: str) -> int:
    file_number = int(square[0])
    rank_index = ord(square[1]) - ord("a")
    return rank_index * 9 + (9 - file_number)
