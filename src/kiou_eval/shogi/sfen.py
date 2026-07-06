"""MVPで必要なSFENの構文検証。"""

from __future__ import annotations

from dataclasses import dataclass

INITIAL_SFEN = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
_PIECES = set("plnsgbrkPLNSGBRK")
_PROMOTABLE = set("plnsbrPLNSBR")
_HAND_PIECES = set("RBGSNLP rbgsnlp".replace(" ", ""))


class SfenError(ValueError):
    """SFENの形式が不正。"""


@dataclass(frozen=True, slots=True)
class SfenPosition:
    board: str
    turn: str
    hands: str
    move_number: int


def _validate_rank(rank: str) -> None:
    squares = 0
    index = 0
    while index < len(rank):
        token = rank[index]
        if token.isdigit() and token != "0":
            squares += int(token)
        elif token == "+":
            index += 1
            if index >= len(rank) or rank[index] not in _PROMOTABLE:
                raise SfenError("成駒の表記が不正です")
            squares += 1
        elif token in _PIECES:
            squares += 1
        else:
            raise SfenError(f"盤面に不正な文字があります: {token}")
        index += 1
    if squares != 9:
        raise SfenError("各段は9マスでなければなりません")


def _validate_hands(hands: str) -> None:
    if hands == "-":
        return
    index = 0
    while index < len(hands):
        start = index
        while index < len(hands) and hands[index].isdigit():
            index += 1
        if start != index and int(hands[start:index]) < 2:
            raise SfenError("持ち駒の枚数指定が不正です")
        if index >= len(hands) or hands[index] not in _HAND_PIECES:
            raise SfenError("持ち駒の表記が不正です")
        index += 1


def parse_sfen(sfen: str) -> SfenPosition:
    """SFENを構文検証して各フィールドを返す。"""
    fields = sfen.strip().split()
    if len(fields) != 4:
        raise SfenError("SFENは盤面・手番・持ち駒・手数の4項目で指定してください")
    board, turn, hands, move_text = fields
    ranks = board.split("/")
    if len(ranks) != 9:
        raise SfenError("盤面は9段で指定してください")
    for rank in ranks:
        _validate_rank(rank)
    if turn not in {"b", "w"}:
        raise SfenError("手番は'b'（先手）または'w'（後手）で指定してください")
    _validate_hands(hands)
    try:
        move_number = int(move_text)
    except ValueError as exc:
        raise SfenError("手数は整数で指定してください") from exc
    if move_number < 1:
        raise SfenError("手数は1以上で指定してください")
    return SfenPosition(board, turn, hands, move_number)
