"""Rich-based terminal renderer for trace events."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

from adt.tracing.context import TraceContext
from adt.tracing.cost import CostEstimator


class TraceRenderer:
    """Render a :class:`TraceContext` as a Rich tree panel."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def render(self, trace: TraceContext, *, model: str = "gpt-4o-mini") -> None:
        """Print a trace summary tree to the console."""
        tree = Tree(
            f"[bold]Trace[/bold] {trace.trace_id}  "
            f"[dim]({trace.elapsed_ms():.0f} ms)[/dim]"
        )

        for event in trace.events:
            label = f"[bold]{event.component}[/bold] → {event.event_type}"
            if event.iteration is not None:
                label += f" [dim](iter {event.iteration})[/dim]"

            node = tree.add(label)
            for key, value in event.data.items():
                node.add(f"[dim]{key}:[/dim] {value}")

        tokens = trace.cumulative_tokens
        if tokens["total_tokens"] > 0:
            cost = CostEstimator.estimate(
                model,
                tokens["prompt_tokens"],
                tokens["completion_tokens"],
            )
            cost_node = tree.add("[bold]Cost estimate[/bold]")
            cost_node.add(
                f"[dim]tokens:[/dim] {tokens['prompt_tokens']} prompt "
                f"+ {tokens['completion_tokens']} completion "
                f"= {tokens['total_tokens']} total"
            )
            cost_node.add(f"[dim]estimated:[/dim] ${cost.total_cost_usd:.6f} USD")

        self._console.print(
            Panel(tree, title="Trace", border_style="blue", title_align="left")
        )
