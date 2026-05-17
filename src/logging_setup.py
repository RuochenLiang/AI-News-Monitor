from __future__ import annotations

import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.secrets import sanitize_for_log


class SecretMaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = sanitize_for_log(record.getMessage())
        record.args = ()
        return True


def setup_logging(runtime_dir: Path) -> None:
    logs_dir = runtime_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    masking_filter = SecretMaskingFilter()

    app_handler = RotatingFileHandler(logs_dir / "app.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)
    app_handler.addFilter(masking_filter)

    error_handler = RotatingFileHandler(logs_dir / "error.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(masking_filter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(masking_filter)

    root.addHandler(app_handler)
    root.addHandler(error_handler)
    root.addHandler(console_handler)


def alert_logger(runtime_dir: Path) -> logging.Logger:
    logger = logging.getLogger("alerts")
    logs_dir = runtime_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    if not logger.handlers:
        handler = RotatingFileHandler(logs_dir / "alerts.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        handler.addFilter(SecretMaskingFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def cleanup_old_logs(runtime_dir: Path, retention_days: int) -> None:
    if retention_days <= 0:
        return
    logs_dir = runtime_dir / "logs"
    if not logs_dir.exists():
        return
    cutoff = time.time() - retention_days * 86400
    for path in logs_dir.glob("*.log*"):
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            logging.getLogger(__name__).warning("Could not remove old log file: %s", path)
