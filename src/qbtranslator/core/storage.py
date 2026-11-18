"""
storage.py - JSON tabanlı yerel depolama.

Varsayılan veri dizini: %LOCALAPPDATA%\\QBTranslator\\data
Testler ve taşınabilir kullanım için QB_DATA_DIR ortam değişkeni kullanılabilir.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
import uuid
from pathlib import Path

from qbtranslator.core.langs import fold_text
from qbtranslator.core.paths import DATA_DIR

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "ui_language": "system",
    "hotkey": "ctrl+alt+t",
    "ocr_hotkey": "ctrl+alt+o",
    "ocr_enabled": False,
    "ocr_language": "auto",
    "autostart": True,
    "tray_icon": True,
    "target_lang": "tr",
    "source_lang": "auto",
    "engine": "google",
    "backup_engines": False,
    "clipboard_monitor": False,
    "restore_clipboard": True,
    "popup_autohide_seconds": 8,
    "tts_rate": 0,
    "history_limit": 500,
    "libretranslate_endpoint": "https://libretranslate.com",
    "libretranslate_api_key": "",
    "lingva_endpoint": "https://lingva.ml",
    "llm_endpoint": "http://localhost:11434/v1",
    "llm_model": "",
    "llm_api_key": "",
    "window_geometry": "",
}


def _validate_config_value(key: str, value, default):
    """Bozuk/elle düzenlenmiş config değerlerinin açılışı bozmasını engeller."""
    if isinstance(default, bool):
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
    elif isinstance(default, int):
        if isinstance(value, int) and not isinstance(value, bool):
            if key == "popup_autohide_seconds":
                return max(0, min(3600, value))
            if key == "tts_rate":
                return max(-10, min(10, value))
            if key == "history_limit":
                return max(1, min(5000, value))
            return value
    elif isinstance(default, str):
        if isinstance(value, str):
            return value
    logger.warning("config: '%s' değeri geçersiz; varsayılan kullanılıyor.", key)
    return default


def _validate_config(raw: dict) -> dict:
    return {
        key: _validate_config_value(key, raw.get(key, default), default)
        for key, default in DEFAULT_CONFIG.items()
    }


def _normalize_records(raw, kind: str) -> list[dict]:
    """Geçmiş/kayıtlı kelime dosyalarındaki bozuk kayıtları tolere eder."""
    if not isinstance(raw, list):
        return []
    fields = (
        ("ts", "source_text", "translation", "source_lang", "target_lang", "engine")
        if kind == "history"
        else ("word", "translation", "source_lang", "target_lang", "created")
    )
    records: list[dict] = []
    seen_ids: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        record_id = item.get("id")
        if not record_id:
            continue
        record_id = str(record_id)
        if record_id in seen_ids:
            # Aynı id iki kez varsa Treeview çöker; yeni id verip veriyi koru.
            record_id = uuid.uuid4().hex
        seen_ids.add(record_id)
        record = dict(item)
        record["id"] = record_id
        for field in fields:
            value = record.get(field, "")
            record[field] = value if isinstance(value, str) else ("" if value is None else str(value))
        records.append(record)
    return records


class Store:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.last_error = ""
        raw_config = self._load_json("config.json", {})
        self.config = _validate_config(raw_config if isinstance(raw_config, dict) else {})
        self.history = _normalize_records(self._load_json("history.json", []), "history")
        self.words = _normalize_records(self._load_json("words.json", []), "words")

    # ------------------------------------------------------------------
    # Düşük seviye JSON işlemleri
    # ------------------------------------------------------------------
    @staticmethod
    def _backup_path(path: Path) -> Path:
        return path.with_name(path.name + ".bak")

    def _load_json(self, name: str, default):
        path = DATA_DIR / name
        backup = self._backup_path(path)
        for candidate in (path, backup):
            try:
                # utf-8-sig: BOM'lu dosyaları da okuyabilir (PowerShell/Notepad kaynaklı).
                with open(candidate, "r", encoding="utf-8-sig") as handle:
                    data = json.load(handle)
                if candidate == backup:
                    logger.warning("%s bozuk/eksik; yedekten okundu.", name)
                    try:
                        shutil.copy2(backup, path)
                    except OSError:
                        pass
                return data
            except FileNotFoundError:
                continue
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
                logger.warning("%s okunamadı (%s): %s", name, candidate.name, error)
                if candidate == path:
                    corrupt = path.with_name(path.name + ".corrupt")
                    try:
                        if not corrupt.exists():
                            os.replace(path, corrupt)
                    except OSError:
                        pass
        return default

    def _save_json(self, name: str, value) -> bool:
        path = DATA_DIR / name
        temp = path.with_name(path.name + ".tmp")
        backup = self._backup_path(path)
        try:
            with open(temp, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError:
                    pass
            if path.exists():
                try:
                    shutil.copy2(path, backup)
                except OSError as error:
                    logger.warning("%s yedeği yazılamadı: %s", name, error)
            os.replace(temp, path)
            self.last_error = ""
            return True
        except OSError as error:
            self.last_error = f"{name}: {error}"
            logger.exception("%s yazılamadı", name)
            try:
                temp.unlink()
            except OSError:
                pass
            return False

    # ------------------------------------------------------------------
    # Ayar
    # ------------------------------------------------------------------
    def save_config(self) -> bool:
        with self._lock:
            return self._save_json("config.json", self.config)

    # ------------------------------------------------------------------
    # Geçmiş
    # ------------------------------------------------------------------
    def add_history(
        self,
        source_text: str,
        translation: str,
        source_lang: str,
        target_lang: str,
        engine: str,
    ) -> None:
        source_text = (source_text or "").strip()
        translation = (translation or "").strip()
        if not source_text or not translation:
            return
        with self._lock:
            if self.history:
                last = self.history[0]
                if (
                    last.get("source_text") == source_text
                    and last.get("translation") == translation
                ):
                    return
            record = {
                "id": uuid.uuid4().hex,
                "ts": time.strftime("%Y-%m-%d %H:%M"),
                "source_text": source_text,
                "translation": translation,
                "source_lang": source_lang or "",
                "target_lang": target_lang or "",
                "engine": engine or "",
            }
            self.history.insert(0, record)
            try:
                limit = int(self.config.get("history_limit") or 500)
            except (TypeError, ValueError):
                limit = 500
            limit = max(1, min(5000, limit))
            del self.history[limit:]
            self._save_json("history.json", self.history)

    def clear_history(self) -> None:
        with self._lock:
            self.history = []
            self._save_json("history.json", self.history)

    def delete_history(self, record_id: str) -> None:
        with self._lock:
            self.history = [item for item in self.history if item.get("id") != record_id]
            self._save_json("history.json", self.history)

    # ------------------------------------------------------------------
    # Kayıtlı kelimeler
    # ------------------------------------------------------------------
    def add_word(
        self,
        word: str,
        translation: str,
        source_lang: str,
        target_lang: str,
    ) -> dict:
        word = (word or "").strip()
        translation = (translation or "").strip()
        with self._lock:
            for existing in self.words:
                if (
                    fold_text(existing.get("word", "")) == fold_text(word)
                    and fold_text(existing.get("translation", "")) == fold_text(translation)
                ):
                    return existing
            record = {
                "id": uuid.uuid4().hex,
                "word": word,
                "translation": translation,
                "source_lang": source_lang or "",
                "target_lang": target_lang or "",
                "created": time.strftime("%Y-%m-%d %H:%M"),
            }
            self.words.insert(0, record)
            self._save_json("words.json", self.words)
            return record

    def delete_word(self, word_id: str) -> None:
        with self._lock:
            self.words = [item for item in self.words if item.get("id") != word_id]
            self._save_json("words.json", self.words)

    def clear_words(self) -> None:
        with self._lock:
            self.words = []
            self._save_json("words.json", self.words)
