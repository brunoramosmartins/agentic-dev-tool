"""LLM client unit tests with a mocked OpenAI client."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from openai import APIStatusError

from adt.core.llm import LLMClient
from adt.models.schemas import LLMMessage


def _choice(content: str, tool_calls: object | None = None) -> MagicMock:
    msg = MagicMock(content=content, tool_calls=tool_calls)
    return MagicMock(message=msg)


def test_chat_returns_text() -> None:
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[_choice("hello")],
        usage=MagicMock(prompt_tokens=2, completion_tokens=3, total_tokens=5),
    )
    llm = LLMClient(client=client)
    out = llm.chat([LLMMessage(role="user", content="hi")])
    assert out.content == "hello"
    assert out.tool_calls is None
    assert llm.last_usage["total_tokens"] == 5


def test_chat_parses_tool_calls() -> None:
    client = MagicMock()
    tc = MagicMock()
    tc.id = "id1"
    tc.function.name = "echo"
    tc.function.arguments = '{"message": "z"}'
    client.chat.completions.create.return_value = MagicMock(
        choices=[_choice("", tool_calls=[tc])],
        usage=MagicMock(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )
    llm = LLMClient(client=client)
    out = llm.chat([LLMMessage(role="user", content="go")])
    assert out.tool_calls is not None
    assert out.tool_calls[0].name == "echo"
    assert out.tool_calls[0].arguments == {"message": "z"}


def test_complete_json_object() -> None:
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[_choice('{"agent":"repo_agent"}')],
        usage=MagicMock(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )
    llm = LLMClient(client=client)
    data = llm.complete_json_object(
        system="s",
        user="u",
        model="m",
        max_completion_tokens=50,
    )
    assert data.get("agent") == "repo_agent"
    call_kw = client.chat.completions.create.call_args[1]
    assert call_kw.get("response_format") == {"type": "json_object"}


def test_chat_retries_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    sleeps: list[float] = []
    monkeypatch.setattr("adt.core.llm.time.sleep", lambda s: sleeps.append(s))

    err = APIStatusError(
        message="rate limit",
        response=MagicMock(status_code=429),
        body=None,
    )
    ok = MagicMock(
        choices=[_choice("ok")],
        usage=MagicMock(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )
    client.chat.completions.create.side_effect = [err, ok]
    llm = LLMClient(client=client, max_retries=3)
    out = llm.chat([LLMMessage(role="user", content="x")])
    assert out.content == "ok"
    assert sleeps == [1.0]
