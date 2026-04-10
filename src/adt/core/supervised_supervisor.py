"""Supervised-mode supervisor: guides users step-by-step instead of solving."""

from __future__ import annotations

import json
import logging
from typing import Any

from adt.logging.json_log import log_adt
from adt.models.schemas import (
    CodeIssue,
    ReviewFeedback,
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


_REVIEW_SYSTEM_PROMPT = """You are a senior engineer performing a technical code \
review for a software engineer who is learning.

## Communication rules
- Always reply in the same language the user used in their question or context.
- Be technical, precise, and specific. Reference concrete lines and identifiers.
- No filler, no generic praise, no motivational closings.

## Review behavior
- Read the submitted code carefully. Assume it is a work-in-progress solution.
- Identify real issues only. Do NOT invent problems to fill space.
- Classify each issue by severity:
  - error: blocks correctness (bugs, crashes, wrong output)
  - warning: risky or likely to break under edge cases
  - suggestion: readability, naming, idiomatic improvements
- Cite the 1-based line number when the issue is localized; omit it for
  file-wide observations.
- For each issue, provide a fix_hint that guides without revealing the full
  solution (ask a question or point at the concept).
- Strengths must be specific. "Good code" is not acceptable.
- next_step must be actionable: what the user should do right now.
- overall_assessment:
  - needs_work: at least one error-severity issue
  - on_track: no errors, but warnings or several suggestions remain
  - excellent: no issues worth fixing; ready to advance

## Anti-patterns
- Do NOT rewrite the whole function for the user.
- Do NOT provide the full corrected code.
- Do NOT give generic advice ("add tests", "use types") without tying it to
  a concrete line or pattern in the submission.

## Output format
You MUST respond with a single JSON object (no markdown, no extra text):
{{
  "issues": [
    {{
      "line": 12,
      "severity": "warning",
      "description": "Variable name `x` does not convey intent.",
      "fix_hint": "What does this value represent in the problem domain?"
    }}
  ],
  "improvements": ["non-blocking improvement tied to a specific location"],
  "strengths": ["specific thing the submission got right"],
  "next_step": "concrete action to take now",
  "overall_assessment": "on_track"
}}

The user's difficulty level is: {level}
"""


def build_review_system_prompt(level: str) -> str:
    """Return the code review system prompt with the difficulty level interpolated."""
    return _REVIEW_SYSTEM_PROMPT.format(level=level)


def build_review_user_prompt(
    *,
    file_path: str,
    code: str,
    extra_context: str | None = None,
    step_context: str | None = None,
) -> str:
    """Assemble the reviewer user message from code and optional session context.

    Args:
        file_path: Display path of the file being reviewed.
        code: Full file contents to review.
        extra_context: Optional description of what the code should do.
        step_context: Optional reminder of the current supervised step the
            user is working on (from session state).
    """
    parts: list[str] = []
    if step_context:
        parts.append(f"Current supervised step:\n{step_context.strip()}")
    if extra_context:
        parts.append(f"User-provided context:\n{extra_context.strip()}")
    parts.append(f"File: {file_path}")
    parts.append("```\n" + code.rstrip() + "\n```")
    parts.append(
        "Review the code above and return the JSON object described in the "
        "system prompt. Do not include any text outside the JSON."
    )
    return "\n\n".join(parts)


def parse_review_feedback(raw_answer: str) -> ReviewFeedback | None:
    """Parse a structured JSON review into :class:`ReviewFeedback`.

    Returns ``None`` if parsing or validation fails; callers should fall back
    to displaying the raw text.
    """
    text = raw_answer.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError:
        log_adt(
            logger,
            logging.WARNING,
            event="review_parse_failure",
            raw_length=len(raw_answer),
        )
        return None

    if not isinstance(data, dict):
        return None

    try:
        raw_issues = data.get("issues") or []
        issues: list[CodeIssue] = []
        for item in raw_issues:
            if not isinstance(item, dict):
                continue
            issues.append(
                CodeIssue(
                    line=item.get("line"),
                    severity=item.get("severity", "suggestion"),
                    description=item.get("description", ""),
                    fix_hint=item.get("fix_hint", ""),
                )
            )
        return ReviewFeedback(
            issues=issues,
            improvements=list(data.get("improvements") or []),
            strengths=list(data.get("strengths") or []),
            next_step=data.get("next_step", ""),
            overall_assessment=data.get("overall_assessment", "on_track"),
        )
    except Exception:  # noqa: BLE001
        log_adt(
            logger,
            logging.WARNING,
            event="review_validation_failure",
            raw_length=len(raw_answer),
        )
        return None
