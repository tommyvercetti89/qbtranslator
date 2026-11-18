"""Windows açılışında otomatik başlatma."""

from __future__ import annotations

import sys
import winreg
from pathlib import Path

from qbtranslator.core.appinfo import APP_NAME

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
DEFAULT_VALUE_NAME = APP_NAME


def _interpreter() -> str:
    executable = Path(sys.executable)
    pythonw = executable.with_name("pythonw.exe")
    return str(pythonw if pythonw.exists() else executable)


def _launch_script() -> Path:
    return Path(__file__).resolve().parents[3] / "run.py"


def command_line() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --background'
    return f'"{_interpreter()}" "{_launch_script()}" --background'


def is_enabled(value_name: str = DEFAULT_VALUE_NAME) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _kind = winreg.QueryValueEx(key, value_name)
            return bool(value)
    except OSError:
        return False


def enable(value_name: str = DEFAULT_VALUE_NAME) -> bool:
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, command_line())
        return True
    except OSError:
        return False


def disable(value_name: str = DEFAULT_VALUE_NAME) -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, value_name)
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def sync(enabled: bool, value_name: str = DEFAULT_VALUE_NAME) -> bool:
    return enable(value_name) if enabled else disable(value_name)
