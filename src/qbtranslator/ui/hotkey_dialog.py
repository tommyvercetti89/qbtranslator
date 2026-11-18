"""Global shortcut capture dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from qbtranslator.core.win32util import parse_hotkey
from qbtranslator.i18n import t

_SPECIAL_KEYS = {
    Qt.Key_Space: "space",
    Qt.Key_Tab: "tab",
    Qt.Key_Return: "enter",
    Qt.Key_Enter: "enter",
    Qt.Key_Backspace: "backspace",
    Qt.Key_Delete: "delete",
    Qt.Key_Insert: "insert",
    Qt.Key_Home: "home",
    Qt.Key_End: "end",
    Qt.Key_PageUp: "pageup",
    Qt.Key_PageDown: "pagedown",
    Qt.Key_Left: "left",
    Qt.Key_Up: "up",
    Qt.Key_Right: "right",
    Qt.Key_Down: "down",
}


def key_to_token(key: int) -> str | None:
    if Qt.Key_A <= key <= Qt.Key_Z:
        return chr(key).lower()
    if Qt.Key_0 <= key <= Qt.Key_9:
        return chr(key)
    if Qt.Key_F1 <= key <= Qt.Key_F12:
        return f"f{key - Qt.Key_F1 + 1}"
    return _SPECIAL_KEYS.get(key)


class HotkeyCaptureDialog(QDialog):
    def __init__(self, parent, initial: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(t("hotkey.title"))
        self.setModal(True)
        self.setMinimumWidth(460)
        self._spec = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

        title = QLabel(t("hotkey.instruction"))
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self.value = QLineEdit()
        self.value.setReadOnly(True)
        self.value.setPlaceholderText(t("hotkey.placeholder"))
        self.value.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value)

        self.status = QLabel("")
        self.status.setObjectName("Status")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        note = QLabel(t("hotkey.note"))
        note.setObjectName("Muted")
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QHBoxLayout()
        self.clear_button = QPushButton(t("common.clear"))
        self.clear_button.clicked.connect(self._clear)
        buttons.addWidget(self.clear_button)
        self.cancel_button = QPushButton(t("common.cancel"))
        self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_button)
        buttons.addStretch(1)
        self.save_button = QPushButton(t("common.save"))
        self.save_button.setObjectName("Accent")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.accept)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

        if initial:
            try:
                parse_hotkey(initial)
                self._set_spec(initial)
            except ValueError:
                pass

        self.setFocusPolicy(Qt.StrongFocus)

    @property
    def spec(self) -> str:
        return self._spec

    def _set_spec(self, spec: str) -> None:
        self._spec = spec
        self.value.setText(spec)
        self.status.setText(t("hotkey.valid"))
        self.status.setStyleSheet("color: #5ecb8a;")
        self.save_button.setEnabled(True)

    def _clear(self) -> None:
        self._spec = ""
        self.value.clear()
        self.status.setText(t("hotkey.waiting"))
        self.status.setStyleSheet("color: #8fa0b5;")
        self.save_button.setEnabled(False)

    def _modifier_text(self, event: QKeyEvent) -> str:
        modifiers = event.modifiers()
        parts: list[str] = []
        if modifiers & Qt.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.AltModifier:
            parts.append("alt")
        if modifiers & Qt.ShiftModifier:
            parts.append("shift")
        if modifiers & Qt.MetaModifier:
            parts.append("win")
        return "+".join(parts)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        if event.key() in {
            Qt.Key_Control,
            Qt.Key_Shift,
            Qt.Key_Alt,
            Qt.Key_Meta,
            Qt.Key_AltGr,
        }:
            self.status.setText(t("hotkey.waiting"))
            self.status.setStyleSheet("color: #8fa0b5;")
            return
        token = key_to_token(event.key())
        if not token:
            self.status.setText(t("hotkey.unsupported"))
            self.status.setStyleSheet("color: #ff7b7b;")
            return
        modifiers = self._modifier_text(event)
        if not modifiers:
            self.status.setText(t("hotkey.modifier_required"))
            self.status.setStyleSheet("color: #ff7b7b;")
            return
        spec = f"{modifiers}+{token}"
        try:
            parse_hotkey(spec)
        except ValueError as error:
            self.status.setText(t("hotkey.invalid", error=error))
            self.status.setStyleSheet("color: #ff7b7b;")
            return
        self._set_spec(spec)
