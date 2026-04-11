"""Reader for the rotating learning log."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from adt.analytics import logger as _logger_mod
from adt.analytics.events import LearningEvent

logger = logging.getLogger(__name__)


def _parse_line(line: str) -> LearningEvent | None:
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    try:
        return LearningEvent.model_validate(data)
    except Exception:  # noqa: BLE001 — tolerate schema drift
        return None


def read_learning_events(
    *,
    log_dir: Path | None = None,
    path: Path | None = None,
    limit: int | None = None,
) -> list[LearningEvent]:
    """Load learning events from ``learning.jsonl`` (oldest first).

    Args:
        log_dir: Directory containing the log; defaults to ``~/.adt/logs``.
        path: Explicit path override for tests. Takes precedence over
            ``log_dir``.
        limit: When set, return only the most recent ``limit`` events.

    Returns:
        A list of validated :class:`LearningEvent` instances. Missing file,
        corrupted lines, and schema mismatches are silently skipped so the
        stats command stays resilient to partial writes.
    """
    target = path if path is not None else _logger_mod.learning_log_path(log_dir)
    if not target.exists():
        return []
    try:
        content = target.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("learning_log_read_failed: %s", exc)
        return []

    events: list[LearningEvent] = []
    for raw in content.splitlines():
        event = _parse_line(raw)
        if event is not None:
            events.append(event)

    if limit is not None and limit > 0:
        events = events[-limit:]
    return events
