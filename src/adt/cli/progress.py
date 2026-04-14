"""Rich progress bars for tool execution (file walks, multi-fetch).

Provides a ``ProgressCallback`` protocol and a Rich-backed implementation
that can be injected into tool handlers via the ``progress`` parameter on
:class:`~adt.mcp.registry.ToolDefinition`.

Disabled by the same ``ADT_NO_PROGRESS=1`` flag as :mod:`adt.cli.status`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from adt.cli.status import _progress_enabled

if TYPE_CHECKING:
    from rich.console import Console
    from rich.progress import Progress, TaskID


class ProgressCallback(Protocol):
    """Minimal interface for reporting incremental progress."""

    def __call__(self, current: int, total: int) -> None: ...


class RichProgressReporter:
    """Wraps a ``rich.progress.Progress`` bar behind the callback protocol.

    The caller calls ``start(label, total)`` to begin a task, then passes
    :meth:`step` as the ``progress`` callback to tool handlers.
    """

    def __init__(self, console: Console) -> None:
        self._console = console
        self._enabled = _progress_enabled()
        self._progress: Progress | None = None
        self._task_id: TaskID | None = None
        self._calls: list[tuple[int, int]] = []

    @property
    def calls(self) -> list[tuple[int, int]]:
        """Recorded ``(current, total)`` pairs (for testing)."""
        return list(self._calls)

    def start(self, label: str, total: int) -> None:
        """Create and start a Rich progress bar."""
        if not self._enabled:
            return
        from rich.progress import (
            BarColumn,
            MofNCompleteColumn,
            Progress,
            TextColumn,
            TimeRemainingColumn,
        )

        self._progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=self._console,
        )
        self._progress.start()
        self._task_id = self._progress.add_task(label, total=total)

    def step(self, current: int, total: int) -> None:
        """Advance the progress bar by one unit."""
        self._calls.append((current, total))
        if self._progress is not None and self._task_id is not None:
            self._progress.update(
                self._task_id,
                completed=current,
                total=total,
            )

    def finish(self) -> None:
        """Stop and clean up the progress bar."""
        if self._progress is not None:
            self._progress.stop()
            self._progress = None
            self._task_id = None


class NullProgressReporter:
    """No-op progress reporter for non-interactive contexts."""

    def __init__(self) -> None:
        self._calls: list[tuple[int, int]] = []

    @property
    def calls(self) -> list[tuple[int, int]]:
        return list(self._calls)

    def start(self, label: str, total: int) -> None:
        pass

    def step(self, current: int, total: int) -> None:
        self._calls.append((current, total))

    def finish(self) -> None:
        pass
