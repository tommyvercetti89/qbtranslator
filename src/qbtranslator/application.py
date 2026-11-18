"""QBTranslator uygulama giriş noktası."""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from qbtranslator.core.appinfo import APP_VERSION
from qbtranslator.core.applog import setup_logging
from qbtranslator.core.paths import ASSETS_DIR, DATA_DIR
from qbtranslator.ui.main_window import MainWindow
from qbtranslator.ui.theme import QSS


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("QBTranslator")
    app.setOrganizationName("QBTranslator")
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(QSS)
    app.setQuitOnLastWindowClosed(False)

    icon_path = ASSETS_DIR / "QBTranslator.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    return app


def main(argv: list[str] | None = None) -> int:
    arguments = argv if argv is not None else sys.argv
    setup_logging(DATA_DIR)
    app = create_application(arguments)
    window = MainWindow()
    window.show()

    if "--smoke" in arguments[1:]:
        QTimer.singleShot(1800, window._quit_app)
    if "--smoke-translate" in arguments[1:]:
        QTimer.singleShot(800, window._smoke_translate)
    return app.exec()
