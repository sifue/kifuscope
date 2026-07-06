"""静止画像とスクリーンキャプチャの入力。"""

from __future__ import annotations

from pathlib import Path

import cv2
import mss
import numpy as np


def load_image(path: Path) -> np.ndarray:
    """静止画像をOpenCV BGR形式で読み込む。"""
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"画像を読み込めません: {path}")
    return image


def capture_screen(monitor: int = 1) -> np.ndarray:
    """指定モニターを1フレーム取得する。MVP 5の連続取得でも再利用する。"""
    with mss.mss() as screen:
        if monitor < 0 or monitor >= len(screen.monitors):
            raise ValueError(f"モニター番号が不正です: {monitor}")
        frame = np.asarray(screen.grab(screen.monitors[monitor]))
    return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

