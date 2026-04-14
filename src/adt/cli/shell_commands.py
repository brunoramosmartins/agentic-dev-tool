"""Slash command dispatcher for the ``adt shell`` REPL.

Each slash command is a simple function that receives the REPL state
and an argument string, then returns a status message (or empty string).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console


@dataclass
class ShellState:
    """Mutable state shared across REPL turns."""

    active_session: str = "default"
    active_agent: str | None = None
    trace_enabled: bool = False
    model: str = "gpt-4o-mini"
    repo: list[str] = field(default_factory=list)
    verbose: bool = False
    cost_threshold: float = 0.05


def _cmd_help(state: ShellState, _args: str, console: Console) -> str:
    """Print available REPL slash commands."""
    lines = [
        "[bold]adt shell — slash commands[/bold]",
        "",
        "  /help                Show this help",
        "  /exit                Exit the REPL",
        "  /clear               Clear the terminal",
        "  /trace on|off        Toggle request tracing",
        "  /stats [--last N]    Show learning stats",
        "  /session list        List sessions",
        "  /session switch <n>  Switch active session",
        "  /session delete <n>  Delete a session",
        "  /agent <name>        Force agent for next queries",
        "  /agent clear         Clear forced agent",
        "  /cost                Show cost threshold",
        "  /version             Show version",
        "  /start <problem>     Start supervised session",
        "  /next                Advance to next step",
        "  /hint                Request a hint",
        "  /submit <code|@path> Submit code for review",
        "",
        "  Any other input is sent as `adt ask <input>`",
    ]
    console.print("\n".join(lines))
    return ""


def _cmd_exit(_state: ShellState, _args: str, _console: Console) -> str:
    raise SystemExit(0)


def _cmd_clear(_state: ShellState, _args: str, console: Console) -> str:
    console.clear()
    return ""


def _cmd_trace(state: ShellState, args: str, console: Console) -> str:
    arg = args.strip().lower()
    if arg == "on":
        state.trace_enabled = True
        console.print("[green]Tracing enabled.[/green]")
    elif arg == "off":
        state.trace_enabled = False
        console.print("[dim]Tracing disabled.[/dim]")
    else:
        status = "on" if state.trace_enabled else "off"
        console.print(f"[dim]Trace is {status}. Usage: /trace on|off[/dim]")
    return ""


def _cmd_stats(_state: ShellState, args: str, console: Console) -> str:
    from adt.analytics import compute_stats, read_learning_events
    from adt.cli.stats_renderer import StatsRenderer

    last_n = None
    parts = args.strip().split()
    import contextlib

    for i, p in enumerate(parts):
        if p == "--last" and i + 1 < len(parts):
            with contextlib.suppress(ValueError):
                last_n = int(parts[i + 1])

    events = read_learning_events()
    stats = compute_stats(events, last_n=last_n)
    StatsRenderer(console).render(stats)
    return ""


def _cmd_session(state: ShellState, args: str, console: Console) -> str:
    from adt.core.session_store import SessionStore

    parts = args.strip().split(maxsplit=1)
    subcmd = parts[0] if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    store = SessionStore()

    if subcmd == "list":
        names = store.list()
        if not names:
            console.print("[dim]No sessions found.[/dim]")
        else:
            active = state.active_session
            for n in names:
                marker = " [green]← active[/green]" if n == active else ""
                console.print(f"  {n}{marker}")
    elif subcmd == "switch" and arg:
        state.active_session = arg
        console.print(f"[green]Switched to session '{arg}'.[/green]")
    elif subcmd == "delete" and arg:
        if store.path(arg).exists():
            store.delete(arg)
            console.print(f"[green]Session '{arg}' deleted.[/green]")
            if state.active_session == arg:
                state.active_session = "default"
        else:
            console.print(f"[dim]Session '{arg}' not found.[/dim]")
    else:
        console.print("[dim]Usage: /session list | switch <name> | delete <name>[/dim]")
    return ""


def _cmd_agent(state: ShellState, args: str, console: Console) -> str:
    valid = {"repo_agent", "research_agent", "project_agent"}
    arg = args.strip()
    if arg == "clear":
        state.active_agent = None
        console.print("[dim]Agent override cleared.[/dim]")
    elif arg in valid:
        state.active_agent = arg
        console.print(f"[green]Agent forced to '{arg}'.[/green]")
    elif arg:
        console.print(
            f"[red]Unknown agent '{arg}'.[/red] Valid: {', '.join(sorted(valid))}"
        )
    else:
        current = state.active_agent or "auto (supervisor)"
        console.print(f"[dim]Active agent: {current}[/dim]")
    return ""


def _cmd_cost(state: ShellState, _args: str, console: Console) -> str:
    console.print(
        f"[dim]Cost confirmation threshold: ${state.cost_threshold:.4f}[/dim]"
    )
    return ""


def _cmd_version(_state: ShellState, _args: str, console: Console) -> str:
    try:
        from importlib import metadata

        ver = metadata.version("agentic-dev-tool")
    except Exception:  # noqa: BLE001
        ver = "dev"
    console.print(f"[dim]adt {ver}[/dim]")
    return ""


def _cmd_start(state: ShellState, args: str, console: Console) -> str:
    """Start or resume a supervised session."""
    problem = args.strip()
    if not problem:
        console.print("[red]Usage: /start <problem description>[/red]")
        return ""

    level = "intermediate"
    # Parse --level flag
    parts = problem.split()
    for i, p in enumerate(parts):
        if p == "--level" and i + 1 < len(parts):
            level = parts[i + 1]
            parts = parts[:i] + parts[i + 2 :]
            problem = " ".join(parts)
            break

    from adt.ask_session import AskConfigurationError, run_ask

    try:
        exe = run_ask(
            query=problem,
            repo=state.repo or None,
            mode="supervised",
            level=level,
            session_name=state.active_session,
            trace=state.trace_enabled,
            configure_logging=False,
        )
    except AskConfigurationError as exc:
        console.print(f"[red]{exc}[/red]")
        return ""

    if exe.supervised_response is not None:
        from adt.cli.supervised_renderer import SupervisedRenderer

        SupervisedRenderer(console).render(
            exe.supervised_response,
            level=exe.supervised_level,
        )
    else:
        from rich.markdown import Markdown
        from rich.panel import Panel

        console.print(
            Panel(
                Markdown(exe.response.answer),
                title="Supervised",
                border_style="cyan",
            )
        )
    return ""


def _cmd_next(state: ShellState, _args: str, console: Console) -> str:
    """Advance to the next supervised step."""
    from adt.ask_session import AskConfigurationError, run_ask

    try:
        exe = run_ask(
            query="Continue to the next step.",
            repo=state.repo or None,
            mode="supervised",
            level="intermediate",
            session_name=state.active_session,
            trace=state.trace_enabled,
            configure_logging=False,
        )
    except AskConfigurationError as exc:
        console.print(f"[red]{exc}[/red]")
        return ""

    if exe.supervised_response is not None:
        from adt.cli.supervised_renderer import SupervisedRenderer

        SupervisedRenderer(console).render(exe.supervised_response)
    else:
        console.print(f"[dim]{exe.response.answer[:500]}[/dim]")
    return ""


def _cmd_hint(state: ShellState, _args: str, console: Console) -> str:
    """Request a hint for the current supervised step."""
    from adt.ask_session import AskConfigurationError, run_ask

    try:
        exe = run_ask(
            query="Give me a hint for the current step.",
            repo=state.repo or None,
            mode="supervised",
            level="beginner",
            session_name=state.active_session,
            trace=state.trace_enabled,
            configure_logging=False,
        )
    except AskConfigurationError as exc:
        console.print(f"[red]{exc}[/red]")
        return ""

    if exe.supervised_response is not None:
        from adt.cli.supervised_renderer import SupervisedRenderer

        SupervisedRenderer(console).render(exe.supervised_response)
    else:
        console.print(f"[dim]{exe.response.answer[:500]}[/dim]")
    return ""


def _cmd_submit(state: ShellState, args: str, console: Console) -> str:
    """Submit code for review in the supervised session."""
    code = args.strip()
    if not code:
        console.print("[red]Usage: /submit <code> or /submit @path[/red]")
        return ""

    # Handle @path syntax
    if code.startswith("@"):
        from pathlib import Path

        fpath = Path(code[1:])
        if not fpath.is_file():
            console.print(f"[red]File not found: {fpath}[/red]")
            return ""
        code = fpath.read_text(encoding="utf-8")

    import tempfile

    from adt.review_session import ReviewConfigurationError, run_review

    # Write code to a temp file for the reviewer
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = run_review(
            file=tmp_path,
            level="intermediate",
            session_name=state.active_session,
            verbose=False,
        )
    except ReviewConfigurationError as exc:
        console.print(f"[red]{exc}[/red]")
        return ""
    finally:
        import os

        os.unlink(tmp_path)

    if result.feedback is not None:
        from adt.cli.review_renderer import ReviewRenderer

        ReviewRenderer(console).render(result.feedback)
    else:
        console.print(f"[dim]{result.raw_answer or '(no response)'}[/dim]")
    return ""


# ── Command registry ──────────────────────────────────────────────────

SLASH_COMMANDS: dict[str, Any] = {
    "/help": _cmd_help,
    "/exit": _cmd_exit,
    "/quit": _cmd_exit,
    "/clear": _cmd_clear,
    "/trace": _cmd_trace,
    "/stats": _cmd_stats,
    "/session": _cmd_session,
    "/agent": _cmd_agent,
    "/cost": _cmd_cost,
    "/version": _cmd_version,
    "/start": _cmd_start,
    "/next": _cmd_next,
    "/hint": _cmd_hint,
    "/submit": _cmd_submit,
}

COMMAND_NAMES: list[str] = sorted(SLASH_COMMANDS.keys())


def dispatch(
    line: str,
    state: ShellState,
    console: Console,
) -> bool:
    """Try to dispatch *line* as a slash command.

    Returns ``True`` if the line was handled (even if the command failed),
    ``False`` if it should be treated as a free-form query.
    """
    stripped = line.strip()
    if not stripped.startswith("/"):
        return False

    parts = stripped.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    handler = SLASH_COMMANDS.get(cmd)
    if handler is None:
        console.print(
            f"[red]Unknown command: {cmd}[/red]. Type /help for available commands."
        )
        return True

    handler(state, args, console)
    return True
