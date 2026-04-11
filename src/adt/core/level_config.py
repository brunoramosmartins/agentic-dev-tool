"""Data-driven difficulty levels for the supervised learning mode.

A :class:`LevelConfig` encodes the intensity of supervision for a given user
skill level. The values drive prompt conditioning (hints per step, question
count, explanation depth, feedback tone) so the LLM can adapt without
changing the agent code. The :data:`LEVEL_CONFIGS` registry maps each
:data:`~adt.models.schemas.Level` to its configuration.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from adt.models.schemas import Level

ExplanationDepth = Literal["detailed", "moderate", "minimal"]
FeedbackFocus = Literal["encouraging", "balanced", "critical"]


class LevelConfig(BaseModel):
    """Configuration for a specific supervision difficulty level.

    Attributes:
        name: Level identifier (matches :data:`~adt.models.schemas.Level`).
        hints_per_step: Target number of hints the supervisor should emit
            per step. ``0`` means the model should withhold hints entirely.
        questions_per_step: Target number of reflective questions per step.
        explanation_depth: How much prose the model should spend explaining
            each step. Higher depth trades brevity for clarity.
        show_alternatives: When True, the model may mention alternative
            approaches or trade-offs.
        feedback_focus: Tone of the code review feedback.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Level = Field(..., description="Level identifier.")
    hints_per_step: int = Field(..., ge=0, le=5)
    questions_per_step: int = Field(..., ge=1, le=5)
    explanation_depth: ExplanationDepth = Field(...)
    show_alternatives: bool = Field(...)
    feedback_focus: FeedbackFocus = Field(...)


LEVEL_CONFIGS: dict[Level, LevelConfig] = {
    "beginner": LevelConfig(
        name="beginner",
        hints_per_step=3,
        questions_per_step=1,
        explanation_depth="detailed",
        show_alternatives=False,
        feedback_focus="encouraging",
    ),
    "intermediate": LevelConfig(
        name="intermediate",
        hints_per_step=2,
        questions_per_step=2,
        explanation_depth="moderate",
        show_alternatives=True,
        feedback_focus="balanced",
    ),
    "advanced": LevelConfig(
        name="advanced",
        hints_per_step=0,
        questions_per_step=3,
        explanation_depth="minimal",
        show_alternatives=True,
        feedback_focus="critical",
    ),
}


def get_level_config(level: Level) -> LevelConfig:
    """Return the :class:`LevelConfig` for ``level``.

    Falls back to the intermediate configuration for unknown values so
    callers never have to defend against missing keys.
    """
    return LEVEL_CONFIGS.get(level, LEVEL_CONFIGS["intermediate"])


def _hints_clause(cfg: LevelConfig) -> str:
    if cfg.hints_per_step == 0:
        return "Provide NO hints. Force the user to reason through the step."
    noun = "hint" if cfg.hints_per_step == 1 else "hints"
    return f"Provide exactly {cfg.hints_per_step} {noun} per step."


def _questions_clause(cfg: LevelConfig) -> str:
    noun = "question" if cfg.questions_per_step == 1 else "questions"
    return f"Ask exactly {cfg.questions_per_step} reflective {noun} per step."


def _alternatives_clause(cfg: LevelConfig) -> str:
    if cfg.show_alternatives:
        return "You MAY mention one alternative approach or trade-off when relevant."
    return "Do NOT mention alternative approaches; stick to a single path."


def _depth_clause(cfg: LevelConfig) -> str:
    if cfg.explanation_depth == "detailed":
        return (
            "Use detailed prose for each step. Define terms, reference concrete "
            "examples, and explain the 'why' behind each requirement."
        )
    if cfg.explanation_depth == "minimal":
        return (
            "Keep prose minimal. Assume strong fundamentals. Favor precision "
            "over explanation."
        )
    return "Use moderate prose. Explain non-obvious decisions but stay concise."


def _tone_clause(cfg: LevelConfig) -> str:
    if cfg.feedback_focus == "encouraging":
        return (
            "Feedback tone: encouraging. Highlight strengths first; issues must "
            "still be specific and actionable."
        )
    if cfg.feedback_focus == "critical":
        return (
            "Feedback tone: critical. Focus on code quality, edge cases, and "
            "design trade-offs. Skip generic validation of correct code."
        )
    return "Feedback tone: balanced. Mix specific strengths with concrete issues."


def format_level_directives(cfg: LevelConfig) -> str:
    """Return a multi-line directive block describing level-specific behavior.

    The block is consumed verbatim by prompt builders, so callers only pay
    the cost of conditioning once per request. Every clause is grounded in
    a single attribute of :class:`LevelConfig`, keeping the output fully
    data-driven.
    """
    lines = [
        f"## Level: {cfg.name}",
        f"- {_hints_clause(cfg)}",
        f"- {_questions_clause(cfg)}",
        f"- {_depth_clause(cfg)}",
        f"- {_alternatives_clause(cfg)}",
        f"- {_tone_clause(cfg)}",
    ]
    return "\n".join(lines)
