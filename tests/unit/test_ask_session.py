"""Tests for ``adt.ask_session``."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from adt.ask_session import AskConfigurationError, AskExecution, run_ask
from adt.models.schemas import AgentResponse


def test_run_ask_missing_api_key() -> None:
    with (
        patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False),
        pytest.raises(AskConfigurationError, match="OPENAI_API_KEY"),
    ):
        run_ask(query="hi", configure_logging=False)


def test_run_ask_invalid_agent() -> None:
    with (
        patch.dict(os.environ, {"OPENAI_API_KEY": "sk-x"}, clear=False),
        pytest.raises(AskConfigurationError, match="Invalid agent"),
    ):
        run_ask(query="hi", force_agent="nope", configure_logging=False)


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.ask_session.build_runner")
def test_run_ask_success(mock_br: MagicMock, tmp_path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    mock_runner = MagicMock()
    mock_runner.run.return_value = AgentResponse(
        answer="ok",
        tools_used=[],
        context_summary="",
        routed_agent="repo_agent",
    )
    mock_br.return_value = mock_runner
    exe = run_ask(query="q", repo=[str(repo)], configure_logging=False)
    assert isinstance(exe, AskExecution)
    assert exe.response.answer == "ok"
    mock_br.assert_called_once()
    mock_runner.run.assert_called_once()
