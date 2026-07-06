"""静止画像とスクリーンキャプチャの入力。"""

from __future__ import annotations

import ctypes
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import cv2
import mss
import numpy as np


@dataclass(frozen=True, slots=True)
class WindowCaptureResult:
    """ウィンドウキャプチャ結果。"""

    image: np.ndarray
    title: str
    left: int
    top: int
    width: int
    height: int


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


def capture_window(title: str = "KIOU", *, exact: bool = True) -> WindowCaptureResult:
    """Windowsのウィンドウタイトルから1フレーム取得する。

    OBSの映像をPythonへ戻すのではなく、棋桜ウィンドウを直接キャプチャするための入口。
    ウィンドウが最小化されている場合や、他ウィンドウに完全に隠れている場合は安定しない。
    """
    if sys.platform != "win32":
        raise ValueError("ウィンドウ名指定キャプチャはWindowsでのみ利用できます")
    window = _find_windows_window(title, exact=exact)
    monitor = {
        "left": window.left,
        "top": window.top,
        "width": window.width,
        "height": window.height,
    }
    with mss.mss() as screen:
        frame = np.asarray(screen.grab(monitor))
    return WindowCaptureResult(
        image=cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR),
        title=window.title,
        left=window.left,
        top=window.top,
        width=window.width,
        height=window.height,
    )


@dataclass(frozen=True, slots=True)
class _WindowsWindow:
    title: str
    left: int
    top: int
    width: int
    height: int


def _find_windows_window(title: str, *, exact: bool) -> _WindowsWindow:
    """Windows APIで表示中のウィンドウを検索する。"""
    user32 = ctypes.windll.user32
    with suppress(OSError):
        user32.SetProcessDPIAware()

    windows: list[_WindowsWindow] = []

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd: int, _: int) -> bool:
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        window_title = buffer.value
        matched = window_title == title if exact else title in window_title
        if not matched:
            return True
        rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True
        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)
        if width < 1 or height < 1:
            return True
        windows.append(_WindowsWindow(window_title, int(rect.left), int(rect.top), width, height))
        return True

    user32.EnumWindows(enum_proc(callback), 0)
    if not windows:
        mode = "完全一致" if exact else "部分一致"
        raise ValueError(f"タイトルが「{title}」に{mode}する表示中ウィンドウが見つかりません")
    return max(windows, key=lambda item: item.width * item.height)
