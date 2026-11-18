"""Geliştirme ortamından uygulamayı başlatır."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

if __name__ == "__main__":
    application = importlib.import_module("qbtranslator.application")
    raise SystemExit(application.main())
