"""Smoke tests for the ``adt review`` Typer command."""

from __future__ import annotations

import os
from unittest.mock import patch

from typer.testing import CliRunner

from adt.cli.app import app
from adt.core.session import SessionContext
from adt.models.schemas import CodeIssue, ReviewFeedback
from adt.review_session import ReviewExecution


def _ok_execution() -> ReviewExecution:
    return ReviewExecution(
        feedback=ReviewFeedback(
            issues=[
                CodeIssue(
                    line=3,
                    severity="warning",
                    description="Variable `x` is not descriptive.",
                    fix_hint="What does it represent?",
                ),
            ],
            improvements=["Add a docstring."],
            strengths=["Function signature is clear."],
            next_step="Rename `x` and rerun the test.",
            overall_assessment="on_track",
        ),
        raw_answer="{...}",
        session=SessionContext(
            problem_summary="Binary search",
            current_step=2,
            total_steps=4,
        ),
    )


def test_review_rejects_invalid_level(tmp_path) -> None:
    target = tmp_path / "x.py"
    target.write_text("a = 1\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["review", str(target), "--level", "expert"])
    assert result.exit_code == 1


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.cli.app.run_review")
def test_review_renders_feedback(mock_run, tmp_path) -> None:
    mock_run.return_value = _ok_execution()
    target = tmp_path / "solution.py"
    target.write_text("def f(): return 1\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["review", str(target)])
    assert result.exit_code == 0
    assert "On Track" in result.stdout
    assert "Variable `x` is not descriptive" in result.stdout
    assert "Rename `x`" in result.stdout
    # Session footer
    assert "step 2/4" in result.stdout
    assert "Binary search" in result.stdout


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.cli.app.run_review")
def test_review_unparsed_feedback_exits_nonzero(mock_run, tmp_path) -> None:
    mock_run.return_value = ReviewExecution(
        feedback=None,
        raw_answer="not json",
        session=SessionContext(),
    )
    target = tmp_path / "x.py"
    target.write_text("a = 1\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["review", str(target)])
    assert result.exit_code == 1
    assert "raw" in result.stdout.lower()


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.cli.app.run_review")
def test_review_configuration_error(mock_run, tmp_path) -> None:
    from adt.review_session import ReviewConfigurationError

    mock_run.side_effect = ReviewConfigurationError("missing file")
    target = tmp_path / "x.py"
    target.write_text("a = 1\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["review", str(target)])
    assert result.exit_code == 1


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.cli.app.run_review")
def test_review_unexpected_exception(mock_run, tmp_path) -> None:
    mock_run.side_effect = RuntimeError("kaboom")
    target = tmp_path / "x.py"
    target.write_text("a = 1\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["review", str(target)])
    assert result.exit_code == 1
