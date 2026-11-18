"""Release metadata and public asset checks."""

from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

from PySide6.QtGui import QIcon, QImage
from PySide6.QtWidgets import QApplication

from qbtranslator import APP_VERSION

ROOT = Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_versions_are_consistent(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(pyproject["project"]["version"], APP_VERSION)

        version_info = (ROOT / "build_tools" / "version_info.txt").read_text(
            encoding="utf-8"
        )
        parts = APP_VERSION.split(".")
        numeric = f"({parts[0]}, {parts[1]}, {parts[2]}, 0)"
        self.assertIn(numeric, version_info)

    def test_public_assets_load(self) -> None:
        assets = ROOT / "src" / "qbtranslator" / "assets"
        self.assertTrue((assets / "QBTranslator.ico").exists())
        icon = QIcon(str(assets / "QBTranslator.ico"))
        self.assertFalse(icon.isNull())

        check = QImage(str(assets / "check.png"))
        self.assertFalse(check.isNull())
        self.assertEqual((check.width(), check.height()), (16, 16))

    def test_public_readme_has_no_expanded_user_path(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"C:\\Users\\[^\s]+", text))
        self.assertIn("C:\\path\\to\\QBTranslator", text)


if __name__ == "__main__":
    unittest.main()
