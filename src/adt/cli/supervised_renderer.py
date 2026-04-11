"""Rich-based terminal renderer for supervised mode responses."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from adt.models.schemas import SupervisedResponse

_LEVEL_STYLES: dict[str, tuple[str, str]] = {
    "beginner": ("green", "Beginner"),
    "intermediate": ("cyan", "Intermediate"),
    "advanced": ("magenta", "Advanced"),
}


class SupervisedRenderer:
    """Render a :class:`SupervisedResponse` as a teaching panel."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def render(
        self,
        response: SupervisedResponse,
        *,
        level: str | None = None,
    ) -> None:
        """Print the current step with goal, requirements, hints, and questions.

        Args:
            response: Parsed structured response to display.
            level: Optional difficulty level. When provided, it is shown in
                the panel header and color-codes the border.
        """
        step = response.current_step
        border, label = _LEVEL_STYLES.get(level or "", ("cyan", ""))

        header = Text()
        if label:
            header.append("Level: ", style="bold")
            header.append(label, style=f"bold {border}")
            header.append("\n")
        header.append("Problem: ", style="bold")
        header.append(response.problem_summary)
        header.append("\n\n")
        header.append(
            f"Step {step.step_number} of {response.total_steps}: ",
            style=f"bold {border}",
        )
        header.append(step.goal)

        sections: list[Text] = [header]

        if step.requirements:
            sections.append(self._section("Requirements", step.requirements))
        if step.hints:
            sections.append(self._section("Hints", step.hints))
        if step.questions:
            sections.append(self._section("Questions for you", step.questions))

        if response.progress_note:
            note = Text()
            note.append("\n")
            note.append("Next: ", style="bold dim")
            note.append(response.progress_note, style="dim")
            sections.append(note)

        title = "Supervised Mode"
        if label:
            title = f"Supervised Mode — {label}"
        self._console.print(
            Panel(
                Group(*sections),
                title=title,
                border_style=border,
                title_align="left",
            ),
        )

    @staticmethod
    def _section(title: str, items: list[str]) -> Text:
        text = Text()
        text.append("\n")
        text.append(f"{title}:", style="bold")
        text.append("\n")
        for item in items:
            text.append("  - ", style="cyan")
            text.append(item)
            text.append("\n")
        return text
