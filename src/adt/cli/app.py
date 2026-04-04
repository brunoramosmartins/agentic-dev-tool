"""Typer CLI entry point (bootstrap; `ask` and agents ship in later phases)."""

from __future__ import annotations

from importlib import metadata

import typer

app = typer.Typer(help="Agentic Dev Tool CLI", add_completion=False)


def _version_string() -> str:
    try:
        return metadata.version("agentic-dev-tool")
    except metadata.PackageNotFoundError:
        return "0.1.0-dev"


@app.command("version")
def version_cmd() -> None:
    """Print the installed package version."""
    typer.echo(_version_string())


@app.command("info")
def info_cmd() -> None:
    """Print short bootstrap status (full CLI in Phase 2)."""
    typer.echo(
        "adt Phase 0 — tooling and skeleton ready. "
        "The `ask` command ships in Phase 2.",
    )


if __name__ == "__main__":
    app()
