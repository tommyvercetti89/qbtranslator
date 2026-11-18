"""i18n catalog and formatting tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from qbtranslator.i18n import I18n, resolve_language

LOCALES = Path(__file__).resolve().parents[1] / "src" / "qbtranslator" / "locales"


class I18nTests(unittest.TestCase):
    @staticmethod
    def _catalog(language: str) -> dict[str, str]:
        with open(LOCALES / f"{language}.json", encoding="utf-8") as handle:
            return json.load(handle)

    def test_catalog_keys_match(self) -> None:
        self.assertEqual(set(self._catalog("tr")), set(self._catalog("en")))

    def test_turkish_and_english_lookup(self) -> None:
        self.assertEqual(I18n("tr").t("app.subtitle"), "masaüstü çevirmen")
        self.assertEqual(I18n("en").t("app.subtitle"), "desktop translator")

    def test_format_parameters(self) -> None:
        english = I18n("en")
        self.assertEqual(english.t("translate.char_count", count=5), "5 characters")
        self.assertEqual(
            english.t("status.engine_chip", engine="MyMemory"),
            "Engine: MyMemory",
        )

    def test_resolve_explicit_language(self) -> None:
        self.assertEqual(resolve_language("en"), "en")
        self.assertEqual(resolve_language("tr"), "tr")

    def test_catalogs_have_no_em_dash(self) -> None:
        for language in ("tr", "en"):
            for key, value in self._catalog(language).items():
                self.assertNotIn("\u2014", value, f"{language}:{key}")
                self.assertNotIn("\u2013", value, f"{language}:{key}")


if __name__ == "__main__":
    unittest.main()
