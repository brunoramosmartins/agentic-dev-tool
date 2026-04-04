"""Smoke tests for the Typer CLI."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from adt.cli.app import app
from adt.models.schemas import AgentResponse


def test_cli_version() -> None:
    """The ``version`` command should print a non-empty string."""
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip()


def test_cli_info() -> None:
    """The ``info`` command should mention the MVP ``ask`` flow."""
    runner = CliRunner()
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "ask" in result.stdout.lower()


def test_cli_config_show() -> None:
    """``config show`` prints effective settings."""
    runner = CliRunner()
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "default_model" in result.stdout


def test_cli_config_path() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["config", "path"])
    assert result.exit_code == 0
    assert ".adt" in result.stdout and "config.toml" in result.stdout


def test_cli_config_set_writes_file(tmp_path, monkeypatch) -> None:
    from adt import config as cfgmod

    p = tmp_path / "cfg.toml"
    monkeypatch.setattr(cfgmod, "adt_config_path", lambda: p)
    runner = CliRunner()
    result = runner.invoke(app, ["config", "set", "log_level", "WARNING"])
    assert result.exit_code == 0
    assert p.is_file()
    assert "WARNING" in p.read_text(encoding="utf-8")


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.cli.app.build_runner")
def test_cli_ask_multi_repo(mock_build, tmp_path) -> None:
    mock_runner = MagicMock()
    mock_runner.run.return_value = AgentResponse(
        answer="ok",
        tools_used=[],
        context_summary="",
        routed_agent="repo_agent",
    )
    mock_build.return_value = mock_runner
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["ask", "compare trees", "--repo", str(a), "--repo", str(b)],
    )
    assert result.exit_code == 0
    roots = mock_build.call_args[0][0]
    assert isinstance(roots, dict)
    assert len(roots) == 2


def test_cli_ask_requires_api_key(tmp_path) -> None:
    """``ask`` without ``OPENAI_API_KEY`` must exit with an error."""
    runner = CliRunner()
    repo = tmp_path / "r"
    repo.mkdir()
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        result = runner.invoke(app, ["ask", "hello?", "--repo", str(repo)])
    assert result.exit_code == 1


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.cli.app.build_runner")
def test_cli_ask_runs_runner(mock_build, tmp_path) -> None:
    """``ask`` should call ``build_runner_for_repo`` and print the model answer."""
    mock_runner = MagicMock()
    mock_runner.run.return_value = AgentResponse(
        answer="Stubbed answer.",
        tools_used=["read_repo_tree"],
        context_summary="ctx",
        routed_agent="repo_agent",
    )
    mock_runner.last_token_usage = {"total_tokens": 10}
    mock_build.return_value = mock_runner
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "x.py").write_text("a = 1\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["ask", "Describe this repo.", "--repo", str(repo)],
    )
    assert result.exit_code == 0
    assert "Stubbed answer." in result.stdout
    assert "repo_agent" in result.stdout
    mock_build.assert_called_once()


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.cli.app.build_runner")
def test_cli_ask_accepts_force_agent(mock_build, tmp_path) -> None:
    """``--agent`` should be forwarded on :class:`~adt.models.schemas.QueryRequest`."""
    mock_runner = MagicMock()
    mock_runner.run.return_value = AgentResponse(
        answer="Research stub.",
        tools_used=["search_papers"],
        context_summary="",
        routed_agent="research_agent",
    )
    mock_build.return_value = mock_runner
    repo = tmp_path / "r"
    repo.mkdir()
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "ask",
            "papers on RAG?",
            "--repo",
            str(repo),
            "--agent",
            "research_agent",
        ],
    )
    assert result.exit_code == 0
    mock_runner.run.assert_called_once()
    req = mock_runner.run.call_args[0][0]
    assert req.force_agent == "research_agent"


@patch("adt.cli.app.build_runner")
def test_cli_ask_rejects_invalid_agent(mock_build, tmp_path) -> None:
    """Unknown ``--agent`` values must exit before the runner is built."""
    runner = CliRunner()
    repo = tmp_path / "r"
    repo.mkdir()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        result = runner.invoke(
            app,
            ["ask", "hi", "--repo", str(repo), "--agent", "not_an_agent"],
        )
    assert result.exit_code == 1
    mock_build.assert_not_called()
