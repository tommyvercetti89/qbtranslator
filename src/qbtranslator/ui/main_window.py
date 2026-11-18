"""QBTranslator ana penceresi."""

from __future__ import annotations

import ctypes
import threading
import time

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QCompleter,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from qbtranslator.core.appinfo import APP_VERSION
from qbtranslator.core.langs import (
    fold_text,
    label_to_code,
    language_label,
    language_name,
    source_labels,
    target_labels,
)
from qbtranslator.core.paths import ASSETS_DIR
from qbtranslator.core.storage import Store
from qbtranslator.core.translator import (
    ENGINE_LABELS,
    ENGINE_OPTIONS,
    TranslationOutcome,
    translate,
)
from qbtranslator.core.tray import TrayIcon
from qbtranslator.core.tts import SpeechEngine
from qbtranslator.core.win32util import GlobalHotkey, capture_selected_text
from qbtranslator.i18n import (
    resolve_language,
    set_language,
    t,
    ui_language_options,
)
from qbtranslator.ui.popup import TranslationPopup
from qbtranslator.ui.theme import (
    GREEN,
    MUTED,
    RED,
)

SHORTCUT = "ctrl+alt+t"


# --------------------------------------------------------------------------
# Worker sinyalleri
# --------------------------------------------------------------------------
class TaskSignals(QObject):
    finished = Signal(object, float, object)
    failed = Signal(str, object)


class CaptureSignals(QObject):
    finished = Signal(str)


class HotkeyBridge(QObject):
    triggered = Signal()


class TraySignals(QObject):
    show = Signal()
    quit = Signal()


class TranslateTask(QRunnable):
    def __init__(
        self,
        text: str,
        source: str,
        target: str,
        config: dict,
        context: tuple,
        signals: TaskSignals,
    ) -> None:
        super().__init__()
        self.text = text
        self.source = source
        self.target = target
        self.config = config
        self.context = context
        self.signals = signals

    def run(self) -> None:
        started = time.perf_counter()
        try:
            outcome = translate(self.text, self.source, self.target, self.config)
            self.signals.finished.emit(
                outcome, time.perf_counter() - started, self.context
            )
        except Exception as error:
            self.signals.failed.emit(str(error), self.context)


class CaptureTask(QRunnable):
    def __init__(self, restore_clipboard: bool, signals: CaptureSignals) -> None:
        super().__init__()
        self.restore_clipboard = restore_clipboard
        self.signals = signals

    def run(self) -> None:
        try:
            text = capture_selected_text(self.restore_clipboard)
        except Exception:
            text = ""
        self.signals.finished.emit(text or "")


# --------------------------------------------------------------------------
# Ana pencere
# --------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.store = Store()
        self.config = self.store.config
        self.ui_lang = resolve_language(self.config.get("ui_language", "system"))
        set_language(self.ui_lang)
        self.source_labels = source_labels(self.ui_lang)
        self.target_labels = target_labels(self.ui_lang)

        self.setWindowTitle(t("app.name"))
        self.resize(1180, 790)
        self.setMinimumSize(980, 680)
        icon_path = ASSETS_DIR / "QBTranslator.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.tts = SpeechEngine()
        self.popup: TranslationPopup | None = None
        self.tray: TrayIcon | None = None
        self.hotkey = GlobalHotkey()
        self._popup_seq = 0
        self._manual_busy = False
        self._capturing = False
        self._force_quit = False
        self._tray_hint_shown = False
        self._manual_result: TranslationOutcome | None = None
        self._manual_context: tuple[str, str, str] | None = None
        self._history_records: list[dict] = []
        self._dark_title_done = False

        self.task_signals = TaskSignals(self)
        self.capture_signals = CaptureSignals(self)
        self.hotkey_bridge = HotkeyBridge(self)
        self.tray_signals = TraySignals(self)
        self.task_signals.finished.connect(self._on_task_finished)
        self.task_signals.failed.connect(self._on_task_failed)
        self.capture_signals.finished.connect(self._on_capture_finished)
        self.hotkey_bridge.triggered.connect(self._on_hotkey)
        self.tray_signals.show.connect(self._show_from_tray)
        self.tray_signals.quit.connect(self._quit_app)

        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(3)

        self._build_ui()
        self._load_config_to_ui()
        self._reload_history()
        self._reload_words()
        self._start_hotkey()
        self._default_status()
        self._start_tray()

    # ------------------------------------------------------------------
    # Tema / pencere başlığı
    # ------------------------------------------------------------------
    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._dark_title_done:
            self._dark_title_done = True
            self._enable_dark_title_bar()

    def _enable_dark_title_bar(self) -> None:
        try:
            hwnd = int(self.winId())
            value = ctypes.c_int(1)
            for attribute in (20, 19):
                result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
                )
                if result == 0:
                    break
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Arayüz
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("Root")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_content(), 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(226)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setSpacing(8)

        brand = QLabel(t("app.name"))
        brand.setObjectName("Brand")
        layout.addWidget(brand)
        sub = QLabel(t("app.subtitle"))
        sub.setObjectName("BrandSub")
        layout.addWidget(sub)
        layout.addSpacing(22)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: list[QPushButton] = []
        nav_items = (
            ("nav.translate", "⌨"),
            ("nav.history", "◷"),
            ("nav.words", "▤"),
            ("nav.settings", "⚙"),
        )
        for index, (label_key, icon) in enumerate(nav_items):
            button = QPushButton(f"  {icon}   {t(label_key)}")
            button.setObjectName("Nav")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, i=index: self._set_page(i))
            self.nav_group.addButton(button, index)
            self.nav_buttons.append(button)
            layout.addWidget(button)
        self.nav_buttons[0].setChecked(True)

        layout.addStretch(1)

        self.hotkey_chip = QLabel(f"⌨  {self.config.get('hotkey', SHORTCUT)}")
        self.hotkey_chip.setObjectName("Chip")
        self.hotkey_chip.setToolTip(t("settings.hotkey"))
        layout.addWidget(self.hotkey_chip)

        version = QLabel(t("app.version", version=APP_VERSION))
        version.setObjectName("Tiny")
        version.setWordWrap(True)
        layout.addWidget(version)
        return sidebar

    def _build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(10)
        self.page_title = QLabel(t("page.translate"))
        self.page_title.setObjectName("PageTitle")
        header.addWidget(self.page_title)
        header.addStretch(1)
        self.engine_chip = QLabel(t("status.engine_chip", engine="..."))
        self.engine_chip.setObjectName("Chip")
        header.addWidget(self.engine_chip)
        self.target_chip = QLabel(t("status.target_chip", target="..."))
        self.target_chip.setObjectName("Chip")
        header.addWidget(self.target_chip)
        layout.addLayout(header)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_translate_page())
        self.stack.addWidget(self._build_history_page())
        self.stack.addWidget(self._build_words_page())
        self.stack.addWidget(self._build_settings_page())
        layout.addWidget(self.stack, 1)

        status_row = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("Status")
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        status_row.addWidget(self.status_label, 1)
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self._default_status)
        layout.addLayout(status_row)
        return content

    @staticmethod
    def _card() -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        return card, layout

    @staticmethod
    def _muted(text: str = "") -> QLabel:
        label = QLabel(text)
        label.setObjectName("Muted")
        return label

    def _build_translate_page(self) -> QWidget:
        page = QWidget()
        page_layout = QHBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(14)

        left = QVBoxLayout()
        left.setSpacing(14)

        source_card, source_layout = self._card()
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.addWidget(QLabel(t("common.source")))
        self.source_combo = QComboBox()
        self.source_combo.addItems(self.source_labels)
        self.source_combo.setMinimumWidth(180)
        top_row.addWidget(self.source_combo)

        self.swap_button = QPushButton("⇄")
        self.swap_button.setObjectName("Ghost")
        self.swap_button.setFixedWidth(36)
        self.swap_button.setToolTip(t("common.swap_languages"))
        self.swap_button.clicked.connect(self._swap_languages)
        top_row.addWidget(self.swap_button)

        top_row.addWidget(QLabel(t("common.target")))
        self.target_combo = QComboBox()
        self.target_combo.setEditable(True)
        self.target_combo.addItems(self.target_labels)
        self.target_combo.setMinimumWidth(210)
        completer = QCompleter(self.target_labels, self.target_combo)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.target_combo.setCompleter(completer)
        self.target_combo.activated.connect(self._on_main_target_changed)
        self.target_combo.lineEdit().editingFinished.connect(self._on_main_target_changed)
        top_row.addWidget(self.target_combo)
        top_row.addStretch(1)
        source_layout.addLayout(top_row)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText(
            t("translate.placeholder", hotkey=self.config.get("hotkey", SHORTCUT))
        )
        self.input_text.setMinimumHeight(150)
        source_layout.addWidget(self.input_text)

        action_row = QHBoxLayout()
        self.translate_button = QPushButton(f"{t('common.translate')}   Ctrl+Enter")
        self.translate_button.setObjectName("Accent")
        self.translate_button.clicked.connect(self._manual_translate)
        action_row.addWidget(self.translate_button)
        paste_button = QPushButton(t("common.paste"))
        paste_button.clicked.connect(self._paste)
        action_row.addWidget(paste_button)
        clear_button = QPushButton(t("common.clear"))
        clear_button.clicked.connect(self._clear_input)
        action_row.addWidget(clear_button)
        action_row.addStretch(1)
        self.char_label = QLabel(t("translate.char_count", count=0))
        self.char_label.setObjectName("Tiny")
        action_row.addWidget(self.char_label)
        source_layout.addLayout(action_row)
        self.input_text.textChanged.connect(self._on_input_changed)
        QShortcut(QKeySequence("Ctrl+Return"), self.input_text, activated=self._manual_translate)
        left.addWidget(source_card)

        result_card, result_layout = self._card()
        result_header = QHBoxLayout()
        result_header.addWidget(QLabel(t("nav.translate")))
        result_header.addStretch(1)
        self.copy_button = QPushButton(t("common.copy"))
        self.copy_button.clicked.connect(self._copy_manual)
        result_header.addWidget(self.copy_button)
        self.speak_button = QPushButton(t("common.read"))
        self.speak_button.clicked.connect(self._speak_manual)
        result_header.addWidget(self.speak_button)
        self.save_button = QPushButton(t("common.save_word"))
        self.save_button.clicked.connect(self._save_manual_word)
        result_header.addWidget(self.save_button)
        result_layout.addLayout(result_header)

        self.output_text = QTextBrowser()
        self.output_text.setOpenExternalLinks(False)
        self.output_text.setPlaceholderText(t("translate.result_placeholder"))
        self.output_text.setMinimumHeight(230)
        self.output_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        result_layout.addWidget(self.output_text, 1)
        self.manual_status = QLabel("")
        self.manual_status.setObjectName("Status")
        self.manual_status.setWordWrap(True)
        result_layout.addWidget(self.manual_status)
        left.addWidget(result_card, 1)

        page_layout.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(14)
        right.setContentsMargins(0, 0, 0, 0)
        history_card, history_layout = self._card()
        history_header = QHBoxLayout()
        history_header.addWidget(self._section_title(t("translate.recent")))
        history_header.addStretch(1)
        all_button = QPushButton(t("common.all"))
        all_button.setObjectName("Ghost")
        all_button.clicked.connect(lambda: self._set_page(1))
        history_header.addWidget(all_button)
        history_layout.addLayout(history_header)
        self.recent_list = QListWidget()
        self.recent_list.setMinimumWidth(290)
        self.recent_list.setMaximumWidth(340)
        self.recent_list.setWordWrap(True)
        self.recent_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.recent_list.setResizeMode(QListView.Adjust)
        self.recent_list.itemDoubleClicked.connect(self._open_history_item)
        history_layout.addWidget(self.recent_list, 1)
        right.addWidget(history_card, 1)

        tip_card, tip_layout = self._card()
        tip_layout.addWidget(self._section_title(t("translate.tip_title")))
        tip = self._muted(t("translate.tip"))
        tip.setWordWrap(True)
        tip_layout.addWidget(tip)
        right.addWidget(tip_card)
        page_layout.addLayout(right)
        return page

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        card, card_layout = self._card()
        header = QHBoxLayout()
        header.addWidget(self._section_title(t("history.title")))
        header.addStretch(1)
        clear = QPushButton(t("history.clear"))
        clear.setObjectName("Danger")
        clear.clicked.connect(self._clear_history)
        header.addWidget(clear)
        card_layout.addLayout(header)
        self.history_list = QListWidget()
        self.history_list.setWordWrap(True)
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list.setResizeMode(QListView.Adjust)
        self.history_list.itemDoubleClicked.connect(self._open_history_item)
        card_layout.addWidget(self.history_list, 1)
        layout.addWidget(card, 1)
        return page

    def _build_words_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        card, card_layout = self._card()
        header = QHBoxLayout()
        header.addWidget(self._section_title(t("words.title")))
        header.addStretch(1)
        clear = QPushButton(t("words.clear"))
        clear.setObjectName("Danger")
        clear.clicked.connect(self._clear_words)
        header.addWidget(clear)
        card_layout.addLayout(header)
        self.words_list = QListWidget()
        self.words_list.setWordWrap(True)
        self.words_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.words_list.setResizeMode(QListView.Adjust)
        card_layout.addWidget(self.words_list, 1)
        layout.addWidget(card, 1)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        card, card_layout = self._card()
        card_layout.addWidget(self._section_title(t("settings.title")))
        note = self._muted(t("settings.description"))
        note.setWordWrap(True)
        card_layout.addWidget(note)
        card_layout.addSpacing(8)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)
        grid.addWidget(QLabel(t("settings.default_target")), 0, 0)
        self.settings_target = QComboBox()
        self.settings_target.addItems(self.target_labels)
        grid.addWidget(self.settings_target, 0, 1)
        grid.addWidget(QLabel(t("settings.primary_engine")), 1, 0)
        self.settings_engine = QComboBox()
        for label, code in ENGINE_OPTIONS:
            self.settings_engine.addItem(t(f"engine.option.{code}"), code)
        grid.addWidget(self.settings_engine, 1, 1)
        grid.addWidget(QLabel(t("settings.hotkey")), 2, 0)
        self.settings_hotkey = QLineEdit()
        self.settings_hotkey.setPlaceholderText("ctrl+alt+t")
        grid.addWidget(self.settings_hotkey, 2, 1)
        grid.addWidget(QLabel(t("settings.ocr_language")), 3, 0)
        self.settings_ocr_language = QComboBox()
        self.settings_ocr_language.addItems(self.source_labels)
        grid.addWidget(self.settings_ocr_language, 3, 1)
        grid.addWidget(QLabel(t("settings.ui_language")), 4, 0)
        self.settings_language = QComboBox()
        for code, label in ui_language_options():
            self.settings_language.addItem(label, code)
        grid.addWidget(self.settings_language, 4, 1)
        grid.setColumnStretch(1, 1)
        card_layout.addLayout(grid)
        card_layout.addSpacing(8)

        self.settings_backup = QCheckBox(t("settings.backup"))
        card_layout.addWidget(self.settings_backup)
        save = QPushButton(t("settings.save_apply"))
        save.setObjectName("Accent")
        save.clicked.connect(self._save_settings)
        card_layout.addWidget(save, alignment=Qt.AlignLeft)
        language_note = self._muted(t("settings.language_restart"))
        language_note.setWordWrap(True)
        card_layout.addWidget(language_note)
        card_layout.addWidget(self._muted(t("settings.note")))
        card_layout.addStretch(1)
        layout.addWidget(card, 1)
        return page

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        return label

    # ------------------------------------------------------------------
    # Navigasyon
    # ------------------------------------------------------------------
    def _set_page(self, index: int) -> None:
        if index < 0 or index >= self.stack.count():
            return
        self.stack.setCurrentIndex(index)
        self.page_title.setText(
            (
                t("page.translate"),
                t("page.history"),
                t("page.words"),
                t("page.settings"),
            )[index]
        )
        if index in (0, 1):
            self._reload_history()
        elif index == 2:
            self._reload_words()
        self.nav_buttons[index].setChecked(True)

    # ------------------------------------------------------------------
    # Konfigürasyon
    # ------------------------------------------------------------------
    def _load_config_to_ui(self) -> None:
        self._set_combo_code(
            self.source_combo, self.config.get("source_lang", "auto"), True
        )
        self._set_combo_code(
            self.target_combo, self.config.get("target_lang", "en"), False
        )
        self.settings_hotkey.setText(self.config.get("hotkey", SHORTCUT))
        self._set_combo_code(
            self.settings_target, self.config.get("target_lang", "en"), False
        )
        engine_code = self.config.get("engine", "google")
        engine_index = self.settings_engine.findData(engine_code)
        if engine_index >= 0:
            self.settings_engine.setCurrentIndex(engine_index)
        self._set_combo_code(
            self.settings_ocr_language, self.config.get("ocr_language", "auto"), True
        )
        language_index = self.settings_language.findData(
            self.config.get("ui_language", "system")
        )
        if language_index >= 0:
            self.settings_language.setCurrentIndex(language_index)
        self.settings_backup.setChecked(bool(self.config.get("backup_engines")))
        self._update_chips()

    def _set_combo_code(self, combo: QComboBox, code: str, include_auto: bool) -> None:
        combo.blockSignals(True)
        label = language_label(code, self.ui_lang, include_auto=include_auto)
        index = combo.findText(label)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            combo.setCurrentText(label)
        combo.blockSignals(False)

    def _update_chips(self) -> None:
        engine = ENGINE_LABELS.get(self.config.get("engine", "google"), "?")
        target = language_name(self.config.get("target_lang", "en"), self.ui_lang)
        self.engine_chip.setText(t("status.engine_chip", engine=engine))
        self.target_chip.setText(t("status.target_chip", target=target))

    def _set_target_language(self, code: str) -> None:
        if not code or code == "auto":
            return
        self.config["target_lang"] = code
        self.store.save_config()
        self._set_combo_code(self.target_combo, code, False)
        self._set_combo_code(self.settings_target, code, False)
        if self.popup and self.popup.isVisible():
            self.popup.set_target_display(code)
        self._update_chips()

    def _on_main_target_changed(self, *_args) -> None:
        code = label_to_code(self.target_combo.currentText(), self.config.get("target_lang", "en"))
        if code and code != self.config.get("target_lang"):
            self._set_target_language(code)
            self._notify(t("status.target_updated"))

    def _swap_languages(self) -> None:
        source = label_to_code(self.source_combo.currentText(), "auto")
        target = label_to_code(self.target_combo.currentText(), "en")
        if source == "auto":
            source = target
            target = "tr" if target != "tr" else "en"
        else:
            source, target = target, source
        self._set_combo_code(self.source_combo, source, True)
        self._set_target_language(target)

    def _save_settings(self) -> None:
        from qbtranslator.core.win32util import parse_hotkey

        hotkey_spec = (self.settings_hotkey.text() or "").strip().lower()
        try:
            parse_hotkey(hotkey_spec)
        except ValueError as error:
            self._notify(t("status.invalid_hotkey", error=error), error=True)
            return

        target = label_to_code(self.settings_target.currentText(), "en")
        engine = self.settings_engine.currentData() or "google"
        old_hotkey = self.config.get("hotkey", SHORTCUT)
        ui_language = self.settings_language.currentData() or "system"
        self.config.update(
            {
                "hotkey": hotkey_spec,
                "target_lang": target,
                "engine": engine,
                "ui_language": ui_language,
                "backup_engines": self.settings_backup.isChecked(),
                "ocr_language": label_to_code(
                    self.settings_ocr_language.currentText(), "auto"
                ),
            }
        )
        if not self.store.save_config():
            self._notify(t("status.settings_save_failed"), error=True)
            return
        self._set_combo_code(self.target_combo, target, False)
        self._update_chips()
        self._start_hotkey()
        if self.hotkey and not self._hotkey_registered:
            self.config["hotkey"] = old_hotkey
            self.store.save_config()
            self.settings_hotkey.setText(old_hotkey)
            self._start_hotkey()
            self._notify(t("status.hotkey_failed"), error=True)
            return
        if resolve_language(ui_language) != self.ui_lang:
            self._notify(t("settings.language_restart"))
        else:
            self._notify(t("status.settings_saved"))

    # ------------------------------------------------------------------
    # Manuel çeviri
    # ------------------------------------------------------------------
    def _on_input_changed(self) -> None:
        self.char_label.setText(
            t("translate.char_count", count=len(self.input_text.toPlainText()))
        )
        if self._manual_result is not None:
            self._manual_result = None
            self._manual_context = None
            self.output_text.clear()
            self.manual_status.setText("")

    def _paste(self) -> None:
        text = QApplication.clipboard().text()
        if text:
            self.input_text.setPlainText(text)

    def _clear_input(self) -> None:
        self.input_text.clear()
        self.output_text.clear()
        self.manual_status.setText("")
        self._manual_result = None
        self._manual_context = None

    def _manual_translate(self) -> None:
        text = self.input_text.toPlainText().strip()
        if not text:
            self._notify(t("status.empty_text"), error=True)
            return
        if self._manual_busy:
            return
        source = label_to_code(self.source_combo.currentText(), "auto")
        target = label_to_code(
            self.target_combo.currentText(), self.config.get("target_lang", "en")
        )
        if not target or target == "auto":
            self._notify(t("status.target_required"), error=True)
            return
        self._manual_busy = True
        self._manual_result = None
        self._manual_context = None
        self.translate_button.setEnabled(False)
        self.translate_button.setText(t("common.translating"))
        self.output_text.setPlainText("...")
        self.manual_status.setText(t("common.translating"))
        self.manual_status.setStyleSheet(f"color: {MUTED};")
        self._queue_translate(
            text,
            source,
            target,
            ("manual", text, source, target),
        )
    def _queue_translate(self, text: str, source: str, target: str, context: tuple) -> None:
        task = TranslateTask(
            text, source, target, dict(self.config), context, self.task_signals
        )
        self.thread_pool.start(task)

    def _on_task_finished(self, outcome, elapsed: float, context: object) -> None:
        context = tuple(context)
        if context[0] == "popup":
            _, request_id, source_text, _source, _target = context
            if self.popup and self.popup.request_id == request_id:
                self.popup.show_result(outcome)
            self.store.add_history(
                source_text,
                outcome.text,
                outcome.source_lang,
                outcome.target_lang,
                outcome.engine,
            )
            self._reload_history()
            return

        _kind, text, source, target = context
        self._manual_busy = False
        self._manual_result = outcome
        self._manual_context = (text, source, target)
        self.translate_button.setEnabled(True)
        self.translate_button.setText(f"{t('common.translate')}   Ctrl+Enter")
        self.output_text.setPlainText(outcome.text)
        self.manual_status.setStyleSheet(f"color: {GREEN};")
        self.manual_status.setText(
            t(
                "status.result_meta",
                engine=outcome.engine_label,
                seconds=f"{elapsed:.2f}",
                source=language_name(outcome.source_lang, self.ui_lang),
                target=language_name(outcome.target_lang, self.ui_lang),
            )
        )
        self.store.add_history(
            text,
            outcome.text,
            outcome.source_lang,
            outcome.target_lang,
            outcome.engine,
        )
        self._reload_history()

    def _on_task_failed(self, message: str, context: object) -> None:
        context = tuple(context)
        if context[0] == "popup":
            request_id = context[1]
            if self.popup and self.popup.request_id == request_id:
                self.popup.show_error(message)
            return
        self._manual_busy = False
        self._manual_result = None
        self._manual_context = None
        self.translate_button.setEnabled(True)
        self.translate_button.setText(f"{t('common.translate')}   Ctrl+Enter")
        self.output_text.setPlainText(message)
        self.manual_status.setStyleSheet(f"color: {RED};")
        self.manual_status.setText(t("status.translation_failed"))

    # ------------------------------------------------------------------
    # Popup
    # ------------------------------------------------------------------
    def _popup_translate(self, text: str) -> None:
        target = self.config.get("target_lang", "en")
        if self.popup:
            self.popup.close()
        self.popup = TranslationPopup(self, text, "auto")
        self._popup_seq += 1
        self.popup.request_id = self._popup_seq
        self.popup.show_loading()
        self._queue_translate(
            text,
            "auto",
            target,
            ("popup", self._popup_seq, text, "auto", target),
        )

    def on_popup_target_changed(self, popup: TranslationPopup, code: str) -> None:
        if popup is not self.popup:
            return
        self._set_target_language(code)
        text = (popup.source_text or "").strip()
        if not text:
            return
        self._popup_seq += 1
        popup.request_id = self._popup_seq
        popup.show_loading(reposition=False)
        self._queue_translate(
            text,
            "auto",
            code,
            ("popup", self._popup_seq, text, "auto", code),
        )

    def swap_popup(self, popup: TranslationPopup) -> None:
        if popup is not self.popup or not popup.result:
            return
        detected = (popup.result.source_lang or "").strip()
        if not detected or detected == "auto":
            popup.show_error(t("popup.unknown_language"))
            return
        new_text = popup.result.text
        new_source_lang = popup.result.target_lang
        new_target = detected
        popup.source_text = new_text
        popup.source_label.setText(popup._trim_source(new_text))
        popup.result = None
        popup.set_target_display(new_target)
        self._set_target_language(new_target)
        self._popup_seq += 1
        popup.request_id = self._popup_seq
        popup.show_loading(reposition=False)
        self._queue_translate(
            new_text,
            new_source_lang,
            new_target,
            ("popup", self._popup_seq, new_text, new_source_lang, new_target),
        )

    def on_popup_closed(self, popup: TranslationPopup) -> None:
        if popup is self.popup:
            self.popup = None
        popup.deleteLater()

    def save_popup_word(self, popup: TranslationPopup) -> bool:
        if not popup.result:
            return False
        return self._save_word(
            popup.source_text,
            popup.result.text,
            popup.result.source_lang or popup.source_lang,
            popup.result.target_lang,
        )

    # ------------------------------------------------------------------
    # Global kısayol / seçim
    # ------------------------------------------------------------------
    def _start_hotkey(self) -> None:
        self.hotkey.stop()
        spec = self.config.get("hotkey", SHORTCUT)
        try:
            self._hotkey_registered = self.hotkey.start(
                spec, self.hotkey_bridge.triggered.emit
            )
        except ValueError:
            self._hotkey_registered = False
        if self._hotkey_registered:
            self.hotkey_chip.setText(f"⌨  {spec}")
            self.hotkey_chip.setStyleSheet("color: #9ec8ff;")
        else:
            self.hotkey_chip.setText(f"⌨  {t('status.hotkey_missing')}")
            self.hotkey_chip.setStyleSheet(f"color: {RED};")

    def _on_hotkey(self) -> None:
        if self._capturing or self._force_quit:
            return
        self._capturing = True
        self._notify(t("status.selection"))
        task = CaptureTask(
            bool(self.config.get("restore_clipboard", True)), self.capture_signals
        )
        self.thread_pool.start(task)

    def _on_capture_finished(self, text: str) -> None:
        self._capturing = False
        if text:
            self._popup_translate(text)
        else:
            self._notify(t("status.selection_empty"), error=True)

    # ------------------------------------------------------------------
    # Geçmiş / kelimeler
    # ------------------------------------------------------------------
    def _reload_history(self) -> None:
        self._history_records = list(self.store.history)
        if hasattr(self, "history_list"):
            self.history_list.clear()
        if hasattr(self, "recent_list"):
            self.recent_list.clear()
        if not self._history_records:
            empty_text = t("history.empty")
            for list_widget in (getattr(self, "history_list", None), getattr(self, "recent_list", None)):
                if list_widget is not None:
                    empty = QListWidgetItem(empty_text)
                    empty.setFlags(Qt.NoItemFlags)
                    list_widget.addItem(empty)
            return
        for index, record in enumerate(self._history_records[:100]):
            text = self._format_history(record)
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, index)
            item.setToolTip(text)
            if hasattr(self, "history_list"):
                self.history_list.addItem(item)
            if index < 7 and hasattr(self, "recent_list"):
                recent = QListWidgetItem(text)
                recent.setData(Qt.UserRole, index)
                recent.setToolTip(text)
                self.recent_list.addItem(recent)

    @staticmethod
    def _format_history(record: dict) -> str:
        source = " ".join((record.get("source_text", "") or "").split())
        translation = " ".join((record.get("translation", "") or "").split())
        if len(source) > 60:
            source = source[:57] + "…"
        if len(translation) > 70:
            translation = translation[:67] + "…"
        return f"{source}   →   {translation}"

    def _open_history_item(self, item: QListWidgetItem) -> None:
        try:
            record = self._history_records[int(item.data(Qt.UserRole))]
        except (IndexError, TypeError, ValueError):
            return
        self.input_text.setPlainText(record.get("source_text", ""))
        outcome = TranslationOutcome(
            text=record.get("translation", ""),
            source_lang=record.get("source_lang", ""),
            target_lang=record.get("target_lang", ""),
            engine=record.get("engine", ""),
        )
        self._manual_result = outcome
        self._manual_context = (
            record.get("source_text", ""),
            record.get("source_lang", "auto"),
            record.get("target_lang", "en"),
        )
        self.output_text.setPlainText(outcome.text)
        self.manual_status.setStyleSheet(f"color: {GREEN};")
        self.manual_status.setText(
            t(
                "status.history_meta",
                engine=outcome.engine_label,
                source=language_name(outcome.source_lang, self.ui_lang),
                target=language_name(outcome.target_lang, self.ui_lang),
            )
        )
        if record.get("target_lang"):
            self._set_target_language(record["target_lang"])
        self._set_page(0)

    def _clear_history(self) -> None:
        if not self.store.history:
            return
        answer = QMessageBox.question(
            self,
            t("history.clear_confirm_title"),
            t("history.clear_confirm"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.store.clear_history()
            self._reload_history()

    def _reload_words(self) -> None:
        if not hasattr(self, "words_list"):
            return
        self.words_list.clear()
        if not self.store.words:
            empty = QListWidgetItem(t("words.empty"))
            empty.setFlags(Qt.NoItemFlags)
            self.words_list.addItem(empty)
            return
        for record in self.store.words[:200]:
            word = record.get("word", "")
            translation = record.get("translation", "")
            item = QListWidgetItem(f"{word}   →   {translation}")
            item.setToolTip(f"{word}\n{translation}")
            self.words_list.addItem(item)

    def _clear_words(self) -> None:
        if not self.store.words:
            return
        answer = QMessageBox.question(
            self,
            t("words.clear_confirm_title"),
            t("words.clear_confirm"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.store.clear_words()
            self._reload_words()

    # ------------------------------------------------------------------
    # Kopyala / ses / kelime
    # ------------------------------------------------------------------
    def copy_text(self, text: str) -> None:
        if text:
            QApplication.clipboard().setText(text)
            self._notify(t("status.copied"))

    def _copy_manual(self) -> None:
        if self._manual_result:
            self.copy_text(self._manual_result.text)

    def speak_text(self, text: str) -> bool:
        if not text:
            return False
        if self.tts.is_speaking:
            self.tts.stop()
            return False
        rate = self.config.get("tts_rate", 0)
        threading.Thread(
            target=self.tts.speak, args=(text, rate), daemon=True, name="TTSWorker"
        ).start()
        return True

    def _speak_manual(self) -> None:
        if self._manual_result:
            speaking = self.speak_text(self._manual_result.text)
            self.speak_button.setText(t("common.stop") if speaking else t("common.read"))
            QTimer.singleShot(
                1300, lambda: self.speak_button.setText(t("common.read"))
            )

    def _save_word(self, word: str, translation: str, source_lang: str, target_lang: str) -> bool:
        word = (word or "").strip()
        translation = (translation or "").strip()
        if not word or not translation:
            return False
        was_present = any(
            fold_text(item.get("word", "")) == fold_text(word)
            and fold_text(item.get("translation", "")) == fold_text(translation)
            for item in self.store.words
        )
        self.store.add_word(word, translation, source_lang, target_lang)
        self._reload_words()
        return not was_present

    def _save_manual_word(self) -> None:
        if not self._manual_result or not self._manual_context:
            self._notify(t("status.result_required"), error=True)
            return
        source_text, source, target = self._manual_context
        if self.input_text.toPlainText().strip() != source_text:
            self._notify(t("status.text_changed"), error=True)
            return
        saved = self._save_word(
            source_text,
            self._manual_result.text,
            self._manual_result.source_lang or source,
            self._manual_result.target_lang or target,
        )
        self._notify(t("status.word_saved") if saved else t("status.word_exists"))

    # ------------------------------------------------------------------
    # Tepsi / kapanış
    # ------------------------------------------------------------------
    def _start_tray(self) -> None:
        try:
            self.tray = TrayIcon(
                tooltip=t("tray.tooltip"),
                on_show=lambda: self.tray_signals.show.emit(),
                on_quit=lambda: self.tray_signals.quit.emit(),
                icon_path=str(ASSETS_DIR / "QBTranslator.ico"),
                open_label=t("tray.open"),
                quit_label=t("tray.quit"),
            )
            if not self.tray.start():
                self.tray = None
        except Exception:
            self.tray = None
        if self.tray is None:
            self._notify(t("status.tray_unavailable"))

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:
        if self._force_quit or not (self.tray and self.tray.available):
            self._shutdown()
            event.accept()
            app = QApplication.instance()
            if app:
                app.quit()
            return
        self.hide()
        if not self._tray_hint_shown:
            self._tray_hint_shown = True
            self.tray.show_balloon(
                t("tray.balloon_title"),
                t("tray.balloon_text"),
            )
        event.ignore()

    def _quit_app(self) -> None:
        self._force_quit = True
        self._shutdown()
        app = QApplication.instance()
        if app:
            app.quit()

    def _shutdown(self) -> None:
        try:
            self.hotkey.stop()
        except Exception:
            pass
        try:
            self.tts.stop()
        except Exception:
            pass
        try:
            if self.popup:
                self.popup.close()
        except Exception:
            pass
        try:
            if self.tray:
                self.tray.stop()
                self.tray = None
        except Exception:
            pass
        try:
            self.thread_pool.waitForDone(1000)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Durum
    # ------------------------------------------------------------------
    def _default_status(self) -> None:
        engine = ENGINE_LABELS.get(self.config.get("engine", "google"), "?")
        target = language_name(self.config.get("target_lang", "en"), self.ui_lang)
        self.status_label.setStyleSheet(f"color: {MUTED};")
        self.status_label.setText(
            t(
                "status.default",
                engine=engine,
                target=target,
                hotkey=self.config.get("hotkey", SHORTCUT),
            )
        )

    def _notify(self, text: str, error: bool = False) -> None:
        self.status_label.setStyleSheet(f"color: {RED if error else GREEN};")
        self.status_label.setText(text)
        self.status_timer.start(3500)

    def _smoke_translate(self) -> None:
        self.input_text.setPlainText("Merhaba dünya, bugün hava çok güzel.")
        self._manual_translate()
        QTimer.singleShot(6000, self._smoke_print)

    def _smoke_print(self) -> None:
        print("output:", repr(self.output_text.toPlainText()), flush=True)
        print("manual_status:", repr(self.manual_status.text()), flush=True)
        print("history:", len(self.store.history), flush=True)
        print("hotkey_registered:", bool(self._hotkey_registered), flush=True)
        self._quit_app()
