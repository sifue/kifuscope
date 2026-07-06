"""画面内の認識領域設定。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class Rect:
    """左上原点のピクセル矩形。"""

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0 or self.width < 1 or self.height < 1:
            raise ValueError("認識領域の座標とサイズが不正です")

    def crop(self, image: np.ndarray) -> np.ndarray:
        """画像境界を検証して矩形を切り出す。"""
        image_height, image_width = image.shape[:2]
        if self.x + self.width > image_width or self.y + self.height > image_height:
            raise ValueError(
                f"認識領域が画像範囲外です: rect={self}, image={image_width}x{image_height}"
            )
        return image[self.y : self.y + self.height, self.x : self.x + self.width]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Rect:
        return cls(*(int(value[key]) for key in ("x", "y", "width", "height")))


@dataclass(frozen=True, slots=True)
class HandSlot:
    """持ち駒の枚数表示領域。pieceは先手表記の駒種を使う。"""

    side: str
    piece: str
    rect: Rect

    def __post_init__(self) -> None:
        if self.side not in {"black", "white"}:
            raise ValueError("持ち駒のsideはblackまたはwhiteで指定してください")
        if self.piece not in set("RBGSNLP"):
            raise ValueError("持ち駒のpieceが不正です")


@dataclass(frozen=True, slots=True)
class Calibration:
    """1つの画面レイアウトに対応するキャリブレーション。"""

    board: Rect
    hand_slots: tuple[HandSlot, ...] = field(default_factory=tuple)
    turn: Rect | None = None
    rotate_board_180: bool = False
    board_threshold: float = 0.78
    hand_threshold: float = 0.78
    turn_threshold: float = 0.78
    stable_frames: int = 3
    legal_match_threshold: float = 0.90
    legal_margin: float = 0.02

    def __post_init__(self) -> None:
        for value in (
            self.board_threshold,
            self.hand_threshold,
            self.turn_threshold,
            self.legal_match_threshold,
        ):
            if not 0 <= value <= 1:
                raise ValueError("信頼度の閾値は0から1で指定してください")
        if self.stable_frames < 1:
            raise ValueError("stable_framesは1以上で指定してください")

    @classmethod
    def from_file(cls, path: Path) -> Calibration:
        """JSONファイルから読み込む。"""
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"キャリブレーションを読み込めません: {path}: {exc}") from exc
        slots = tuple(
            HandSlot(item["side"], item["piece"], Rect.from_dict(item["rect"]))
            for item in payload.get("hand_slots", [])
        )
        turn = Rect.from_dict(payload["turn"]) if payload.get("turn") else None
        return cls(
            board=Rect.from_dict(payload["board"]),
            hand_slots=slots,
            turn=turn,
            rotate_board_180=bool(payload.get("rotate_board_180", False)),
            board_threshold=float(payload.get("board_threshold", 0.78)),
            hand_threshold=float(payload.get("hand_threshold", 0.78)),
            turn_threshold=float(payload.get("turn_threshold", 0.78)),
            stable_frames=int(payload.get("stable_frames", 3)),
            legal_match_threshold=float(payload.get("legal_match_threshold", 0.90)),
            legal_margin=float(payload.get("legal_margin", 0.02)),
        )
