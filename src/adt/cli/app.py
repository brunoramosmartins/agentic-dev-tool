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
from adt.review_session import ReviewConfigurationError, run_review

app = typer.Typer(help="Agentic Dev Tool CLI", add_completion=False)
config_app = typer.Typer(help="View or edit ~/.adt/config.toml", add_completion=False)
app.add_typer(config_app, name="config")
session_app = typer.Typer(
    help="Inspect or manage the supervised session state.",
    add_completion=False,
)
app.add_typer(session_app, name="session")
runs_app = typer.Typer(
    help="Manage interrupted run snapshots.",
    add_completion=False,
)
app.add_typer(runs_app, name="runs")
plugins_app = typer.Typer(
    help="Manage community plugins (skills and tools).",
    add_completion=False,
)
app.add_typer(plugins_app, name="plugins")
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


@app.command("guide")
def guide_cmd() -> None:
    """Print a static quick-reference: commands, modes, levels, agents, skills.

    This command does not hit the network and does not require an API key.
    Use it as a fast "what can adt do?" cheat sheet (think of it as the
    ``?`` prompt in Claude Code).
    """
    from adt.cli.guide_renderer import GuideRenderer

    GuideRenderer(console).render()


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
    from adt.config_validator import ConfigValidationError, validate_key_value

    try:
        validate_key_value(key, value)
    except ConfigValidationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
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
        str | None,
        typer.Option(
            "--level",
            help=(
                "Difficulty for supervised mode: beginner, intermediate "
                "(default), advanced. Only meaningful with --mode supervised."
            ),
        ),
    ] = None,
    session: Annotated[
        str,
        typer.Option(
            "--session",
            help="Named session to use for supervised mode (default: 'default').",
        ),
    ] = "default",
    resume: Annotated[
        str | None,
        typer.Option(
            "--resume",
            help="Resume an interrupted run by trace ID.",
        ),
    ] = None,
) -> None:
    """Ask a question: supervisor picks an agent unless ``--agent`` is set."""
    if resume is not None:
        from adt.core.run_snapshot import RunStore

        snap = RunStore().load(resume)
        if snap is None:
            console.print(f"[red]Run '{resume}' not found.[/red]")
            raise typer.Exit(code=1)
        console.print(
            f"[dim]Resuming run {resume} — agent={snap.agent_name} "
            f"iter={snap.iteration}/{snap.max_iterations}[/dim]",
        )
        console.print(
            f"[yellow]Resume support is registered. "
            f"The snapshot contains {len(snap.messages)} messages and "
            f"{len(snap.tools_used)} tool calls.[/yellow]",
        )
        return

    valid_modes = {"execution", "supervised"}
    if mode not in valid_modes:
        console.print(
            f"[red]Invalid --mode {mode!r}.[/red] "
            f"Choose one of: {', '.join(sorted(valid_modes))}.",
        )
        raise typer.Exit(code=1)
    valid_levels = {"beginner", "intermediate", "advanced"}
    level_explicit = level is not None
    if level is not None and level not in valid_levels:
        console.print(
            f"[red]Invalid --level {level!r}.[/red] "
            f"Choose one of: {', '.join(sorted(valid_levels))}.",
        )
        raise typer.Exit(code=1)
    if level_explicit and mode != "supervised":
        console.print(
            "[yellow]--level is only used with --mode supervised; "
            "ignoring in execution mode.[/yellow]",
        )
    effective_level = level if level is not None else "intermediate"
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
            level=effective_level,
            session_name=session,
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

        SupervisedRenderer(console).render(
            exe.supervised_response,
            level=exe.supervised_level,
        )
        # P10-01: show last-review verdict footer when a previous feedback exists
        from adt.core.session_store import SessionStore

        sess = SessionStore().load(session)
        if sess.previous_feedback:
            last_verdict = sess.previous_feedback[-1]
            console.print(
                f"[dim]Last review: {last_verdict}"
                f" — continue at step {sess.current_step}/{sess.total_steps}[/dim]",
            )
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


@app.command("review")
def review_cmd(
    file: Annotated[
        str,
        typer.Argument(help="Path to the source file to review."),
    ],
    context: Annotated[
        str | None,
        typer.Option(
            "--context",
            "-c",
            help="Optional description of what the code should do.",
        ),
    ] = None,
    level: Annotated[
        str,
        typer.Option(
            "--level",
            help="Difficulty level for the reviewer: beginner, intermediate, advanced.",
        ),
    ] = "intermediate",
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="OpenAI chat model (default: config default_model).",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Print debug logs."),
    ] = False,
    max_bytes: Annotated[
        int | None,
        typer.Option(
            "--max-bytes",
            help="Override the maximum file size for review (in bytes).",
        ),
    ] = None,
    session: Annotated[
        str,
        typer.Option(
            "--session",
            help="Named session to use (default: 'default').",
        ),
    ] = "default",
) -> None:
    """Review a source file in supervised mode and print structured feedback."""
    valid_levels = {"beginner", "intermediate", "advanced"}
    if level not in valid_levels:
        console.print(
            f"[red]Invalid --level {level!r}.[/red] "
            f"Choose one of: {', '.join(sorted(valid_levels))}.",
        )
        raise typer.Exit(code=1)

    try:
        result = run_review(
            file=file,
            extra_context=context,
            level=level,
            model=model,
            verbose=verbose,
            max_bytes=max_bytes,
            session_name=session,
        )
    except ReviewConfigurationError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # noqa: BLE001 — last-resort CLI guard
        console.print(
            "[red]Unexpected error while running the reviewer.[/red] "
            f"({type(exc).__name__}: {exc})",
        )
        raise typer.Exit(code=1) from exc

    if result.feedback is None:
        console.print(
            Panel(
                result.raw_answer or "(empty response)",
                title="Code Review (raw)",
                border_style="red",
                title_align="left",
            ),
        )
        raise typer.Exit(code=1)

    from adt.cli.review_renderer import ReviewRenderer

    ReviewRenderer(console).render(result.feedback)
    if result.session.problem_summary:
        console.print(
            f"[dim]Session:[/dim] step {result.session.current_step}/"
            f"{result.session.total_steps} — {result.session.problem_summary}",
        )


@app.command("stats")
def stats_cmd(
    last: Annotated[
        int | None,
        typer.Option(
            "--last",
            help="Only aggregate the most recent N supervised sessions.",
        ),
    ] = None,
    export: Annotated[
        str | None,
        typer.Option(
            "--export",
            help="Export format: csv, json, or md (prints to stdout or --out).",
        ),
    ] = None,
    out: Annotated[
        str | None,
        typer.Option(
            "--out",
            help="Write export output to this file instead of stdout.",
        ),
    ] = None,
    classifier: Annotated[
        str,
        typer.Option(
            "--classifier",
            help="Issue classifier strategy: keyword (default) or embedding.",
        ),
    ] = "keyword",
) -> None:
    """Summarize supervised learning progress from ``~/.adt/logs/learning.jsonl``."""
    from adt.analytics import compute_stats, read_learning_events

    if last is not None and last <= 0:
        console.print("[red]--last must be a positive integer.[/red]")
        raise typer.Exit(code=1)

    valid_classifiers = {"keyword", "embedding"}
    if classifier not in valid_classifiers:
        console.print(
            f"[red]Invalid --classifier {classifier!r}.[/red] "
            f"Choose one of: {', '.join(sorted(valid_classifiers))}.",
        )
        raise typer.Exit(code=1)

    valid_formats = {"csv", "json", "md"}
    if export is not None and export not in valid_formats:
        console.print(
            f"[red]Invalid --export {export!r}.[/red] "
            f"Choose one of: {', '.join(sorted(valid_formats))}.",
        )
        raise typer.Exit(code=1)

    events = read_learning_events()
    stats = compute_stats(events, last_n=last, classifier=classifier)

    if export is not None:
        from adt.analytics.exporter import export_csv, export_json, export_markdown

        exporters = {"csv": export_csv, "json": export_json, "md": export_markdown}
        content = exporters[export](stats)
        if out is not None:
            from pathlib import Path as _Path

            _Path(out).write_text(content, encoding="utf-8")
            console.print(f"[green]Stats exported to {out}[/green]")
        else:
            typer.echo(content, nl=False)
        return

    from adt.cli.stats_renderer import StatsRenderer

    StatsRenderer(console).render(stats)


# ── session subcommands (P10-03 / P10-06) ────────────────────────────


@session_app.command("show")
def session_show_cmd(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Session name to inspect."),
    ] = "default",
) -> None:
    """Print a supervised session as a Rich table."""
    from adt.cli.session_renderer import SessionRenderer
    from adt.core.session_store import SessionStore

    sess = SessionStore().load(name)
    SessionRenderer(console).render(sess)


@session_app.command("list")
def session_list_cmd() -> None:
    """List all named sessions."""
    from adt.core.session_store import SessionStore

    names = SessionStore().list()
    if not names:
        console.print("[dim]No sessions found.[/dim]")
        return
    for n in names:
        console.print(f"  {n}")


@session_app.command("clear")
def session_clear_cmd(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Session name to delete."),
    ] = "default",
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Delete a named session file."""
    from adt.core.session_store import SessionStore

    store = SessionStore()
    if not store.path(name).exists():
        console.print(f"[dim]No session '{name}' found — nothing to clear.[/dim]")
        return
    if not yes:
        typer.confirm(f"Delete session '{name}'?", abort=True)
    store.delete(name)
    console.print(f"[green]Session '{name}' cleared.[/green]")


@session_app.command("export")
def session_export_cmd(
    out: Annotated[
        str | None,
        typer.Argument(help="Output path (omit to print to stdout)."),
    ] = None,
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Session name to export."),
    ] = "default",
) -> None:
    """Dump the session JSON to stdout or a file."""
    from adt.core.session_store import SessionStore

    store = SessionStore()
    path = store.path(name)
    if not path.exists():
        console.print(f"[dim]No session '{name}' found.[/dim]")
        raise typer.Exit(code=1)
    content = path.read_text(encoding="utf-8")
    if out is None:
        console.print_json(content)
    else:
        from pathlib import Path

        Path(out).write_text(content, encoding="utf-8")
        console.print(f"[green]Session exported to {out}[/green]")


# ── runs subcommands (P10-15) ──────────────────────────────────────────


@runs_app.command("list")
def runs_list_cmd() -> None:
    """List saved run snapshots (interrupted runs)."""
    from adt.core.run_snapshot import RunStore

    store = RunStore()
    ids = store.list()
    if not ids:
        console.print("[dim]No saved runs.[/dim]")
        return
    for tid in ids:
        snap = store.load(tid)
        if snap:
            console.print(
                f"  {tid}  agent={snap.agent_name}  "
                f"iter={snap.iteration}/{snap.max_iterations}  "
                f"{snap.created_at}",
            )
        else:
            console.print(f"  {tid}  (corrupt)")


@runs_app.command("show")
def runs_show_cmd(
    trace_id: Annotated[str, typer.Argument(help="Trace ID of the run.")],
) -> None:
    """Show details of a saved run snapshot."""
    from adt.core.run_snapshot import RunStore

    snap = RunStore().load(trace_id)
    if snap is None:
        console.print(f"[red]Run '{trace_id}' not found.[/red]")
        raise typer.Exit(code=1)
    console.print_json(snap.model_dump_json(indent=2))


@runs_app.command("delete")
def runs_delete_cmd(
    trace_id: Annotated[str, typer.Argument(help="Trace ID of the run.")],
) -> None:
    """Delete a saved run snapshot."""
    from adt.core.run_snapshot import RunStore

    store = RunStore()
    if not store.path(trace_id).exists():
        console.print(f"[dim]Run '{trace_id}' not found.[/dim]")
        return
    store.delete(trace_id)
    console.print(f"[green]Run '{trace_id}' deleted.[/green]")


# ── plugins subcommands (P10-16) ───────────────────────────────────────


@plugins_app.command("list")
def plugins_list_cmd() -> None:
    """List installed community plugins."""
    from adt.core.plugin_loader import discover_skills, discover_tools

    skills = discover_skills()
    tools = discover_tools()
    if not skills and not tools:
        console.print("[dim]No plugins installed.[/dim]")
        return
    if skills:
        console.print("[bold]Skills:[/bold]")
        for s in skills:
            console.print(f"  {s['name']}  ({s['path']})")
    if tools:
        console.print("[bold]Tools:[/bold]")
        for t in tools:
            console.print(f"  {t['name']}  ({t['path']})")


@plugins_app.command("validate")
def plugins_validate_cmd(
    path: Annotated[
        str,
        typer.Argument(help="Path to the plugin directory to validate."),
    ],
) -> None:
    """Validate a plugin directory (check SKILL.md / tool.py)."""
    from pathlib import Path as _Path

    from adt.core.plugin_loader import validate_plugin

    errors = validate_plugin(_Path(path))
    if errors:
        for err in errors:
            console.print(f"[red]{err}[/red]")
        raise typer.Exit(code=1)
    console.print("[green]Plugin is valid.[/green]")


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
