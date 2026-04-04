"""Typer CLI entry point including the ``ask`` command (repo and research agents)."""

from __future__ import annotations

import logging
import os
from importlib import metadata
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from adt.bootstrap import build_runner_for_repo
from adt.models.schemas import QueryRequest

app = typer.Typer(help="Agentic Dev Tool CLI", add_completion=False)
console = Console()

_VALID_AGENTS = frozenset({"repo_agent", "research_agent", "project_agent"})


def _version_string() -> str:
    """Return the installed distribution version, or a dev fallback."""
    try:
        return metadata.version("agentic-dev-tool")
    except metadata.PackageNotFoundError:
        return "0.4.0-dev"


def _format_ask_panel(agent_name: str, answer: str) -> None:
    """Print the model answer with formatting tuned for the routed agent."""
    if agent_name == "research_agent":
        console.print(
            Panel(
                Markdown(answer),
                title="Answer",
                border_style="cyan",
                title_align="left",
            ),
        )
        return
    console.print(Panel(answer, title="Answer", border_style="green"))


@app.command("version")
def version_cmd() -> None:
    """Print the installed package version."""
    typer.echo(_version_string())


@app.command("info")
def info_cmd() -> None:
    """Print short project status and feature summary."""
    typer.echo(
        'adt — Phase 3. Use: adt ask "question" --repo . '
        "or research queries (arXiv). Optional: --agent research_agent.",
    )


@app.command("ask")
def ask_cmd(
    query: Annotated[
        str,
        typer.Argument(
            help="Natural language question (repository, research, or project).",
        ),
    ],
    repo: Annotated[
        Path,
        typer.Option(
            "--repo",
            "-r",
            help="Path to the repository root (for context and repo tools).",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = Path("."),
    agent: Annotated[
        str | None,
        typer.Option(
            "--agent",
            "-a",
            help=(
                "Force a specific agent: repo_agent, research_agent, or project_agent "
                "(skips supervisor routing)."
            ),
        ),
    ] = None,
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
    """Ask a question: supervisor picks an agent unless ``--agent`` is set."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        console.print(
            "[red]Missing OPENAI_API_KEY.[/red] "
            "Set it in the environment or in a `.env` file.",
        )
        raise typer.Exit(code=1)

    if agent is not None and agent not in _VALID_AGENTS:
        console.print(
            "[red]Invalid --agent.[/red] "
            f"Choose one of: {', '.join(sorted(_VALID_AGENTS))}.",
        )
        raise typer.Exit(code=1)

    repo_path = repo.resolve()
    runner = build_runner_for_repo(
        repo_path,
        model=model,
        api_key=api_key,
    )
    request = QueryRequest(
        query=query,
        repo_path=str(repo_path),
        force_agent=agent,
    )
    response = runner.run(request)

    routed = response.routed_agent or agent or "supervisor"
    console.print(f"[dim]Agent:[/dim] [bold]{routed}[/bold]")
    _format_ask_panel(response.routed_agent or agent or "", response.answer)
    tools_line = ", ".join(response.tools_used) if response.tools_used else "none"
    console.print(f"[dim]Tools used:[/dim] {tools_line}")
    if verbose:
        console.print(f"[dim]Last LLM token usage:[/dim] {runner.last_token_usage}")
        ctx = response.context_summary
        console.print(f"[dim]Context summary (truncated):[/dim] {ctx!r}")


if __name__ == "__main__":
    app()
