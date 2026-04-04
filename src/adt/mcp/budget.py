"""Token budget slices for system, context, tools schema, and completion."""

from __future__ import annotations

import os

# Default window for one ``Runner.run`` turn (logical budget, not model maximum).
DEFAULT_TOTAL_TOKEN_BUDGET = 16_384


def read_total_budget_from_environ() -> int:
    """Return ``ADT_TOKEN_BUDGET`` if valid, else :data:`DEFAULT_TOTAL_TOKEN_BUDGET`."""
    raw = os.environ.get("ADT_TOKEN_BUDGET", "").strip()
    if not raw:
        return DEFAULT_TOTAL_TOKEN_BUDGET
    try:
        v = int(raw)
    except ValueError:
        return DEFAULT_TOTAL_TOKEN_BUDGET
    return max(1024, v)


def allocate_budget(total_tokens: int | None = None) -> dict[str, int]:
    """Split a total token budget into MCP layers (20/50/10/20 percent).

    Args:
        total_tokens: Whole budget for one request turn; defaults to env or
            :data:`DEFAULT_TOTAL_TOKEN_BUDGET`.

    Returns:
        Keys: ``system``, ``context``, ``tools``, ``response`` — integer caps.
    """
    total = (
        total_tokens if total_tokens is not None else read_total_budget_from_environ()
    )
    total = max(1024, int(total))
    return {
        "system": int(total * 0.20),
        "context": int(total * 0.50),
        "tools": int(total * 0.10),
        "response": int(total * 0.20),
    }
