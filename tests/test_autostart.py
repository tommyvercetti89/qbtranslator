"""Otomatik başlatma yardımcıları testleri."""

from __future__ import annotations

import unittest
import uuid

from qbtranslator.core import autostart


class AutostartTests(unittest.TestCase):
    def test_command_line_points_to_background_start(self) -> None:
        command = autostart.command_line()
        self.assertIn("--background", command)
        self.assertTrue(command.startswith('"'))

    def test_registry_value_roundtrip(self) -> None:
        # Test değeri benzersizdir ve sonunda temizlenir; kullanıcı ayarına dokunmaz.
        value_name = f"QBTranslatorTest_{uuid.uuid4().hex}"
        try:
            self.assertTrue(autostart.enable(value_name))
            self.assertTrue(autostart.is_enabled(value_name))
            self.assertTrue(autostart.disable(value_name))
            self.assertFalse(autostart.is_enabled(value_name))
        finally:
            autostart.disable(value_name)


if __name__ == "__main__":
    unittest.main()
