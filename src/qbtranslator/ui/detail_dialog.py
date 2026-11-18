"""Translation detail dialog used by history."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from qbtranslator.i18n import t


class TranslationDetailDialog(QDialog):
    def __init__(self, parent, app, source_text: str, translation: str, meta: str) -> None:
        super().__init__(parent)
        self.app = app
        self.translation = translation
        self.setWindowTitle(t("history.detail_title"))
        self.setModal(True)
        self.resize(680, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        meta_label = QLabel(meta)
        meta_label.setObjectName("Muted")
        layout.addWidget(meta_label)

        layout.addWidget(QLabel(t("common.source")))
        source = QTextBrowser()
        source.setPlainText(source_text)
        source.setMinimumHeight(100)
        layout.addWidget(source)

        layout.addWidget(QLabel(t("nav.translate")))
        result = QTextBrowser()
        result.setPlainText(translation)
        result.setMinimumHeight(140)
        layout.addWidget(result, 1)

        buttons = QHBoxLayout()
        copy = QPushButton(t("common.copy"))
        copy.clicked.connect(self._copy)
        buttons.addWidget(copy)
        speak = QPushButton(t("common.read"))
        speak.clicked.connect(self._speak)
        buttons.addWidget(speak)
        buttons.addStretch(1)
        close = QPushButton(t("common.close"))
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def _copy(self) -> None:
        self.app.copy_text(self.translation)

    def _speak(self) -> None:
        self.app.speak_text(self.translation)
