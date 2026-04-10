"""Supervised-mode supervisor: guides users step-by-step instead of solving."""

from __future__ import annotations

import json
import logging
from typing import Any

from adt.logging.json_log import log_adt
from adt.models.schemas import (
    SupervisedResponse,
    SupervisedStep,
)

logger = logging.getLogger(__name__)

_SUPERVISED_SYSTEM_PROMPT = """You are a technical mentor guiding a software engineer \
through problem decomposition and incremental implementation.

## Communication rules
- Always reply in the same language the user used in their question.
- Be technical, precise, and direct. No filler.

## Core behavior
- Decompose the problem into small, implementable steps (3-7 steps typical).
- Present ONLY the current step. Do not reveal future steps in detail.
- Do NOT provide the full solution. Guide the user to implement it themselves.
- Each step must have a clear goal, concrete requirements, optional hints, and
  reflective questions.
- Adapt depth based on the configured difficulty level:
  - beginner: more hints, smaller steps, explicit type annotations guidance
  - intermediate: balanced hints, standard step granularity
  - advanced: minimal hints, larger steps, focus on design trade-offs

## Anti-patterns to avoid
- Do NOT say "looks good!" or give generic praise.
- Do NOT skip steps or jump to the final answer.
- Do NOT assume the user knows implementation details without evidence.
- Do NOT provide code blocks with the full solution.

## Output format
You MUST respond with a single JSON object (no markdown, no extra text):
{{
  "problem_summary": "concise restatement of the problem",
  "current_step": {{
    "step_number": 1,
    "goal": "what to achieve",
    "requirements": ["concrete deliverable 1", "concrete deliverable 2"],
    "hints": ["nudge without revealing solution"],
    "questions": ["reflective question to deepen understanding"]
  }},
  "total_steps": 4,
  "progress_note": "brief note on what follows this step"
}}

The user's difficulty level is: {level}
"""


def build_supervised_system_prompt(level: str) -> str:
    """Return the system prompt with the difficulty level interpolated."""
    return _SUPERVISED_SYSTEM_PROMPT.format(level=level)


def parse_supervised_response(raw_answer: str) -> SupervisedResponse | None:
    """Try to parse structured JSON from the LLM answer into SupervisedResponse.

    Returns None if parsing fails (caller falls back to raw text display).
    """
    text = raw_answer.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        data: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError:
        log_adt(
            logger,
            logging.WARNING,
            event="supervised_parse_failure",
            raw_length=len(raw_answer),
        )
        return None

    if not isinstance(data, dict):
        return None

    try:
        step_data = data.get("current_step", {})
        step = SupervisedStep(
            step_number=step_data.get("step_number", 1),
            goal=step_data.get("goal", ""),
            requirements=step_data.get("requirements", []),
            hints=step_data.get("hints", []),
            questions=step_data.get("questions", []),
        )
        return SupervisedResponse(
            problem_summary=data.get("problem_summary", ""),
            current_step=step,
            total_steps=data.get("total_steps", 1),
            progress_note=data.get("progress_note", ""),
        )
    except Exception:  # noqa: BLE001
        log_adt(
            logger,
            logging.WARNING,
            event="supervised_validation_failure",
            raw_length=len(raw_answer),
        )
        return None
