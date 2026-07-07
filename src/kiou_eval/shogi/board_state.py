"""画像認識と合法手追跡で共有する局面モデル。"""

from __future__ import annotations

from dataclasses import dataclass, field

import cshogi

from .sfen import SfenError, parse_sfen

HAND_ORDER = "RBGSNLPrbgsnlp"
BOARD_PIECES = frozenset(
    {
        "P",
        "L",
        "N",
        "S",
        "G",
        "B",
        "R",
        "K",
        "+P",
        "+L",
        "+N",
        "+S",
        "+B",
        "+R",
        "p",
        "l",
        "n",
        "s",
        "g",
        "b",
        "r",
        "k",
        "+p",
        "+l",
        "+n",
        "+s",
        "+b",
        "+r",
    }
)


class PositionValidationError(ValueError):
    """局面が将棋の基本制約を満たさない。"""


def _expand_rank(rank: str) -> list[str | None]:
    squares: list[str | None] = []
    index = 0
    while index < len(rank):
        token = rank[index]
        if token.isdigit():
            squares.extend([None] * int(token))
        elif token == "+":
            index += 1
            squares.append("+" + rank[index])
        else:
            squares.append(token)
        index += 1
    return squares


def _parse_hands(text: str) -> dict[str, int]:
    hands: dict[str, int] = {}
    if text == "-":
        return hands
    index = 0
    while index < len(text):
        start = index
        while index < len(text) and text[index].isdigit():
            index += 1
        count = int(text[start:index]) if start != index else 1
        hands[text[index]] = count
        index += 1
    return hands


@dataclass(frozen=True, slots=True)
class BoardState:
    """SFEN順（9筋から1筋、1段から9段）の81マス局面。"""

    squares: tuple[str | None, ...]
    hands: dict[str, int] = field(default_factory=dict)
    turn: str = "b"
    move_number: int = 1

    def __post_init__(self) -> None:
        if len(self.squares) != 81:
            raise ValueError("盤面は81マスで指定してください")
        if self.turn not in {"b", "w"}:
            raise ValueError("手番は'b'または'w'で指定してください")
        if self.move_number < 1:
            raise ValueError("手数は1以上で指定してください")
        invalid = {piece for piece in self.squares if piece is not None} - BOARD_PIECES
        if invalid:
            raise ValueError(f"未対応の駒表記があります: {sorted(invalid)}")

    @classmethod
    def from_sfen(cls, sfen: str) -> BoardState:
        """検証済みSFENから局面を生成する。"""
        parsed = parse_sfen(sfen)
        squares = tuple(
            square for rank in parsed.board.split("/") for square in _expand_rank(rank)
        )
        return cls(squares, _parse_hands(parsed.hands), parsed.turn, parsed.move_number)

    def to_sfen(self) -> str:
        """局面をSFEN文字列へ変換する。"""
        ranks: list[str] = []
        for row in range(9):
            rank = ""
            empty = 0
            for piece in self.squares[row * 9 : (row + 1) * 9]:
                if piece is None:
                    empty += 1
                    continue
                if empty:
                    rank += str(empty)
                    empty = 0
                rank += piece
            if empty:
                rank += str(empty)
            ranks.append(rank)
        hand_text = "".join(
            (str(self.hands[piece]) if self.hands.get(piece, 0) > 1 else "") + piece
            for piece in HAND_ORDER
            if self.hands.get(piece, 0) > 0
        )
        return f"{'/'.join(ranks)} {self.turn} {hand_text or '-'} {self.move_number}"

    def validate(self) -> None:
        """王・二歩・駒数とcshogi内部整合性を検証する。"""
        if self.squares.count("K") != 1 or self.squares.count("k") != 1:
            raise PositionValidationError("先手・後手の王が1枚ずつ必要です")
        self._validate_nifu()
        self._validate_piece_counts()
        try:
            board = cshogi.Board(self.to_sfen())
        except Exception as exc:
            raise PositionValidationError(f"cshogiがSFENを読み込めません: {exc}") from exc
        if not board.is_ok():
            raise PositionValidationError("cshogiの局面整合性検証に失敗しました")

    def _validate_nifu(self) -> None:
        for file_index in range(9):
            pieces = [self.squares[row * 9 + file_index] for row in range(9)]
            if pieces.count("P") > 1:
                raise PositionValidationError(f"先手が二歩です（盤面列 {file_index + 1}）")
            if pieces.count("p") > 1:
                raise PositionValidationError(f"後手が二歩です（盤面列 {file_index + 1}）")

    def _validate_piece_counts(self) -> None:
        limits = {"P": 18, "L": 4, "N": 4, "S": 4, "G": 4, "B": 2, "R": 2, "K": 2}
        totals = dict.fromkeys(limits, 0)
        for piece in self.squares:
            if piece is not None:
                totals[piece[-1].upper()] += 1
        for piece, count in self.hands.items():
            key = piece.upper()
            if key not in totals or count < 0:
                raise PositionValidationError("持ち駒の種類または枚数が不正です")
            totals[key] += count
        for piece, limit in limits.items():
            if totals[piece] > limit:
                raise PositionValidationError(f"駒数が上限を超えています: {piece}")


@dataclass(frozen=True, slots=True)
class BoardObservation:
    """未確定要素を許容する画像認識結果。"""

    squares: tuple[str | None | object, ...]
    square_confidences: tuple[float, ...]
    hands: dict[str, int] | None
    turn: str | None
    confidence: float

    def __post_init__(self) -> None:
        if len(self.squares) != 81 or len(self.square_confidences) != 81:
            raise ValueError("盤面観測は81マスで指定してください")

    def to_state(self, move_number: int = 1) -> BoardState | None:
        """全要素が確定している場合だけ局面へ変換する。"""
        if self.hands is None or self.turn is None:
            return None
        if any(square is UNKNOWN for square in self.squares):
            return None
        return BoardState(self.squares, self.hands, self.turn, move_number)  # type: ignore[arg-type]

    def has_complete_board(self) -> bool:
        """盤面81マスだけが全て確定しているかを返す。"""
        return not any(square is UNKNOWN for square in self.squares)

    def to_board_sfen_guess(self) -> str | None:
        """盤面だけから推定SFENを作る。手番・持ち駒・手数は仮値を使う。"""
        if not self.has_complete_board():
            return None
        return BoardState(self.squares, {}, "b", 1).to_sfen()  # type: ignore[arg-type]


class _UnknownSquare:
    def __repr__(self) -> str:
        return "UNKNOWN"


UNKNOWN = _UnknownSquare()


def validate_sfen_position(sfen: str) -> BoardState:
    """SFENを局面モデルとcshogiで検証して返す。"""
    try:
        state = BoardState.from_sfen(sfen)
    except SfenError as exc:
        raise PositionValidationError(str(exc)) from exc
    state.validate()
    return state
