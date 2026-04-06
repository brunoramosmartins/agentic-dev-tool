"""Unit tests for CostEstimator."""

from __future__ import annotations

from adt.tracing.cost import CostBreakdown, CostEstimator


def test_known_model_pricing() -> None:
    result = CostEstimator.estimate("gpt-4o-mini", 1_000_000, 1_000_000)
    assert result.prompt_cost_usd == 0.15
    assert result.completion_cost_usd == 0.60
    assert result.total_cost_usd == 0.75


def test_gpt4o_pricing() -> None:
    result = CostEstimator.estimate("gpt-4o", 1_000_000, 1_000_000)
    assert result.prompt_cost_usd == 2.50
    assert result.completion_cost_usd == 10.00
    assert result.total_cost_usd == 12.50


def test_unknown_model_uses_default() -> None:
    result = CostEstimator.estimate("unknown-model", 1_000_000, 1_000_000)
    # Default pricing = gpt-4o-mini
    assert result.prompt_cost_usd == 0.15
    assert result.completion_cost_usd == 0.60


def test_zero_tokens() -> None:
    result = CostEstimator.estimate("gpt-4o-mini", 0, 0)
    assert result.total_cost_usd == 0.0


def test_small_token_count() -> None:
    result = CostEstimator.estimate("gpt-4o-mini", 500, 200)
    assert result.prompt_cost_usd > 0
    assert result.completion_cost_usd > 0
    assert result.total_cost_usd < 0.001


def test_cost_breakdown_fields() -> None:
    result = CostEstimator.estimate("gpt-4o-mini", 100, 50)
    assert isinstance(result, CostBreakdown)
    assert result.model == "gpt-4o-mini"
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 50


def test_gpt41_mini_pricing() -> None:
    result = CostEstimator.estimate("gpt-4.1-mini", 1_000_000, 1_000_000)
    assert result.prompt_cost_usd == 0.40
    assert result.completion_cost_usd == 1.60
