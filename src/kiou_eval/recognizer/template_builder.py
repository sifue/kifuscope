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
    return written
