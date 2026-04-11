"""Smoke tests for the static ``adt guide`` quick-reference command."""

from __future__ import annotations

import io

from rich.console import Console
from typer.testing import CliRunner

from adt.cli.app import app
from adt.cli.guide_renderer import GuideRenderer


def test_guide_renderer_contains_all_sections() -> None:
    buf = io.StringIO()
    console = Console(file=buf, color_system=None, width=120, record=False)
    GuideRenderer(console).render()
    out = buf.getvalue()

    # Top-level
    assert "Quick Reference" in out
    assert "supervised learning" in out.lower()

    # Commands: one row per entry
    for cmd in ("ask", "review", "stats", "serve", "guide", "config"):
        assert cmd in out

    # Modes
    assert "execution" in out
    assert "supervised" in out

    # Levels
    for lvl in ("beginner", "intermediate", "advanced"):
        assert lvl in out

    # Agents
    for agent in ("repo_agent", "project_agent", "research_agent"):
        assert agent in out

    # Skills
    assert "supervised_engineering" in out

    # Environment
    assert "OPENAI_API_KEY" in out
    assert "GITHUB_TOKEN" in out


def test_cli_guide_command_runs_without_api_key(monkeypatch) -> None:
    # The guide must work even without any OpenAI key in the environment.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    runner = CliRunner()
    result = runner.invoke(app, ["guide"])
    assert result.exit_code == 0
    assert "Quick Reference" in result.stdout
    assert "ask" in result.stdout
    assert "supervised" in result.stdout
    assert "stats" in result.stdout
