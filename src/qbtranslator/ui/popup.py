"""PySide6 çeviri balonu prototipi."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFontMetrics, QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from qbtranslator.core.langs import label_to_code, language_label, language_name, target_labels
from qbtranslator.core.win32util import GlobalHotkey
from qbtranslator.i18n import get_language, t
from qbtranslator.ui.language_picker import LanguagePickerDialog
from qbtranslator.ui.theme import (
    MUTED,
    RED,
    TEXT,
)


class _EscapeBridge(QObject):
    triggered = Signal()


class _TargetCombo(QComboBox):
    popup_shown = Signal()
    popup_hidden = Signal()

    def showPopup(self) -> None:
        super().showPopup()
        self.popup_shown.emit()

    def hidePopup(self) -> None:
        super().hidePopup()
        self.popup_hidden.emit()


class TranslationPopup(QWidget):
    """İmlecin yanında açılan, çerçevesiz ve sürüklenebilir balon."""

    def __init__(self, app, source_text: str, source_lang: str = "auto") -> None:
        super().__init__(None)
        self.app = app
        self.ui_lang = get_language()
        self.target_labels = target_labels(self.ui_lang)
        self.source_text = source_text or ""
        self.source_lang = source_lang or "auto"
        self.result = None
        self.target_code = app.config.get("target_lang", "tr")
        self.request_id = 0
        self._drag_pos: QPoint | None = None
        self._closing = False
        self._actions_enabled = False

        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedWidth(560)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.close)

        self._escape_bridge = _EscapeBridge(self)
        self._escape_bridge.triggered.connect(self.close)
        self._escape_listener = GlobalHotkey()
        self._escape_started = False

        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)

        self.panel = QFrame(self)
        self.panel.setObjectName("PopupPanel")
        outer.addWidget(self.panel)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(38)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 175))
        self.panel.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(9)

        header = QHBoxLayout()
        header.setSpacing(8)
        self.header_title = QLabel(t("popup.title"), self.panel)
        self.header_title.setObjectName("PopupTitle")
        header.addWidget(self.header_title)
        header.addStretch(1)

        close_button = QPushButton("✕", self.panel)
        close_button.setObjectName("Ghost")
        close_button.setFixedSize(26, 26)
        close_button.setToolTip(t("popup.close_tooltip"))
        close_button.clicked.connect(self.close)
        header.addWidget(close_button)
        layout.addLayout(header)

        self.source_label = QLabel(self._trim_source(self.source_text), self.panel)
        self.source_label.setObjectName("PopupSource")
        self.source_label.setWordWrap(True)
        self.source_label.setMaximumWidth(480)
        self.source_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.source_label)

        separator = QFrame(self.panel)
        separator.setObjectName("Separator")
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        self.result_label = QLabel("…", self.panel)
        self.result_label.setObjectName("PopupResult")
        self.result_label.setWordWrap(True)
        self.result_label.setFixedWidth(480)
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.result_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        layout.addWidget(self.result_label)

        self.status_label = QLabel("", self.panel)
        self.status_label.setObjectName("PopupStatus")
        layout.addWidget(self.status_label)

        target_row = QHBoxLayout()
        target_row.setSpacing(7)
        target_label = QLabel(t("popup.target"), self.panel)
        target_label.setObjectName("PopupStatus")
        target_row.addWidget(target_label)

        self.target_combo = _TargetCombo(self.panel)
        self.target_combo.setEditable(True)
        self.target_combo.addItems(self.target_labels)
        self.target_combo.setFixedWidth(250)
        self.target_combo.setCurrentText(
            language_label(self.target_code, self.ui_lang, include_auto=False)
        )
        completer = QCompleter(self.target_labels, self.target_combo)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.target_combo.setCompleter(completer)
        self.target_combo.activated.connect(self._on_target_changed)
        self.target_combo.lineEdit().editingFinished.connect(self._on_target_changed)
        self.target_combo.popup_shown.connect(self._on_combo_popup_shown)
        self.target_combo.popup_hidden.connect(self._on_combo_popup_hidden)
        target_row.addWidget(self.target_combo)

        self.language_search_button = QPushButton("⌕", self.panel)
        self.language_search_button.setObjectName("Ghost")
        self.language_search_button.setFixedWidth(30)
        self.language_search_button.setToolTip(t("language_picker.title"))
        self.language_search_button.clicked.connect(self._open_language_picker)
        target_row.addWidget(self.language_search_button)

        self.swap_button = QPushButton("⇄", self.panel)
        self.swap_button.setObjectName("Ghost")
        self.swap_button.setFixedWidth(38)
        self.swap_button.setToolTip(t("popup.swap_tooltip"))
        self.swap_button.clicked.connect(self._on_swap)
        target_row.addWidget(self.swap_button)
        target_row.addStretch(1)
        layout.addLayout(target_row)

        buttons = QHBoxLayout()
        buttons.setSpacing(7)
        self.copy_button = self._button(buttons, t("common.copy"), self._copy)
        self.speak_button = self._button(buttons, t("common.read"), self._speak)
        self.save_button = self._button(buttons, t("common.save_word"), self._save)
        buttons.addStretch(1)
        self.close_button = self._button(buttons, t("common.close"), self.close)
        layout.addLayout(buttons)

        self.header_title.installEventFilter(self)
        self.panel.installEventFilter(self)
        for widget in self.findChildren(QWidget):
            widget.installEventFilter(self)
        self.installEventFilter(self)
        self.set_actions_enabled(False)

    @staticmethod
    def _button(layout: QHBoxLayout, text: str, callback) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    # ------------------------------------------------------------------
    def set_actions_enabled(self, enabled: bool) -> None:
        self._actions_enabled = enabled
        for button in (self.copy_button, self.speak_button, self.save_button):
            button.setEnabled(enabled)
        self.swap_button.setEnabled(enabled and self.result is not None)

    def set_target_display(self, code: str) -> None:
        if not code or code == "auto":
            return
        self.target_code = code
        self.target_combo.blockSignals(True)
        self.target_combo.setCurrentText(
            language_label(code, self.ui_lang, include_auto=False)
        )
        self.target_combo.blockSignals(False)

    # ------------------------------------------------------------------
    def show_loading(self, source_text: str | None = None, reposition: bool = True) -> None:
        if source_text is not None:
            self.source_text = source_text
            self.source_label.setText(self._trim_source(source_text))
        self.result = None
        self.header_title.setText(t("popup.loading"))
        self.result_label.setStyleSheet(f"color: {MUTED}; font-size: 12pt;")
        self.result_label.setText("...")
        self.status_label.setText("")
        self.set_actions_enabled(False)
        self._adjust_size()
        if reposition:
            self._show_near_cursor()
        else:
            self._restart_autohide()

    def show_result(self, outcome) -> None:
        self.result = outcome
        self.header_title.setText(t("popup.title"))
        self.result_label.setStyleSheet(f"color: {TEXT}; font-size: 12pt;")
        self.result_label.setText(outcome.text)
        source = (
            language_name(outcome.source_lang, self.ui_lang)
            if outcome.source_lang
            else "?"
        )
        self.status_label.setText(
            t(
                "popup.status",
                source=source,
                target=language_name(outcome.target_lang, self.ui_lang),
                engine=outcome.engine_label,
            )
        )
        self.set_target_display(outcome.target_lang)
        self.set_actions_enabled(True)
        self.swap_button.setEnabled(bool(outcome.source_lang))
        self._adjust_size()
        if not self.isVisible():
            self._show_near_cursor()
        self._restart_autohide()

    def show_error(self, message: str) -> None:
        self.result = None
        self.header_title.setText(t("popup.title"))
        self.result_label.setStyleSheet(f"color: {RED}; font-size: 10pt;")
        self.result_label.setText(message)
        self.status_label.setText(t("popup.error"))
        self.set_actions_enabled(False)
        self._adjust_size()
        if not self.isVisible():
            self._show_near_cursor()
        self._restart_autohide()

    # ------------------------------------------------------------------
    def _on_combo_popup_shown(self) -> None:
        self._hide_timer.stop()
        self._stop_escape_listener()

    def _on_combo_popup_hidden(self) -> None:
        if not self.isVisible():
            return
        self._start_escape_listener()
        self._restart_autohide()

    def _open_language_picker(self) -> None:
        self._hide_timer.stop()
        self._stop_escape_listener()
        dialog = LanguagePickerDialog(self, self.target_code, self.ui_lang)
        if dialog.exec() == QDialog.Accepted and dialog.selected_code:
            self.target_code = dialog.selected_code
            self.set_target_display(dialog.selected_code)
            self.app.on_popup_target_changed(self, dialog.selected_code)
        if self.isVisible():
            self._start_escape_listener()
            self._restart_autohide()

    def _on_target_changed(self, *_args) -> None:
        code = label_to_code(self.target_combo.currentText(), self.target_code)
        if not code or code == self.target_code:
            return
        self.target_code = code
        self.app.on_popup_target_changed(self, code)

    def _on_swap(self) -> None:
        if self.result and self.result.source_lang:
            self.app.swap_popup(self)

    def _copy(self) -> None:
        if not self.result:
            return
        self.app.copy_text(self.result.text)
        self._flash(self.copy_button, t("popup.copied"))

    def _speak(self) -> None:
        if not self.result:
            return
        speaking = self.app.speak_text(self.result.text)
        self._flash(self.speak_button, t("common.stop") if speaking else t("common.read"))

    def _save(self) -> None:
        if not self.result:
            return
        saved = self.app.save_popup_word(self)
        self._flash(
            self.save_button,
            t("popup.saved") if saved else t("popup.exists"),
        )

    def _flash(self, button: QPushButton, text: str, duration: int = 1300) -> None:
        original = button.property("originalText") or button.text()
        button.setProperty("originalText", original)
        button.setText(text)
        QTimer.singleShot(
            duration,
            lambda: self._restore_button(button, original),
        )

    @staticmethod
    def _restore_button(button: QPushButton, text: str) -> None:
        try:
            button.setText(text)
            button.setProperty("originalText", "")
        except RuntimeError:
            pass

    # ------------------------------------------------------------------
    def _trim_source(self, text: str) -> str:
        text = " ".join((text or "").split())
        if len(text) > 280:
            text = text[:277] + "…"
        return text

    def _adjust_size(self) -> None:
        text = self.result_label.text() or " "
        metrics = QFontMetrics(self.result_label.font())
        rect = metrics.boundingRect(
            QRect(0, 0, 480, 10000), Qt.TextWordWrap, text
        )
        height = max(44, min(290, rect.height() + 10))
        self.result_label.setFixedHeight(height)
        self.adjustSize()

    def _show_near_cursor(self) -> None:
        self._adjust_size()
        cursor = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        width = self.width()
        height = self.height()
        pos_x = cursor.x() + 18
        if pos_x + width > area.right() - 12:
            pos_x = cursor.x() - width - 18
        pos_y = cursor.y() + 26
        if pos_y + height > area.bottom() - 12:
            pos_y = cursor.y() - height - 20
        pos_x = max(area.left() + 8, min(pos_x, area.right() - width - 8))
        pos_y = max(area.top() + 8, min(pos_y, area.bottom() - height - 8))
        self.move(pos_x, pos_y)
        self.show()
        self.raise_()
        self._restart_autohide()

    # ------------------------------------------------------------------
    def _restart_autohide(self) -> None:
        self._hide_timer.stop()
        try:
            seconds = int(self.app.config.get("popup_autohide_seconds") or 0)
        except (TypeError, ValueError):
            seconds = 0
        if seconds > 0:
            self._hide_timer.start(seconds * 1000)

    def enterEvent(self, event) -> None:
        self._hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._restart_autohide()
        super().leaveEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._start_escape_listener()

    def _start_escape_listener(self) -> None:
        if self._escape_started:
            return
        try:
            self._escape_started = self._escape_listener.start(
                "esc",
                self._escape_bridge.triggered.emit,
                allow_no_modifier=True,
            )
        except ValueError:
            self._escape_started = False

    def _stop_escape_listener(self) -> None:
        try:
            self._escape_listener.stop()
        except Exception:
            pass
        self._escape_started = False

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
            self.close()
            return True
        if obj in (getattr(self, "header_title", None), getattr(self, "panel", None)):
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if event.type() == QEvent.MouseMove and self._drag_pos is not None:
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                return True
            if event.type() == QEvent.MouseButtonRelease:
                self._drag_pos = None
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self._hide_timer.stop()
        self._stop_escape_listener()
        if not self._closing:
            self._closing = True
            self.app.on_popup_closed(self)
        event.accept()
