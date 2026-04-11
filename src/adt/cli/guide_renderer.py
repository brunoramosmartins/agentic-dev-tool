"""Static quick-reference renderer for ``adt guide``.

The guide is rendered entirely from in-process data (no API calls, no
environment variables required). It is intentionally short — think of it as
the equivalent of ``?`` in Claude Code: a concise tour of the commands,
modes, levels, agents, and skills that ship with ``adt``.
"""

from __future__ import annotations

from importlib import metadata

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

_TAGLINE = (
    "Portfolio-grade CLI that routes natural-language questions to "
    "specialized agents, with supervised learning, code review, tracing, "
    "and learning analytics."
)

_COMMANDS: tuple[tuple[str, str, str], ...] = (
    (
        "ask",
        "Run an agent on a question.",
        'adt ask "Explain src/ layout" --repo .',
    ),
    (
        "ask --mode supervised",
        "Guided, step-by-step learning instead of a solution.",
        'adt ask "Implement binary search" --mode supervised --level beginner',
    ),
    (
        "review",
        "Send a code file to the reviewer LLM for structured feedback.",
        "adt review src/mymod/solution.py --context 'binary search'",
    ),
    (
        "stats",
        "Summarize supervised learning progress from the local log.",
        "adt stats --last 10",
    ),
    (
        "serve",
        "Start the optional FastAPI server (requires the [api] extra).",
        "adt serve --port 8765",
    ),
    (
        "config show|set|path",
        "Inspect or edit ~/.adt/config.toml.",
        "adt config show",
    ),
    (
        "guide",
        "Print this quick-reference (no API key needed).",
        "adt guide",
    ),
    (
        "version / info",
        "Print package version / short feature line.",
        "adt version",
    ),
)

_MODES: tuple[tuple[str, str, str], ...] = (
    (
        "execution",
        "Default. Solves the task end-to-end using the routed agent.",
        "adt ask '...' --repo .",
    ),
    (
        "supervised",
        "Teaches instead of solving. Emits steps, hints, and checkpoints "
        "via the supervised_engineering skill.",
        "adt ask '...' --mode supervised --level intermediate",
    ),
)

_LEVELS: tuple[tuple[str, str, str], ...] = (
    (
        "beginner",
        "Small steps, more hints, explicit type guidance.",
        "green",
    ),
    (
        "intermediate",
        "Balanced granularity and hinting (default for supervised).",
        "cyan",
    ),
    (
        "advanced",
        "Larger steps, design trade-offs, minimal hand-holding.",
        "magenta",
    ),
)

_AGENTS: tuple[tuple[str, str], ...] = (
    (
        "repo_agent",
        "Reads local trees and files, explains architecture, compares repos.",
    ),
    (
        "project_agent",
        "GitHub issues + milestones + local markdown roadmap/CHANGELOG.",
    ),
    (
        "research_agent",
        "arXiv search + HTTP fetch for technical topics.",
    ),
)

_SKILLS: tuple[tuple[str, str], ...] = (
    (
        "supervised_engineering",
        "Teaching heuristics, decomposition patterns, and review rubric "
        "injected into supervised + review prompts.",
    ),
)

_ENV: tuple[tuple[str, str, str], ...] = (
    ("OPENAI_API_KEY", "required", "Used by ask / review / serve."),
    (
        "GITHUB_TOKEN",
        "optional",
        "Higher GitHub API limits for project_agent (or pass --token).",
    ),
    (
        "ADT_*",
        "optional",
        "Override config.toml at runtime (see `adt config show`).",
    ),
)


def _package_version() -> str:
    try:
        return metadata.version("agentic-dev-tool")
    except metadata.PackageNotFoundError:
        return "dev"


def _commands_table() -> Table:
    table = Table(
        title="Commands",
        title_style="bold",
        title_justify="left",
        show_header=True,
        header_style="bold",
        expand=True,
    )
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("What it does")
    table.add_column("Example", style="dim")
    for name, purpose, example in _COMMANDS:
        table.add_row(name, purpose, example)
    return table


def _modes_table() -> Table:
    table = Table(
        title="Modes",
        title_style="bold",
        title_justify="left",
        show_header=True,
        header_style="bold",
        expand=True,
    )
    table.add_column("Mode", style="bold", no_wrap=True)
    table.add_column("Purpose")
    table.add_column("Example", style="dim")
    for name, purpose, example in _MODES:
        table.add_row(name, purpose, example)
    return table


def _levels_table() -> Table:
    table = Table(
        title="Difficulty Levels (supervised mode)",
        title_style="bold",
        title_justify="left",
        show_header=True,
        header_style="bold",
        expand=True,
    )
    table.add_column("Level", no_wrap=True)
    table.add_column("Effect on teaching")
    for name, effect, color in _LEVELS:
        table.add_row(Text(name, style=f"bold {color}"), effect)
    return table


def _agents_table() -> Table:
    table = Table(
        title="Agents",
        title_style="bold",
        title_justify="left",
        show_header=True,
        header_style="bold",
        expand=True,
    )
    table.add_column("Agent", style="cyan", no_wrap=True)
    table.add_column("Specialty")
    for name, spec in _AGENTS:
        table.add_row(name, spec)
    return table


def _skills_table() -> Table:
    table = Table(
        title="Skills",
        title_style="bold",
        title_justify="left",
        show_header=True,
        header_style="bold",
        expand=True,
    )
    table.add_column("Skill", style="cyan", no_wrap=True)
    table.add_column("What it provides")
    for name, desc in _SKILLS:
        table.add_row(name, desc)
    return table


def _env_table() -> Table:
    table = Table(
        title="Environment",
        title_style="bold",
        title_justify="left",
        show_header=True,
        header_style="bold",
        expand=True,
    )
    table.add_column("Variable", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Purpose")
    for name, status, purpose in _ENV:
        style = "bold red" if status == "required" else "dim"
        table.add_row(name, Text(status, style=style), purpose)
    return table


def _footer() -> Text:
    text = Text()
    text.append("Tips: ", style="bold")
    text.append("`adt <command> --help` shows every flag. ")
    text.append("`adt ask --trace` adds a routing/LLM trace panel. ")
    text.append("`adt stats` shows your supervised learning history.\n")
    text.append("Docs: ", style="bold")
    text.append("README.md · docs/architecture.md · docs/mcp.md · docs/agents.md")
    return text


class GuideRenderer:
    """Render the static ``adt guide`` quick-reference."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def render(self) -> None:
        """Print the quick-reference panel."""
        header = Text()
        header.append("adt ", style="bold cyan")
        header.append(f"v{_package_version()}", style="dim")
        header.append("\n")
        header.append(_TAGLINE)

        body = Group(
            header,
            Text(),
            _commands_table(),
            Text(),
            _modes_table(),
            Text(),
            _levels_table(),
            Text(),
            _agents_table(),
            Text(),
            _skills_table(),
            Text(),
            _env_table(),
            Text(),
            _footer(),
        )

        self._console.print(
            Panel(
                body,
                title="adt — Quick Reference",
                border_style="cyan",
                title_align="left",
            ),
        )
