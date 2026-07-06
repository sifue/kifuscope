"""棋桜画面のテンプレート認識。"""

from .board_recognizer import RecognitionResult, ScreenRecognizer
from .calibration import Calibration, HandSlot, Rect
from .capture import load_image
from .template_builder import build_templates
from .templates import TemplateLibrary

__all__ = [
    "Calibration",
    "HandSlot",
    "RecognitionResult",
    "Rect",
    "ScreenRecognizer",
    "TemplateLibrary",
    "build_templates",
    "load_image",
]
