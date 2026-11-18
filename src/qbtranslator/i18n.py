"""Küçük, bağımlılıksız i18n katmanı."""

from __future__ import annotations

import ctypes
import json
import locale
from pathlib import Path

from qbtranslator.core.appinfo import APP_NAME

SUPPORTED = ("tr", "en")
SYSTEM = "system"
_LOCALES_DIR = Path(__file__).resolve().parent / "locales"


def _system_language() -> str:
    try:
        if hasattr(ctypes, "windll"):
            lang_id = int(ctypes.windll.kernel32.GetUserDefaultUILanguage())
            primary = lang_id & 0x3FF
            return "tr" if primary == 0x1F else "en"
    except Exception:
        pass
    try:
        code = (locale.getlocale()[0] or "").lower()
        return "tr" if code.startswith("tr") else "en"
    except Exception:
        return "en"


def resolve_language(preference: str | None) -> str:
    value = (preference or SYSTEM).strip().lower()
    if value in SUPPORTED:
        return value
    return _system_language()


class I18n:
    def __init__(self, language: str = "tr") -> None:
        self._fallback = self._load("tr")
        self._catalogs: dict[str, dict[str, str]] = {
            "tr": self._fallback,
            "en": self._load("en"),
        }
        self.set_language(language)

    @staticmethod
    def _load(language: str) -> dict[str, str]:
        path = _LOCALES_DIR / f"{language}.json"
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return {str(key): str(value) for key, value in data.items()}
        except (OSError, json.JSONDecodeError):
            pass
        return {}

    def set_language(self, language: str) -> None:
        code = language if language in SUPPORTED else "tr"
        self._language = code
        self._catalog = self._catalogs.get(code, self._fallback)

    @property
    def language(self) -> str:
        return self._language

    def t(self, key: str, **params) -> str:
        template = self._catalog.get(key) or self._fallback.get(key) or key
        try:
            return template.format(**params)
        except (KeyError, ValueError):
            return template


_i18n = I18n("tr")


def set_language(language: str) -> None:
    _i18n.set_language(language)


def get_language() -> str:
    return _i18n.language


def t(key: str, **params) -> str:
    return _i18n.t(key, **params)


def ui_language_options() -> list[tuple[str, str]]:
    return [
        ("system", t("language.system")),
        ("tr", t("language.tr")),
        ("en", t("language.en")),
    ]


def app_title() -> str:
    return t("app.name")


def app_name() -> str:
    return APP_NAME
