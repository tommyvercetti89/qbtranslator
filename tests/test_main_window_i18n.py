"""Main window language wiring tests."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from qbtranslator.application import create_application
from qbtranslator.core import storage
from qbtranslator.ui.main_window import MainWindow

os.environ["QB_DISABLE_AUTOSTART"] = "1"


class MainWindowLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or create_application([])

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="qb_window_test_"))
        self._old_data_dir = storage.DATA_DIR
        storage.DATA_DIR = self.temp_dir
        self._write_config("en")

    def tearDown(self) -> None:
        if hasattr(self, "window"):
            self.window._force_quit = True
            self.window._shutdown()
            self.window.deleteLater()
            self.app.processEvents()
        storage.DATA_DIR = self._old_data_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_config(self, language: str) -> None:
        config = {
            "ui_language": language,
            "target_lang": "en",
            "source_lang": "auto",
            "engine": "mymemory",
            "backup_engines": True,
            "hotkey": "ctrl+alt+shift+f12",
            "ocr_language": "tr",
            "tray_icon": False,
        }
        (self.temp_dir / "config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

    def _create_window(self) -> MainWindow:
        return MainWindow()

    def test_english_interface(self) -> None:
        self.window = self._create_window()

        self.assertEqual(self.window.page_title.text(), "Translate")
        self.assertEqual(self.window.source_combo.itemText(0), "Auto-detect")
        self.assertEqual(self.window.target_combo.itemText(0), "Turkish (tr)")
        self.assertTrue(self.window.translate_button.text().startswith("Translate"))
        self.assertTrue(self.window.nav_buttons[1].text().strip().endswith("History"))
        self.assertEqual(self.window.settings_language.currentData(), "en")

    def test_turkish_interface(self) -> None:
        self._write_config("tr")
        self.window = self._create_window()

        self.assertEqual(self.window.page_title.text(), "Çeviri")
        self.assertEqual(self.window.source_combo.itemText(0), "Otomatik algıla")
        self.assertEqual(self.window.target_combo.itemText(0), "Türkçe (tr)")
        self.assertTrue(self.window.translate_button.text().startswith("Çevir"))


if __name__ == "__main__":
    unittest.main()
