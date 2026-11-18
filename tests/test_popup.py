"""Translation popup state tests."""

from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication

from qbtranslator import i18n
from qbtranslator.core.translator import TranslationOutcome
from qbtranslator.ui.popup import TranslationPopup


class FakeApp:
    def __init__(self) -> None:
        self.config = {"target_lang": "en", "popup_autohide_seconds": 0}
        self.closed = []

    def copy_text(self, _text: str) -> None:
        return None

    def speak_text(self, _text: str) -> bool:
        return False

    def save_popup_word(self, _popup) -> bool:
        return True

    def on_popup_target_changed(self, _popup, _code: str) -> None:
        return None

    def swap_popup(self, _popup) -> None:
        return None

    def on_popup_closed(self, popup) -> None:
        self.closed.append(popup)


class PopupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        i18n.set_language("tr")
        self.fake_app = FakeApp()
        self.popup = TranslationPopup(self.fake_app, "Merhaba", "tr")

    def tearDown(self) -> None:
        self.popup.close()
        self.app.processEvents()
        i18n.set_language("tr")

    def test_result_enables_actions(self) -> None:
        outcome = TranslationOutcome(
            text="Hello", source_lang="tr", target_lang="en", engine="mymemory"
        )
        self.popup.show_result(outcome)

        self.assertIs(self.popup.result, outcome)
        self.assertTrue(self.popup.copy_button.isEnabled())
        self.assertTrue(self.popup.swap_button.isEnabled())

    def test_loading_clears_result_and_disables_actions(self) -> None:
        outcome = TranslationOutcome(
            text="Hello", source_lang="tr", target_lang="en", engine="mymemory"
        )
        self.popup.show_result(outcome)
        self.popup.show_loading(reposition=False)

        self.assertIsNone(self.popup.result)
        self.assertFalse(self.popup.copy_button.isEnabled())
        self.assertFalse(self.popup.swap_button.isEnabled())

    def test_error_clears_result(self) -> None:
        outcome = TranslationOutcome(
            text="Hello", source_lang="tr", target_lang="en", engine="mymemory"
        )
        self.popup.show_result(outcome)
        self.popup.show_error("error")

        self.assertIsNone(self.popup.result)
        self.assertFalse(self.popup.copy_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
