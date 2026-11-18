"""Global kısayol ayrıştırma testleri."""

from __future__ import annotations

import unittest

from qbtranslator.core.win32util import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_NOREPEAT,
    MOD_SHIFT,
    parse_hotkey,
)


class ParseHotkeyTests(unittest.TestCase):
    def test_combined_modifiers(self) -> None:
        modifiers, key = parse_hotkey("ctrl+alt+shift+t")
        self.assertEqual(modifiers, MOD_CONTROL | MOD_ALT | MOD_SHIFT | MOD_NOREPEAT)
        self.assertEqual(key, ord("T"))

    def test_function_key(self) -> None:
        modifiers, key = parse_hotkey("ctrl+F12")
        self.assertEqual(modifiers, MOD_CONTROL | MOD_NOREPEAT)
        self.assertEqual(key, 0x7B)

    def test_bare_escape_requires_explicit_permission(self) -> None:
        with self.assertRaises(ValueError):
            parse_hotkey("esc")
        modifiers, key = parse_hotkey("esc", require_modifier=False)
        self.assertEqual(modifiers, MOD_NOREPEAT)
        self.assertEqual(key, 0x1B)

    def test_empty_and_unknown_specs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_hotkey("")
        with self.assertRaises(ValueError):
            parse_hotkey("ctrl+alt+bilinmeyen")

    def test_modifier_only_spec_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_hotkey("ctrl+alt")


if __name__ == "__main__":
    unittest.main()
