"""Unit tests for GitHub and markdown project tools (mocked HTTP)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from adt.tools.project import read_issues, read_markdown, read_milestones


def _mock_httpx_client_for_github_get(
    json_payload: object,
    *,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    """Return a context-manager client whose ``get`` yields a configured response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_payload
    mock_resp.headers = headers or {"x-ratelimit-remaining": "59"}
    mock_resp.text = ""
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


@patch("adt.tools.project.httpx.Client")
def test_read_issues_parses_list(mock_cls: MagicMock) -> None:
    """Issues list should exclude pull_request entries and include metadata."""
    payload = [
        {
            "number": 2,
            "title": "Real issue",
            "state": "open",
            "user": {"login": "alice"},
            "html_url": "https://github.com/o/r/issues/2",
            "labels": [{"name": "bug"}],
        },
        {
            "number": 3,
            "title": "A PR",
            "state": "open",
            "pull_request": {},
            "user": {"login": "bob"},
            "html_url": "https://github.com/o/r/pull/3",
            "labels": [],
        },
    ]
    mock_cls.return_value = _mock_httpx_client_for_github_get(payload)
    out = read_issues("o", "r", state="open", max_results=10, token=None)
    assert "Real issue" in out
    assert "#2" in out
    assert "A PR" not in out


@patch("adt.tools.project.httpx.Client")
def test_read_issues_rate_limit_403(mock_cls: MagicMock) -> None:
    """403 responses should mention rate limits and token guidance."""
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.json.return_value = {"message": "API rate limit exceeded"}
    mock_resp.headers = {
        "x-ratelimit-remaining": "0",
        "x-ratelimit-reset": "1700000000",
    }
    mock_resp.text = ""
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_cls.return_value = mock_client
    out = read_issues("o", "r", token=None)
    assert "403" in out or "rate" in out.lower()
    assert "GITHUB_TOKEN" in out or "token" in out.lower()


@patch("adt.tools.project.httpx.Client")
def test_read_milestones_parses_list(mock_cls: MagicMock) -> None:
    """Milestone payload should be formatted as text lines."""
    payload = [
        {
            "title": "v1.0",
            "state": "open",
            "description": "First release",
            "open_issues": 3,
            "closed_issues": 1,
            "due_on": "2026-12-01T00:00:00Z",
            "html_url": "https://github.com/o/r/milestone/1",
        },
    ]
    mock_cls.return_value = _mock_httpx_client_for_github_get(payload)
    out = read_milestones("o", "r", state="open", token=None)
    assert "v1.0" in out
    assert "open_issues=3" in out


def test_read_markdown_strips_front_matter(sample_repo_path: str) -> None:
    """ROADMAP fixture should load and drop YAML front matter."""
    root = Path(sample_repo_path)
    out = read_markdown(root, "ROADMAP.md", max_chars=50_000)
    assert "Phase A" in out
    assert "title: Sample roadmap" not in out


def test_read_markdown_rejects_non_md(sample_repo_path: str) -> None:
    """Only markdown suffixes are allowed."""
    root = Path(sample_repo_path)
    out = read_markdown(root, "main.py")
    assert "Error" in out
