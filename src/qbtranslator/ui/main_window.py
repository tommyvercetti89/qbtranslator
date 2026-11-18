"""QBTranslator ana penceresi."""

from __future__ import annotations

import csv
import ctypes
import os
import re
import threading
import time

from PySide6.QtCore import QObject, QRect, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QFileDialog,
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
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from qbtranslator.core import autostart
from qbtranslator.core.appinfo import APP_VERSION
from qbtranslator.core.langs import (
    fold_text,
    label_to_code,
    language_label,
    language_name,
    source_labels,
    target_labels,
)
from qbtranslator.core.ocr import (
    cleanup_temp_captures,
    clear_last_capture,
    recognize_region,
)
from qbtranslator.core.paths import ASSETS_DIR, DATA_DIR
from qbtranslator.core.storage import DEFAULT_CONFIG, Store
from qbtranslator.core.translator import (
    ENGINE_LABELS,
    ENGINE_OPTIONS,
    TranslationOutcome,
    translate,
)
from qbtranslator.core.tray import TrayIcon
from qbtranslator.core.tts import SpeechEngine
from qbtranslator.core.win32util import (
    ClipboardWatcher,
    GlobalHotkey,
    capture_selected_text,
)
from qbtranslator.i18n import (
    resolve_language,
    set_language,
    t,
    ui_language_options,
)
from qbtranslator.ui.detail_dialog import TranslationDetailDialog
from qbtranslator.ui.hotkey_dialog import HotkeyCaptureDialog
from qbtranslator.ui.language_picker import LanguagePickerDialog
from qbtranslator.ui.popup import TranslationPopup
from qbtranslator.ui.region_selector import RegionSelector
from qbtranslator.ui.study_dialog import StudyDialog
from qbtranslator.ui.theme import (
    GREEN,
    MUTED,
    RED,
    YELLOW,
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


class ClipboardBridge(QObject):
    text = Signal(str)


class OCRSignals(QObject):
    finished = Signal(str, str)


class OCRTask(QRunnable):
    def __init__(self, region: tuple[int, int, int, int], language: str, signals: OCRSignals) -> None:
        super().__init__()
        self.region = region
        self.language = language
        self.signals = signals

    def run(self) -> None:
        try:
            text, error = recognize_region(*self.region, language=self.language)
        except Exception as exc:
            text, error = "", str(exc)
        self.signals.finished.emit(text or "", error or "")


class HotkeyBridge(QObject):
    triggered = Signal()


class OcrHotkeyBridge(QObject):
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
        try:
            clear_last_capture()
            cleanup_temp_captures()
        except Exception:
            pass
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
        self.ocr_hotkey = GlobalHotkey()
        self.clipboard = ClipboardWatcher(self._on_clipboard_text)
        self._popup_seq = 0
        self._manual_busy = False
        self._capturing = False
        self._force_quit = False
        self._tray_hint_shown = False
        self._manual_result: TranslationOutcome | None = None
        self._manual_context: tuple[str, str, str] | None = None
        self._history_records: list[dict] = []
        self._words_view: list[dict] = []
        self._dark_title_done = False
        self._last_clipboard_text = ""
        self._suppress_clipboard_until = 0.0
        self._hotkey_ok = False
        self._ocr_hotkey_ok = False
        self._ocr_active = False
        self._ocr_selector: RegionSelector | None = None
        self._loading_settings = False
        self._settings_save_buttons: dict[str, QPushButton] = {}

        self.task_signals = TaskSignals(self)
        self.capture_signals = CaptureSignals(self)
        self.clipboard_bridge = ClipboardBridge(self)
        self.ocr_signals = OCRSignals(self)
        self.hotkey_bridge = HotkeyBridge(self)
        self.ocr_hotkey_bridge = OcrHotkeyBridge(self)
        self.tray_signals = TraySignals(self)
        self.task_signals.finished.connect(self._on_task_finished)
        self.task_signals.failed.connect(self._on_task_failed)
        self.capture_signals.finished.connect(self._on_capture_finished)
        self.clipboard_bridge.text.connect(self._handle_clipboard_text)
        self.ocr_signals.finished.connect(self._on_ocr_finished)
        self.hotkey_bridge.triggered.connect(self._on_hotkey)
        self.ocr_hotkey_bridge.triggered.connect(self._on_ocr_hotkey)
        self.tray_signals.show.connect(self._show_from_tray)
        self.tray_signals.quit.connect(self._quit_app)

        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(3)

        self._build_ui()
        self._load_config_to_ui()
        self._reload_history()
        self._reload_words()
        self._restore_geometry()
        self._apply_settings(initial=True)

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
            ("nav.about", "ℹ"),
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

        self.monitor_chip = QLabel("")
        self.monitor_chip.setObjectName("Chip")
        layout.addWidget(self.monitor_chip)

        self.ocr_chip = QLabel("")
        self.ocr_chip.setObjectName("Chip")
        layout.addWidget(self.ocr_chip)

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
        self.stack.addWidget(self._build_about_page())
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
        self.source_combo.activated.connect(self._on_source_changed)
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
        self.target_search_button = QPushButton("⌕")
        self.target_search_button.setObjectName("Ghost")
        self.target_search_button.setFixedWidth(34)
        self.target_search_button.setToolTip(t("language_picker.title"))
        self.target_search_button.clicked.connect(self._search_target_language)
        top_row.addWidget(self.target_search_button)
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

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel(t("history.search")))
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText(t("history.search"))
        self.history_search.textChanged.connect(self._reload_history)
        toolbar.addWidget(self.history_search, 1)
        copy_button = QPushButton(t("history.copy_selected"))
        copy_button.clicked.connect(self._copy_selected_history)
        toolbar.addWidget(copy_button)
        save_button = QPushButton(t("history.save_selected"))
        save_button.clicked.connect(self._save_selected_history_word)
        toolbar.addWidget(save_button)
        delete_button = QPushButton(t("history.delete_selected"))
        delete_button.clicked.connect(self._delete_selected_history)
        toolbar.addWidget(delete_button)
        detail_button = QPushButton(t("history.detail_title"))
        detail_button.clicked.connect(self._open_selected_history_detail)
        toolbar.addWidget(detail_button)
        card_layout.addLayout(toolbar)

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

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel(t("words.search")))
        self.words_search = QLineEdit()
        self.words_search.setPlaceholderText(t("words.search"))
        self.words_search.textChanged.connect(self._reload_words)
        toolbar.addWidget(self.words_search, 1)
        delete_button = QPushButton(t("words.delete_selected"))
        delete_button.clicked.connect(self._delete_selected_word)
        toolbar.addWidget(delete_button)
        export_button = QPushButton(t("words.export"))
        export_button.clicked.connect(self._export_words_csv)
        toolbar.addWidget(export_button)
        study_button = QPushButton(t("words.study"))
        study_button.clicked.connect(self._open_study_mode)
        toolbar.addWidget(study_button)
        card_layout.addLayout(toolbar)

        self.words_list = QListWidget()
        self.words_list.setWordWrap(True)
        self.words_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.words_list.setResizeMode(QListView.Adjust)
        card_layout.addWidget(self.words_list, 1)
        layout.addWidget(card, 1)
        return page

    def _build_settings_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        general_card, general = self._card()
        general.addLayout(self._settings_header("settings.title", "general"))
        general.addWidget(self._muted(t("settings.description")))
        save_hint = self._muted(t("settings.save_hint"))
        save_hint.setWordWrap(True)
        general.addWidget(save_hint)
        general_grid = QGridLayout()
        general_grid.setHorizontalSpacing(18)
        general_grid.setVerticalSpacing(12)
        general_grid.addWidget(QLabel(t("settings.hotkey")), 0, 0)
        hotkey_row = QWidget()
        hotkey_layout = QHBoxLayout(hotkey_row)
        hotkey_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_hotkey = QLineEdit()
        self.settings_hotkey.setPlaceholderText("ctrl+alt+t")
        hotkey_layout.addWidget(self.settings_hotkey, 1)
        hotkey_capture = QPushButton(t("settings.capture"))
        hotkey_capture.clicked.connect(
            lambda: self._capture_hotkey(self.settings_hotkey)
        )
        hotkey_layout.addWidget(hotkey_capture)
        general_grid.addWidget(hotkey_row, 0, 1)
        self.settings_autostart = QCheckBox(t("settings.autostart"))
        general_grid.addWidget(self.settings_autostart, 1, 0, 1, 2)
        self.settings_monitor = QCheckBox(t("settings.monitor"))
        general_grid.addWidget(self.settings_monitor, 2, 0, 1, 2)
        self.settings_restore = QCheckBox(t("settings.restore_clipboard"))
        general_grid.addWidget(self.settings_restore, 3, 0, 1, 2)
        general_grid.addWidget(QLabel(t("settings.ui_language")), 4, 0)
        self.settings_language = QComboBox()
        for code, label in ui_language_options():
            self.settings_language.addItem(label, code)
        general_grid.addWidget(self.settings_language, 4, 1)
        general_grid.setColumnStretch(1, 1)
        general.addLayout(general_grid)
        layout.addWidget(general_card)

        ocr_card, ocr = self._card()
        ocr.addLayout(self._settings_header("settings.ocr_title", "ocr"))
        self.settings_ocr_enabled = QCheckBox(t("settings.ocr_enabled"))
        ocr.addWidget(self.settings_ocr_enabled)
        ocr_hotkey_row = QWidget()
        ocr_hotkey_layout = QHBoxLayout(ocr_hotkey_row)
        ocr_hotkey_layout.setContentsMargins(0, 0, 0, 0)
        ocr_hotkey_layout.addWidget(QLabel(t("settings.ocr_hotkey")))
        self.settings_ocr_hotkey = QLineEdit()
        self.settings_ocr_hotkey.setPlaceholderText("ctrl+alt+o")
        ocr_hotkey_layout.addWidget(self.settings_ocr_hotkey, 1)
        ocr_capture = QPushButton(t("settings.capture"))
        ocr_capture.clicked.connect(
            lambda: self._capture_hotkey(self.settings_ocr_hotkey)
        )
        ocr_hotkey_layout.addWidget(ocr_capture)
        ocr.addWidget(ocr_hotkey_row)
        ocr_language_row = QWidget()
        ocr_language_layout = QHBoxLayout(ocr_language_row)
        ocr_language_layout.setContentsMargins(0, 0, 0, 0)
        ocr_language_layout.addWidget(QLabel(t("settings.ocr_language")))
        self.settings_ocr_language = QComboBox()
        self.settings_ocr_language.addItems(self.source_labels)
        ocr_language_layout.addWidget(self.settings_ocr_language, 1)
        ocr.addWidget(ocr_language_row)
        ocr_note = self._muted(t("settings.ocr_note"))
        ocr_note.setWordWrap(True)
        ocr.addWidget(ocr_note)
        layout.addWidget(ocr_card)

        translate_card, translate = self._card()
        translate.addLayout(self._settings_header("nav.translate", "translation"))
        translate_grid = QGridLayout()
        translate_grid.setHorizontalSpacing(18)
        translate_grid.setVerticalSpacing(12)
        translate_grid.addWidget(QLabel(t("settings.default_target")), 0, 0)
        self.settings_target = QComboBox()
        self.settings_target.addItems(self.target_labels)
        translate_grid.addWidget(self.settings_target, 0, 1)
        translate_grid.addWidget(QLabel(t("settings.primary_engine")), 1, 0)
        self.settings_engine = QComboBox()
        for _label, code in ENGINE_OPTIONS:
            self.settings_engine.addItem(t(f"engine.option.{code}"), code)
        self.settings_engine.currentIndexChanged.connect(self._on_engine_changed)
        translate_grid.addWidget(self.settings_engine, 1, 1)
        translate_grid.setColumnStretch(1, 1)
        translate.addLayout(translate_grid)
        self.settings_backup = QCheckBox(t("settings.backup"))
        translate.addWidget(self.settings_backup)
        layout.addWidget(translate_card)

        engine_card, engine = self._card()
        engine.addLayout(self._settings_header("settings.engine_settings", "engine"))
        engine_body = QWidget()
        engine_body_layout = QVBoxLayout(engine_body)
        engine_body_layout.setContentsMargins(0, 0, 0, 0)
        engine_body_layout.setSpacing(0)
        self._engine_pages: dict[str, QWidget] = {}

        def add_engine_page(code: str, note: str) -> tuple[QWidget, QGridLayout]:
            page = QWidget()
            page_layout = QGridLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setHorizontalSpacing(14)
            page_layout.setVerticalSpacing(10)
            note_label = QLabel(note)
            note_label.setObjectName("Muted")
            note_label.setWordWrap(True)
            page_layout.addWidget(note_label, 0, 0, 1, 2)
            self._engine_pages[code] = page
            page.setVisible(False)
            engine_body_layout.addWidget(page)
            return page, page_layout

        add_engine_page("google", t("settings.engine_google"))
        add_engine_page("mymemory", t("settings.engine_mymemory"))
        _page, grid = add_engine_page("libretranslate", t("settings.engine_libretranslate"))
        grid.addWidget(QLabel(t("settings.endpoint")), 1, 0)
        self.settings_libre_endpoint = QLineEdit()
        grid.addWidget(self.settings_libre_endpoint, 1, 1)
        grid.addWidget(QLabel(t("settings.api_key")), 2, 0)
        self.settings_libre_key = QLineEdit()
        self.settings_libre_key.setEchoMode(QLineEdit.Password)
        grid.addWidget(self.settings_libre_key, 2, 1)
        grid.setColumnStretch(1, 1)
        _page, grid = add_engine_page("lingva", t("settings.engine_lingva"))
        grid.addWidget(QLabel(t("settings.endpoint")), 1, 0)
        self.settings_lingva_endpoint = QLineEdit()
        grid.addWidget(self.settings_lingva_endpoint, 1, 1)
        grid.setColumnStretch(1, 1)
        _page, grid = add_engine_page("llm", t("settings.engine_llm"))
        grid.addWidget(QLabel(t("settings.endpoint")), 1, 0)
        self.settings_llm_endpoint = QLineEdit()
        grid.addWidget(self.settings_llm_endpoint, 1, 1)
        grid.addWidget(QLabel(t("settings.model")), 2, 0)
        self.settings_llm_model = QLineEdit()
        grid.addWidget(self.settings_llm_model, 2, 1)
        grid.addWidget(QLabel(t("settings.api_key")), 3, 0)
        self.settings_llm_key = QLineEdit()
        self.settings_llm_key.setEchoMode(QLineEdit.Password)
        grid.addWidget(self.settings_llm_key, 3, 1)
        grid.setColumnStretch(1, 1)
        engine.addWidget(engine_body)
        layout.addWidget(engine_card)

        misc_card, misc = self._card()
        misc.addLayout(self._settings_header("settings.window_audio", "window"))
        misc_grid = QGridLayout()
        misc_grid.setHorizontalSpacing(18)
        misc_grid.setVerticalSpacing(10)
        misc_grid.addWidget(QLabel(t("settings.popup_autohide")), 0, 0)
        self.settings_autohide = QSpinBox()
        self.settings_autohide.setRange(0, 120)
        misc_grid.addWidget(self.settings_autohide, 0, 1)
        misc_grid.addWidget(QLabel(t("settings.tts_rate")), 1, 0)
        self.settings_tts_rate = QSpinBox()
        self.settings_tts_rate.setRange(-10, 10)
        misc_grid.addWidget(self.settings_tts_rate, 1, 1)
        misc_grid.addWidget(QLabel(t("settings.history_limit")), 2, 0)
        self.settings_history_limit = QSpinBox()
        self.settings_history_limit.setRange(50, 5000)
        self.settings_history_limit.setSingleStep(50)
        misc_grid.addWidget(self.settings_history_limit, 2, 1)
        self.settings_tray = QCheckBox(t("settings.tray_icon"))
        misc_grid.addWidget(self.settings_tray, 3, 0, 1, 2)
        misc_grid.setColumnStretch(1, 1)
        misc.addLayout(misc_grid)
        layout.addWidget(misc_card)

        background_card, background = self._card()
        background.addWidget(self._section_title(t("settings.background_title")))
        background_text = self._muted(t("settings.background_text"))
        background_text.setWordWrap(True)
        background.addWidget(background_text)
        background_buttons = QHBoxLayout()
        hide_button = QPushButton(t("settings.hide_to_tray"))
        hide_button.clicked.connect(self._hide_to_tray)
        background_buttons.addWidget(hide_button)
        quit_button = QPushButton(t("settings.quit"))
        quit_button.setObjectName("Danger")
        quit_button.clicked.connect(self._confirm_quit)
        background_buttons.addWidget(quit_button)
        background_buttons.addStretch(1)
        background.addLayout(background_buttons)
        layout.addWidget(background_card)

        save_row = QHBoxLayout()
        reset = QPushButton(t("settings.reset"))
        reset.clicked.connect(self._reset_settings)
        save_row.addWidget(reset)
        self.settings_status = QLabel("")
        self.settings_status.setObjectName("Status")
        save_row.addWidget(self.settings_status, 1)
        layout.addLayout(save_row)
        layout.addWidget(self._muted(t("settings.language_restart")))
        layout.addWidget(self._muted(t("settings.note")))
        layout.addStretch(1)

        self._wire_settings_dirty_tracking()
        scroll.setWidget(content)
        return scroll

    def _settings_header(self, title_key: str, section: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self._section_title(t(title_key)))
        row.addStretch(1)
        button = QPushButton(t("settings.save_section"))
        button.setObjectName("Accent")
        button.setEnabled(False)
        button.clicked.connect(
            lambda _checked=False, name=section: self._save_settings_section(name)
        )
        row.addWidget(button)
        self._settings_save_buttons[section] = button
        return row

    def _wire_settings_dirty_tracking(self) -> None:
        watched = (
            (self.settings_hotkey, "textChanged", "general"),
            (self.settings_autostart, "toggled", "general"),
            (self.settings_monitor, "toggled", "general"),
            (self.settings_restore, "toggled", "general"),
            (self.settings_language, "currentIndexChanged", "general"),
            (self.settings_ocr_enabled, "toggled", "ocr"),
            (self.settings_ocr_hotkey, "textChanged", "ocr"),
            (self.settings_ocr_language, "currentIndexChanged", "ocr"),
            (self.settings_target, "currentIndexChanged", "translation"),
            (self.settings_engine, "currentIndexChanged", "translation"),
            (self.settings_backup, "toggled", "translation"),
            (self.settings_libre_endpoint, "textChanged", "engine"),
            (self.settings_libre_key, "textChanged", "engine"),
            (self.settings_lingva_endpoint, "textChanged", "engine"),
            (self.settings_llm_endpoint, "textChanged", "engine"),
            (self.settings_llm_model, "textChanged", "engine"),
            (self.settings_llm_key, "textChanged", "engine"),
            (self.settings_autohide, "valueChanged", "window"),
            (self.settings_tts_rate, "valueChanged", "window"),
            (self.settings_history_limit, "valueChanged", "window"),
            (self.settings_tray, "toggled", "window"),
        )
        for widget, signal_name, section in watched:
            getattr(widget, signal_name).connect(
                lambda *_args, name=section: self._mark_settings_dirty(name)
            )

    def _mark_settings_dirty(self, section: str) -> None:
        if self._loading_settings:
            return
        button = self._settings_save_buttons.get(section)
        if button is not None:
            button.setEnabled(True)
        self.settings_status.setText(t("settings.unsaved"))
        self.settings_status.setStyleSheet(f"color: {YELLOW};")

    def _set_section_clean(self, section: str) -> None:
        button = self._settings_save_buttons.get(section)
        if button is not None:
            button.setEnabled(False)
        self._update_settings_status()

    def _mark_section_saved(self, section: str) -> None:
        button = self._settings_save_buttons.get(section)
        if button is not None:
            button.setEnabled(False)
        if any(item.isEnabled() for item in self._settings_save_buttons.values()):
            self.settings_status.setText(t("settings.unsaved"))
            self.settings_status.setStyleSheet(f"color: {YELLOW};")
        else:
            self.settings_status.setText(t("settings.saved_section"))
            self.settings_status.setStyleSheet(f"color: {GREEN};")

    def _update_settings_status(self) -> None:
        if not hasattr(self, "settings_status"):
            return
        if any(item.isEnabled() for item in self._settings_save_buttons.values()):
            self.settings_status.setText(t("settings.unsaved"))
            self.settings_status.setStyleSheet(f"color: {YELLOW};")
        else:
            self.settings_status.setText("")
            self.settings_status.setStyleSheet("")

    def _clear_settings_dirty(self) -> None:
        for button in self._settings_save_buttons.values():
            button.setEnabled(False)
        if hasattr(self, "settings_status"):
            self.settings_status.setText("")
            self.settings_status.setStyleSheet("")

    def _build_about_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        card, card_layout = self._card()
        card_layout.addWidget(self._section_title(t("about.title")))
        title = QLabel(t("app.name"))
        title.setObjectName("PageTitle")
        card_layout.addWidget(title)
        version = QLabel(t("app.version", version=APP_VERSION))
        version.setObjectName("Muted")
        card_layout.addWidget(version)
        content = QTextBrowser()
        content.setOpenExternalLinks(False)
        text = t("about.content")
        text += f"\n\n{t('about.data_dir')}:\n{DATA_DIR}"
        content.setPlainText(text)
        card_layout.addWidget(content, 1)
        layout.addWidget(card, 1)
        return page

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        return label

    def _confirm(self, title: str, text: str) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        yes = box.addButton(t("common.yes"), QMessageBox.ButtonRole.AcceptRole)
        no = box.addButton(t("common.no"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(no)
        box.exec()
        return box.clickedButton() is yes

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
                t("page.about"),
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
        self._loading_settings = True
        try:
            self._load_config_to_ui_impl()
        finally:
            self._loading_settings = False
            self._clear_settings_dirty()

    def _load_config_to_ui_impl(self) -> None:
        self._set_combo_code(
            self.source_combo, self.config.get("source_lang", "auto"), True
        )
        self._set_combo_code(
            self.target_combo, self.config.get("target_lang", "en"), False
        )
        self.settings_hotkey.setText(self.config.get("hotkey", SHORTCUT))
        self.settings_ocr_hotkey.setText(
            self.config.get("ocr_hotkey", "ctrl+alt+o")
        )
        self.settings_autostart.setChecked(bool(self.config.get("autostart", True)))
        self.settings_monitor.setChecked(
            bool(self.config.get("clipboard_monitor"))
        )
        self.settings_restore.setChecked(
            bool(self.config.get("restore_clipboard", True))
        )
        self.settings_ocr_enabled.setChecked(bool(self.config.get("ocr_enabled")))
        self._set_combo_code(
            self.settings_target, self.config.get("target_lang", "en"), False
        )
        engine_code = self.config.get("engine", "google")
        engine_index = self.settings_engine.findData(engine_code)
        if engine_index >= 0:
            self.settings_engine.setCurrentIndex(engine_index)
        self._on_engine_changed()
        self._set_combo_code(
            self.settings_ocr_language, self.config.get("ocr_language", "auto"), True
        )
        language_index = self.settings_language.findData(
            self.config.get("ui_language", "system")
        )
        if language_index >= 0:
            self.settings_language.setCurrentIndex(language_index)
        self.settings_backup.setChecked(bool(self.config.get("backup_engines")))
        self.settings_libre_endpoint.setText(
            self.config.get("libretranslate_endpoint", "")
        )
        self.settings_libre_key.setText(
            self.config.get("libretranslate_api_key", "")
        )
        self.settings_lingva_endpoint.setText(
            self.config.get("lingva_endpoint", "")
        )
        self.settings_llm_endpoint.setText(self.config.get("llm_endpoint", ""))
        self.settings_llm_model.setText(self.config.get("llm_model", ""))
        self.settings_llm_key.setText(self.config.get("llm_api_key", ""))
        self.settings_autohide.setValue(
            int(self.config.get("popup_autohide_seconds", 8) or 0)
        )
        self.settings_tts_rate.setValue(int(self.config.get("tts_rate", 0) or 0))
        self.settings_history_limit.setValue(
            int(self.config.get("history_limit", 500) or 500)
        )
        self.settings_tray.setChecked(bool(self.config.get("tray_icon", True)))
        self._update_chips()

    def _on_engine_changed(self, *_args) -> None:
        code = self.settings_engine.currentData() or "google"
        for page_code, page in self._engine_pages.items():
            page.setVisible(page_code == code)

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
        self._update_status_chips()

    def _update_status_chips(self) -> None:
        monitor = t(
            "status.state_on"
            if self.config.get("clipboard_monitor")
            else "status.state_off"
        )
        ocr = t(
            "status.state_on"
            if self.config.get("ocr_enabled")
            else "status.state_off"
        )
        self.monitor_chip.setText(t("status.monitor_chip", state=monitor))
        self.ocr_chip.setText(t("status.ocr_chip", state=ocr))

    def _on_source_changed(self, *_args) -> None:
        code = label_to_code(self.source_combo.currentText(), "auto")
        if self.config.get("source_lang") != code:
            self.config["source_lang"] = code
            self.store.save_config()

    def _search_target_language(self) -> None:
        current = label_to_code(
            self.target_combo.currentText(), self.config.get("target_lang", "en")
        )
        dialog = LanguagePickerDialog(self, current, self.ui_lang)
        if dialog.exec() == QDialog.Accepted and dialog.selected_code:
            self._set_target_language(dialog.selected_code)

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
        self.config["source_lang"] = source
        self.store.save_config()
        self._set_target_language(target)

    def _save_settings(self) -> None:
        for section in ("general", "ocr", "translation", "engine", "window"):
            button = self._settings_save_buttons.get(section)
            if button is not None and button.isEnabled():
                self._save_settings_section(section)

    def _save_settings_section(self, section: str) -> None:
        handlers = {
            "general": self._save_general_settings,
            "ocr": self._save_ocr_settings,
            "translation": self._save_translation_settings,
            "engine": self._save_engine_settings,
            "window": self._save_window_settings,
        }
        handler = handlers.get(section)
        if handler is not None:
            handler()

    def _validate_hotkey(self, spec: str) -> bool:
        from qbtranslator.core.win32util import parse_hotkey

        try:
            parse_hotkey(spec)
            return True
        except ValueError as error:
            self._notify(t("status.invalid_hotkey", error=error), error=True)
            return False

    def _restore_section_ui(self, values: dict) -> None:
        self._loading_settings = True
        try:
            if "hotkey" in values:
                self.settings_hotkey.setText(values["hotkey"])
            if "ocr_hotkey" in values:
                self.settings_ocr_hotkey.setText(values["ocr_hotkey"])
            if "ocr_enabled" in values:
                self.settings_ocr_enabled.setChecked(bool(values["ocr_enabled"]))
        finally:
            self._loading_settings = False

    def _save_general_settings(self) -> None:
        hotkey_spec = (self.settings_hotkey.text() or "").strip().lower()
        if not self._validate_hotkey(hotkey_spec):
            return
        ocr_hotkey_spec = (
            self.config.get("ocr_hotkey", "ctrl+alt+o") or ""
        ).strip().lower()
        if self.config.get("ocr_enabled") and hotkey_spec == ocr_hotkey_spec:
            self._notify(
                t("status.invalid_hotkey", error=t("settings.same_hotkey")),
                error=True,
            )
            return

        old = {
            "hotkey": self.config.get("hotkey", SHORTCUT),
            "autostart": bool(self.config.get("autostart", True)),
            "clipboard_monitor": bool(self.config.get("clipboard_monitor")),
            "restore_clipboard": bool(self.config.get("restore_clipboard", True)),
            "ui_language": self.config.get("ui_language", "system"),
        }
        ui_language = self.settings_language.currentData() or "system"
        self.config.update(
            {
                "hotkey": hotkey_spec,
                "autostart": self.settings_autostart.isChecked(),
                "clipboard_monitor": self.settings_monitor.isChecked(),
                "restore_clipboard": self.settings_restore.isChecked(),
                "ui_language": ui_language,
            }
        )
        if not self.store.save_config():
            self.config.update(old)
            self._notify(t("status.settings_save_failed"), error=True)
            return

        self._apply_hotkeys(main=True, ocr=False)
        if not self._hotkey_ok:
            self.config["hotkey"] = old["hotkey"]
            self.store.save_config()
            self._restore_section_ui({"hotkey": old["hotkey"]})
            self._apply_hotkeys(main=True, ocr=False)
            self._set_section_clean("general")
            self._notify(t("status.hotkey_failed"), error=True)
            return

        self._apply_clipboard_monitor()
        autostart_ok = self._apply_autostart()
        self._update_chips()
        self._mark_section_saved("general")
        if not autostart_ok:
            return
        if resolve_language(ui_language) != self.ui_lang:
            self._notify(t("settings.language_restart"))
        else:
            self._notify(t("status.settings_saved"))

    def _save_ocr_settings(self) -> None:
        ocr_enabled = self.settings_ocr_enabled.isChecked()
        ocr_hotkey_spec = (self.settings_ocr_hotkey.text() or "").strip().lower()
        if ocr_enabled:
            if not self._validate_hotkey(ocr_hotkey_spec):
                return
            hotkey_spec = (self.config.get("hotkey", SHORTCUT) or "").strip().lower()
            if ocr_hotkey_spec == hotkey_spec:
                self._notify(
                    t("status.invalid_hotkey", error=t("settings.same_hotkey")),
                    error=True,
                )
                return

        old = {
            "ocr_enabled": bool(self.config.get("ocr_enabled")),
            "ocr_hotkey": self.config.get("ocr_hotkey", "ctrl+alt+o"),
            "ocr_language": self.config.get("ocr_language", "auto"),
        }
        self.config.update(
            {
                "ocr_enabled": ocr_enabled,
                "ocr_hotkey": ocr_hotkey_spec or "ctrl+alt+o",
                "ocr_language": label_to_code(
                    self.settings_ocr_language.currentText(), "auto"
                ),
            }
        )
        if not self.store.save_config():
            self.config.update(old)
            self._notify(t("status.settings_save_failed"), error=True)
            return

        self._apply_hotkeys(main=False, ocr=True)
        if ocr_enabled and not self._ocr_hotkey_ok:
            self.config.update(old)
            self.store.save_config()
            self._restore_section_ui(old)
            self._apply_hotkeys(main=False, ocr=True)
            self._set_section_clean("ocr")
            self._notify(t("status.ocr_hotkey_failed"), error=True)
            return

        self._update_status_chips()
        self._mark_section_saved("ocr")
        self._notify(t("status.settings_saved"))

    def _save_translation_settings(self) -> None:
        target = label_to_code(self.settings_target.currentText(), "en")
        if not target or target == "auto":
            self._notify(t("status.target_required"), error=True)
            return
        old = {
            "target_lang": self.config.get("target_lang", "en"),
            "engine": self.config.get("engine", "google"),
            "backup_engines": bool(self.config.get("backup_engines")),
        }
        engine = self.settings_engine.currentData() or "google"
        self.config.update(
            {
                "target_lang": target,
                "engine": engine,
                "backup_engines": self.settings_backup.isChecked(),
            }
        )
        if not self.store.save_config():
            self.config.update(old)
            self._notify(t("status.settings_save_failed"), error=True)
            return

        self._set_combo_code(self.target_combo, target, False)
        if self.popup and self.popup.isVisible():
            self.popup.set_target_display(target)
        self._update_chips()
        self._mark_section_saved("translation")
        self._notify(t("status.settings_saved"))

    def _save_engine_settings(self) -> None:
        old = {
            "libretranslate_endpoint": self.config.get("libretranslate_endpoint", ""),
            "libretranslate_api_key": self.config.get("libretranslate_api_key", ""),
            "lingva_endpoint": self.config.get("lingva_endpoint", ""),
            "llm_endpoint": self.config.get("llm_endpoint", ""),
            "llm_model": self.config.get("llm_model", ""),
            "llm_api_key": self.config.get("llm_api_key", ""),
        }
        self.config.update(
            {
                "libretranslate_endpoint": self.settings_libre_endpoint.text().strip(),
                "libretranslate_api_key": self.settings_libre_key.text().strip(),
                "lingva_endpoint": self.settings_lingva_endpoint.text().strip(),
                "llm_endpoint": self.settings_llm_endpoint.text().strip(),
                "llm_model": self.settings_llm_model.text().strip(),
                "llm_api_key": self.settings_llm_key.text().strip(),
            }
        )
        if not self.store.save_config():
            self.config.update(old)
            self._notify(t("status.settings_save_failed"), error=True)
            return
        self._mark_section_saved("engine")
        self._notify(t("status.settings_saved"))

    def _save_window_settings(self) -> None:
        old = {
            "popup_autohide_seconds": self.config.get("popup_autohide_seconds", 8),
            "tts_rate": self.config.get("tts_rate", 0),
            "history_limit": self.config.get("history_limit", 500),
            "tray_icon": bool(self.config.get("tray_icon", True)),
        }
        self.config.update(
            {
                "popup_autohide_seconds": self.settings_autohide.value(),
                "tts_rate": self.settings_tts_rate.value(),
                "history_limit": self.settings_history_limit.value(),
                "tray_icon": self.settings_tray.isChecked(),
            }
        )
        if not self.store.save_config():
            self.config.update(old)
            self._notify(t("status.settings_save_failed"), error=True)
            return

        tray_ok = self._apply_tray()
        self._update_status_chips()
        self._mark_section_saved("window")
        if tray_ok:
            self._notify(t("status.settings_saved"))

    def _apply_settings(self, initial: bool = False) -> None:
        self._apply_hotkeys(initial=initial)
        self._apply_clipboard_monitor()
        self._apply_autostart()
        self._apply_tray()
        self._update_chips()
        self._default_status()

    def _apply_hotkeys(
        self, initial: bool = False, main: bool = True, ocr: bool = True
    ) -> None:
        if main:
            self.hotkey.stop()
            hotkey_spec = self.config.get("hotkey", SHORTCUT)
            try:
                self._hotkey_ok = self.hotkey.start(
                    hotkey_spec, self.hotkey_bridge.triggered.emit
                )
            except ValueError:
                self._hotkey_ok = False
            if self._hotkey_ok:
                self.hotkey_chip.setText(f"⌨  {hotkey_spec}")
                self.hotkey_chip.setStyleSheet("color: #9ec8ff;")
            else:
                self.hotkey_chip.setText(f"⌨  {t('status.hotkey_missing')}")
                self.hotkey_chip.setStyleSheet(f"color: {RED};")

        if not ocr:
            return
        self.ocr_hotkey.stop()
        ocr_enabled = bool(self.config.get("ocr_enabled"))
        self._ocr_hotkey_ok = True
        if ocr_enabled:
            self._ocr_hotkey_ok = False
            ocr_spec = self.config.get("ocr_hotkey", "ctrl+alt+o")
            try:
                from qbtranslator.core.win32util import parse_hotkey

                parse_hotkey(ocr_spec)
                if (
                    ocr_spec.strip().lower()
                    == self.config.get("hotkey", SHORTCUT).strip().lower()
                ):
                    raise ValueError(t("settings.same_hotkey"))
                self._ocr_hotkey_ok = self.ocr_hotkey.start(
                    ocr_spec, self.ocr_hotkey_bridge.triggered.emit
                )
            except ValueError:
                self._ocr_hotkey_ok = False
        if ocr_enabled and not self._ocr_hotkey_ok:
            self._notify(t("status.ocr_hotkey_failed"), error=True)

    def _capture_hotkey(self, edit: QLineEdit) -> None:
        self._pause_hotkeys()
        try:
            dialog = HotkeyCaptureDialog(self, (edit.text() or "").strip())
            if dialog.exec() == QDialog.Accepted and dialog.spec:
                edit.setText(dialog.spec)
                self.settings_status.setText(t("hotkey.valid"))
                self.settings_status.setStyleSheet(f"color: {GREEN};")
        finally:
            self._resume_hotkeys()

    def _pause_hotkeys(self) -> None:
        self.hotkey.stop()
        self.ocr_hotkey.stop()

    def _resume_hotkeys(self) -> None:
        self._apply_hotkeys()

    def _apply_clipboard_monitor(self) -> None:
        want = bool(self.config.get("clipboard_monitor"))
        if want and not self.clipboard.is_alive():
            self.clipboard = ClipboardWatcher(self._on_clipboard_text)
            self.clipboard.start()
        elif not want and self.clipboard.is_alive():
            self.clipboard.stop()

    def _on_clipboard_text(self, text: str) -> None:
        if not self.config.get("clipboard_monitor"):
            return
        if time.time() < self._suppress_clipboard_until:
            return
        text = (text or "").strip()
        if len(text) < 2 or len(text) > 5000:
            return
        lowered = text.lower()
        if lowered.startswith(("http://", "https://")) and " " not in text:
            return
        self.clipboard_bridge.text.emit(text)

    def _handle_clipboard_text(self, text: str) -> None:
        if not self.config.get("clipboard_monitor") or self._force_quit:
            return
        text = (text or "").strip()
        if not text or text == self._last_clipboard_text:
            return
        self._last_clipboard_text = text
        self._popup_translate(text)

    def _apply_autostart(self) -> bool:
        if os.environ.get("QB_DISABLE_AUTOSTART") == "1":
            return True
        want = bool(self.config.get("autostart", True))
        if not autostart.sync(want):
            self._notify(t("status.autostart_failed"), error=True)
            return False
        return True

    def _apply_tray(self) -> bool:
        if not bool(self.config.get("tray_icon", True)):
            if self.tray is not None:
                self.tray.stop()
                self.tray = None
            return True
        if self.tray is None or not self.tray.available:
            self._start_tray()
        self._update_status_chips()
        return bool(self.tray and self.tray.available)

    def _restore_geometry(self) -> None:
        value = self.config.get("window_geometry", "")
        match = re.fullmatch(r"(\d+)x(\d+)([+-]\d+)([+-]\d+)", value or "")
        if not match:
            return
        width, height = int(match.group(1)), int(match.group(2))
        x, y = int(match.group(3)), int(match.group(4))
        if width < 900 or height < 640:
            return
        rect = QRect(x, y, width, height)
        if not any(
            rect.intersects(screen.availableGeometry())
            for screen in QGuiApplication.screens()
        ):
            return
        self.setGeometry(rect)

    def _save_geometry(self) -> None:
        geometry = self.geometry()
        self.config["window_geometry"] = (
            f"{geometry.width()}x{geometry.height()}+{geometry.x()}+{geometry.y()}"
        )

    def _reset_settings(self) -> None:
        if not self._confirm(t("settings.reset"), t("settings.reset_confirm")):
            return
        self.config.clear()
        self.config.update(dict(DEFAULT_CONFIG))
        self.store.save_config()
        self._load_config_to_ui()
        self._apply_settings()
        self.settings_status.setText(t("settings.reset_done"))
        self.settings_status.setStyleSheet(f"color: {GREEN};")
        self._notify(t("settings.reset_done"))


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

    def _show_popup_loading(self, source_text: str) -> TranslationPopup:
        if self.popup:
            self.popup.close()
        self.popup = TranslationPopup(self, source_text, "auto")
        self._popup_seq += 1
        self.popup.request_id = self._popup_seq
        self.popup.show_loading(reposition=False)
        return self.popup

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
    def _on_hotkey(self) -> None:
        if self._capturing or self._force_quit:
            return
        self._capturing = True
        self._suppress_clipboard_until = time.time() + 1.6
        self._notify(t("status.selection"))
        task = CaptureTask(
            bool(self.config.get("restore_clipboard", True)), self.capture_signals
        )
        self.thread_pool.start(task)

    def _on_capture_finished(self, text: str) -> None:
        self._capturing = False
        self._suppress_clipboard_until = time.time() + 0.8
        try:
            self.clipboard.sync()
        except Exception:
            pass
        if text:
            self._popup_translate(text)
        else:
            self._notify(t("status.selection_empty"), error=True)

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------
    def _on_ocr_hotkey(self) -> None:
        if self._ocr_active or self._force_quit:
            return
        if not self.config.get("ocr_enabled"):
            self._notify(t("status.ocr_disabled"))
            return
        self._ocr_active = True
        if self.popup:
            self.popup.close()
        self._notify(t("status.ocr_selecting"))
        try:
            self._ocr_selector = RegionSelector()
            self._ocr_selector.region_selected.connect(self._on_ocr_region)
            self._ocr_selector.cancelled.connect(self._on_ocr_cancelled)
            self._ocr_selector.show()
        except Exception:
            self._ocr_selector = None
            self._ocr_active = False
            self._notify(t("status.ocr_failed"), error=True)

    def _on_ocr_cancelled(self) -> None:
        self._ocr_selector = None
        self._ocr_active = False
        self._notify(t("status.ocr_cancelled"))

    def _on_ocr_region(self, region) -> None:
        self._ocr_selector = None
        self._ocr_active = False
        if not region:
            self._notify(t("status.ocr_cancelled"))
            return
        self._notify(t("status.ocr_recognizing"))
        task = OCRTask(
            tuple(region),
            self.config.get("ocr_language", "auto"),
            self.ocr_signals,
        )
        self.thread_pool.start(task)

    def _on_ocr_finished(self, text: str, error: str) -> None:
        if error:
            popup = self._show_popup_loading("")
            message = error
            try:
                from qbtranslator.core.ocr import last_capture_path

                capture = last_capture_path()
                if capture:
                    message += f"\n\n{t('ocr.last_capture')}:\n{capture}"
            except Exception:
                pass
            popup.show_error(message)
            self._notify(t("status.ocr_failed"), error=True)
            return
        text = (text or "").strip()
        if not text:
            popup = self._show_popup_loading("")
            popup.show_error(t("status.ocr_empty"))
            self._notify(t("status.ocr_empty"), error=True)
            return
        self._notify(t("status.ocr_done"))
        self._popup_translate(text[:5000])

    # ------------------------------------------------------------------
    # Geçmiş / kelimeler
    # ------------------------------------------------------------------
    def _reload_history(self) -> None:
        self._history_records = list(self.store.history)
        query = ""
        if hasattr(self, "history_search"):
            query = fold_text(self.history_search.text().strip())
        filtered: list[dict] = []
        for record in self._history_records:
            if query:
                haystack = fold_text(
                    f"{record.get('source_text', '')} {record.get('translation', '')}"
                )
                if query not in haystack:
                    continue
            filtered.append(record)

        if hasattr(self, "history_list"):
            self.history_list.clear()
        if hasattr(self, "recent_list"):
            self.recent_list.clear()

        if hasattr(self, "recent_list"):
            if not self._history_records:
                empty = QListWidgetItem(t("history.empty"))
                empty.setFlags(Qt.NoItemFlags)
                self.recent_list.addItem(empty)
            else:
                for record in self._history_records[:7]:
                    text = self._format_history(record)
                    item = QListWidgetItem(text)
                    item.setData(Qt.UserRole, record.get("id", ""))
                    item.setToolTip(text)
                    self.recent_list.addItem(item)

        if hasattr(self, "history_list"):
            if not filtered:
                empty = QListWidgetItem(
                    t("history.empty") if not self._history_records else t("history.no_match")
                )
                empty.setFlags(Qt.NoItemFlags)
                self.history_list.addItem(empty)
            else:
                for record in filtered:
                    text = self._format_history(record)
                    item = QListWidgetItem(text)
                    item.setData(Qt.UserRole, record.get("id", ""))
                    item.setToolTip(
                        f"{record.get('source_text', '')}\n{record.get('translation', '')}"
                    )
                    self.history_list.addItem(item)

    def _record_by_id(self, record_id: str) -> dict | None:
        for record in self._history_records:
            if record.get("id") == record_id:
                return record
        return None

    @staticmethod
    def _format_history(record: dict) -> str:
        source = " ".join((record.get("source_text", "") or "").split())
        translation = " ".join((record.get("translation", "") or "").split())
        if len(source) > 60:
            source = source[:57] + "..."
        if len(translation) > 70:
            translation = translation[:67] + "..."
        return f"{source}   →   {translation}"

    def _selected_history(self) -> dict | None:
        if not hasattr(self, "history_list"):
            return None
        item = self.history_list.currentItem()
        if item is None:
            return None
        record_id = item.data(Qt.UserRole)
        return self._record_by_id(str(record_id)) if record_id else None

    def _copy_selected_history(self) -> None:
        record = self._selected_history()
        if not record:
            self._notify(t("status.select_record"), error=True)
            return
        self.copy_text(record.get("translation", ""))

    def _save_selected_history_word(self) -> None:
        record = self._selected_history()
        if not record:
            self._notify(t("status.select_record"), error=True)
            return
        saved = self._save_word(
            record.get("source_text", ""),
            record.get("translation", ""),
            record.get("source_lang", ""),
            record.get("target_lang", ""),
        )
        self._notify(t("status.word_saved") if saved else t("status.word_exists"))

    def _delete_selected_history(self) -> None:
        record = self._selected_history()
        if not record:
            self._notify(t("status.select_record"), error=True)
            return
        if not self._confirm(t("history.delete_selected"), t("history.delete_confirm")):
            return
        self.store.delete_history(record["id"])
        self._reload_history()

    def _clear_history(self) -> None:
        if not self.store.history:
            return
        if not self._confirm(
            t("history.clear_confirm_title"), t("history.clear_confirm")
        ):
            return
        self.store.clear_history()
        self._reload_history()

    def _open_selected_history_detail(self) -> None:
        record = self._selected_history()
        if not record:
            self._notify(t("status.select_record"), error=True)
            return
        meta = (
            f"{language_name(record.get('source_lang', ''), self.ui_lang)}"
            f" → {language_name(record.get('target_lang', ''), self.ui_lang)}"
            f"   •   {ENGINE_LABELS.get(record.get('engine', ''), record.get('engine', ''))}"
            f"   •   {record.get('ts', '')}"
        )
        dialog = TranslationDetailDialog(
            self,
            self,
            record.get("source_text", ""),
            record.get("translation", ""),
            meta,
        )
        dialog.exec()

    def _open_history_item(self, item: QListWidgetItem) -> None:
        record_id = item.data(Qt.UserRole)
        if not record_id:
            return
        record = self._record_by_id(str(record_id))
        if not record:
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

    def _reload_words(self) -> None:
        if not hasattr(self, "words_list"):
            return
        self.words_list.clear()
        query = ""
        if hasattr(self, "words_search"):
            query = fold_text(self.words_search.text().strip())
        self._words_view = []
        for record in self.store.words:
            if query:
                haystack = fold_text(
                    f"{record.get('word', '')} {record.get('translation', '')}"
                )
                if query not in haystack:
                    continue
            self._words_view.append(record)
        if not self._words_view:
            empty = QListWidgetItem(
                t("words.empty") if not self.store.words else t("words.no_match")
            )
            empty.setFlags(Qt.NoItemFlags)
            self.words_list.addItem(empty)
            return
        for record in self._words_view:
            word = record.get("word", "")
            translation = record.get("translation", "")
            item = QListWidgetItem(f"{word}   →   {translation}")
            item.setData(Qt.UserRole, record.get("id", ""))
            item.setToolTip(f"{word}\n{translation}")
            self.words_list.addItem(item)

    def _selected_word(self) -> dict | None:
        if not hasattr(self, "words_list"):
            return None
        item = self.words_list.currentItem()
        if item is None:
            return None
        word_id = item.data(Qt.UserRole)
        if not word_id:
            return None
        for record in self.store.words:
            if record.get("id") == word_id:
                return record
        return None

    def _delete_selected_word(self) -> None:
        record = self._selected_word()
        if not record:
            self._notify(t("status.select_record"), error=True)
            return
        if not self._confirm(t("words.delete_selected"), t("words.delete_confirm")):
            return
        self.store.delete_word(record["id"])
        self._reload_words()

    def _clear_words(self) -> None:
        if not self.store.words:
            return
        if not self._confirm(
            t("words.clear_confirm_title"), t("words.clear_confirm")
        ):
            return
        self.store.clear_words()
        self._reload_words()

    def _export_words_csv(self) -> None:
        if not self.store.words:
            self._notify(t("words.export_empty"), error=True)
            return
        path, _selected = QFileDialog.getSaveFileName(
            self,
            t("words.export_title"),
            "",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        t("words.csv_word"),
                        t("words.csv_translation"),
                        t("words.csv_source"),
                        t("words.csv_target"),
                        t("words.csv_date"),
                    ]
                )
                for record in self.store.words:
                    writer.writerow(
                        [
                            record.get("word", ""),
                            record.get("translation", ""),
                            record.get("source_lang", ""),
                            record.get("target_lang", ""),
                            record.get("created", ""),
                        ]
                    )
        except OSError as error:
            self._notify(t("words.export_error", error=error), error=True)
            return
        self._notify(t("words.export_success", path=path))

    def _open_study_mode(self) -> None:
        if not self.store.words:
            self._notify(t("words.study_empty"), error=True)
            return
        dialog = StudyDialog(self, self, list(self.store.words))
        dialog.exec()


    # ------------------------------------------------------------------
    # Kopyala / ses / kelime
    # ------------------------------------------------------------------
    def copy_text(self, text: str) -> None:
        if text:
            QApplication.clipboard().setText(text)
            self._suppress_clipboard_until = time.time() + 0.8
            try:
                self.clipboard.sync()
            except Exception:
                pass
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

    def start_in_background(self) -> None:
        if self.tray and self.tray.available:
            self.hide()
        else:
            self.showMinimized()

    def _hide_to_tray(self) -> None:
        self._save_geometry()
        self.store.save_config()
        if self.tray and self.tray.available:
            self.hide()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self.tray.show_balloon(
                    t("tray.balloon_title"),
                    t("tray.balloon_text"),
                )
        else:
            self.showMinimized()
            self._notify(t("status.tray_unavailable"))

    def _confirm_quit(self) -> None:
        if self._confirm(t("settings.quit"), t("settings.quit_confirm")):
            self._quit_app()

    def closeEvent(self, event) -> None:
        self._save_geometry()
        self.store.save_config()
        if self._force_quit or not (self.tray and self.tray.available):
            self._shutdown()
            event.accept()
            app = QApplication.instance()
            if app:
                app.quit()
            return
        self._hide_to_tray()
        event.ignore()

    def _quit_app(self) -> None:
        self._force_quit = True
        self._shutdown()
        app = QApplication.instance()
        if app:
            app.quit()

    def _shutdown(self) -> None:
        try:
            self._save_geometry()
            self.store.save_config()
        except Exception:
            pass
        for listener in (self.hotkey, self.ocr_hotkey):
            try:
                listener.stop()
            except Exception:
                pass
        try:
            self.clipboard.stop()
        except Exception:
            pass
        try:
            self.tts.stop()
        except Exception:
            pass
        try:
            if self._ocr_selector is not None:
                self._ocr_selector.close()
                self._ocr_selector = None
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
        print("hotkey_registered:", bool(self._hotkey_ok), flush=True)
        self._quit_app()
