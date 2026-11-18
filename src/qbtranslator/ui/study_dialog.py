"""Saved word card study dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from qbtranslator.i18n import t


class StudyDialog(QDialog):
    def __init__(self, parent, app, words: list[dict]) -> None:
        super().__init__(parent)
        self.app = app
        self.words = words
        self.index = 0
        self.revealed = False
        self.setWindowTitle(t("words.study_title"))
        self.setModal(True)
        self.resize(560, 380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(8)

        self.counter = QLabel("")
        self.counter.setObjectName("Muted")
        self.counter.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.counter)

        self.word = QLabel("")
        self.word.setObjectName("PageTitle")
        self.word.setAlignment(Qt.AlignCenter)
        self.word.setWordWrap(True)
        layout.addWidget(self.word, 1)

        self.translation = QLabel("")
        self.translation.setObjectName("SectionTitle")
        self.translation.setAlignment(Qt.AlignCenter)
        self.translation.setWordWrap(True)
        layout.addWidget(self.translation, 1)

        self.hint = QLabel(t("words.study_hint"))
        self.hint.setObjectName("Tiny")
        self.hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.hint)

        buttons = QHBoxLayout()
        previous = QPushButton(t("words.study_previous"))
        previous.clicked.connect(self._previous)
        buttons.addWidget(previous)
        self.reveal_button = QPushButton(t("words.study_reveal"))
        self.reveal_button.clicked.connect(self._reveal)
        buttons.addWidget(self.reveal_button)
        next_button = QPushButton(t("words.study_next"))
        next_button.clicked.connect(self._next)
        buttons.addWidget(next_button)
        speak = QPushButton(t("words.study_speak"))
        speak.clicked.connect(self._speak)
        buttons.addWidget(speak)
        close = QPushButton(t("words.study_close"))
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)

        self._refresh()

    def _current(self) -> dict | None:
        return self.words[self.index] if self.words else None

    def _refresh(self) -> None:
        record = self._current()
        if not record:
            self.counter.setText("")
            self.word.setText(t("words.study_empty"))
            self.translation.setText("")
            self.reveal_button.setEnabled(False)
            return
        self.reveal_button.setEnabled(True)
        self.counter.setText(
            t(
                "words.study_counter",
                index=self.index + 1,
                count=len(self.words),
                source=record.get("source_lang", ""),
                target=record.get("target_lang", ""),
            )
        )
        self.word.setText(record.get("word", ""))
        self.translation.setText(
            record.get("translation", "") if self.revealed else "• • • • • •"
        )

    def _reveal(self) -> None:
        self.revealed = not self.revealed
        self._refresh()

    def _next(self) -> None:
        if not self.words:
            return
        self.index = (self.index + 1) % len(self.words)
        self.revealed = False
        self._refresh()

    def _previous(self) -> None:
        if not self.words:
            return
        self.index = (self.index - 1) % len(self.words)
        self.revealed = False
        self._refresh()

    def _speak(self) -> None:
        record = self._current()
        if record:
            self.app.speak_text(record.get("translation", ""))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Space:
            self._reveal()
            return
        if event.key() == Qt.Key_Right:
            self._next()
            return
        if event.key() == Qt.Key_Left:
            self._previous()
            return
        if event.key() == Qt.Key_Escape:
            self.accept()
            return
        super().keyPressEvent(event)
