"""JSON line logging to ``~/.adt/logs`` for observability."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AdtJsonFormatter(logging.Formatter):
    """Emit one JSON object per log record (``adt`` extra merges into payload)."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize ``record`` including optional ``adt`` dict from ``extra``."""
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }
        adt = getattr(record, "adt", None)
        if isinstance(adt, dict):
            payload.update(adt)
        else:
            payload["message"] = record.getMessage()
        return json.dumps(payload, default=str)


def setup_adt_file_logging(
    *,
    log_dir: Path | None = None,
    level: int = logging.INFO,
) -> Path:
    """Attach one JSON log file for the ``adt`` logger namespace.

    Args:
        log_dir: Directory for ``adt.jsonl`` (default ``~/.adt/logs``).
        level: Minimum level for the ``adt`` logger and the file handler.

    Returns:
        Path to ``adt.jsonl``.
    """
    base = log_dir if log_dir is not None else Path.home() / ".adt" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    log_path = base / "adt.jsonl"
    adt_root = logging.getLogger("adt")
    if any(isinstance(h.formatter, AdtJsonFormatter) for h in adt_root.handlers):
        return log_path
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(AdtJsonFormatter())
    adt_root.setLevel(level)
    adt_root.addHandler(handler)
    return log_path


def log_adt(logger: logging.Logger, level: int, **fields: Any) -> None:
    """Log a structured event using ``extra={\"adt\": fields}``.

    Callers may include a ``trace_id`` key in *fields* for correlation.
    """
    logger.log(level, "", extra={"adt": fields})
