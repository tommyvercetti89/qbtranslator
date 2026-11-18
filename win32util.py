"""
win32util.py — Windows API köprüsü (yalnızca standart kütüphane / ctypes).

Sağladıkları:
  * Global kısayol (RegisterHotKey + mesaj döngüsü)
  * Pano okuma / yazma (CF_UNICODETEXT)
  * Pano değişim izleyicisi (GetClipboardSequenceNumber)
  * İmleç konumu
  * Ctrl+C simülasyonu (seçili metni kopyalamak için)
  * Seçim yakalama yardımcısı
"""

from __future__ import annotations

import ctypes
import re
import threading
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

# --------------------------------------------------------------------------
# Sabitler
# --------------------------------------------------------------------------
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

VK_CONTROL = 0x11
VK_MENU = 0x12
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_C = 0x43

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


# --------------------------------------------------------------------------
# Yapılar
# --------------------------------------------------------------------------
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


# --------------------------------------------------------------------------
# API imzaları
# --------------------------------------------------------------------------
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardSequenceNumber.restype = wintypes.DWORD

kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HANDLE
kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalFree.argtypes = [wintypes.HANDLE]
kernel32.GlobalFree.restype = wintypes.HANDLE

user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wintypes.UINT

user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ULONG_PTR]
user32.keybd_event.restype = None

user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short

user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL

user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL]
user32.SetWindowRgn.restype = ctypes.c_int
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int

gdi32.CreateRectRgn.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
gdi32.CreateRectRgn.restype = wintypes.HANDLE
gdi32.CombineRgn.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE, ctypes.c_int]
gdi32.CombineRgn.restype = ctypes.c_int
gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
gdi32.DeleteObject.restype = wintypes.BOOL

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

RGN_DIFF = 4
GA_ROOT = 2


# --------------------------------------------------------------------------
# İmleç
# --------------------------------------------------------------------------
def get_cursor_pos() -> tuple[int, int]:
    pt = POINT()
    if not user32.GetCursorPos(ctypes.byref(pt)):
        return (0, 0)
    return (int(pt.x), int(pt.y))


def get_virtual_screen() -> tuple[int, int, int, int]:
    """Tüm monitörleri kapsayan sanal ekran: (x, y, genişlik, yükseklik)."""
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79
    x = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    y = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    width = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    height = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
    if width <= 0 or height <= 0:
        width = int(user32.GetSystemMetrics(0))
        height = int(user32.GetSystemMetrics(1))
        x, y = 0, 0
    return x, y, width, height


# --------------------------------------------------------------------------
# Pano
# --------------------------------------------------------------------------
def _open_clipboard(retries: int = 6, delay: float = 0.02) -> bool:
    for _ in range(retries):
        if user32.OpenClipboard(None):
            return True
        time.sleep(delay)
    return False


def get_clipboard_text() -> str:
    """Panodaki metni döndürür; metin yoksa boş string."""
    if not _open_clipboard():
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr) or ""
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def set_clipboard_text(text: str) -> bool:
    """Panoya Unicode metin yazar."""
    data = ctypes.create_unicode_buffer(text or "")
    size = ctypes.sizeof(data)
    if not _open_clipboard():
        return False
    try:
        if not user32.EmptyClipboard():
            return False
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not handle:
            return False
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            kernel32.GlobalFree(handle)
            return False
        ctypes.memmove(ptr, data, size)
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            kernel32.GlobalFree(handle)
            return False
        return True
    finally:
        user32.CloseClipboard()


def get_clipboard_sequence() -> int:
    return int(user32.GetClipboardSequenceNumber())


# --------------------------------------------------------------------------
# Klavye simülasyonu
# --------------------------------------------------------------------------
def _key_event(vk: int, flags: int = 0) -> INPUT:
    return INPUT(
        type=INPUT_KEYBOARD,
        u=_INPUTUNION(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, time=0, dwExtraInfo=0)),
    )


def send_ctrl_c() -> bool:
    """Etkin pencereye Ctrl+C gönderir. Başarılıysa True döner."""
    events = (INPUT * 4)(
        _key_event(VK_CONTROL),
        _key_event(VK_C),
        _key_event(VK_C, KEYEVENTF_KEYUP),
        _key_event(VK_CONTROL, KEYEVENTF_KEYUP),
    )
    if user32.SendInput(4, events, ctypes.sizeof(INPUT)) == 4:
        return True
    # Yedek yol: bazı ortamlarda SendInput engellenebilir; eski API'ye düş.
    try:
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_C, 0, 0, 0)
        user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        return True
    except Exception:
        return False


def _is_pressed(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def get_modifier_flags() -> tuple[bool, bool, bool]:
    """Anlık Ctrl / Alt / Shift durumu: (ctrl, alt, shift)."""
    return (_is_pressed(VK_CONTROL), _is_pressed(VK_MENU), _is_pressed(VK_SHIFT))


def wait_modifiers_released(timeout: float = 1.2) -> bool:
    """Kısayol tuşları bırakılana kadar bekler (Ctrl+C'den önce gerekli)."""
    keys = (VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not any(_is_pressed(k) for k in keys):
            return True
        time.sleep(0.02)
    return False


def capture_selected_text(restore_clipboard: bool = True) -> str:
    """
    Etkin uygulamadaki seçimi Ctrl+C ile panoya kopyalar ve okur.

    Dönüş: seçilen metin (yakalanamazsa boş string). Hata fırlatmaz.
    """
    try:
        previous = get_clipboard_text()
        before_seq = get_clipboard_sequence()

        # Kısayol tuş kombinasyonu hâlâ basılıysa önce bırakılmasını bekle,
        # aksi halde Ctrl+C yerine AltGr/Ctrl+Alt kombinasyonları tetiklenebilir.
        wait_modifiers_released()
        time.sleep(0.08)

        send_ctrl_c()

        text = ""
        deadline = time.time() + 0.9
        while time.time() < deadline:
            time.sleep(0.04)
            if get_clipboard_sequence() != before_seq:
                text = get_clipboard_text()
                break

        if restore_clipboard and previous and text and text != previous:
            # Kullanıcı seçimi kopyalamak istemedi; eski panoyu geri koy.
            set_clipboard_text(previous)

        return (text or "").strip()
    except Exception:
        return ""


# --------------------------------------------------------------------------
# Global kısayol
# --------------------------------------------------------------------------
_MODIFIER_MAP = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "windows": MOD_WIN,
    "meta": MOD_WIN,
}

_SPECIAL_KEYS = {
    "space": 0x20,
    "esc": 0x1B,
    "escape": 0x1B,
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
    "backspace": 0x08,
    "delete": 0x2E,
    "insert": 0x2D,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
}


def parse_hotkey(spec: str) -> tuple[int, int]:
    """
    'ctrl+alt+t' formatındaki kısayolu (modifiers, vk) çiftine çevirir.
    Geçersizse ValueError fırlatır.
    """
    parts = [p for p in re.split(r"[+\s]+", (spec or "").strip().lower()) if p]
    if not parts:
        raise ValueError("Kısayol boş olamaz.")

    mods = 0
    vk = None
    for part in parts:
        if part in _MODIFIER_MAP:
            mods |= _MODIFIER_MAP[part]
        elif re.fullmatch(r"f([1-9]|1[0-2])", part):
            vk = 0x6F + int(part[1:])
        elif re.fullmatch(r"[a-z]", part):
            vk = ord(part.upper())
        elif re.fullmatch(r"[0-9]", part):
            vk = ord(part)
        elif part in _SPECIAL_KEYS:
            vk = _SPECIAL_KEYS[part]
        else:
            raise ValueError(f"Bilinmeyen tuş: {part}")

    if vk is None:
        raise ValueError("Kısayolda bir normal tuş olmalı (örn. ctrl+alt+t).")
    if mods == 0:
        raise ValueError("En az bir değiştirici tuş gerekli (Ctrl, Alt, Shift veya Win).")

    return mods | MOD_NOREPEAT, vk


class GlobalHotkey:
    """RegisterHotKey tabanlı global kısayol dinleyicisi (kendi thread'i ile)."""

    HOTKEY_ID = 1

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._stop = threading.Event()

    def start(self, spec: str, callback, on_error=None) -> None:
        self.stop()
        mods, vk = parse_hotkey(spec)
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(mods, vk, callback, on_error),
            daemon=True,
            name="GlobalHotkey",
        )
        self._thread.start()

    def _run(self, mods: int, vk: int, callback, on_error) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, self.HOTKEY_ID, mods, vk):
            error_code = ctypes.get_last_error()
            self._thread_id = None
            if on_error:
                try:
                    on_error(error_code)
                except Exception:
                    pass
            return
        try:
            msg = wintypes.MSG()
            while not self._stop.is_set():
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret in (0, -1):
                    break
                if msg.message == WM_HOTKEY and int(msg.wParam) == self.HOTKEY_ID:
                    try:
                        callback()
                    except Exception:
                        pass
        finally:
            user32.UnregisterHotKey(None, self.HOTKEY_ID)
            self._thread_id = None

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive() and self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=1.5)
        self._thread = None
        self._stop.clear()


# --------------------------------------------------------------------------
# Pano izleyici
# --------------------------------------------------------------------------
class ClipboardWatcher(threading.Thread):
    """Panodaki metin değişimlerini izleyen thread."""

    def __init__(self, callback, interval: float = 0.45) -> None:
        super().__init__(daemon=True, name="ClipboardWatcher")
        self._callback = callback
        self._interval = interval
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._last_seq = get_clipboard_sequence()

    def sync(self) -> None:
        """Mevcut pano durumunu 'görüldü' olarak işaretler (kendi yazdıklarımız için)."""
        with self._lock:
            self._last_seq = get_clipboard_sequence()

    def run(self) -> None:
        while not self._stop_event.is_set():
            self._stop_event.wait(self._interval)
            if self._stop_event.is_set():
                break
            try:
                with self._lock:
                    seq = get_clipboard_sequence()
                    if seq == self._last_seq:
                        continue
                    self._last_seq = seq
                text = get_clipboard_text().strip()
                if text:
                    self._callback(text)
            except Exception:
                continue

    def stop(self) -> None:
        self._stop_event.set()
        if self.is_alive():
            self.join(timeout=1.0)


# --------------------------------------------------------------------------
# Pencere / bölge yardımcıları (OCR katmanı ve tek örnek kontrolü için)
# --------------------------------------------------------------------------
def get_toplevel_hwnd(widget) -> int:
    """Tk widget'ının gerçek üst düzey pencere tutamacını (HWND) döndürür."""
    try:
        hwnd = int(widget.winfo_id())
    except Exception:
        return 0
    root = user32.GetAncestor(hwnd, GA_ROOT)
    return int(root or hwnd)


def set_window_region_hole(hwnd: int, hole: tuple[int, int, int, int] | None) -> bool:
    """
    Pencereye dikdörtgen bir 'delik' açar (dışarısı görünür kalır).
    OCR seçim katmanında dış alanı karartıp seçimi berrak göstermek için kullanılır.
    """
    if not hwnd:
        return False
    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    width = int(rect.right - rect.left)
    height = int(rect.bottom - rect.top)
    if width <= 0 or height <= 0:
        return False

    full = gdi32.CreateRectRgn(0, 0, width, height)
    if not full:
        return False

    if hole is not None:
        x, y, w, h = (int(value) for value in hole)
        x = max(0, min(width, x))
        y = max(0, min(height, y))
        w = max(0, min(width - x, w))
        h = max(0, min(height - y, h))
        if w > 0 and h > 0:
            hole_region = gdi32.CreateRectRgn(x, y, x + w, y + h)
            if hole_region:
                gdi32.CombineRgn(full, full, hole_region, RGN_DIFF)
                gdi32.DeleteObject(hole_region)

    if not user32.SetWindowRgn(hwnd, full, True):
        gdi32.DeleteObject(full)
        return False
    return True


def reset_window_region(hwnd: int) -> bool:
    return set_window_region_hole(hwnd, None)


def find_window_by_title(title: str) -> int:
    """Gizli/ikonik pencereler dahil başlıkla üst düzey pencere arar."""
    found: list[int] = []

    def callback(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if buffer.value == title:
                found.append(int(hwnd))
                return False
        return True

    try:
        user32.EnumWindows(WNDENUMPROC(callback), 0)
    except Exception:
        return 0
    return found[0] if found else 0


def activate_window_by_title(title: str) -> bool:
    """Aynı uygulamanın açık penceresini öne getirir (tek örnek kontrolü)."""
    hwnd = find_window_by_title(title)
    if not hwnd:
        return False
    SW_RESTORE = 9
    SW_SHOW = 5
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.ShowWindow(hwnd, SW_SHOW)
    user32.SetForegroundWindow(hwnd)
    return True


def close_window_by_title(title: str) -> bool:
    """Pencereye WM_CLOSE gönderir (uygulama kendi kapanış akışını çalıştırır)."""
    hwnd = find_window_by_title(title)
    if not hwnd:
        return False
    WM_CLOSE = 0x0010
    return bool(user32.PostMessageW(hwnd, WM_CLOSE, 0, 0))
