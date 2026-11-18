"""
tts.py — Windows SAPI ile sesli okuma.

Ek paket gerekmez: PowerShell üzerinden System.Speech kullanılır.
Metin, işlem argümanı yerine ortam değişkeniyle aktarılır; böylece
tırnak/kaçış sorunları ve Türkçe karakter bozulması yaşanmaz.

ÖNEMLİ: Konuşma PowerShell alt sürecinde çalışır. Uygulama kapandığında
bu alt sürecin de kesin olarak sonlanması için Windows Job Object
(JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE) kullanılır; uygulama süreci sona
erdiğinde işletim sistemi tüm alt süreçleri otomatik öldürür.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import threading
from ctypes import wintypes

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
MAX_SPEAK_CHARS = 3000

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

JobObjectExtendedLimitInformation = 9
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ULONG_PTR),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
kernel32.CreateJobObjectW.restype = wintypes.HANDLE
kernel32.SetInformationJobObject.argtypes = [
    wintypes.HANDLE,
    ctypes.c_int,
    ctypes.c_void_p,
    wintypes.DWORD,
]
kernel32.SetInformationJobObject.restype = wintypes.BOOL
kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL


def _create_kill_on_close_job():
    """Uygulama kapanınca alt süreçleri öldüren Job Object oluşturur."""
    try:
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            job,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            kernel32.CloseHandle(job)
            return None
        return job
    except Exception:
        return None


def _assign_process_to_job(job, pid: int) -> None:
    if not job:
        return
    try:
        handle = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, int(pid))
        if not handle:
            return
        try:
            kernel32.AssignProcessToJobObject(job, handle)
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        pass


class SpeechEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._job = _create_kill_on_close_job()

    # ------------------------------------------------------------------
    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    # ------------------------------------------------------------------
    def speak(self, text: str, rate: int = 0) -> None:
        """Metni sesli okur. Çağıran thread'i meşgul eder; UI'da thread ile çağırın."""
        text = (text or "").strip()
        if not text:
            return
        text = text[:MAX_SPEAK_CHARS]
        try:
            rate = max(-10, min(10, int(rate)))
        except (TypeError, ValueError):
            rate = 0

        self.stop()

        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = {rate}; "
            "$t = $env:MTT_TTS_TEXT; "
            "if ($t -and $t.Trim().Length -gt 0) { $s.Speak($t) }"
        )
        env = os.environ.copy()
        env["MTT_TTS_TEXT"] = text

        try:
            proc = subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                creationflags=CREATE_NO_WINDOW,
            )
        except OSError:
            return

        _assign_process_to_job(self._job, proc.pid)

        with self._lock:
            self._proc = proc

        try:
            proc.wait(timeout=180)
        except subprocess.TimeoutExpired:
            self._kill(proc)
        finally:
            with self._lock:
                if self._proc is proc:
                    self._proc = None

    def stop(self) -> None:
        with self._lock:
            proc = self._proc
            self._proc = None
        if proc:
            self._kill(proc)

    @staticmethod
    def _kill(proc: subprocess.Popen) -> None:
        if proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass
