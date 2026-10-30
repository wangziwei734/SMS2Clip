"""Windows clipboard helpers."""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from typing import Callable


CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


def _windows_clipboard_set_text(text: str) -> None:
    if sys.platform != "win32":
        raise OSError("Clipboard writing is only implemented for Windows")

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.CloseClipboard.restype = wintypes.BOOL
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL

    if not user32.OpenClipboard(None):
        raise OSError("Could not open the Windows clipboard")

    handle = None
    try:
        if not user32.EmptyClipboard():
            raise OSError("Could not empty the Windows clipboard")

        data = (text + "\0").encode("utf-16-le")
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not handle:
            raise OSError("Could not allocate clipboard memory")

        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            raise OSError("Could not lock clipboard memory")
        try:
            ctypes.memmove(pointer, data, len(data))
        finally:
            kernel32.GlobalUnlock(handle)

        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            raise OSError("Could not set the Windows clipboard")
        handle = None
    finally:
        user32.CloseClipboard()
        if handle:
            kernel32.GlobalFree(handle)


def set_clipboard_text(text: str) -> None:
    """Set clipboard text, retrying briefly when another app owns the clipboard."""

    last_error: OSError | None = None
    for _ in range(10):
        try:
            _windows_clipboard_set_text(text)
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.05)
    raise last_error or OSError("Could not set the Windows clipboard")


class ClipboardWriter:
    """Write the full SMS and then the extracted code to the clipboard."""

    def __init__(
        self,
        set_text: Callable[[str], None] = set_clipboard_text,
        sleep: Callable[[float], None] = time.sleep,
        gap_seconds: float = 0.35,
    ) -> None:
        self._set_text = set_text
        self._sleep = sleep
        self._gap_seconds = gap_seconds

    def copy_full_then_code(self, full_text: str, code: str | None) -> None:
        self._set_text(full_text)
        if code:
            self._sleep(self._gap_seconds)
            self._set_text(code)
