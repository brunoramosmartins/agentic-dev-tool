"""Rich-based renderer for :class:`LearningStats`."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from adt.analytics.stats import LearningStats
from adt.cli.i18n import t


class StatsRenderer:
    """Render a :class:`LearningStats` summary as a terminal panel."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def render(self, stats: LearningStats) -> None:
        """Print the stats panel."""
        header = Text()
        header.append(
            f"{t('stats.sessions')}: {stats.sessions}".ljust(22),
            style="bold",
        )
        header.append(
            f"{t('stats.avg_steps')}: {stats.avg_steps_per_session}",
            style="bold",
        )
        header.append("\n")
        header.append(
            f"{t('stats.reviews')}:  {stats.reviews}".ljust(22),
            style="bold",
        )
        header.append(
            f"{t('stats.avg_iterations')}: {stats.avg_iterations_per_step}",
            style="bold",
        )

        sections: list[Text] = [header]

        if stats.common_issues:
            issues = Text()
            issues.append("\n")
            issues.append(f"{t('stats.common_issues')}:\n", style="bold")
            for rank, (name, count) in enumerate(stats.common_issues, start=1):
                issues.append(f"  {rank}. ")
                issues.append(name, style="yellow")
                noun = t("stats.occurrence") if count == 1 else t("stats.occurrences")
                issues.append(f" ({count} {noun})\n", style="dim")
            sections.append(issues)

        if stats.assessments:
            verdict = Text()
            verdict.append("\n")
            verdict.append(f"{t('stats.review_verdicts')}:\n", style="bold")
            for name, count in sorted(stats.assessments.items(), key=lambda kv: -kv[1]):
                verdict.append("  - ")
                verdict.append(name, style=_verdict_style(name))
                verdict.append(f" x{count}\n", style="dim")
            sections.append(verdict)

        if stats.improvement_trend:
            trend = Text()
            trend.append("\n")
            trend.append(f"{t('stats.improvement_trend')}:\n", style="bold")
            trend.append(f"  {t('stats.iterations_per_session')}: ")
            arrow = " -> ".join(str(v) for v in stats.improvement_trend)
            trend.append(arrow, style="cyan")
            sections.append(trend)

        if stats.total_tokens:
            tokens = Text()
            tokens.append("\n")
            tokens.append(f"{t('stats.total_tokens')}: ", style="bold")
            tokens.append(f"{stats.total_tokens:,}", style="dim")
            sections.append(tokens)

        if stats.sessions == 0:
            empty = Text()
            empty.append("\n")
            empty.append(t("stats.no_events"), style="dim")
            sections.append(empty)

        self._console.print(
            Panel(
                Group(*sections),
                title=t("stats.title"),
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
