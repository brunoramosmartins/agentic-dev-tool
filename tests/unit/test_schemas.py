"""Validation tests for Pydantic schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from adt.models.schemas import LLMMessage, QueryRequest, RoutedRequest, ToolCall


def test_query_request_defaults() -> None:
    q = QueryRequest(query="hello")
    assert q.repo_path is None
    assert q.options == {}


def test_tool_call_agent_default() -> None:
    tc = ToolCall(name="t", arguments={})
    assert tc.agent == ""


def test_llm_message_role_literal() -> None:
    with pytest.raises(ValidationError):
        LLMMessage(role="nope", content="x")  # type: ignore[arg-type]


def test_llm_message_tool_requires_id() -> None:
    with pytest.raises(ValidationError):
        LLMMessage(role="tool", content="result")


def test_llm_message_tool_ok() -> None:
    m = LLMMessage(role="tool", content="ok", tool_call_id="abc")
    assert m.tool_call_id == "abc"


def test_routed_request_roundtrip() -> None:
    q = QueryRequest(query="x", options={"k": 1})
    r = RoutedRequest(agent_name="repo_agent", request=q)
    assert r.agent_name == "repo_agent"
    assert r.request.query == "x"
