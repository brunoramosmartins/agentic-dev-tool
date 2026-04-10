"""Lightweight supervised-mode session state persisted between CLI runs.

The CLI process is short-lived, but users expect follow-up ``adt ask`` and
``adt review`` commands to build on the previous step. We persist a minimal
snapshot under ``~/.adt/session.json`` so the next invocation can reload it.
Only the most recent session is kept.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from adt.config import ensure_adt_dir
from adt.logging.json_log import log_adt
from adt.models.schemas import SupervisedResponse

logger = logging.getLogger(__name__)


def session_file_path() -> Path:
    """Return the path to ``~/.adt/session.json``."""
    return ensure_adt_dir() / "session.json"


@dataclass
class SessionContext:
    """Tracks state within a supervised learning session.

    Attributes:
        problem_summary: Concise problem statement from the first supervised
            turn. Used to detect when the user switched to a new problem.
        current_step: 1-based index of the step the user is currently on.
        total_steps: Total number of planned steps.
        previous_feedback: Short summaries of past review assessments in order.
        iteration_count: Number of commands executed against this session.
    """

    problem_summary: str = ""
    current_step: int = 0
    total_steps: int = 0
    previous_feedback: list[str] = field(default_factory=list)
    iteration_count: int = 0

    # ---------- predicates ----------

    def is_empty(self) -> bool:
        """Return True if no supervised session has been started yet."""
        return not self.problem_summary and self.current_step == 0

    def matches_problem(self, other_summary: str) -> bool:
        """Return True when ``other_summary`` describes the same problem.

        Uses a coarse containment check so small wording differences do not
        reset the session unnecessarily.
        """
        if not self.problem_summary or not other_summary:
            return False
        a = self.problem_summary.strip().lower()
        b = other_summary.strip().lower()
        if not a or not b:
            return False
        return a == b or a in b or b in a

    # ---------- mutations ----------

    def update_from_supervised(self, response: SupervisedResponse) -> None:
        """Refresh the session from a parsed :class:`SupervisedResponse`.

        Resets feedback history if the problem summary changed so the new
        session starts clean.
        """
        if not self.matches_problem(response.problem_summary):
            self.previous_feedback = []
        self.problem_summary = response.problem_summary
        self.current_step = response.current_step.step_number
        self.total_steps = response.total_steps
        self.iteration_count += 1

    def record_feedback(self, assessment: str) -> None:
        """Append a short review outcome to the feedback history."""
        summary = assessment.strip()
        if not summary:
            return
        self.previous_feedback.append(summary)
        # keep the history small
        if len(self.previous_feedback) > 10:
            self.previous_feedback = self.previous_feedback[-10:]
        self.iteration_count += 1

    def clear(self) -> None:
        """Reset all state to the initial empty session."""
        self.problem_summary = ""
        self.current_step = 0
        self.total_steps = 0
        self.previous_feedback = []
        self.iteration_count = 0

    # ---------- rendering ----------

    def as_step_context(self) -> str:
        """Return a compact string describing the current step for review prompts."""
        if self.is_empty():
            return ""
        lines = [
            f"Problem: {self.problem_summary}",
            f"Step {self.current_step} of {self.total_steps}",
        ]
        if self.previous_feedback:
            recent = self.previous_feedback[-1]
            lines.append(f"Previous feedback: {recent}")
        return "\n".join(lines)

    # ---------- persistence ----------

    def save(self, path: Path | None = None) -> None:
        """Write the session to disk as JSON (best-effort)."""
        target = path or session_file_path()
        try:
            target.write_text(
                json.dumps(asdict(self), indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            log_adt(
                logger,
                logging.WARNING,
                event="session_save_failed",
                error=str(exc),
            )

    @classmethod
    def load(cls, path: Path | None = None) -> SessionContext:
        """Load a session from disk, returning an empty one on any failure."""
        target = path or session_file_path()
        if not target.exists():
            return cls()
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log_adt(
                logger,
                logging.WARNING,
                event="session_load_failed",
                error=str(exc),
            )
            return cls()
        if not isinstance(data, dict):
            return cls()
        return cls(
            problem_summary=str(data.get("problem_summary", "")),
            current_step=int(data.get("current_step", 0) or 0),
            total_steps=int(data.get("total_steps", 0) or 0),
            previous_feedback=[str(x) for x in (data.get("previous_feedback") or [])],
            iteration_count=int(data.get("iteration_count", 0) or 0),
        )

    @classmethod
    def reset(cls, path: Path | None = None) -> None:
        """Delete any persisted session file (no-op if missing)."""
        target = path or session_file_path()
        if target.exists():
            try:
                target.unlink()
            except OSError as exc:
                log_adt(
                    logger,
                    logging.WARNING,
                    event="session_reset_failed",
                    error=str(exc),
                )
