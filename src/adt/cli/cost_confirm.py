"""Cost confirmation prompt before expensive LLM calls.

Uses :class:`~adt.tracing.cost.CostEstimator` to compute an upper-bound
estimate and prompts the user when it exceeds the configured threshold.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console


_DEFAULT_THRESHOLD: float = 0.05


def _should_confirm(
    estimated_cost: float,
    threshold: float,
    *,
    yes_flag: bool = False,
) -> bool:
    """Return whether an interactive confirmation is needed."""
    if yes_flag:
        return False
    if os.environ.get("ADT_NO_CONFIRM", "").strip() in ("1", "true", "yes"):
        return False
    return estimated_cost > threshold


def estimate_upper_bound(
    model: str,
    prompt_tokens: int,
    max_completion_tokens: int,
) -> float:
    """Return the worst-case USD cost for one LLM call."""
    from adt.tracing.cost import CostEstimator

    breakdown = CostEstimator.estimate(model, prompt_tokens, max_completion_tokens)
    return breakdown.total_cost_usd


def confirm_cost(
    console: Console,
    model: str,
    prompt_tokens: int,
    max_completion_tokens: int,
    *,
    threshold: float = _DEFAULT_THRESHOLD,
    yes_flag: bool = False,
) -> bool:
    """Check cost and prompt the user if above threshold.

    Returns:
        ``True`` if the user confirmed or the cost is below the threshold.
        ``False`` if the user declined.
    """
    cost = estimate_upper_bound(model, prompt_tokens, max_completion_tokens)
    if not _should_confirm(cost, threshold, yes_flag=yes_flag):
        return True

    console.print(
        f"[yellow]Estimated cost: ${cost:.4f} (threshold: ${threshold:.4f})[/yellow]"
    )
    try:
        import typer

        typer.confirm("Continue?", default=False, abort=False)
    except (KeyboardInterrupt, EOFError):
        console.print("[dim]Cancelled.[/dim]")
        return False
    except SystemExit:
        # typer.confirm with abort=False should not raise SystemExit,
        # but handle gracefully
        console.print("[dim]Cancelled.[/dim]")
        return False
    return True
