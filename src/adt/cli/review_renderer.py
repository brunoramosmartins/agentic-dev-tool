"""Rich-based terminal renderer for supervised code review feedback."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from adt.models.schemas import CodeIssue, ReviewFeedback

_ASSESSMENT_LABEL = {
    "needs_work": ("Needs Work", "red"),
    "on_track": ("On Track", "yellow"),
    "excellent": ("Excellent", "green"),
}

_SEVERITY_GLYPH = {
    "error": ("x", "red"),
    "warning": ("!", "yellow"),
    "suggestion": ("i", "blue"),
}


class ReviewRenderer:
    """Render a :class:`ReviewFeedback` as a structured terminal panel."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def render(self, feedback: ReviewFeedback) -> None:
        """Print the review with assessment, issues, strengths, and next step."""
        sections: list[Text] = [self._assessment_header(feedback.overall_assessment)]

        if feedback.issues:
            sections.append(self._issues_section(feedback.issues))
        if feedback.strengths:
            sections.append(self._bullet_section("Strengths", feedback.strengths))
        if feedback.improvements:
            sections.append(self._bullet_section("Improvements", feedback.improvements))
        if feedback.next_step:
            note = Text()
            note.append("\n")
            note.append("Next Step:\n", style="bold")
            note.append("  ")
            note.append(feedback.next_step)
            sections.append(note)

        border = _ASSESSMENT_LABEL.get(feedback.overall_assessment, ("", "cyan"))[1]
        self._console.print(
            Panel(
                Group(*sections),
                title="Code Review",
                border_style=border,
                title_align="left",
            ),
        )

    # ---------- sections ----------

    @staticmethod
    def _assessment_header(assessment: str) -> Text:
        label, color = _ASSESSMENT_LABEL.get(assessment, (assessment, "white"))
        text = Text()
        text.append("Assessment: ", style="bold")
        text.append(label, style=f"bold {color}")
        return text

    @staticmethod
    def _issues_section(issues: list[CodeIssue]) -> Text:
        text = Text()
        text.append("\n")
        text.append("Issues:\n", style="bold")
        for issue in issues:
            glyph, color = _SEVERITY_GLYPH.get(issue.severity, ("-", "white"))
            text.append("  ")
            text.append(glyph, style=color)
            text.append(" ")
            if issue.line is not None:
                text.append(f"Line {issue.line}: ", style="bold")
            text.append(issue.description)
            text.append("\n")
            if issue.fix_hint:
                text.append("      Hint: ", style="dim")
                text.append(issue.fix_hint, style="dim")
                text.append("\n")
        return text

    @staticmethod
    def _bullet_section(title: str, items: list[str]) -> Text:
        text = Text()
        text.append("\n")
        text.append(f"{title}:\n", style="bold")
        for item in items:
            text.append("  - ", style="cyan")
            text.append(item)
            text.append("\n")
        return text
