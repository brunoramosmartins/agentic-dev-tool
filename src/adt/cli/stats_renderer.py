"""Rich-based renderer for :class:`LearningStats`."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from adt.analytics.stats import LearningStats


class StatsRenderer:
    """Render a :class:`LearningStats` summary as a terminal panel."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def render(self, stats: LearningStats) -> None:
        """Print the stats panel."""
        header = Text()
        header.append(f"Sessions: {stats.sessions}".ljust(22), style="bold")
        header.append(
            f"Avg steps/session: {stats.avg_steps_per_session}",
            style="bold",
        )
        header.append("\n")
        header.append(f"Reviews:  {stats.reviews}".ljust(22), style="bold")
        header.append(
            f"Avg iterations/session: {stats.avg_iterations_per_step}",
            style="bold",
        )

        sections: list[Text] = [header]

        if stats.common_issues:
            issues = Text()
            issues.append("\n")
            issues.append("Common Issues:\n", style="bold")
            for rank, (name, count) in enumerate(stats.common_issues, start=1):
                issues.append(f"  {rank}. ")
                issues.append(name, style="yellow")
                noun = "occurrence" if count == 1 else "occurrences"
                issues.append(f" ({count} {noun})\n", style="dim")
            sections.append(issues)

        if stats.assessments:
            verdict = Text()
            verdict.append("\n")
            verdict.append("Review Verdicts:\n", style="bold")
            for name, count in sorted(stats.assessments.items(), key=lambda kv: -kv[1]):
                verdict.append("  - ")
                verdict.append(name, style=_verdict_style(name))
                verdict.append(f" x{count}\n", style="dim")
            sections.append(verdict)

        if stats.improvement_trend:
            trend = Text()
            trend.append("\n")
            trend.append("Improvement Trend:\n", style="bold")
            trend.append("  Iterations per session: ")
            arrow = " -> ".join(str(v) for v in stats.improvement_trend)
            trend.append(arrow, style="cyan")
            sections.append(trend)

        if stats.total_tokens:
            tokens = Text()
            tokens.append("\n")
            tokens.append("Total LLM tokens: ", style="bold")
            tokens.append(f"{stats.total_tokens:,}", style="dim")
            sections.append(tokens)

        if stats.sessions == 0:
            empty = Text()
            empty.append("\n")
            empty.append(
                "No supervised learning events recorded yet. Run "
                "`adt ask ... --mode supervised` or `adt review` first.",
                style="dim",
            )
            sections.append(empty)

        self._console.print(
            Panel(
                Group(*sections),
                title="Learning Stats",
                border_style="blue",
                title_align="left",
            ),
        )


def _verdict_style(name: str) -> str:
    if name == "needs_work":
        return "red"
    if name == "on_track":
        return "yellow"
    if name == "excellent":
        return "green"
    return "white"
