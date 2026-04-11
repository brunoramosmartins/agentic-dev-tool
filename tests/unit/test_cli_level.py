"""Smoke tests for the ``--level`` flag on ``adt ask``."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from adt.ask_session import AskExecution
from adt.cli.app import app
from adt.models.schemas import AgentResponse, SupervisedResponse, SupervisedStep


def _ok_execution(
    level: str | None,
    supervised: bool,
) -> AskExecution:
    runner_mock = MagicMock()
    runner_mock.last_token_usage = {"total_tokens": 1}
    runner_mock.last_budget_report = None
    resp = AgentResponse(
        answer="ok",
        tools_used=[],
        context_summary="",
        routed_agent="repo_agent",
    )
    supervised_resp = None
    if supervised:
        supervised_resp = SupervisedResponse(
            problem_summary="Implement binary search",
            current_step=SupervisedStep(
                step_number=1,
                goal="Define signature",
                requirements=["accept sorted list"],
            ),
            total_steps=3,
        )
    return AskExecution(
        response=resp,
        runner=runner_mock,
        supervised_response=supervised_resp,
        supervised_level=level if supervised else None,
    )


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.cli.app.run_ask")
def test_level_without_supervised_emits_warning(mock_run, tmp_path) -> None:
    mock_run.return_value = _ok_execution(level=None, supervised=False)
    repo = tmp_path / "r"
    repo.mkdir()
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["ask", "hi", "--repo", str(repo), "--level", "beginner"],
    )
    assert result.exit_code == 0
    assert "--level is only used with --mode supervised" in result.stdout


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.cli.app.run_ask")
def test_level_without_supervised_still_forwards_default(mock_run, tmp_path) -> None:
    mock_run.return_value = _ok_execution(level=None, supervised=False)
    repo = tmp_path / "r"
    repo.mkdir()
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["ask", "hi", "--repo", str(repo), "--level", "advanced"],
    )
    assert result.exit_code == 0
    # run_ask still receives a level (effective default) so the downstream
    # QueryRequest validator does not break.
    kwargs = mock_run.call_args.kwargs
    assert kwargs["level"] == "advanced"
    assert kwargs["mode"] == "execution"


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.cli.app.run_ask")
def test_level_with_supervised_mode_no_warning(mock_run, tmp_path) -> None:
    mock_run.return_value = _ok_execution(level="beginner", supervised=True)
    repo = tmp_path / "r"
    repo.mkdir()
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "ask",
            "teach me binary search",
            "--repo",
            str(repo),
            "--mode",
            "supervised",
            "--level",
            "beginner",
        ],
    )
    assert result.exit_code == 0
    assert "--level is only used" not in result.stdout
    assert "Beginner" in result.stdout
    kwargs = mock_run.call_args.kwargs
    assert kwargs["mode"] == "supervised"
    assert kwargs["level"] == "beginner"


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.cli.app.run_ask")
def test_default_level_is_intermediate_and_silent(mock_run, tmp_path) -> None:
    mock_run.return_value = _ok_execution(level=None, supervised=False)
    repo = tmp_path / "r"
    repo.mkdir()
    runner = CliRunner()
    result = runner.invoke(app, ["ask", "hi", "--repo", str(repo)])
    assert result.exit_code == 0
    assert "--level is only used" not in result.stdout
    kwargs = mock_run.call_args.kwargs
    assert kwargs["level"] == "intermediate"


def test_invalid_level_still_rejected(tmp_path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    runner = CliRunner()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        result = runner.invoke(
            app,
            ["ask", "hi", "--repo", str(repo), "--level", "expert"],
        )
    assert result.exit_code == 1
