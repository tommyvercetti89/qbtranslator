"""Yeni PySide6 iletişim kutuları ve yardımcı bileşen testleri."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QTextBrowser

from qbtranslator import i18n
from qbtranslator.ui.detail_dialog import TranslationDetailDialog
from qbtranslator.ui.hotkey_dialog import HotkeyCaptureDialog, key_to_token
from qbtranslator.ui.language_picker import LanguagePickerDialog
from qbtranslator.ui.region_selector import RegionSelector
from qbtranslator.ui.study_dialog import StudyDialog


class FakeApp:
    def __init__(self) -> None:
        self.copied: list[str] = []
        self.spoken: list[str] = []

    def copy_text(self, text: str) -> None:
        self.copied.append(text)

    def speak_text(self, text: str) -> bool:
        self.spoken.append(text)
        return False


def _key(key: int, modifiers: Qt.KeyboardModifier = Qt.NoModifier) -> QKeyEvent:
    return QKeyEvent(QEvent.KeyPress, key, modifiers)


class HotkeyDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_key_token_mapping(self) -> None:
        self.assertEqual(key_to_token(Qt.Key_A), "a")
        self.assertEqual(key_to_token(Qt.Key_7), "7")
        self.assertEqual(key_to_token(Qt.Key_F12), "f12")
        self.assertEqual(key_to_token(Qt.Key_Space), "space")
        self.assertIsNone(key_to_token(Qt.Key_Escape))
        self.assertIsNone(key_to_token(Qt.Key_Menu))

    def test_captures_combination(self) -> None:
        dialog = HotkeyCaptureDialog(None)
        try:
            dialog.keyPressEvent(_key(Qt.Key_T, Qt.ControlModifier | Qt.ShiftModifier))
            self.assertEqual(dialog.spec, "ctrl+shift+t")
            self.assertTrue(dialog.save_button.isEnabled())
        finally:
            dialog.deleteLater()

    def test_bare_key_is_rejected(self) -> None:
        dialog = HotkeyCaptureDialog(None)
        try:
            dialog.keyPressEvent(_key(Qt.Key_T))
            self.assertEqual(dialog.spec, "")
            self.assertFalse(dialog.save_button.isEnabled())
        finally:
            dialog.deleteLater()

    def test_escape_cancels_dialog(self) -> None:
        dialog = HotkeyCaptureDialog(None)
        try:
            dialog.keyPressEvent(_key(Qt.Key_Escape))
            self.assertEqual(dialog.result(), 0)
        finally:
            dialog.deleteLater()


class LanguagePickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_accent_insensitive_search_and_selection(self) -> None:
        i18n.set_language("tr")
        dialog = LanguagePickerDialog(None, "en", "tr")
        try:
            dialog.search.setText("turkce")
            codes = [
                dialog.list.item(index).data(Qt.UserRole)
                for index in range(dialog.list.count())
            ]
            self.assertIn("tr", codes)
            dialog.list.setCurrentRow(codes.index("tr"))
            dialog._accept_selected()
            self.assertEqual(dialog.selected_code, "tr")
            self.assertEqual(dialog.result(), 1)
        finally:
            dialog.deleteLater()

    def test_empty_search_disables_save(self) -> None:
        i18n.set_language("en")
        dialog = LanguagePickerDialog(None, "en", "en")
        try:
            dialog.search.setText("zzzzzz")
            self.assertEqual(dialog.list.count(), 0)
            self.assertFalse(dialog.ok_button.isEnabled())
            self.assertIn("0", dialog.count.text())
        finally:
            dialog.deleteLater()


class StudyDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        i18n.set_language("tr")
        self.words = [
            {
                "word": "merhaba",
                "translation": "hello",
                "source_lang": "tr",
                "target_lang": "en",
            },
            {
                "word": "kitap",
                "translation": "book",
                "source_lang": "tr",
                "target_lang": "en",
            },
        ]

    def test_reveal_and_navigation(self) -> None:
        dialog = StudyDialog(None, FakeApp(), self.words)
        try:
            self.assertEqual(dialog.word.text(), "merhaba")
            self.assertNotEqual(dialog.translation.text(), "hello")
            dialog._reveal()
            self.assertEqual(dialog.translation.text(), "hello")
            dialog._next()
            self.assertEqual(dialog.word.text(), "kitap")
            self.assertNotEqual(dialog.translation.text(), "book")
            dialog._previous()
            self.assertEqual(dialog.word.text(), "merhaba")
        finally:
            dialog.deleteLater()

    def test_keyboard_shortcuts(self) -> None:
        dialog = StudyDialog(None, FakeApp(), self.words)
        try:
            dialog.keyPressEvent(_key(Qt.Key_Space))
            self.assertEqual(dialog.translation.text(), "hello")
            dialog.keyPressEvent(_key(Qt.Key_Right))
            self.assertEqual(dialog.index, 1)
            dialog.keyPressEvent(_key(Qt.Key_Left))
            self.assertEqual(dialog.index, 0)
        finally:
            dialog.deleteLater()

    def test_empty_word_list(self) -> None:
        dialog = StudyDialog(None, FakeApp(), [])
        try:
            self.assertEqual(dialog.word.text(), i18n.t("words.study_empty"))
            self.assertFalse(dialog.reveal_button.isEnabled())
        finally:
            dialog.deleteLater()


class DetailDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_shows_source_and_translation(self) -> None:
        dialog = TranslationDetailDialog(
            None, FakeApp(), "Merhaba dünya", "Hello world", "tr -> en"
        )
        try:
            browsers = dialog.findChildren(QTextBrowser)
            self.assertEqual(len(browsers), 2)
            self.assertEqual(browsers[0].toPlainText(), "Merhaba dünya")
            self.assertEqual(browsers[1].toPlainText(), "Hello world")
        finally:
            dialog.deleteLater()


class RegionSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_selection_rectangle(self) -> None:
        selector = RegionSelector()
        try:
            selector._start = QPoint(10, 20)
            selector._current = QPoint(110, 220)
            rect = selector._selection_rect()
            self.assertEqual(rect.x(), 10)
            self.assertEqual(rect.y(), 20)
            # QRect iki noktayı da kapsar; 10..110 aralığı 101 pikseldir.
            self.assertEqual(rect.width(), 101)
            self.assertEqual(rect.height(), 201)
        finally:
            selector.deleteLater()

    def test_escape_emits_cancelled(self) -> None:
        selector = RegionSelector()
        cancelled: list[bool] = []
        selector.cancelled.connect(lambda: cancelled.append(True))
        try:
            selector.keyPressEvent(_key(Qt.Key_Escape))
            self.assertEqual(cancelled, [True])
        finally:
            if not selector._done:
                selector.deleteLater()

    def test_release_reports_physical_cursor_region(self) -> None:
        selector = RegionSelector()
        selector._start = QPoint(10, 20)
        selector._current = QPoint(110, 220)
        selector._start_physical = (100, 200)
        selected: list[tuple] = []
        selector.region_selected.connect(lambda region: selected.append(region))
        event = QMouseEvent(
            QEvent.MouseButtonRelease,
            QPointF(110, 220),
            QPointF(300, 400),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )
        try:
            with patch(
                "qbtranslator.ui.region_selector.get_cursor_pos",
                return_value=(300, 400),
            ):
                selector.mouseReleaseEvent(event)
            self.assertEqual(selected, [(100, 200, 200, 200)])
        finally:
            if not selector._done:
                selector.deleteLater()


if __name__ == "__main__":
    unittest.main()
