"""Interactive REPL for ``adt shell``.

Powered by ``prompt_toolkit`` with persistent history, tab completion
for slash commands and agent names, and multiline editing (Alt+Enter).
Free-form input is dispatched as ``adt ask <line>`` against the active
session, using the streaming pipeline when available.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompt_toolkit.completion import Completer
    from rich.console import Console

    from adt.cli.shell_commands import ShellState


_HISTORY_PATH = Path.home() / ".adt" / "shell_history"


def _ensure_prompt_toolkit() -> None:
    """Raise a friendly error if prompt_toolkit is not installed."""
    try:
        import prompt_toolkit  # noqa: F401
    except ImportError:
        msg = (
            "Install agentic-dev-tool[shell] to use adt shell.\n"
            "  pip install 'agentic-dev-tool[shell]'"
        )
        raise SystemExit(msg) from None


def _build_completer() -> Completer:
    """Build a WordCompleter for slash commands and agent names."""
    from prompt_toolkit.completion import WordCompleter

    from adt.cli.shell_commands import COMMAND_NAMES

    words = list(COMMAND_NAMES) + [
        "repo_agent",
        "research_agent",
        "project_agent",
        "on",
        "off",
        "list",
        "switch",
        "delete",
        "beginner",
        "intermediate",
        "advanced",
    ]
    return WordCompleter(words, ignore_case=True)


def run_shell(
    console: Console,
    *,
    repo: list[str] | None = None,
    model: str | None = None,
    trace: bool = False,
) -> None:
    """Main REPL loop — blocks until the user exits."""
    _ensure_prompt_toolkit()

    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory

    from adt.cli.shell_commands import ShellState, dispatch

    # Ensure ~/.adt exists for history
    _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    state = ShellState(
        repo=list(repo or []),
        model=model or "gpt-4o-mini",
        trace_enabled=trace,
    )

    completer = _build_completer()
    session: PromptSession[str] = PromptSession(
        history=FileHistory(str(_HISTORY_PATH)),
        completer=completer,
        multiline=False,
    )

    console.print(
        "[bold cyan]adt shell[/bold cyan] — "
        "interactive agent REPL. "
        "Type [bold]/help[/bold] for commands, "
        "[bold]Ctrl+D[/bold] to exit."
    )
    console.print(
        f"[dim]Session: {state.active_session} | "
        f"Model: {state.model} | "
        f"Trace: {'on' if state.trace_enabled else 'off'}[/dim]"
    )

    while True:
        try:
            line = session.prompt("adt> ")
        except KeyboardInterrupt:
            console.print("[dim]Interrupted. Type /exit to quit.[/dim]")
            continue
        except EOFError:
            console.print("[dim]Bye![/dim]")
            break

        stripped = line.strip()
        if not stripped:
            continue

        # Try slash command first
        if dispatch(stripped, state, console):
            continue

        # Free-form query → adt ask
        _dispatch_ask(stripped, state, console)

    # Save session on exit
    _save_session_on_exit(state)


def _dispatch_ask(query: str, state: ShellState, console: Console) -> None:
    """Run the ask pipeline for a free-form query."""
    from adt.ask_session import AskConfigurationError, run_ask

    try:
        exe = run_ask(
            query=query,
            repo=state.repo or None,
            force_agent=state.active_agent,
            model=state.model,
            trace=state.trace_enabled,
            mode="execution",
            session_name=state.active_session,
            verbose=state.verbose,
            configure_logging=False,
        )
    except AskConfigurationError as exc:
        console.print(f"[red]{exc}[/red]")
        return

    from rich.markdown import Markdown
    from rich.panel import Panel

    routed = exe.response.routed_agent or "supervisor"
    console.print(f"[dim]Agent:[/dim] [bold]{routed}[/bold]")
    console.print(
        Panel(
            Markdown(exe.response.answer),
            title="Answer",
            border_style="green",
            title_align="left",
        )
    )

    tools_line = (
        ", ".join(exe.response.tools_used) if exe.response.tools_used else "none"
    )
    console.print(f"[dim]Tools used:[/dim] {tools_line}")

    if exe.trace_context is not None:
        from adt.tracing.renderer import TraceRenderer

        TraceRenderer(console).render(exe.trace_context, model=state.model)


def _save_session_on_exit(state: ShellState) -> None:
    """Persist session metadata on REPL exit."""
    try:
        from adt.core.session_store import SessionStore

        store = SessionStore()
        # Touch the session file to mark last-used
        if store.path(state.active_session).exists():
            store.path(state.active_session).touch()
    except Exception:  # noqa: BLE001
        pass
