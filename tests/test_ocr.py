"""OCR yardımcıları için hızlı birim testleri."""

from __future__ import annotations

import unittest

from qbtranslator import i18n
from qbtranslator.core.ocr import _tesseract_language, recognize_region


class OcrTests(unittest.TestCase):
    def tearDown(self) -> None:
        i18n.set_language("tr")

    def test_invalid_region_is_rejected_in_english(self) -> None:
        i18n.set_language("en")
        text, error = recognize_region(0, 0, 0, 0)
        self.assertEqual(text, "")
        self.assertEqual(error, "Invalid selection area.")

    def test_invalid_region_is_rejected_in_turkish(self) -> None:
        i18n.set_language("tr")
        text, error = recognize_region(0, 0, -5, 10)
        self.assertEqual(text, "")
        self.assertIn("Geçersiz", error)

    def test_tesseract_language_mapping(self) -> None:
        self.assertEqual(_tesseract_language("tr"), "tur")
        self.assertEqual(_tesseract_language("en"), "eng")
        self.assertEqual(_tesseract_language("zh-CN"), "chi_sim")
        self.assertEqual(_tesseract_language("pt-BR"), "por")
        self.assertEqual(_tesseract_language("auto"), "")
        self.assertEqual(_tesseract_language("bilinmeyen"), "")


if __name__ == "__main__":
    unittest.main()
