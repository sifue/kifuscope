"""盤面・持ち駒・手番の統合テンプレート認識。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from kiou_eval.shogi import UNKNOWN, BoardObservation, PositionValidationError

from .calibration import Calibration
from .templates import LABEL_TO_PIECE, TemplateLibrary


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    """1フレームの認識結果。"""

    status: str
    message: str
    observation: BoardObservation
    sfen: str | None = None

    def to_dict(self) -> dict[str, object]:
        squares = ["unknown" if value is UNKNOWN else value for value in self.observation.squares]
        return {
            "status": self.status,
            "message": self.message,
            "confidence": self.observation.confidence,
            "sfen": self.sfen,
            "board_sfen_guess": self.observation.to_board_sfen_guess(),
            "turn": self.observation.turn,
            "hands": self.observation.hands,
            "squares": squares,
            "square_confidences": list(self.observation.square_confidences),
        }


class ScreenRecognizer:
    """キャリブレーションに従い1枚の画面を局面観測へ変換する。"""

    def __init__(self, calibration: Calibration, templates: TemplateLibrary) -> None:
        self.calibration = calibration
        self.templates = templates

    def recognize(self, image: np.ndarray, *, move_number: int = 1) -> RecognitionResult:
        board_image = self.calibration.board.crop(image)
        squares, square_confidences = self._recognize_board(board_image)
        hands, hand_confidences = self._recognize_hands(image)
        turn, turn_confidence = self._recognize_turn(image)
        confidences = list(square_confidences) + hand_confidences
        if turn_confidence is not None:
            confidences.append(turn_confidence)
        confidence = float(np.mean(confidences)) if confidences else 0.0
        observation = BoardObservation(
            tuple(squares), tuple(square_confidences), hands, turn, confidence
        )
        state = observation.to_state(move_number)
        if state is None:
            if observation.has_complete_board():
                return RecognitionResult(
                    "board_observed",
                    "盤面は認識しました。手番・持ち駒は合法手追跡で補正します",
                    observation,
                )
            return RecognitionResult(
                "recognition_failed", "局面の一部を確定できませんでした", observation
            )
        try:
            state.validate()
        except PositionValidationError as exc:
            return RecognitionResult(
                "recognition_failed", f"局面の合法性検証に失敗しました: {exc}", observation
            )
        return RecognitionResult("ok", "局面を認識しました", observation, state.to_sfen())

    def _recognize_board(
        self, board_image: np.ndarray
    ) -> tuple[list[str | None | object], list[float]]:
        height, width = board_image.shape[:2]
        x_edges = np.linspace(0, width, 10, dtype=int)
        y_edges = np.linspace(0, height, 10, dtype=int)
        squares: list[str | None | object] = []
        confidences: list[float] = []
        for row in range(9):
            for column in range(9):
                patch = board_image[
                    y_edges[row] : y_edges[row + 1], x_edges[column] : x_edges[column + 1]
                ]
                match = self.templates.match(patch, "board")
                confidences.append(match.confidence)
                squares.append(
                    LABEL_TO_PIECE[match.label]
                    if match.confidence >= self.calibration.board_threshold
                    else UNKNOWN
                )
        if self.calibration.rotate_board_180:
            squares.reverse()
            confidences.reverse()
        return squares, confidences

    def _recognize_hands(
        self, image: np.ndarray
    ) -> tuple[dict[str, int] | None, list[float]]:
        if not self.calibration.hand_slots or not self.templates.has_group("hand"):
            return None, []
        hands: dict[str, int] = {}
        confidences: list[float] = []
        for slot in self.calibration.hand_slots:
            match = self.templates.match(slot.rect.crop(image), "hand")
            confidences.append(match.confidence)
            if match.confidence < self.calibration.hand_threshold or not match.label.isdigit():
                return None, confidences
            count = int(match.label)
            if count:
                piece = slot.piece if slot.side == "black" else slot.piece.lower()
                hands[piece] = count
        return hands, confidences

    def _recognize_turn(self, image: np.ndarray) -> tuple[str | None, float | None]:
        if self.calibration.turn is None or not self.templates.has_group("turn"):
            return None, None
        match = self.templates.match(self.calibration.turn.crop(image), "turn")
        if match.confidence < self.calibration.turn_threshold:
            return None, match.confidence
        turn = {"black": "b", "white": "w"}.get(match.label)
        return turn, match.confidence
