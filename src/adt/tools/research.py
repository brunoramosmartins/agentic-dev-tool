"""HTTP-backed tools for literature search (arXiv) and article text extraction."""

from __future__ import annotations

import ipaddress
import re
import textwrap
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from adt import __version__

_ARXIV_API = "http://export.arxiv.org/api/query"
_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_MAX_FETCH_BYTES = 2 * 1024 * 1024
_DEFAULT_TIMEOUT = 30.0


def _clamp_int(value: int, low: int, high: int) -> int:
    """Return ``value`` bounded to the inclusive ``[low, high]`` range."""
    return max(low, min(high, value))


def _normalize_arxiv_whitespace(text: str) -> str:
    """Collapse redundant whitespace and strip a short text blob."""
    cleaned = re.sub(r"\s+", " ", text.strip())
    return cleaned


def _host_is_blocked_for_ssrf(host: str) -> bool:
    """Return True if the hostname or IP must not be fetched (basic SSRF guard).

    Blocks loopback, link-local, private, and reserved addresses when ``host``
    parses as an IP. Blocks obvious local hostnames.

    Args:
        host: Host part of a URL (no port).

    Returns:
        True when fetching this host should be refused.
    """
    h = host.lower().rstrip(".")
    if h in ("localhost", "0.0.0.0"):
        return True
    if h.endswith(".localhost") or h.endswith(".local"):
        return True
    try:
        addr = ipaddress.ip_address(h.strip("[]"))
    except ValueError:
        return False
    return not addr.is_global


def _assert_url_safe(url: str) -> None:
    """Raise ``ValueError`` if ``url`` is not a fetchable public HTTP(S) URL."""
    if not url or not url.strip():
        msg = "URL is empty."
        raise ValueError(msg)
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        msg = "Only http and https URLs are supported."
        raise ValueError(msg)
    hostname = parsed.hostname
    if not hostname:
        msg = "URL is missing a hostname."
        raise ValueError(msg)
    if _host_is_blocked_for_ssrf(hostname):
        msg = "Refusing to fetch loopback, private, or non-global hosts."
        raise ValueError(msg)


class _HTMLToText(HTMLParser):
    """Extract visible text from HTML, skipping ``script``/``style`` content."""

    def __init__(self) -> None:
        """Initialize parser state for text accumulation."""
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Track skipped elements and insert breaks after block-level tags."""
        t = tag.lower()
        if t in ("script", "style", "noscript", "template"):
            self._skip_depth += 1
        elif self._skip_depth == 0 and t in (
            "br",
            "p",
            "div",
            "li",
            "tr",
            "h1",
            "h2",
            "h3",
            "h4",
            "section",
            "article",
        ):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """End skipping for closing ``script``/``style``-like tags."""
        t = tag.lower()
        if t in ("script", "style", "noscript", "template") and self._skip_depth > 0:
            self._skip_depth -= 1
        elif self._skip_depth == 0 and t in ("p", "div", "section", "article"):
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        """Append character data when not inside a skipped subtree."""
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        """Join extracted fragments and normalize blank lines."""
        raw = "".join(self._parts)
        lines = [ln.strip() for ln in raw.splitlines()]
        non_empty = [ln for ln in lines if ln]
        return "\n".join(non_empty)


def search_papers(query: str, max_results: int = 10) -> str:
    """Search arXiv for papers matching ``query`` and return a text summary.

    Uses the public arXiv Atom API (no API key). Results include title, authors
    (when present), abstract snippet, and link to the abstract page.

    Args:
        query: Free-text search string (passed to ``search_query=all:...``).
        max_results: Maximum entries to return (clamped between 1 and 50).

    Returns:
        Human-readable listing, or an error description if the request fails.
    """
    q = query.strip()
    if not q:
        return "Error: search query is empty."
    n = _clamp_int(max_results, 1, 50)
    params: dict[str, str | int] = {
        "search_query": f"all:{q}",
        "start": 0,
        "max_results": n,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    try:
        with httpx.Client(
            timeout=_DEFAULT_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    f"agentic-dev-tool/{__version__} "
                    "(+https://github.com/brunoramosmartins/agentic-dev-tool)"
                ),
            },
        ) as client:
            response = client.get(_ARXIV_API, params=params)
            response.raise_for_status()
            body = response.text
    except httpx.HTTPError as exc:
        return f"Error: arXiv HTTP request failed: {exc!s}"

    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        return f"Error: failed to parse arXiv response: {exc!s}"

    entries = root.findall(f"{_ATOM_NS}entry")
    if not entries:
        return f"No arXiv papers found for query: {q!r}."

    lines: list[str] = [f"arXiv search results for {q!r} ({len(entries)} items):\n"]
    for i, entry in enumerate(entries, start=1):
        title_el = entry.find(f"{_ATOM_NS}title")
        title = (
            _normalize_arxiv_whitespace(title_el.text or "")
            if title_el is not None
            else ""
        )
        summary_el = entry.find(f"{_ATOM_NS}summary")
        summary_raw = (summary_el.text or "") if summary_el is not None else ""
        summary = _normalize_arxiv_whitespace(summary_raw)
        if len(summary) > 600:
            summary = summary[:597] + "..."
        id_el = entry.find(f"{_ATOM_NS}id")
        link = (id_el.text or "").strip() if id_el is not None else ""
        if not link:
            for link_el in entry.findall(f"{_ATOM_NS}link"):
                href = link_el.attrib.get("href", "")
                if link_el.attrib.get("type") == "text/html" or not link:
                    link = href
        authors: list[str] = []
        for author in entry.findall(f"{_ATOM_NS}author"):
            name_el = author.find(f"{_ATOM_NS}name")
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())
        author_line = ", ".join(authors[:8]) if authors else "(authors not listed)"
        if len(authors) > 8:
            author_line += ", …"
        lines.append(f"{i}. {title}")
        lines.append(f"   Authors: {author_line}")
        lines.append(f"   Abstract: {summary}")
        lines.append(f"   URL: {link}")
        lines.append("")
    return "\n".join(lines).rstrip()


def fetch_article(url: str, max_chars: int = 80000) -> str:
    """Download a page and return extracted plain text (basic HTML stripping).

    Only ``http``/``https`` URLs with a globally routable host are allowed.
    Response size is capped before parsing; extracted text is truncated to
    ``max_chars``.

    Args:
        url: Document location to fetch.
        max_chars: Maximum number of characters of extracted text to return.

    Returns:
        Extracted text (possibly truncated), or an error message string.
    """
    try:
        _assert_url_safe(url)
    except ValueError as exc:
        return f"Error: {exc}"

    limit = _clamp_int(max_chars, 1000, 500_000)
    raw: bytes = b""
    ctype = ""
    content_type_header = ""
    try:
        with (
            httpx.Client(
                timeout=_DEFAULT_TIMEOUT,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        f"agentic-dev-tool/{__version__} "
                        "(+https://github.com/brunoramosmartins/agentic-dev-tool)"
                    ),
                },
            ) as client,
            client.stream("GET", url.strip()) as response,
        ):
            response.raise_for_status()
            content_type_header = response.headers.get("content-type", "")
            ctype = content_type_header.split(";")[0].strip().lower()
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                chunks.append(chunk)
                total += len(chunk)
                if total > _MAX_FETCH_BYTES:
                    msg = f"Error: response larger than {_MAX_FETCH_BYTES} bytes."
                    return msg
            raw = b"".join(chunks)
    except httpx.HTTPError as exc:
        return f"Error: HTTP request failed: {exc!s}"

    if not raw:
        return "Error: empty response body."

    if ctype and ctype not in (
        "text/html",
        "text/plain",
        "application/xhtml+xml",
        "",
    ):
        return (
            f"Error: unsupported content-type {ctype!r}; "
            "only HTML and plain text are handled."
        )

    charset = "utf-8"
    if "charset=" in content_type_header.lower():
        part = content_type_header.lower().split("charset=")[-1].split(";")[0]
        charset = part.strip().strip('"') or charset

    try:
        text = raw.decode(charset)
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")

    if ctype == "text/plain" or (not ctype and not raw.lstrip().startswith(b"<")):
        body = text.strip()
        if len(body) > limit:
            body = body[: limit - 3] + "..."
        return textwrap.dedent(
            f"""Fetched plain text from URL ({len(body)} chars shown, max {limit}):
{body}""",
        ).strip()

    parser = _HTMLToText()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:  # noqa: BLE001 — best-effort HTML parse
        return f"Error: failed to parse HTML: {exc!s}"

    body = parser.get_text()
    if len(body) > limit:
        body = body[: limit - 3] + "..."
    return textwrap.dedent(
        f"""Extracted text from HTML ({len(body)} chars shown, max {limit}):
{body}""",
    ).strip()
