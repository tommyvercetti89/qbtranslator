"""
tray.py - Windows sistem tepsisi simgesi (yalnızca standart kütüphane / ctypes).

Özellikler:
  * Tepsi simgesi + araç ipucu
  * Sol tık / çift tık: ana pencereyi göster
  * Sağ tık menüsü: "QBTranslator'u Aç", "Çıkış"
  * Balon bildirimi (arka plana küçültüldüğünde)
  * İkinci örnek / --quit için gizli pencere mesajları

Tkinter ana döngüsüne dokunmaz; kendi gizli Win32 penceresi ve mesaj
döngüsü ayrı bir thread'de çalışır. Geri çağrımlar yalnızca kuyruğa
olay bırakır (thread-safe).
"""

from __future__ import annotations

import ctypes
import os
import sys
import threading
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_APP = 0x8000
WM_TRAY = WM_APP + 1
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_NULL = 0x0000
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_CONTEXTMENU = 0x007B

NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_INFO = 0x00000010
NIIF_INFO = 0x00000001

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_RETURNCMD = 0x0100
TPM_RIGHTBUTTON = 0x0002

IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
IDI_APPLICATION = 32512
IDC_ARROW = 32512

TRAY_CLASS_NAME = "QBTranslatorTrayWnd"
TRAY_WINDOW_TITLE = "QBTranslatorTray"
SHOW_MESSAGE_NAME = "QBTranslator_ShowWindow_1"
QUIT_MESSAGE_NAME = "QBTranslator_Quit_1"
TASKBAR_CREATED_NAME = "TaskbarCreated"

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_byte * 8),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", GUID),
        ("hBalloonIcon", wintypes.HICON),
    ]


# ---------------------------------------------------------------------------
# Win32 prototipleri
# ---------------------------------------------------------------------------
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wintypes.WORD
user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.DefWindowProcW.restype = LRESULT
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
user32.RegisterWindowMessageW.restype = wintypes.UINT
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.PostMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.PostMessageW.restype = wintypes.BOOL
user32.LoadImageW.argtypes = [
    wintypes.HINSTANCE,
    wintypes.LPCWSTR,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.LoadImageW.restype = wintypes.HANDLE
user32.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.LoadIconW.restype = wintypes.HICON
user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.LoadCursorW.restype = wintypes.HANDLE
user32.DestroyIcon.argtypes = [wintypes.HICON]
user32.DestroyIcon.restype = wintypes.BOOL
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.AppendMenuW.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_size_t,
    wintypes.LPCWSTR,
]
user32.AppendMenuW.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.LPVOID,
]
user32.TrackPopupMenu.restype = ctypes.c_int
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.DestroyMenu.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL
shell32.ExtractIconExW.argtypes = [
    wintypes.LPCWSTR,
    ctypes.c_int,
    ctypes.POINTER(wintypes.HICON),
    ctypes.POINTER(wintypes.HICON),
    wintypes.UINT,
]
shell32.ExtractIconExW.restype = wintypes.UINT

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE


# ---------------------------------------------------------------------------
# Global pencere sınıfı (tek sefer kayıt; callback ömrü güvenli)
# ---------------------------------------------------------------------------
_active_tray: "TrayIcon | None" = None
_class_registered = False


def _global_wndproc(hwnd, msg, wparam, lparam):
    tray = _active_tray
    if tray is not None:
        try:
            return tray._handle(hwnd, msg, wparam, lparam)
        except Exception:
            pass
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


_global_wndproc_ref = WNDPROC(_global_wndproc)


def _ensure_class() -> bool:
    global _class_registered
    if _class_registered:
        return True
    hinst = kernel32.GetModuleHandleW(None)
    wc = WNDCLASSW()
    wc.style = 0
    wc.lpfnWndProc = _global_wndproc_ref
    wc.cbClsExtra = 0
    wc.cbWndExtra = 0
    wc.hInstance = hinst
    wc.hIcon = None
    wc.hCursor = user32.LoadCursorW(None, IDC_ARROW)
    wc.hbrBackground = None
    wc.lpszMenuName = None
    wc.lpszClassName = TRAY_CLASS_NAME
    atom = user32.RegisterClassW(ctypes.byref(wc))
    if atom or ctypes.get_last_error() == 1410:  # ERROR_CLASS_ALREADY_EXISTS
        _class_registered = True
    return _class_registered


class TrayIcon:
    def __init__(
        self,
        tooltip: str = "QBTranslator",
        on_show=None,
        on_quit=None,
        icon_path: str | None = None,
        open_label: str = "QBTranslator'u Aç",
        quit_label: str = "Çıkış",
    ) -> None:
        self._tooltip = tooltip
        self._on_show = on_show or (lambda: None)
        self._on_quit = on_quit or (lambda: None)
        self._icon_path = icon_path
        self._open_label = open_label
        self._quit_label = quit_label
        self._thread: threading.Thread | None = None
        self._hwnd: int | None = None
        self._hicon = None
        self._nid: NOTIFYICONDATAW | None = None
        self._available = False
        self._ready = threading.Event()
        self._show_message = user32.RegisterWindowMessageW(SHOW_MESSAGE_NAME)
        self._quit_message = user32.RegisterWindowMessageW(QUIT_MESSAGE_NAME)
        self._taskbar_created = user32.RegisterWindowMessageW(TASKBAR_CREATED_NAME)

    # ------------------------------------------------------------------
    @property
    def available(self) -> bool:
        return self._available

    @property
    def hwnd(self) -> int | None:
        return self._hwnd

    # ------------------------------------------------------------------
    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return self._available
        if not _ensure_class():
            return False
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="QBTranslatorTray"
        )
        self._thread.start()
        self._ready.wait(timeout=4.0)
        return self._available

    def _run(self) -> None:
        global _active_tray
        try:
            hinst = kernel32.GetModuleHandleW(None)
            hwnd = user32.CreateWindowExW(
                0,
                TRAY_CLASS_NAME,
                TRAY_WINDOW_TITLE,
                0,
                0,
                0,
                0,
                0,
                None,
                None,
                hinst,
                None,
            )
            if not hwnd:
                return
            self._hwnd = hwnd
            _active_tray = self

            if not self._add_icon():
                return

            self._available = True
            self._ready.set()

            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            self._available = False
            self._ready.set()
            if _active_tray is self:
                _active_tray = None
            if self._nid is not None:
                try:
                    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
                except Exception:
                    pass
                self._nid = None
            if self._hicon:
                try:
                    user32.DestroyIcon(self._hicon)
                except Exception:
                    pass
                self._hicon = None
            if self._hwnd:
                try:
                    user32.DestroyWindow(self._hwnd)
                except Exception:
                    pass
                self._hwnd = None

    # ------------------------------------------------------------------
    def _load_icon(self):
        if getattr(sys, "frozen", False):
            large = wintypes.HICON()
            small = wintypes.HICON()
            try:
                count = shell32.ExtractIconExW(
                    sys.executable, 0, ctypes.byref(large), ctypes.byref(small), 1
                )
                if count:
                    handle = small.value or large.value
                    if handle:
                        return handle
            except Exception:
                pass

        path = self._icon_path
        if path and os.path.exists(path):
            handle = user32.LoadImageW(
                None, path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE
            )
            if handle:
                return handle

        return user32.LoadIconW(None, IDI_APPLICATION)

    def _add_icon(self) -> bool:
        hicon = self._load_icon()
        self._hicon = hicon
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self._hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = hicon
        nid.szTip = self._tooltip[:127]

        for _attempt in range(4):
            if shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
                self._nid = nid
                return True
            time.sleep(0.4)
        return False

    # ------------------------------------------------------------------
    def _handle(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY:
            event = int(lparam)
            if event in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                self._call(self._on_show)
            elif event in (WM_RBUTTONUP, WM_CONTEXTMENU):
                self._show_menu()
            return 0
        if msg == self._show_message:
            self._call(self._on_show)
            return 0
        if msg == self._quit_message:
            self._call(self._on_quit)
            return 0
        if msg == self._taskbar_created:
            # Explorer yeniden başladığında tepsi simgesini geri koy.
            self._readd_icon()
            return 0
        if msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _readd_icon(self) -> None:
        if self._nid is None:
            if not self._add_icon():
                return
        else:
            self._nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
            try:
                shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._nid))
            except Exception:
                return
        self._available = True

    def _show_menu(self) -> None:
        hwnd = self._hwnd
        if not hwnd:
            return
        menu = user32.CreatePopupMenu()
        if not menu:
            return
        user32.AppendMenuW(menu, MF_STRING, 1, self._open_label)
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING, 2, self._quit_label)

        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(hwnd)
        command = user32.TrackPopupMenu(
            menu,
            TPM_RETURNCMD | TPM_RIGHTBUTTON,
            pt.x,
            pt.y,
            0,
            hwnd,
            None,
        )
        user32.PostMessageW(hwnd, WM_NULL, 0, 0)
        user32.DestroyMenu(menu)

        if command == 1:
            self._call(self._on_show)
        elif command == 2:
            self._call(self._on_quit)

    @staticmethod
    def _call(callback) -> None:
        try:
            callback()
        except Exception:
            pass

    def show_balloon(self, title: str, text: str) -> None:
        if not self._available or self._nid is None:
            return
        nid = self._nid
        nid.uFlags = NIF_INFO
        nid.szInfo = text[:255]
        nid.szInfoTitle = title[:63]
        nid.dwInfoFlags = NIIF_INFO
        try:
            shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))
        except Exception:
            pass

    def stop(self) -> None:
        hwnd = self._hwnd
        if hwnd:
            try:
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            except Exception:
                pass
        thread = self._thread
        if thread:
            thread.join(timeout=3.0)
        self._thread = None
        self._available = False


# ---------------------------------------------------------------------------
# İkinci örnek / --quit iletişimi
# ---------------------------------------------------------------------------
def _post_to_tray(message_name: str) -> bool:
    try:
        hwnd = user32.FindWindowW(TRAY_CLASS_NAME, None)
        if not hwnd:
            return False
        message = user32.RegisterWindowMessageW(message_name)
        return bool(user32.PostMessageW(hwnd, message, 0, 0))
    except Exception:
        return False


def notify_existing_instance() -> bool:
    """Çalışan gizli QBTranslator penceresini göstermesini ister."""
    return _post_to_tray(SHOW_MESSAGE_NAME)


def notify_existing_quit() -> bool:
    """Çalışan QBTranslator'a düzgün kapanma isteği gönderir."""
    return _post_to_tray(QUIT_MESSAGE_NAME)
