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
class TextLineRegion:
    """横書きテキストの文字単位認識領域。"""

    first_char_center_x: int
    first_char_center_y: int
    char_width: int
    char_height: int
    char_step_x: int
    max_chars: int

    def __post_init__(self) -> None:
        if (
            self.first_char_center_x < 0
            or self.first_char_center_y < 0
            or self.char_width < 1
            or self.char_height < 1
            or self.char_step_x < 1
            or self.max_chars < 1
        ):
            raise ValueError("テキスト認識領域の座標とサイズが不正です")

    def char_rect(self, index: int) -> Rect:
        """index番目の文字矩形を返す。"""
        if index < 0 or index >= self.max_chars:
            raise ValueError("文字indexが範囲外です")
        center_x = self.first_char_center_x + self.char_step_x * index
        return Rect(
            round(center_x - self.char_width / 2),
            round(self.first_char_center_y - self.char_height / 2),
            self.char_width,
            self.char_height,
        )

    def rect(self, count: int | None = None) -> Rect:
        """先頭からcount文字分を含む矩形を返す。"""
        actual_count = self.max_chars if count is None else count
        if actual_count < 1 or actual_count > self.max_chars:
            raise ValueError("文字数が範囲外です")
        first = self.char_rect(0)
        last = self.char_rect(actual_count - 1)
        return Rect(
            first.x,
            first.y,
            last.x + last.width - first.x,
            max(first.height, last.height),
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> TextLineRegion:
        return cls(
            first_char_center_x=int(value["first_char_center_x"]),
            first_char_center_y=int(value["first_char_center_y"]),
            char_width=int(value["char_width"]),
            char_height=int(value["char_height"]),
            char_step_x=int(value.get("char_step_x", value["char_width"])),
            max_chars=int(value["max_chars"]),
        )


@dataclass(frozen=True, slots=True)
class Calibration:
    """1つの画面レイアウトに対応するキャリブレーション。"""

    board: Rect
    hand_slots: tuple[HandSlot, ...] = field(default_factory=tuple)
    turn: Rect | None = None
    top_side_label: TextLineRegion | None = None
    move_number_label: TextLineRegion | None = None
    rotate_board_180: bool = False
    board_threshold: float = 0.78
    hand_threshold: float = 0.78
    turn_threshold: float = 0.78
    side_label_threshold: float = 0.78
    move_number_threshold: float = 0.78
    move_number_offset: int = 0
    stable_frames: int = 3
    legal_match_threshold: float = 0.90
    legal_margin: float = 0.02

    def __post_init__(self) -> None:
        for value in (
            self.board_threshold,
            self.hand_threshold,
            self.turn_threshold,
            self.side_label_threshold,
            self.move_number_threshold,
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
        top_side_label = (
            TextLineRegion.from_dict(payload["top_side_label"])
            if payload.get("top_side_label")
            else None
        )
        move_number_label = (
            TextLineRegion.from_dict(payload["move_number_label"])
            if payload.get("move_number_label")
            else None
        )
        return cls(
            board=Rect.from_dict(payload["board"]),
            hand_slots=slots,
            turn=turn,
            top_side_label=top_side_label,
            move_number_label=move_number_label,
            rotate_board_180=bool(payload.get("rotate_board_180", False)),
            board_threshold=float(payload.get("board_threshold", 0.78)),
            hand_threshold=float(payload.get("hand_threshold", 0.78)),
            turn_threshold=float(payload.get("turn_threshold", 0.78)),
            side_label_threshold=float(payload.get("side_label_threshold", 0.78)),
            move_number_threshold=float(payload.get("move_number_threshold", 0.78)),
            move_number_offset=int(payload.get("move_number_offset", 0)),
            stable_frames=int(payload.get("stable_frames", 3)),
            legal_match_threshold=float(payload.get("legal_match_threshold", 0.90)),
            legal_margin=float(payload.get("legal_margin", 0.02)),
        )
