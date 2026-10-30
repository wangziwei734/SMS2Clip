"""Single-instance guard for the Windows manager window."""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from ctypes import wintypes
from typing import Callable

MUTEX_NAME = r"Local\SMS2Clip.Manager"
EVENT_NAME = r"Local\SMS2Clip.Manager.Activate"
ERROR_ALREADY_EXISTS = 183
EVENT_MODIFY_STATE = 0x0002
WAIT_OBJECT_0 = 0


class ManagerInstance:
    def __init__(
        self,
        mutex_name: str = MUTEX_NAME,
        event_name: str = EVENT_NAME,
    ) -> None:
        self.already_running = False
        self._event_name = event_name
        self._kernel32 = None
        self._mutex = None
        self._event = None
        self._thread: threading.Thread | None = None
        self._stopping = threading.Event()
        if sys.platform != "win32":
            return

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [
            ctypes.c_void_p,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateEventW.argtypes = [
            ctypes.c_void_p,
            wintypes.BOOL,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        kernel32.CreateEventW.restype = wintypes.HANDLE
        kernel32.OpenEventW.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        kernel32.OpenEventW.restype = wintypes.HANDLE
        kernel32.SetEvent.argtypes = [wintypes.HANDLE]
        kernel32.SetEvent.restype = wintypes.BOOL
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        self._kernel32 = kernel32

        ctypes.set_last_error(0)
        mutex = kernel32.CreateMutexW(None, False, mutex_name)
        error = ctypes.get_last_error()
        if not mutex:
            raise ctypes.WinError(error)
        self._mutex = mutex
        self.already_running = error == ERROR_ALREADY_EXISTS

        if not self.already_running:
            event = kernel32.CreateEventW(None, False, False, event_name)
            if not event:
                error = ctypes.get_last_error()
                self.close()
                raise ctypes.WinError(error)
            self._event = event

    def signal_existing(self) -> bool:
        if self._kernel32 is None:
            return False
        for _ in range(20):
            event = self._kernel32.OpenEventW(
                EVENT_MODIFY_STATE, False, self._event_name
            )
            if event:
                try:
                    return bool(self._kernel32.SetEvent(event))
                finally:
                    self._kernel32.CloseHandle(event)
            time.sleep(0.05)
        return False

    def wait_for_activation(self, callback: Callable[[], None]) -> None:
        if self._event is None or self._thread is not None:
            return

        def worker() -> None:
            while not self._stopping.is_set():
                result = self._kernel32.WaitForSingleObject(self._event, 250)
                if result == WAIT_OBJECT_0 and not self._stopping.is_set():
                    callback()

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stopping.set()
        if self._event is not None and self._kernel32 is not None:
            try:
                self._kernel32.SetEvent(self._event)
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=0.5)
            self._thread = None
        if self._event is not None and self._kernel32 is not None:
            self._kernel32.CloseHandle(self._event)
            self._event = None
        if self._mutex is not None and self._kernel32 is not None:
            self._kernel32.CloseHandle(self._mutex)
            self._mutex = None
