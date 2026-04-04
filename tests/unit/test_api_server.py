"""FastAPI server smoke tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from adt.api.server import app
from adt.ask_session import AskConfigurationError, AskExecution
from adt.models.schemas import AgentResponse


def test_healthz() -> None:
    client = TestClient(app)
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "version" in data


@patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=False)
@patch("adt.api.server.run_ask")
def test_post_ask_success(mock_run: MagicMock) -> None:
    runner = MagicMock()
    runner.last_token_usage = {"total_tokens": 42}
    mock_run.return_value = AskExecution(
        response=AgentResponse(
            answer="Hello.",
            tools_used=["read_repo_tree"],
            context_summary="ctx",
            routed_agent="repo_agent",
        ),
        runner=runner,
    )
    client = TestClient(app)
    res = client.post(
        "/ask",
        json={"query": "What is this?", "repo": ["."], "no_cache": True},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["answer"] == "Hello."
    assert body["routed_agent"] == "repo_agent"
    assert "read_repo_tree" in body["tools_used"]


@patch("adt.api.server.run_ask")
def test_post_ask_missing_key(mock_run: MagicMock) -> None:
    mock_run.side_effect = AskConfigurationError(
        "Missing OPENAI_API_KEY. Set it in the environment.",
    )
    client = TestClient(app)
    res = client.post("/ask", json={"query": "Hi"})
    assert res.status_code == 503
