"""Rich status spinner for LLM calls and tool execution.

Wraps a ``rich.status.Status`` context that adapts its text as the
runner loop progresses: routing → calling agent → running tool.
Disabled when stdout is not a tty, or ``ADT_NO_PROGRESS=1``.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console
    from rich.status import Status


def _progress_enabled() -> bool:
    """Return ``False`` when spinners/progress should be suppressed."""
    if os.environ.get("ADT_NO_PROGRESS", "").strip() in ("1", "true", "yes"):
        return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


class StatusReporter:
    """Manages a Rich spinner and exposes update methods for each phase."""

    def __init__(self, console: Console) -> None:
        self._console = console
        self._enabled = _progress_enabled()
        self._status: Status | None = None
        self._phases: list[str] = []

    @property
    def phases(self) -> list[str]:
        """Return the recorded phase labels (for testing)."""
        return list(self._phases)

    @contextmanager
    def live(self) -> Generator[StatusReporter, None, None]:
        """Context manager that starts/stops the Rich status spinner."""
        if not self._enabled:
            yield self
            return

        from rich.status import Status

        status = Status("Thinking...", console=self._console, spinner="dots")
        self._status = status
        self._phases.append("Thinking...")
        status.start()
        try:
            yield self
        finally:
            status.stop()
            self._status = None

    def update(self, text: str) -> None:
        """Change the spinner label."""
        self._phases.append(text)
        if self._status is not None:
            self._status.update(text)

    def routing(self) -> None:
        self.update("Routing...")

    def calling_agent(self, agent: str) -> None:
        self.update(f"Calling {agent}...")

    def running_tool(self, tool: str) -> None:
        self.update(f"Running tool: {tool}")

    def building_context(self) -> None:
        self.update("Building context...")

    def iteration(self, n: int, total: int) -> None:
        self.update(f"Iteration {n}/{total}...")
