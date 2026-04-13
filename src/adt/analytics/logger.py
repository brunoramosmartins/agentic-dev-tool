"""Rotating JSON line logger for supervised learning events."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from adt.analytics.events import LearningEvent

LEARNING_LOG_NAME = "learning.jsonl"
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5
_LOGGER_NAME = "adt.learning"
_failure_reported: bool = False


def learning_log_path(log_dir: Path | None = None) -> Path:
    """Return the absolute path to ``learning.jsonl``."""
    base = log_dir if log_dir is not None else Path.home() / ".adt" / "logs"
    return base / LEARNING_LOG_NAME


class _LearningFormatter(logging.Formatter):
    """Serialize a log record payload directly as JSON."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - trivial
        payload = getattr(record, "learning", None)
        if isinstance(payload, str):
            return payload
        return record.getMessage()


def setup_learning_logger(
    *,
    log_dir: Path | None = None,
    max_bytes: int = _MAX_BYTES,
    backup_count: int = _BACKUP_COUNT,
) -> Path:
    """Attach a :class:`RotatingFileHandler` for the learning logger.

    Args:
        log_dir: Directory that should contain ``learning.jsonl``; defaults
            to ``~/.adt/logs``.
        max_bytes: Per-file size before rollover (default 10 MB).
        backup_count: Number of rotated files to retain (default 5).

    Returns:
        The absolute path to the active log file.

    Idempotent: repeated calls reuse the existing handler instead of
    stacking duplicates, so ``log_learning_event`` can call this lazily.
    """
    base = log_dir if log_dir is not None else Path.home() / ".adt" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    path = learning_log_path(base)

    log = logging.getLogger(_LOGGER_NAME)
    log.setLevel(logging.INFO)
    log.propagate = False

    for handler in log.handlers:
        if (
            isinstance(handler, RotatingFileHandler)
            and Path(handler.baseFilename).resolve() == path.resolve()
        ):
            return path

    handler = RotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(_LearningFormatter())
    log.addHandler(handler)
    return path


def log_learning_event(
    event: LearningEvent,
    *,
    log_dir: Path | None = None,
) -> None:
    """Append one :class:`LearningEvent` to the rotating learning log.

    Failures are swallowed (the analytics layer is best-effort; a write
    failure must never break the user-facing command).
    """
    global _failure_reported  # noqa: PLW0603
    try:
        setup_learning_logger(log_dir=log_dir)
        log = logging.getLogger(_LOGGER_NAME)
        serialized = json.dumps(event.model_dump(mode="json"), default=str)
        log.info("", extra={"learning": serialized})
        _failure_reported = False
    except Exception:  # noqa: BLE001 - best-effort analytics
        if not _failure_reported:
            _failure_reported = True
            from adt.logging.json_log import log_adt

            _warn_log = logging.getLogger("adt.analytics")
            log_adt(
                _warn_log,
                logging.WARNING,
                event="learning_log_failed",
                detail="Could not write to learning log; analytics are inactive.",
            )
