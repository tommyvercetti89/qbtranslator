"""
storage.py — JSON tabanlı yerel depolama.

Veriler uygulama klasöründeki data/ dizininde tutulur:
  data/config.json   — ayarlar
  data/history.json  — çeviri geçmişi
  data/words.json    — kayıtlı kelimeler
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path

from appinfo import APP_NAME

APP_DIR = Path(__file__).resolve().parent


def _is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _resolve_data_dir() -> Path:
    """
    Veri dizini:
      * QB_DATA_DIR ortam değişkeni (testler/taşınabilir kullanım için)
      * Kaynak mod: uygulama klasörü / data
      * Paketli (PyInstaller): exe'nin yanındaki data (kurulum dizini)
        yazılamıyorsa %LOCALAPPDATA%\\QBTranslator\\data
    """
    override = os.environ.get("QB_DATA_DIR")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidate = exe_dir / "data"
        if _is_writable(candidate):
            return candidate
        local = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / APP_NAME / "data"
        local.mkdir(parents=True, exist_ok=True)
        return local
    candidate = APP_DIR / "data"
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


DATA_DIR = _resolve_data_dir()

DEFAULT_CONFIG = {
    "hotkey": "ctrl+alt+t",
    "ocr_hotkey": "ctrl+alt+o",
    "ocr_enabled": False,
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


class Store:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        raw_config = self._load_json("config.json", {})
        self.config = raw_config if isinstance(raw_config, dict) else {}
        merged = dict(DEFAULT_CONFIG)
        merged.update({key: value for key, value in self.config.items() if key in DEFAULT_CONFIG})
        self.config = merged

        raw_history = self._load_json("history.json", [])
        self.history: list[dict] = [
            item for item in raw_history if isinstance(item, dict) and item.get("id")
        ] if isinstance(raw_history, list) else []

        raw_words = self._load_json("words.json", [])
        self.words: list[dict] = [
            item for item in raw_words if isinstance(item, dict) and item.get("id")
        ] if isinstance(raw_words, list) else []

    # ------------------------------------------------------------------
    # Düşük seviye JSON işlemleri
    # ------------------------------------------------------------------
    def _load_json(self, name: str, default):
        path = DATA_DIR / name
        try:
            # utf-8-sig: BOM'lu dosyaları da okuyabilir (PowerShell/Notepad kaynaklı).
            with open(path, "r", encoding="utf-8-sig") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return default

    def _save_json(self, name: str, value) -> None:
        path = DATA_DIR / name
        temp = path.with_suffix(".tmp")
        try:
            with open(temp, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
            os.replace(temp, path)
        except OSError:
            # Yazma başarısız olursa sessizce devam et (uygulama çalışmaya devam eder).
            pass

    # ------------------------------------------------------------------
    # Ayar
    # ------------------------------------------------------------------
    def save_config(self) -> None:
        with self._lock:
            self._save_json("config.json", self.config)

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
            limit = int(self.config.get("history_limit") or 500)
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
                    existing.get("word", "").casefold() == word.casefold()
                    and existing.get("translation", "").casefold() == translation.casefold()
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
