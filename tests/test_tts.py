"""qbtranslator.core.tts.py için süreç yaşam döngüsü testleri (PowerShell çalıştırmaz)."""

from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import patch

from qbtranslator.core import tts


class FakeProcess:
    def __init__(self, index: int) -> None:
        self.pid = 1000 + index
        self.killed = threading.Event()
        self.started = threading.Event()

    def wait(self, timeout=None):
        self.started.set()
        self.killed.wait(timeout)
        return 0

    def poll(self):
        return 0 if self.killed.is_set() else None

    def kill(self):
        self.killed.set()


class SpeechEngineTests(unittest.TestCase):
    def test_stop_kills_running_process(self) -> None:
        processes: list[FakeProcess] = []

        def fake_popen(*_args, **_kwargs):
            process = FakeProcess(len(processes))
            processes.append(process)
            return process

        engine = tts.SpeechEngine()
        with patch("qbtranslator.core.tts.subprocess.Popen", side_effect=fake_popen), patch(
            "qbtranslator.core.tts._assign_process_to_job"
        ), patch.object(engine, "_job", None):
            worker = threading.Thread(target=engine.speak, args=("merhaba",), daemon=True)
            worker.start()
            self.assertTrue(processes[0].started.wait(1.0))
            self.assertTrue(engine.is_speaking)

            engine.stop()
            worker.join(timeout=1.0)

        self.assertFalse(worker.is_alive())
        self.assertTrue(processes[0].killed.is_set())
        self.assertFalse(engine.is_speaking)

    def test_second_speak_kills_first(self) -> None:
        processes: list[FakeProcess] = []
        lock = threading.Lock()

        def fake_popen(*_args, **_kwargs):
            with lock:
                process = FakeProcess(len(processes))
                processes.append(process)
            return process

        engine = tts.SpeechEngine()
        with patch("qbtranslator.core.tts.subprocess.Popen", side_effect=fake_popen), patch(
            "qbtranslator.core.tts._assign_process_to_job"
        ), patch.object(engine, "_job", None):
            first = threading.Thread(target=engine.speak, args=("birinci",), daemon=True)
            first.start()
            self.assertTrue(processes[0].started.wait(1.0))

            second = threading.Thread(target=engine.speak, args=("ikinci",), daemon=True)
            second.start()

            deadline = time.time() + 1.0
            while len(processes) < 2 and time.time() < deadline:
                time.sleep(0.01)

            self.assertGreaterEqual(len(processes), 2)
            self.assertTrue(processes[0].killed.is_set())
            self.assertLessEqual(len(processes), 2)

            engine.stop()
            first.join(timeout=1.0)
            second.join(timeout=1.0)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertTrue(processes[1].killed.is_set())


if __name__ == "__main__":
    unittest.main()
