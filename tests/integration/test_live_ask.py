"""Optional live tests against the real OpenAI API (not run in default CI)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from adt.bootstrap import build_runner_for_repo
from adt.models.schemas import QueryRequest


@pytest.mark.live
def test_live_ask_minimal_repo(sample_repo_path: str) -> None:
    """End-to-end call with a real API key (run with ``pytest -m live``).

    Skips automatically when ``OPENAI_API_KEY`` is unset.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    runner = build_runner_for_repo(
        Path(sample_repo_path),
        model=os.environ.get("ADT_LIVE_MODEL", "gpt-4o-mini"),
    )
    res = runner.run(
        QueryRequest(
            query="In one sentence, what does main.py do?",
            repo_path=sample_repo_path,
        ),
    )
    assert len(res.answer.strip()) > 10
