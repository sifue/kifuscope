"""棋桜画面のテンプレート認識。"""

from .board_recognizer import RecognitionResult, ScreenRecognizer
from .calibration import Calibration, HandSlot, Rect, TextLineRegion
from .capture import WindowCaptureResult, capture_screen, capture_window, load_image
from .template_builder import build_templates, build_ui_templates
from .templates import TemplateLibrary

__all__ = [
    "Calibration",
    "HandSlot",
    "RecognitionResult",
    "Rect",
    "ScreenRecognizer",
    "TemplateLibrary",
    "TextLineRegion",
    "WindowCaptureResult",
    "build_templates",
    "build_ui_templates",
    "capture_screen",
    "capture_window",
    "load_image",
]
