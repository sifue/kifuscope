from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from kiou_eval.recognizer import (
    Calibration,
    HandSlot,
    Rect,
    ScreenRecognizer,
    TemplateLibrary,
    build_templates,
)
from kiou_eval.recognizer.templates import PIECE_TO_LABEL
from kiou_eval.shogi import INITIAL_SFEN, BoardState


def _write_template(root: Path, group: str, label: str, value: int) -> None:
    directory = root / group / label
    directory.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(directory / "sample.png"), np.full((10, 10), value, np.uint8))


def _synthetic_recognizer(tmp_path: Path) -> tuple[ScreenRecognizer, np.ndarray]:
    initial = BoardState.from_sfen(INITIAL_SFEN)
    labels = list(dict.fromkeys(PIECE_TO_LABEL[piece] for piece in initial.squares))
    values = {label: 10 + index * 15 for index, label in enumerate(labels)}
    for label, value in values.items():
        _write_template(tmp_path, "board", label, value)
    _write_template(tmp_path, "hand", "0", 7)
    _write_template(tmp_path, "turn", "black", 250)
    _write_template(tmp_path, "turn", "white", 100)

    image = np.zeros((100, 110, 3), np.uint8)
    for index, piece in enumerate(initial.squares):
        row, column = divmod(index, 9)
        value = values[PIECE_TO_LABEL[piece]]
        image[row * 10 : (row + 1) * 10, column * 10 : (column + 1) * 10] = value
    image[0:10, 90:100] = 7
    image[0:10, 100:110] = 250
    calibration = Calibration(
        board=Rect(0, 0, 90, 90),
        hand_slots=(HandSlot("black", "P", Rect(90, 0, 10, 10)),),
        turn=Rect(100, 0, 10, 10),
        board_threshold=0.99,
        hand_threshold=0.99,
        turn_threshold=0.99,
    )
    return ScreenRecognizer(calibration, TemplateLibrary(tmp_path)), image


def test_recognize_complete_initial_position(tmp_path: Path) -> None:
    recognizer, image = _synthetic_recognizer(tmp_path)
    result = recognizer.recognize(image)
    assert result.status == "ok"
    assert result.sfen == INITIAL_SFEN
    assert result.observation.confidence == 1.0


def test_low_confidence_square_stops_position(tmp_path: Path) -> None:
    recognizer, image = _synthetic_recognizer(tmp_path)
    image[0:10, 0:10] = 255
    result = recognizer.recognize(image)
    assert result.status == "recognition_failed"
    assert result.sfen is None


def test_missing_hand_templates_stops_position(tmp_path: Path) -> None:
    recognizer, image = _synthetic_recognizer(tmp_path)
    no_hands = Calibration(board=Rect(0, 0, 90, 90), turn=Rect(100, 0, 10, 10))
    result = ScreenRecognizer(no_hands, recognizer.templates).recognize(image)
    assert result.status == "recognition_failed"
    assert result.observation.hands is None


def test_build_templates_from_known_position(tmp_path: Path) -> None:
    recognizer, image = _synthetic_recognizer(tmp_path / "source")
    output = tmp_path / "built"
    count = build_templates(
        image,
        BoardState.from_sfen(INITIAL_SFEN),
        recognizer.calibration,
        output,
    )
    rebuilt = ScreenRecognizer(recognizer.calibration, TemplateLibrary(output))
    assert count == 83
    assert rebuilt.recognize(image).sfen == INITIAL_SFEN
