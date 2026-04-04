"""Typer CLI entry point including the ``ask`` command (all agents)."""

from __future__ import annotations

import logging
import os
from importlib import metadata
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from adt.bootstrap import build_runner
from adt.models.schemas import QueryRequest
from adt.repo_spec import resolve_repo_target

app = typer.Typer(help="Agentic Dev Tool CLI", add_completion=False)
console = Console()

_VALID_AGENTS = frozenset({"repo_agent", "research_agent", "project_agent"})


def _version_string() -> str:
    """Return the installed distribution version, or a dev fallback."""
    try:
        return metadata.version("agentic-dev-tool")
    except metadata.PackageNotFoundError:
        return "0.5.0-dev"


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
    if agent_name == "project_agent":
        console.print(
            Panel(
                Markdown(answer),
                title="Answer",
                border_style="magenta",
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
        "adt — Phase 4. ask: local path or owner/repo; GitHub tools for "
        "project_agent; --token or GITHUB_TOKEN for API limits.",
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
        str,
        typer.Option(
            "--repo",
            "-r",
            help=(
                "Local directory or GitHub slug owner/repo (markdown root uses cwd "
                "when slug is used)."
            ),
        ),
    ] = ".",
    token: Annotated[
        str | None,
        typer.Option(
            "--token",
            help="GitHub PAT for read_issues / read_milestones (or set GITHUB_TOKEN).",
        ),
    ] = None,
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

    try:
        target = resolve_repo_target(repo)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    github_token = token.strip() if token else None
    if not github_token:
        env_gh = os.environ.get("GITHUB_TOKEN")
        github_token = env_gh.strip() if env_gh else None

    runner = build_runner(
        target.local_root,
        model=model,
        api_key=api_key,
        github_token=github_token,
    )
    request = QueryRequest(
        query=query,
        repo_path=str(target.local_root),
        github_owner=target.github_owner,
        github_repo=target.github_repo,
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
