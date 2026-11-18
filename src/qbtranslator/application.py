"""QBTranslator uygulama giriş noktası."""

from __future__ import annotations

import ctypes
import json
import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from qbtranslator import i18n
from qbtranslator.core.appinfo import APP_NAME, APP_TITLE, APP_VERSION
from qbtranslator.core.applog import setup_logging
from qbtranslator.core.paths import ASSETS_DIR, DATA_DIR
from qbtranslator.core.single_instance import SingleInstance
from qbtranslator.ui.main_window import MainWindow
from qbtranslator.ui.theme import QSS


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(QSS)
    app.setQuitOnLastWindowClosed(False)

    icon_path = ASSETS_DIR / "QBTranslator.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    return app


def _message_box(text: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(0, text, APP_NAME, 0x00000040)
    except Exception:
        pass


def _notify_existing(background: bool) -> None:
    if background:
        return
    shown = False
    try:
        from qbtranslator.core.tray import notify_existing_instance

        shown = notify_existing_instance()
    except Exception:
        shown = False
    if not shown:
        try:
            from qbtranslator.core.win32util import activate_window_by_title

            activate_window_by_title(APP_TITLE)
        except Exception:
            pass
    if not shown:
        _message_box(i18n.t("app.already_running", name=APP_NAME))


def _quit_existing() -> int:
    try:
        from qbtranslator.core.tray import notify_existing_quit

        if notify_existing_quit():
            return 0
    except Exception:
        pass
    try:
        from qbtranslator.core.win32util import close_window_by_title

        close_window_by_title(APP_TITLE)
    except Exception:
        pass
    return 0


def _run_selftest() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    lines: list[str] = []
    exit_code = 0

    try:
        app = create_application([sys.argv[0], "-platform", "offscreen"])
        app.processEvents()
        lines.append("qt=OK")
    except Exception as error:
        lines.append(f"qt=FAIL {error}")
        exit_code = 1

    try:
        import qbtranslator.core.autostart  # noqa: F401
        import qbtranslator.core.ocr  # noqa: F401
        import qbtranslator.core.tray  # noqa: F401
        import qbtranslator.core.tts  # noqa: F401
        import qbtranslator.ui.main_window  # noqa: F401
        import qbtranslator.ui.popup  # noqa: F401

        lines.append("imports=OK")
    except Exception as error:
        lines.append(f"imports=FAIL {error}")
        exit_code = 1

    try:
        import qbtranslator.core.translator as translator_module

        original_get = translator_module._http_get_google

        def fake_google_get(_url: str, timeout: int = 10) -> str:
            return json.dumps({"sentences": [{"trans": "Hello world"}], "src": "tr"})

        translator_module._http_get_google = fake_google_get
        try:
            outcome = translator_module.translate(
                "Merhaba dünya",
                "auto",
                "en",
                {"engine": "google", "backup_engines": False},
            )
        finally:
            translator_module._http_get_google = original_get
        lines.append(f"translate=OK {outcome.text}")
    except Exception as error:
        lines.append(f"translate=FAIL {error}")
        exit_code = 1

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "selftest_result.txt").write_text(
            "\n".join(lines), encoding="utf-8"
        )
    except Exception:
        pass
    return exit_code


def main(argv: list[str] | None = None) -> int:
    arguments = list(argv if argv is not None else sys.argv)
    flags = set(arguments[1:])
    setup_logging(DATA_DIR)
    i18n.set_language(i18n.resolve_language("system"))

    if "--quit" in flags:
        return _quit_existing()
    if "--selftest" in flags:
        return _run_selftest()

    background = bool(flags & {"--background", "--minimized"})
    instance = SingleInstance(APP_NAME)
    if instance.already_running:
        _notify_existing(background)
        return 0

    app = create_application(arguments)
    window = MainWindow()
    if background:
        window.start_in_background()
    else:
        window.show()

    if "--smoke" in flags:
        QTimer.singleShot(1800, window._quit_app)
    if "--smoke-translate" in flags:
        QTimer.singleShot(800, window._smoke_translate)
    return app.exec()
