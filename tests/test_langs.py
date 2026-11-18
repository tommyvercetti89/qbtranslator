"""langs.py arama/normalizasyon testleri."""

from __future__ import annotations

import unittest

from qbtranslator.core.langs import (
    filter_target_languages,
    fold_text,
    label_to_code,
    language_label,
    source_labels,
    target_labels,
)


class LangTests(unittest.TestCase):
    def test_turkish_fold_handles_dotted_and_dotless_i(self) -> None:
        self.assertEqual(fold_text("İSTANBUL"), "istanbul")
        self.assertIn("isik", fold_text("IŞIK"))
        self.assertEqual(fold_text("Türkçe"), "turkce")

    def test_filter_matches_turkish_without_diacritics(self) -> None:
        codes = {code for _label, code in filter_target_languages("turkce")}
        self.assertIn("tr", codes)

    def test_filter_matches_english_name(self) -> None:
        codes = {code for _label, code in filter_target_languages("english")}
        self.assertIn("en", codes)

    def test_label_to_code(self) -> None:
        self.assertEqual(label_to_code("Türkçe (tr)"), "tr")
        self.assertEqual(label_to_code("Otomatik algıla"), "auto")
        self.assertEqual(label_to_code("Turkish (tr)"), "tr")
        self.assertEqual(label_to_code("Auto-detect"), "auto")

    def test_english_labels(self) -> None:
        self.assertEqual(language_label("en", "en"), "English (en)")
        self.assertEqual(language_label("auto", "en"), "Auto-detect")
        self.assertIn("Turkish (tr)", source_labels("en"))
        self.assertIn("English (en)", target_labels("en"))
        self.assertNotIn("Türkçe (tr)", target_labels("en"))

    def test_filter_returns_requested_ui_language(self) -> None:
        results = filter_target_languages("turkce", "en")
        self.assertIn(("Turkish (tr)", "tr"), results)


if __name__ == "__main__":
    unittest.main()
