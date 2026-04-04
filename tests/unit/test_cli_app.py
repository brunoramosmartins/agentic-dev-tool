"""Smoke tests for the Typer CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from adt.cli.app import app


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip()


def test_cli_info() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "Phase" in result.stdout
