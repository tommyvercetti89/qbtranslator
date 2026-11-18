"""applog.py - paketli sürümde de görülebilen dosya günlüğü."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logging(data_dir: Path) -> None:
    """Döner dosya günlüğü kurar; aynı süreçte iki kez çağrılabilir."""
    log_dir = Path(data_dir) / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    target = (log_dir / "app.log").resolve()
    root = logging.getLogger()
    for handler in root.handlers:
        if isinstance(handler, logging.FileHandler):
            try:
                if Path(handler.baseFilename).resolve() == target:
                    return
            except OSError:
                pass

    handler = logging.handlers.RotatingFileHandler(
        target,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    def _excepthook(exc_type, exc_value, traceback):
        logging.getLogger("unhandled").critical(
            "Yakalanmamış hata", exc_info=(exc_type, exc_value, traceback)
        )
        sys.__excepthook__(exc_type, exc_value, traceback)

    sys.excepthook = _excepthook
