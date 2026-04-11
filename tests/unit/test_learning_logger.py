"""Unit tests for the rotating learning logger."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from adt.analytics.events import LearningEvent
from adt.analytics.logger import (
    LEARNING_LOG_NAME,
    learning_log_path,
    log_learning_event,
    setup_learning_logger,
)


def _fresh_logger(tmp_path: Path) -> Path:
    # Drop any cached handlers so each test starts with a clean logger.
    log = logging.getLogger("adt.learning")
    for handler in list(log.handlers):
        handler.close()
        log.removeHandler(handler)
    return setup_learning_logger(log_dir=tmp_path)


def test_learning_log_path_returns_name(tmp_path: Path) -> None:
    assert learning_log_path(tmp_path).name == LEARNING_LOG_NAME


def test_setup_learning_logger_is_idempotent(tmp_path: Path) -> None:
    first = _fresh_logger(tmp_path)
    second = setup_learning_logger(log_dir=tmp_path)
    assert first == second
    log = logging.getLogger("adt.learning")
    # Only one rotating handler should be attached.
    assert len(log.handlers) == 1


def test_log_learning_event_writes_jsonl(tmp_path: Path) -> None:
    _fresh_logger(tmp_path)
    event = LearningEvent(
        trace_id="t1",
        component="supervisor",
        event_type="supervised_step",
        step_id=2,
        iteration_count=1,
        problem_summary="FizzBuzz",
        level="beginner",
    )
    log_learning_event(event, log_dir=tmp_path)

    target = tmp_path / LEARNING_LOG_NAME
    assert target.exists()
    lines = target.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["trace_id"] == "t1"
    assert payload["event_type"] == "supervised_step"
    assert payload["step_id"] == 2
    assert payload["problem_summary"] == "FizzBuzz"


def test_log_learning_event_swallows_errors(tmp_path: Path, monkeypatch) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("explode")

    monkeypatch.setattr("adt.analytics.logger.setup_learning_logger", boom)
    event = LearningEvent(
        trace_id="t", component="supervisor", event_type="supervised_step"
    )
    # Must not raise even though setup blew up.
    log_learning_event(event, log_dir=tmp_path)
