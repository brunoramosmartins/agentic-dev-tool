"""Smoke tests for the ``adt stats`` CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from adt.analytics.events import LearningEvent
from adt.cli.app import app


def _write_sample_log(path: Path) -> None:
    events = [
        LearningEvent(
            trace_id="t1",
            component="supervisor",
            event_type="supervised_step",
            step_id=1,
            iteration_count=1,
            problem_summary="Reverse a linked list",
            level="intermediate",
        ),
        LearningEvent(
            trace_id="t2",
            component="reviewer",
            event_type="code_review",
            step_id=1,
            iteration_count=2,
            assessment="needs_work",
            error_types=["off_by_one"],
            problem_summary="Reverse a linked list",
            level="intermediate",
        ),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(ev.model_dump(mode="json"), default=str) for ev in events)
        + "\n",
        encoding="utf-8",
    )


def test_cli_stats_empty_log(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "adt.analytics.logger.learning_log_path",
        lambda log_dir=None: tmp_path / "learning.jsonl",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Learning Stats" in result.stdout
    assert "No supervised learning events" in result.stdout


def test_cli_stats_with_events(tmp_path, monkeypatch) -> None:
    target = tmp_path / "learning.jsonl"
    _write_sample_log(target)
    monkeypatch.setattr(
        "adt.analytics.logger.learning_log_path",
        lambda log_dir=None: target,
    )
    runner = CliRunner()
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Sessions: 1" in result.stdout
    assert "Reviews:  1" in result.stdout
    assert "off_by_one" in result.stdout
    assert "needs_work" in result.stdout


def test_cli_stats_rejects_non_positive_last() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["stats", "--last", "0"])
    assert result.exit_code == 1
    assert "positive" in result.stdout.lower()
