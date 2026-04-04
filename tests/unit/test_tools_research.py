"""Unit tests for research HTTP tools (mocked ``httpx``)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from adt.tools.research import fetch_article, search_papers

_ARXIV_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.00001</id>
    <title>  Retrieval and Generation  </title>
    <summary> We study RAG systems. </summary>
    <author><name>Jane Doe</name></author>
  </entry>
</feed>
"""


def _mock_httpx_client_for_get(text: str) -> MagicMock:
    """Build a context-manager client whose ``get`` returns a response with ``text``."""
    mock_resp = MagicMock()
    mock_resp.text = text
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


def test_search_papers_empty_query() -> None:
    """An empty query should short-circuit without HTTP."""
    assert "empty" in search_papers("  ", max_results=5).lower()


@patch("adt.tools.research.httpx.Client")
def test_search_papers_parses_atom(mock_cls: MagicMock) -> None:
    """Parsed Atom feed should include title and URL in the text output."""
    mock_cls.return_value = _mock_httpx_client_for_get(_ARXIV_ATOM)
    out = search_papers("rag", max_results=5)
    assert "Retrieval and Generation" in out
    assert "2301.00001" in out
    assert "Jane Doe" in out


@patch("adt.tools.research.httpx.Client")
def test_search_papers_no_entries(mock_cls: MagicMock) -> None:
    """Empty ``entry`` list should produce a clear message."""
    empty_feed = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"></feed>"""
    mock_cls.return_value = _mock_httpx_client_for_get(empty_feed)
    out = search_papers("xyznonexistent12345", max_results=5)
    assert "No arXiv" in out or "no arxiv" in out.lower()


def test_fetch_article_rejects_localhost() -> None:
    """Local hosts must be rejected before any network I/O."""
    out = fetch_article("http://localhost:8080/page")
    assert "Error" in out
    assert "Refusing" in out or "localhost" in out.lower()


def test_fetch_article_rejects_non_http() -> None:
    """Non-HTTP schemes should be rejected."""
    out = fetch_article("file:///etc/passwd")
    assert "Error" in out


@patch("adt.tools.research.httpx.Client")
def test_fetch_article_plain_text(mock_cls: MagicMock) -> None:
    """Plain text responses should be returned without HTML parsing."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.headers = {"content-type": "text/plain; charset=utf-8"}
    mock_resp.iter_bytes = MagicMock(return_value=[b"Hello plain world."])

    stream_cm = MagicMock()
    stream_cm.__enter__ = MagicMock(return_value=mock_resp)
    stream_cm.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream.return_value = stream_cm
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_cls.return_value = mock_client

    out = fetch_article("https://example.com/doc.txt", max_chars=5000)
    assert "Hello plain world" in out


@patch("adt.tools.research.httpx.Client")
def test_fetch_article_html_extracts_text(mock_cls: MagicMock) -> None:
    """HTML body text should be extracted and scripts ignored."""
    html = b"<html><script>x</script><body><p>Visible</p></body></html>"
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.iter_bytes = MagicMock(return_value=[html])

    stream_cm = MagicMock()
    stream_cm.__enter__ = MagicMock(return_value=mock_resp)
    stream_cm.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream.return_value = stream_cm
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_cls.return_value = mock_client

    out = fetch_article("https://example.com/a.html", max_chars=5000)
    assert "Visible" in out
