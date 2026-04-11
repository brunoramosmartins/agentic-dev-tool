"""Unit tests for :func:`read_learning_events`."""

from __future__ import annotations

import json
from pathlib import Path

from adt.analytics.events import LearningEvent
from adt.analytics.reader import read_learning_events


def _write_events(path: Path, count: int) -> list[LearningEvent]:
    events: list[LearningEvent] = []
    lines: list[str] = []
    for i in range(count):
        ev = LearningEvent(
            trace_id=f"t{i}",
            component="supervisor",
            event_type="supervised_step",
            step_id=i,
            problem_summary=f"problem {i}",
        )
        events.append(ev)
        lines.append(json.dumps(ev.model_dump(mode="json"), default=str))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return events


def test_read_learning_events_missing_file(tmp_path: Path) -> None:
    assert read_learning_events(path=tmp_path / "nope.jsonl") == []


def test_read_learning_events_returns_all(tmp_path: Path) -> None:
    target = tmp_path / "learning.jsonl"
    written = _write_events(target, 3)
    loaded = read_learning_events(path=target)
    assert len(loaded) == 3
    assert [e.trace_id for e in loaded] == [e.trace_id for e in written]


def test_read_learning_events_limit(tmp_path: Path) -> None:
    target = tmp_path / "learning.jsonl"
    _write_events(target, 5)
    loaded = read_learning_events(path=target, limit=2)
    assert [e.trace_id for e in loaded] == ["t3", "t4"]


def test_read_learning_events_skips_corrupted_lines(tmp_path: Path) -> None:
    target = tmp_path / "learning.jsonl"
    good = LearningEvent(
        trace_id="ok", component="supervisor", event_type="supervised_step"
    )
    content = "\n".join(
        [
            "",  # blank
            "{not json",  # malformed
            "[1,2,3]",  # not a dict
            json.dumps({"bogus": "shape"}),  # schema mismatch survives the base model
            json.dumps(good.model_dump(mode="json"), default=str),
        ]
    )
    target.write_text(content, encoding="utf-8")
    loaded = read_learning_events(path=target)
    # The bogus one has required fields missing, so it is also skipped.
    assert len(loaded) == 1
    assert loaded[0].trace_id == "ok"
