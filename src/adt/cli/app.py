"""Typer CLI entry point including the ``ask`` command (all agents)."""

from __future__ import annotations

from importlib import metadata
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from adt.ask_session import AskConfigurationError, run_ask
from adt.config import (
    adt_config_path,
    apply_env_overrides,
    load_config_file,
    update_config_key,
)

app = typer.Typer(help="Agentic Dev Tool CLI", add_completion=False)
config_app = typer.Typer(help="View or edit ~/.adt/config.toml", add_completion=False)
app.add_typer(config_app, name="config")
console = Console()

_VALID_AGENTS = frozenset({"repo_agent", "research_agent", "project_agent"})


def _version_string() -> str:
    """Return the installed distribution version, or a dev fallback."""
    try:
        return metadata.version("agentic-dev-tool")
    except metadata.PackageNotFoundError:
        return "1.0.0-dev"


def _format_ask_panel(agent_name: str, answer: str) -> None:
    """Print the model answer with formatting tuned for the routed agent."""
    if agent_name.startswith("chain:"):
        console.print(
            Panel(
                Markdown(answer),
                title="Answer",
                border_style="yellow",
                title_align="left",
            ),
        )
        return
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
    console.print(
        Panel(
            Markdown(answer),
            title="Answer",
            border_style="green",
            title_align="left",
        ),
    )


@app.command("version")
def version_cmd() -> None:
    """Print the installed package version."""
    typer.echo(_version_string())


@app.command("info")
def info_cmd() -> None:
    """Print short project status and feature summary."""
    typer.echo(
        "adt — v1.1.0 production: PyPI package, optional HTTP API (`adt serve`), "
        "multi-repo ask, config.toml, LLM routing. Docs: README, docs/architecture.md.",
    )


@config_app.command("path")
def config_path_cmd() -> None:
    """Print the config file path."""
    typer.echo(str(adt_config_path()))


@config_app.command("show")
def config_show_cmd() -> None:
    """Print effective settings (file + ADT_* env overrides)."""
    cfg = apply_env_overrides(load_config_file())
    typer.echo(f"# effective (after env): {adt_config_path()}")
    for k, v in cfg.to_toml_table().items():
        typer.echo(f"{k} = {v!r}")


@config_app.command("set")
def config_set_cmd(
    key: Annotated[str, typer.Argument(help="Setting name (e.g. default_model).")],
    value: Annotated[
        str,
        typer.Argument(help="New value (comma-list for agent_chain)."),
    ],
) -> None:
    """Persist one key under [adt] in config.toml."""
    try:
        update_config_key(None, key, value)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Saved.")


@app.command("ask")
def ask_cmd(
    query: Annotated[
        str,
        typer.Argument(
            help="Natural language question (repository, research, or project).",
        ),
    ],
    repo: Annotated[
        list[str] | None,
        typer.Option(
            "--repo",
            "-r",
            help=("Local directory or owner/repo slug; repeat for multiple checkouts."),
        ),
    ] = None,
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
                "(skips supervisor routing and agent_chain)."
            ),
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Print debug logs and token usage."),
    ] = False,
    log_level: Annotated[
        str | None,
        typer.Option(
            "--log-level",
            help="File log level: DEBUG, INFO, WARNING, ERROR (default: config).",
        ),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option(
            "--no-cache",
            help="Disable repository tree disk cache for this request.",
        ),
    ] = False,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="OpenAI chat model (default: config default_model).",
        ),
    ] = None,
    trace: Annotated[
        bool,
        typer.Option(
            "--trace",
            help="Show request trace: routing, context, LLM calls, cost estimate.",
        ),
    ] = False,
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            help=(
                "Operational mode: 'execution' (default) solves tasks; "
                "'supervised' guides step-by-step for learning."
            ),
        ),
    ] = "execution",
    level: Annotated[
        str,
        typer.Option(
            "--level",
            help="Difficulty for supervised mode: beginner, intermediate, advanced.",
        ),
    ] = "intermediate",
) -> None:
    """Ask a question: supervisor picks an agent unless ``--agent`` is set."""
    valid_modes = {"execution", "supervised"}
    if mode not in valid_modes:
        console.print(
            f"[red]Invalid --mode {mode!r}.[/red] "
            f"Choose one of: {', '.join(sorted(valid_modes))}.",
        )
        raise typer.Exit(code=1)
    valid_levels = {"beginner", "intermediate", "advanced"}
    if level not in valid_levels:
        console.print(
            f"[red]Invalid --level {level!r}.[/red] "
            f"Choose one of: {', '.join(sorted(valid_levels))}.",
        )
        raise typer.Exit(code=1)
    if agent is not None and agent not in _VALID_AGENTS:
        console.print(
            "[red]Invalid --agent.[/red] "
            f"Choose one of: {', '.join(sorted(_VALID_AGENTS))}.",
        )
        raise typer.Exit(code=1)

    try:
        exe = run_ask(
            query=query,
            repo=repo,
            github_token=token,
            force_agent=agent,
            verbose=verbose,
            log_level=log_level,
            no_cache=no_cache,
            model=model,
            configure_logging=True,
            trace=trace,
            mode=mode,
            level=level,
        )
    except AskConfigurationError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # noqa: BLE001 — last-resort CLI guard
        console.print(
            "[red]Unexpected error while running the agent.[/red] "
            f"({type(exc).__name__}: {exc})",
        )
        raise typer.Exit(code=1) from exc

    response = exe.response
    runner = exe.runner
    routed = response.routed_agent or agent or "supervisor"
    console.print(f"[dim]Agent:[/dim] [bold]{routed}[/bold]")

    if exe.supervised_response is not None:
        from adt.cli.supervised_renderer import SupervisedRenderer

        SupervisedRenderer(console).render(exe.supervised_response)
    else:
        _format_ask_panel(response.routed_agent or agent or "", response.answer)
    tools_line = ", ".join(response.tools_used) if response.tools_used else "none"
    console.print(f"[dim]Tools used:[/dim] {tools_line}")
    if exe.trace_context is not None:
        from adt.tracing.renderer import TraceRenderer

        eff_model = model or "gpt-4o-mini"
        TraceRenderer(console).render(exe.trace_context, model=eff_model)
    if verbose:
        console.print(f"[dim]Last LLM token usage:[/dim] {runner.last_token_usage}")
        ctx = response.context_summary
        console.print(f"[dim]Context summary (truncated):[/dim] {ctx!r}")
        br = getattr(runner, "last_budget_report", None)
        if br:
            console.print(f"[dim]Token budget (estimated):[/dim] {br}")


@app.command("serve")
def serve_cmd(
    host: Annotated[
        str,
        typer.Option("--host", help="Bind address (default 127.0.0.1)."),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", help="TCP port (default 8765)."),
    ] = 8765,
) -> None:
    """Run the optional HTTP API (install ``agentic-dev-tool[api]`` first)."""
    try:
        import uvicorn
    except ImportError:
        console.print(
            "[red]Missing API dependencies.[/red] "
            "Install with: pip install 'agentic-dev-tool[api]'",
        )
        raise typer.Exit(code=1) from None
    from adt.api.server import app as api_app

    console.print(f"[dim]Open http://{host}:{port}/docs[/dim]")
    uvicorn.run(api_app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()
