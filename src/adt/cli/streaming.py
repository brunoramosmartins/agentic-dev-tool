"""Streaming answer renderer using ``rich.live.Live``.

Consumes :class:`RunChunk` events from the streaming runner pipeline
and incrementally renders a Rich Markdown panel in the terminal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from rich.markdown import Markdown
from rich.panel import Panel

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rich.console import Console


@dataclass
class RunChunk:
    """Single event emitted by the streaming pipeline."""

    kind: Literal[
        "token",
        "tool_call_start",
        "tool_call_end",
        "iteration_complete",
        "final",
    ]
    text: str = ""
    tool_name: str = ""
    iteration: int = 0
    data: dict[str, object] = field(default_factory=dict)


class StreamRenderer:
    """Accumulates ``RunChunk`` tokens and live-updates a Markdown panel."""

    def __init__(self, console: Console) -> None:
        self._console = console
        self._buffer: list[str] = []

    def render_stream(
        self,
        chunks: Iterator[RunChunk],
        *,
        border_style: str = "green",
    ) -> str:
        """Consume *chunks*, live-update the panel, and return final text."""
        from rich.live import Live

        panel = Panel(
            Markdown("▌"),
            title="Answer",
            border_style=border_style,
            title_align="left",
        )

        with Live(panel, console=self._console, refresh_per_second=12) as live:
            for chunk in chunks:
                if chunk.kind == "token":
                    self._buffer.append(chunk.text)
                    accumulated = "".join(self._buffer)
                    panel = Panel(
                        Markdown(accumulated + "▌"),
                        title="Answer",
                        border_style=border_style,
                        title_align="left",
                    )
                    live.update(panel)
                elif chunk.kind == "tool_call_start":
                    self._buffer.append(f"\n\n> 🔧 Calling `{chunk.tool_name}`...\n\n")
                    accumulated = "".join(self._buffer)
                    panel = Panel(
                        Markdown(accumulated + "▌"),
                        title="Answer",
                        border_style=border_style,
                        title_align="left",
                    )
                    live.update(panel)
                elif chunk.kind == "tool_call_end":
                    self._buffer.append(f"> ✅ `{chunk.tool_name}` done\n\n")
                    accumulated = "".join(self._buffer)
                    panel = Panel(
                        Markdown(accumulated + "▌"),
                        title="Answer",
                        border_style=border_style,
                        title_align="left",
                    )
                    live.update(panel)
                elif chunk.kind == "final":
                    if chunk.text:
                        self._buffer.clear()
                        self._buffer.append(chunk.text)

            # Final render without cursor
            final_text = "".join(self._buffer)
            panel = Panel(
                Markdown(final_text),
                title="Answer",
                border_style=border_style,
                title_align="left",
            )
            live.update(panel)

        return final_text
