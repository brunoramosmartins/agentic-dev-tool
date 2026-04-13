"""Rich renderer for the ``adt session show`` subcommand."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from adt.core.session import SessionContext


class SessionRenderer:
    """Render a :class:`SessionContext` as a Rich table."""

    def __init__(self, console: Console) -> None:
        self._console = console

    def render(self, sess: SessionContext) -> None:
        if sess.is_empty():
            self._console.print("[dim]No active supervised session.[/dim]")
            return

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="bold")
        table.add_column("Value")
        table.add_row("Problem", sess.problem_summary or "—")
        table.add_row("Step", f"{sess.current_step} / {sess.total_steps}")
        table.add_row("Iterations", str(sess.iteration_count))
        if sess.previous_feedback:
            table.add_row("Last verdict", sess.previous_feedback[-1])
            table.add_row(
                "Feedback history",
                ", ".join(sess.previous_feedback),
            )
        else:
            table.add_row("Feedback", "—")

        self._console.print(
            Panel(table, title="adt — Session", border_style="blue"),
        )
