"""Integration tests: supervised ask/review writes learning events."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from adt.analytics import read_learning_events
from adt.ask_session import run_ask
from adt.core.session import SessionContext
from adt.models.schemas import (
    AgentResponse,
    CodeIssue,
    LLMMessage,
    ReviewFeedback,
)
from adt.review_session import run_review


def _session_file(tmp_path: Path) -> Path:
    return tmp_path / "session.json"


def _redirect_adt_home(tmp_path: Path, monkeypatch) -> Path:
    """Point the learning log + session file at a temporary directory."""
    import logging as _logging

    log_dir = tmp_path / "adt" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "learning.jsonl"

    # Drop any prior learning logger so a fresh handler binds to log_path.
    learning_logger = _logging.getLogger("adt.learning")
    for handler in list(learning_logger.handlers):
        handler.close()
        learning_logger.removeHandler(handler)

    # Redirect the default log path into tmp.
    monkeypatch.setattr(
        "adt.analytics.logger.learning_log_path",
        lambda lg_dir=None: log_path,
    )

    # Make session persistence point into tmp as well.
    session_path = tmp_path / "session.json"
    monkeypatch.setattr("adt.core.session.session_file_path", lambda: session_path)
    if session_path.exists():
        session_path.unlink()
    return log_dir


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.ask_session.build_runner")
def test_supervised_ask_emits_learning_event(
    mock_build: MagicMock, tmp_path: Path, monkeypatch
) -> None:
    log_dir = _redirect_adt_home(tmp_path, monkeypatch)

    import json as _json

    supervised_answer = _json.dumps(
        {
            "problem_summary": "Reverse a linked list in place.",
            "total_steps": 3,
            "current_step": {
                "step_number": 1,
                "goal": "Track the previous pointer",
                "requirements": ["Use a while loop"],
                "hints": ["What does prev point to after one iteration?"],
                "questions": ["What is the loop invariant?"],
            },
            "progress_note": "",
        }
    )

    mock_runner = MagicMock()
    mock_runner.run.return_value = AgentResponse(
        answer=supervised_answer,
        tools_used=[],
        context_summary="",
        routed_agent="repo_agent",
    )
    mock_runner.last_token_usage = {"prompt_tokens": 120, "completion_tokens": 80}
    mock_build.return_value = mock_runner

    repo = tmp_path / "repo"
    repo.mkdir()

    exe = run_ask(
        query="Help me reverse a linked list",
        repo=[str(repo)],
        configure_logging=False,
        mode="supervised",
        level="beginner",
    )
    assert exe.supervised_response is not None

    events = read_learning_events(path=log_dir / "learning.jsonl")
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "supervised_step"
    assert ev.component == "supervisor"
    assert ev.step_id == 1
    assert ev.level == "beginner"
    assert "linked list" in ev.problem_summary.lower()
    assert ev.data.get("prompt_tokens") == 120
    assert ev.data.get("completion_tokens") == 80


def _fake_llm_reply(feedback: ReviewFeedback) -> LLMMessage:
    import json

    payload = {
        "issues": [i.model_dump() for i in feedback.issues],
        "improvements": feedback.improvements,
        "strengths": feedback.strengths,
        "next_step": feedback.next_step,
        "overall_assessment": feedback.overall_assessment,
    }
    return LLMMessage(role="assistant", content=json.dumps(payload))


class _FakeLLM:
    def __init__(self, reply: LLMMessage) -> None:
        self._reply = reply

    def chat(
        self, messages: list[LLMMessage], tools: object
    ) -> LLMMessage:  # pragma: no cover - trivial
        return self._reply


def test_review_emits_code_review_learning_event(tmp_path: Path, monkeypatch) -> None:
    log_dir = _redirect_adt_home(tmp_path, monkeypatch)

    # Preload a session so the event carries problem + step.
    sess = SessionContext(
        problem_summary="Implement binary search",
        current_step=2,
        total_steps=4,
        iteration_count=1,
    )

    feedback = ReviewFeedback(
        issues=[
            CodeIssue(
                line=7,
                severity="warning",
                description="Off-by-one error on the upper bound",
                fix_hint="Should the right index be inclusive?",
            ),
            CodeIssue(
                line=10,
                severity="suggestion",
                description="Variable name `x` is not descriptive",
                fix_hint="What does `x` represent?",
            ),
        ],
        improvements=["Consider an iterative version."],
        strengths=["Function signature is clear."],
        next_step="Fix the upper bound and rerun the test.",
        overall_assessment="needs_work",
    )
    llm = _FakeLLM(_fake_llm_reply(feedback))

    target = tmp_path / "solution.py"
    target.write_text("def search(): pass\n", encoding="utf-8")

    result = run_review(
        file=target,
        level="intermediate",
        configure_logging=False,
        llm=llm,
        session=sess,
    )
    assert result.feedback is not None
    assert result.feedback.overall_assessment == "needs_work"

    events = read_learning_events(path=log_dir / "learning.jsonl")
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "code_review"
    assert ev.component == "reviewer"
    assert ev.assessment == "needs_work"
    assert ev.step_id == 2
    assert ev.problem_summary == "Implement binary search"
    assert "off_by_one" in ev.error_types
    assert "naming" in ev.error_types
    assert ev.data.get("issue_count") == 2
