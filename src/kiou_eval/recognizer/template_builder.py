"""既知局面のスクリーンショットからテンプレートを生成する。"""

from __future__ import annotations

import hashlib
from pathlib import Path

import cv2
import numpy as np

from kiou_eval.shogi import BoardState

from .calibration import Calibration
from .templates import PIECE_TO_LABEL


def _write_png(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise OSError(f"テンプレートを書き込めません: {path}")


def _image_id(image: np.ndarray) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()[:12]


def build_templates(
    image: np.ndarray,
    state: BoardState,
    calibration: Calibration,
    output: Path,
    *,
    top_side: str | None = None,
    move_number: int | None = None,
) -> int:
    """局面ラベルに対応する盤面・持ち駒・手番PNGを切り出す。"""
    state.validate()
    board_image = calibration.board.crop(image)
    height, width = board_image.shape[:2]
    x_edges = np.linspace(0, width, 10, dtype=int)
    y_edges = np.linspace(0, height, 10, dtype=int)
    written = 0
    for visual_index in range(81):
        row, column = divmod(visual_index, 9)
        state_index = 80 - visual_index if calibration.rotate_board_180 else visual_index
        label = PIECE_TO_LABEL[state.squares[state_index]]
        patch = board_image[
            y_edges[row] : y_edges[row + 1], x_edges[column] : x_edges[column + 1]
        ]
        _write_png(
            output / "board" / label / f"cell_{row}_{column}_{_image_id(patch)}.png",
            patch,
        )
        written += 1

    for index, slot in enumerate(calibration.hand_slots):
        piece = slot.piece if slot.side == "black" else slot.piece.lower()
        count = state.hands.get(piece, 0)
        patch = slot.rect.crop(image)
        _write_png(
            output / "hand" / str(count) / f"slot_{index}_{_image_id(patch)}.png",
            patch,
        )
        written += 1

    if calibration.turn is not None:
        label = "black" if state.turn == "b" else "white"
        patch = calibration.turn.crop(image)
        _write_png(output / "turn" / label / f"turn_{_image_id(patch)}.png", patch)
        written += 1
    written += build_ui_templates(
        image,
        calibration,
        output,
        top_side=top_side,
        move_number=move_number,
    )
    return written


def build_ui_templates(
    image: np.ndarray,
    calibration: Calibration,
    output: Path,
    *,
    top_side: str | None = None,
    move_number: int | None = None,
) -> int:
    """先後表示・手数表示など盤面外UIテンプレートだけを生成する。"""
    written = 0
    if calibration.top_side_label is not None and top_side is not None:
        if top_side not in {"black", "white"}:
            raise ValueError("top_sideはblackまたはwhiteで指定してください")
        patch = calibration.top_side_label.rect(2).crop(image)
        _write_png(
            output / "top_side" / top_side / f"top_side_{_image_id(patch)}.png",
            patch,
        )
        written += 1
    if calibration.move_number_label is not None and move_number is not None:
        if move_number < 1:
            raise ValueError("move_numberは1以上で指定してください")
        for index, digit in enumerate(str(move_number)):
            if index >= calibration.move_number_label.max_chars:
                raise ValueError("move_numberがmove_number_label.max_charsを超えています")
            patch = calibration.move_number_label.char_rect(index).crop(image)
            _write_png(
                output / "move_digit" / digit / f"digit_{index}_{_image_id(patch)}.png",
                patch,
            )
            written += 1
    return written
