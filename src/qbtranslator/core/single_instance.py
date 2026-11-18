"""Windows named mutex based single instance control."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

ERROR_ALREADY_EXISTS = 183


class SingleInstance:
    def __init__(self, name: str) -> None:
        self._handle = kernel32.CreateMutexW(None, False, f"{name}_SingleInstance")
        self.already_running = (
            bool(self._handle) and ctypes.get_last_error() == ERROR_ALREADY_EXISTS
        )

    @property
    def handle(self):
        return self._handle

    def close(self) -> None:
        if self._handle:
            kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self) -> "SingleInstance":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
