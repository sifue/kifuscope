"""棋桜画面のテンプレート認識。"""

from .board_recognizer import RecognitionResult, ScreenRecognizer
from .calibration import Calibration, HandSlot, Rect
from .capture import WindowCaptureResult, capture_screen, capture_window, load_image
from .template_builder import build_templates
from .templates import TemplateLibrary

__all__ = [
    "Calibration",
    "HandSlot",
    "RecognitionResult",
    "Rect",
    "ScreenRecognizer",
    "TemplateLibrary",
    "WindowCaptureResult",
    "build_templates",
    "capture_screen",
    "capture_window",
    "load_image",
]
