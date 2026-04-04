"""Typer CLI entry point including the ``ask`` command (repo MVP)."""

from __future__ import annotations

import logging
import os
from importlib import metadata
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from adt.bootstrap import build_runner_for_repo
from adt.models.schemas import QueryRequest

app = typer.Typer(help="Agentic Dev Tool CLI", add_completion=False)
console = Console()


def _version_string() -> str:
    """Return the installed distribution version, or a dev fallback."""
    try:
        return metadata.version("agentic-dev-tool")
    except metadata.PackageNotFoundError:
        return "0.3.0-dev"


@app.command("version")
def version_cmd() -> None:
    """Print the installed package version."""
    typer.echo(_version_string())


@app.command("info")
def info_cmd() -> None:
    """Print short project status and feature summary."""
    typer.echo(
        'adt — Phase 2 MVP. Run: adt ask "your question" --repo .',
    )


@app.command("ask")
def ask_cmd(
    query: Annotated[
        str,
        typer.Argument(help="Natural language question about the repository."),
    ],
    repo: Annotated[
        Path,
        typer.Option(
            "--repo",
            "-r",
            help="Path to the repository root to analyze.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = Path("."),
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Print debug logs and token usage."),
    ] = False,
    model: Annotated[
        str,
        typer.Option(
            "--model",
            "-m",
            help="OpenAI chat model name (default: gpt-4o-mini).",
        ),
    ] = "gpt-4o-mini",
) -> None:
    """Ask a question about a local repository (supervisor → agent → tools → LLM)."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        console.print(
            "[red]Missing OPENAI_API_KEY.[/red] "
            "Set it in the environment or in a `.env` file.",
        )
        raise typer.Exit(code=1)

    repo_path = repo.resolve()
    runner = build_runner_for_repo(
        repo_path,
        model=model,
        api_key=api_key,
    )
    request = QueryRequest(query=query, repo_path=str(repo_path))
    response = runner.run(request)

    console.print(Panel(response.answer, title="Answer", border_style="green"))
    tools_line = ", ".join(response.tools_used) if response.tools_used else "none"
    console.print(f"[dim]Tools used:[/dim] {tools_line}")
    if verbose:
        console.print(f"[dim]Last LLM token usage:[/dim] {runner.last_token_usage}")
        ctx = response.context_summary
        console.print(f"[dim]Context summary (truncated):[/dim] {ctx!r}")


if __name__ == "__main__":
    app()
