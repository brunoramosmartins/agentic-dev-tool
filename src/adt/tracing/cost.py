"""USD cost estimation from token counts and model pricing."""

from __future__ import annotations

from dataclasses import dataclass

# Pricing per 1 M tokens (USD) as of 2025-05.
_PRICING: dict[str, tuple[float, float]] = {
    # (prompt, completion)
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o-mini-2024-07-18": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-2024-08-06": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1": (2.00, 8.00),
}

_DEFAULT_PRICING: tuple[float, float] = (0.15, 0.60)


@dataclass(frozen=True)
class CostBreakdown:
    """Itemised cost estimate for one traced request."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    prompt_cost_usd: float
    completion_cost_usd: float

    @property
    def total_cost_usd(self) -> float:
        return round(self.prompt_cost_usd + self.completion_cost_usd, 8)


class CostEstimator:
    """Estimate USD cost from cumulative token counts and a model name."""

    @staticmethod
    def estimate(
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> CostBreakdown:
        """Return a :class:`CostBreakdown` for the given usage."""
        prompt_rate, completion_rate = _PRICING.get(model, _DEFAULT_PRICING)
        return CostBreakdown(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            prompt_cost_usd=round(prompt_tokens * prompt_rate / 1_000_000, 8),
            completion_cost_usd=round(
                completion_tokens * completion_rate / 1_000_000, 8
            ),
        )
