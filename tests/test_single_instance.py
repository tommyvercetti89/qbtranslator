"""Tek örnek (named mutex) testleri."""

from __future__ import annotations

import unittest
import uuid

from qbtranslator.core.single_instance import SingleInstance


class SingleInstanceTests(unittest.TestCase):
    def test_second_instance_is_detected(self) -> None:
        name = f"QBTranslatorTest_{uuid.uuid4().hex}"
        first = SingleInstance(name)
        try:
            self.assertFalse(first.already_running)
            second = SingleInstance(name)
            try:
                self.assertTrue(second.already_running)
            finally:
                second.close()
        finally:
            first.close()

    def test_close_is_idempotent(self) -> None:
        instance = SingleInstance(f"QBTranslatorTest_{uuid.uuid4().hex}")
        instance.close()
        instance.close()
        self.assertIsNone(instance.handle)


if __name__ == "__main__":
    unittest.main()
