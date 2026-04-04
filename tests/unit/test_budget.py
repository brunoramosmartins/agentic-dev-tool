"""Token budget allocation."""

from __future__ import annotations

from adt.mcp.budget import allocate_budget, read_total_budget_from_environ


def test_allocate_budget_splits() -> None:
    """Slices should sum to roughly the total window."""
    total = 10_000
    parts = allocate_budget(total)
    assert parts["system"] == 2000
    assert parts["context"] == 5000
    assert parts["tools"] == 1000
    assert parts["response"] == 2000


def test_read_total_budget_from_environ(monkeypatch) -> None:
    """ADT_TOKEN_BUDGET should override when parseable."""
    monkeypatch.setenv("ADT_TOKEN_BUDGET", "8192")
    assert read_total_budget_from_environ() == 8192
    monkeypatch.delenv("ADT_TOKEN_BUDGET", raising=False)
    v = read_total_budget_from_environ()
    assert v >= 1024
