"""Ana pencere ayar, geçmiş, kelime, pano ve OCR bağlantı testleri."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from qbtranslator.application import create_application
from qbtranslator.core import storage
from qbtranslator.ui.main_window import MainWindow, OCRSignals, OCRTask

os.environ["QB_DISABLE_AUTOSTART"] = "1"


class WindowFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or create_application([])

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="qb_window_features_"))
        self._old_data_dir = storage.DATA_DIR
        storage.DATA_DIR = self.temp_dir
        self._write_config()

    def tearDown(self) -> None:
        if hasattr(self, "window"):
            self.window._force_quit = True
            self.window._shutdown()
            self.window.deleteLater()
            self.app.processEvents()
        storage.DATA_DIR = self._old_data_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_config(self, **overrides) -> None:
        config = {
            "ui_language": "en",
            "target_lang": "en",
            "source_lang": "auto",
            "engine": "google",
            "hotkey": "ctrl+alt+shift+f9",
            "ocr_hotkey": "ctrl+alt+shift+f8",
            "ocr_enabled": False,
            "tray_icon": False,
            "autostart": False,
            "clipboard_monitor": False,
            "backup_engines": False,
        }
        config.update(overrides)
        (self.temp_dir / "config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

    def _create_window(self) -> MainWindow:
        self.window = MainWindow()
        return self.window

    def test_settings_save_and_reload(self) -> None:
        window = self._create_window()
        window.settings_target.setCurrentText("German (de)")
        engine_index = window.settings_engine.findData("libretranslate")
        self.assertGreaterEqual(engine_index, 0)
        window.settings_engine.setCurrentIndex(engine_index)
        window.settings_libre_endpoint.setText("http://127.0.0.1:5000")
        window.settings_libre_key.setText("secret")
        window.settings_backup.setChecked(True)
        window.settings_autohide.setValue(15)
        window.settings_tts_rate.setValue(-4)
        window.settings_history_limit.setValue(750)
        window.settings_tray.setChecked(False)
        window.source_combo.setCurrentText("Turkish (tr)")
        window._on_source_changed()

        window._save_settings()

        self.assertEqual(window.config["target_lang"], "de")
        self.assertEqual(window.config["engine"], "libretranslate")
        self.assertEqual(window.config["libretranslate_endpoint"], "http://127.0.0.1:5000")
        self.assertEqual(window.config["libretranslate_api_key"], "secret")
        self.assertTrue(window.config["backup_engines"])
        self.assertEqual(window.config["popup_autohide_seconds"], 15)
        self.assertEqual(window.config["tts_rate"], -4)
        self.assertEqual(window.config["history_limit"], 750)
        self.assertEqual(window.config["source_lang"], "tr")
        self.assertFalse(window.config["tray_icon"])

        saved = json.loads((self.temp_dir / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["target_lang"], "de")
        self.assertEqual(saved["tts_rate"], -4)

        window._force_quit = True
        window._shutdown()
        window.deleteLater()
        del self.window
        self.app.processEvents()

        reloaded = self._create_window()
        self.assertEqual(reloaded.settings_target.currentText(), "German (de)")
        self.assertEqual(reloaded.settings_engine.currentData(), "libretranslate")
        self.assertEqual(reloaded.settings_libre_endpoint.text(), "http://127.0.0.1:5000")
        self.assertEqual(reloaded.settings_autohide.value(), 15)
        self.assertEqual(reloaded.settings_tts_rate.value(), -4)
        self.assertEqual(reloaded.settings_history_limit.value(), 750)
        self.assertEqual(reloaded.source_combo.currentText(), "Turkish (tr)")
        self.assertFalse(reloaded.settings_tray.isChecked())

    def test_invalid_hotkey_is_rejected(self) -> None:
        window = self._create_window()
        previous = window.config["hotkey"]
        window.settings_hotkey.setText("bozuk")
        window._save_settings()
        self.assertEqual(window.config["hotkey"], previous)
        self.assertIn("shortcut", window.status_label.text().lower())

    def test_history_search_copy_and_delete(self) -> None:
        window = self._create_window()
        window.store.add_history("Merhaba dünya", "Hello world", "tr", "en", "google")
        window.store.add_history("Kitaplar", "Books", "tr", "en", "google")
        window._reload_history()
        self.assertEqual(window.history_list.count(), 2)

        window.history_search.setText("merhaba")
        self.assertEqual(window.history_list.count(), 1)
        window.history_search.clear()
        window._reload_history()

        window.history_list.setCurrentRow(0)
        window._copy_selected_history()
        self.assertEqual(QApplication.clipboard().text(), "Books")

        window._save_selected_history_word()
        self.assertEqual(len(window.store.words), 1)
        self.assertEqual(window.store.words[0]["word"], "Kitaplar")

        with patch.object(window, "_confirm", return_value=True):
            window._delete_selected_history()
        self.assertEqual(len(window.store.history), 1)

    def test_history_detail_opens(self) -> None:
        window = self._create_window()
        window.store.add_history("Merhaba", "Hello", "tr", "en", "google")
        window._reload_history()
        window.history_list.setCurrentRow(0)

        created: list[tuple] = []

        class FakeDialog:
            def __init__(self, *args) -> None:
                created.append(args)

            def exec(self) -> int:
                return 0

        with patch(
            "qbtranslator.ui.main_window.TranslationDetailDialog",
            FakeDialog,
        ):
            window._open_selected_history_detail()
        self.assertEqual(len(created), 1)

    def test_words_filter_and_export(self) -> None:
        window = self._create_window()
        window.store.add_word("merhaba", "hello", "tr", "en")
        window.store.add_word("kitap", "book", "tr", "en")
        window._reload_words()
        self.assertEqual(window.words_list.count(), 2)

        window.words_search.setText("kitap")
        self.assertEqual(window.words_list.count(), 1)
        window.words_search.clear()
        window._reload_words()

        export_path = self.temp_dir / "words.csv"
        with patch(
            "qbtranslator.ui.main_window.QFileDialog.getSaveFileName",
            return_value=(str(export_path), "CSV (*.csv)"),
        ):
            window._export_words_csv()
        content = export_path.read_text(encoding="utf-8-sig")
        self.assertIn("Word", content)
        self.assertIn("Translation", content)
        self.assertIn("merhaba", content)
        self.assertIn("kitap", content)

    def test_clipboard_monitor_lifecycle_and_filtering(self) -> None:
        self._write_config(clipboard_monitor=True)
        window = self._create_window()
        self.assertTrue(window.clipboard.is_alive())

        with patch.object(window, "_popup_translate") as translate:
            window.config["clipboard_monitor"] = True
            window._suppress_clipboard_until = 0
            window._last_clipboard_text = ""
            window._on_clipboard_text("x")
            window._on_clipboard_text("https://example.com")
            window._on_clipboard_text("Bu metin çevrilmeli.")
            self.app.processEvents()
            translate.assert_called_once_with("Bu metin çevrilmeli.")

        window.config["clipboard_monitor"] = False
        window._apply_clipboard_monitor()
        self.assertFalse(window.clipboard.is_alive())

    def test_ocr_task_and_empty_state(self) -> None:
        window = self._create_window()
        signals = OCRSignals()
        results: list[tuple[str, str]] = []
        signals.finished.connect(lambda text, error: results.append((text, error)))
        task = OCRTask((10, 10, 100, 40), "tr", signals)
        with patch(
            "qbtranslator.ui.main_window.recognize_region",
            return_value=("Merhaba", ""),
        ):
            task.run()
        self.assertEqual(results, [("Merhaba", "")])

        with patch.object(window, "_popup_translate") as translate:
            window._on_ocr_finished("Merhaba", "")
        translate.assert_called_once_with("Merhaba")

    def test_ocr_hotkey_disabled_only_notifies(self) -> None:
        window = self._create_window()
        with patch.object(window, "_notify") as notify:
            window._on_ocr_hotkey()
        notify.assert_called_once()
        self.assertFalse(window._ocr_active)

    def test_pages_include_about(self) -> None:
        window = self._create_window()
        self.assertEqual(window.stack.count(), 5)
        window._set_page(4)
        self.assertEqual(window.page_title.text(), "About")

    def test_window_geometry_persists(self) -> None:
        window = self._create_window()
        window.setGeometry(120, 140, 1040, 720)
        window._save_geometry()
        self.assertEqual(window.config["window_geometry"], "1040x720+120+140")

        window._force_quit = True
        window._shutdown()
        window.deleteLater()
        del self.window
        self.app.processEvents()

        reloaded = self._create_window()
        self.assertEqual(reloaded.width(), 1040)
        self.assertEqual(reloaded.height(), 720)

    def test_section_save_buttons_track_changes(self) -> None:
        window = self._create_window()
        self.assertFalse(
            any(button.isEnabled() for button in window._settings_save_buttons.values())
        )

        window.settings_tts_rate.setValue(5)

        self.assertTrue(window._settings_save_buttons["window"].isEnabled())
        self.assertFalse(window._settings_save_buttons["general"].isEnabled())
        self.assertEqual(window.settings_status.text(), "Unsaved changes")

        window._settings_save_buttons["window"].click()

        self.assertFalse(window._settings_save_buttons["window"].isEnabled())
        self.assertEqual(window.config["tts_rate"], 5)
        self.assertEqual(window.settings_status.text(), "Saved")

    def test_general_and_ocr_section_saves(self) -> None:
        window = self._create_window()

        window.settings_hotkey.setText("ctrl+alt+shift+f3")
        self.assertTrue(window._settings_save_buttons["general"].isEnabled())
        window._settings_save_buttons["general"].click()

        self.assertEqual(window.config["hotkey"], "ctrl+alt+shift+f3")
        self.assertFalse(window._settings_save_buttons["general"].isEnabled())
        self.assertFalse(window.config["tray_icon"])

        window.settings_ocr_enabled.setChecked(True)
        window.settings_ocr_hotkey.setText("ctrl+alt+shift+f2")
        self.assertTrue(window._settings_save_buttons["ocr"].isEnabled())
        window._settings_save_buttons["ocr"].click()

        self.assertTrue(window.config["ocr_enabled"])
        self.assertEqual(window.config["ocr_hotkey"], "ctrl+alt+shift+f2")
        self.assertFalse(window._settings_save_buttons["ocr"].isEnabled())
        self.assertIn("on", window.ocr_chip.text().lower())


if __name__ == "__main__":
    unittest.main()
