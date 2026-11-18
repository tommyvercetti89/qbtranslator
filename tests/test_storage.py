"""storage.py için geçici veri diziniyle çalışan testler."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="qb_storage_test_"))
        self._old_data_dir = os.environ.get("QB_DATA_DIR")
        os.environ["QB_DATA_DIR"] = str(self.temp_dir)
        from qbtranslator.core import paths, storage

        importlib.reload(paths)
        self.storage = importlib.reload(storage)

    def tearDown(self) -> None:
        if self._old_data_dir is None:
            os.environ.pop("QB_DATA_DIR", None)
        else:
            os.environ["QB_DATA_DIR"] = self._old_data_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_invalid_config_types_fall_back_to_defaults(self) -> None:
        raw = {
            "hotkey": 123,
            "history_limit": "abc",
            "tts_rate": 99,
            "popup_autohide_seconds": -5,
            "clipboard_monitor": "yes",
            "target_lang": True,
        }
        (self.temp_dir / "config.json").write_text(
            json.dumps(raw), encoding="utf-8"
        )

        store = self.storage.Store()

        self.assertEqual(store.config["hotkey"], self.storage.DEFAULT_CONFIG["hotkey"])
        self.assertEqual(store.config["history_limit"], 500)
        self.assertEqual(store.config["tts_rate"], 10)
        self.assertEqual(store.config["popup_autohide_seconds"], 0)
        self.assertFalse(store.config["clipboard_monitor"])
        self.assertEqual(store.config["target_lang"], "tr")

    def test_corrupt_json_is_recovered_from_backup(self) -> None:
        store = self.storage.Store()
        store.config["target_lang"] = "de"
        self.assertTrue(store.save_config())
        self.assertTrue(store.save_config())

        (self.temp_dir / "config.json").write_text("{bozuk json", encoding="utf-8")
        recovered = self.storage.Store()

        self.assertEqual(recovered.config["target_lang"], "de")
        self.assertTrue((self.temp_dir / "config.json.corrupt").exists())

    def test_duplicate_record_ids_are_removed(self) -> None:
        history = [
            {"id": "same", "source_text": "bir", "translation": "one"},
            {"id": "same", "source_text": "iki", "translation": "two"},
        ]
        (self.temp_dir / "history.json").write_text(
            json.dumps(history, ensure_ascii=False), encoding="utf-8"
        )

        store = self.storage.Store()

        self.assertEqual(len(store.history), 2)
        self.assertEqual(len({item["id"] for item in store.history}), 2)

    def test_save_failure_is_reported(self) -> None:
        store = self.storage.Store()
        with patch("qbtranslator.core.storage.os.replace", side_effect=OSError("disk full")):
            saved = store.save_config()

        self.assertFalse(saved)
        self.assertIn("disk full", store.last_error)

    def test_bad_history_limit_does_not_crash(self) -> None:
        store = self.storage.Store()
        store.config["history_limit"] = "bozuk"
        store.add_history("merhaba", "hello", "tr", "en", "test")
        self.assertEqual(len(store.history), 1)


if __name__ == "__main__":
    unittest.main()
