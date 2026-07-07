"""画像テンプレートの読み込みと照合。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

PIECE_TO_LABEL = {
    None: "empty",
    "P": "black_pawn",
    "L": "black_lance",
    "N": "black_knight",
    "S": "black_silver",
    "G": "black_gold",
    "B": "black_bishop",
    "R": "black_rook",
    "K": "black_king",
    "+P": "black_promoted_pawn",
    "+L": "black_promoted_lance",
    "+N": "black_promoted_knight",
    "+S": "black_promoted_silver",
    "+B": "black_horse",
    "+R": "black_dragon",
    "p": "white_pawn",
    "l": "white_lance",
    "n": "white_knight",
    "s": "white_silver",
    "g": "white_gold",
    "b": "white_bishop",
    "r": "white_rook",
    "k": "white_king",
    "+p": "white_promoted_pawn",
    "+l": "white_promoted_lance",
    "+n": "white_promoted_knight",
    "+s": "white_promoted_silver",
    "+b": "white_horse",
    "+r": "white_dragon",
}
LABEL_TO_PIECE = {label: piece for piece, label in PIECE_TO_LABEL.items()}


@dataclass(frozen=True, slots=True)
class TemplateMatch:
    label: str
    confidence: float


class TemplateLibrary:
    """``種別/ラベル/*.png`` 形式のテンプレート群。"""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._groups: dict[str, dict[str, list[np.ndarray]]] = {}
        for group in ("board", "hand", "turn", "top_side", "move_digit"):
            self._groups[group] = self._load_group(group)
        board_labels = set(self._groups["board"])
        invalid = board_labels - set(LABEL_TO_PIECE)
        if invalid:
            raise ValueError(f"盤面テンプレートに不明なラベルがあります: {sorted(invalid)}")
        if not board_labels:
            raise ValueError(
                "盤面テンプレートがありません: "
                f"{root / 'board'}。GitHubから取得した直後はテンプレートが含まれません。"
                "KIOUの初期局面スクリーンショットから build-templates を実行してください。"
            )

    def _load_group(self, group: str) -> dict[str, list[np.ndarray]]:
        directory = self.root / group
        loaded: dict[str, list[np.ndarray]] = {}
        if not directory.is_dir():
            return loaded
        for label_dir in sorted(path for path in directory.iterdir() if path.is_dir()):
            images: list[np.ndarray] = []
            for path in sorted(label_dir.glob("*.png")):
                image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
                if image is None:
                    raise ValueError(f"テンプレート画像を読み込めません: {path}")
                images.append(image)
            if images:
                loaded[label_dir.name] = images
        return loaded

    def has_group(self, group: str) -> bool:
        return bool(self._groups.get(group))

    def match(self, patch: np.ndarray, group: str) -> TemplateMatch:
        """平均絶対誤差に基づき最も近いラベルを返す。"""
        templates = self._groups.get(group, {})
        if not templates:
            raise ValueError(f"テンプレート種別がありません: {group}")
        gray = _prepare_for_match(patch)
        best_label = ""
        best_confidence = -1.0
        for label, candidates in templates.items():
            for template in candidates:
                prepared_template = _prepare_for_match(template)
                resized = cv2.resize(
                    gray, (prepared_template.shape[1], prepared_template.shape[0])
                )
                difference = np.mean(
                    np.abs(
                        resized.astype(np.float32) - prepared_template.astype(np.float32)
                    )
                )
                confidence = 1.0 - float(difference / 255.0)
                if confidence > best_confidence:
                    best_label = label
                    best_confidence = confidence
        return TemplateMatch(best_label, max(0.0, min(1.0, best_confidence)))


def _prepare_for_match(image: np.ndarray) -> np.ndarray:
    """照合前に背景色の影響を下げ、駒文字・輪郭を主に残す。"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    height, width = gray.shape[:2]
    margin_y = max(1, int(height * 0.12))
    margin_x = max(1, int(width * 0.12))
    if height - margin_y * 2 >= 4 and width - margin_x * 2 >= 4:
        gray = gray[margin_y : height - margin_y, margin_x : width - margin_x]

    raw = gray.astype(np.uint8)
    sigma = max(1.0, min(raw.shape[:2]) / 8)
    background = cv2.GaussianBlur(raw, (0, 0), sigmaX=sigma, sigmaY=sigma)
    contrast = cv2.absdiff(raw, background)
    if int(contrast.max()) > 0:
        contrast = cv2.normalize(contrast, None, 0, 255, cv2.NORM_MINMAX)

    # 局所コントラストを75%、元画像を25%の重みで比較する。
    # これにより赤い最終手ハイライトなどの背景色変化を抑えつつ、
    # 空マスのような低コントラストテンプレートも識別できる。
    return np.vstack((contrast, contrast, contrast, raw))
