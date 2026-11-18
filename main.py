"""
main.py — QBTranslator giriş noktası.

* Tek örnek: ikinci kez açılırsa mevcut pencere öne getirilir.
* --background: oturum açılışında/otomatik başlatmada simge durumunda başlar,
  kısayolları dinlemeye devam eder.

Çalıştırmak için:  python main.py   (veya baslat.bat)
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from appinfo import APP_NAME, APP_TITLE

_mutex_handle = None


def _enable_dpi_awareness() -> None:
    """Yüksek DPI ekranlarda keskin arayüz için Windows'a bildir."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _acquire_single_instance(background: bool) -> bool:
    """Aynı anda yalnızca bir QBTranslator çalışmasını sağlar."""
    global _mutex_handle
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE

    _mutex_handle = kernel32.CreateMutexW(None, False, f"{APP_NAME}_SingleInstance")
    if not _mutex_handle:
        return True

    ERROR_ALREADY_EXISTS = 183
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        shown = False
        try:
            from tray import notify_existing_instance

            shown = notify_existing_instance()
        except Exception:
            shown = False

        if not shown:
            try:
                from win32util import activate_window_by_title

                activate_window_by_title(APP_TITLE)
            except Exception:
                pass

        if not background and not shown:
            try:
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"{APP_NAME} zaten çalışıyor.\n"
                    "Pencere görev çubuğunda veya sistem tepsisinde olabilir.",
                    APP_NAME,
                    0x00000040,  # MB_ICONINFORMATION
                )
            except Exception:
                pass
        return False
    return True


def _run_selftest() -> int:
    """Paketli sürüm doğrulaması: Tk, modül importları ve çeviri."""
    lines: list[str] = []
    exit_code = 0

    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.update()
        root.destroy()
        lines.append("tk=OK")
    except Exception as error:
        lines.append(f"tk=FAIL {error}")
        exit_code = 1

    try:
        import autostart
        import hotkeydialog
        import langpicker
        import ocr
        import toggle
        import tray
        import tts

        lines.append("imports=OK")
    except Exception as error:
        lines.append(f"imports=FAIL {error}")
        exit_code = 1

    try:
        from translator import translate

        outcome = translate(
            "Merhaba dünya", "auto", "en", {"engine": "google", "backup_engines": False}
        )
        lines.append(f"translate=OK {outcome.text}")
    except Exception as error:
        lines.append(f"translate=FAIL {error}")

    try:
        from storage import DATA_DIR

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "selftest_result.txt").write_text(
            "\n".join(lines), encoding="utf-8"
        )
    except Exception:
        pass
    return exit_code


def main() -> int:
    if not sys.platform.startswith("win"):
        print("Bu uygulama Windows içindir (Win32 kısayol/pano/OCR API'leri kullanır).")
        return 1

    if "--selftest" in sys.argv[1:]:
        return _run_selftest()

    if "--quit" in sys.argv[1:]:
        try:
            from tray import notify_existing_quit

            if notify_existing_quit():
                return 0
        except Exception:
            pass
        try:
            from win32util import close_window_by_title

            close_window_by_title(APP_TITLE)
        except Exception:
            pass
        return 0

    background = any(arg in ("--background", "--minimized") for arg in sys.argv[1:])

    if not _acquire_single_instance(background):
        return 0

    _enable_dpi_awareness()

    from mainwindow import TranslatorApp

    app = TranslatorApp(start_minimized=background)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
