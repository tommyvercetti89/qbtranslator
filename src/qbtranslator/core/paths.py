"""Uygulama yolları ve veri klasörü."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "QBTranslator"
PACKAGE_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = PACKAGE_DIR / "assets"


def _local_data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / APP_NAME / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base


def resolve_data_dir() -> Path:
    override = os.environ.get("QB_DATA_DIR")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return _local_data_dir()


DATA_DIR = resolve_data_dir()
