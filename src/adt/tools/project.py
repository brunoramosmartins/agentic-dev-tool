"""GitHub REST helpers and local markdown reading for the project agent."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx

_GITHUB_API = "https://api.github.com"
_DEFAULT_TIMEOUT = 30.0
_MAX_ISSUES_CAP = 100
_MAX_MILESTONES_CAP = 50


def _safe_resolve_under(root: Path, relative: str) -> Path:
    """Resolve ``relative`` under ``root``; raise ``ValueError`` on escape attempts."""
    root = root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        msg = "Path escapes markdown root."
        raise ValueError(msg) from exc
    return candidate


def _strip_optional_yaml_front_matter(text: str) -> str:
    """Remove a leading YAML front matter block (``---`` … ``---``) when present."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return text
    return "".join(lines[end + 1 :]).lstrip("\n")


def _github_request_headers(token: str | None) -> dict[str, str]:
    """Build headers for GitHub REST requests (API version + optional bearer token)."""
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "agentic-dev-tool-project-agent",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _format_rate_limit_hint(response: httpx.Response) -> str:
    """Return a short human-readable rate-limit note from response headers."""
    remaining = response.headers.get("x-ratelimit-remaining")
    reset = response.headers.get("x-ratelimit-reset")
    limit = response.headers.get("x-ratelimit-limit")
    parts = []
    if remaining is not None:
        parts.append(f"remaining={remaining}")
    if limit is not None:
        parts.append(f"limit={limit}")
    if reset is not None:
        try:
            ts = int(reset)
            when = datetime.fromtimestamp(ts, tz=timezone.utc)
            parts.append(f"resets_utc={when.isoformat()}")
        except ValueError:
            parts.append(f"reset={reset}")
    return "; ".join(parts) if parts else ""


def _github_error_body(response: httpx.Response) -> str:
    """Extract a concise error string from a JSON error response when possible."""
    try:
        data = response.json()
    except Exception:
        return (response.text or "")[:500]
    if isinstance(data, dict):
        msg = data.get("message", "")
        if isinstance(msg, str) and msg:
            return msg
    return (response.text or "")[:500]


def read_issues(
    owner: str,
    repo: str,
    *,
    state: str = "open",
    labels: str = "",
    max_results: int = 30,
    token: str | None = None,
) -> str:
    """List GitHub issues (excluding pull requests) for a repository.

    Uses the public REST API. Unauthenticated requests are limited to roughly
    60 requests per hour per IP; pass a token for higher limits.

    Args:
        owner: GitHub organization or user login.
        repo: Repository name.
        state: ``open``, ``closed``, or ``all``.
        labels: Comma-separated label names to filter (GitHub ``labels`` param).
        max_results: Maximum issues to return (capped at 100).
        token: Optional ``GITHUB_TOKEN`` or PAT with ``repo`` scope for private repos.

    Returns:
        A text summary of issues, or an error description including rate-limit hints.
    """
    o = owner.strip()
    r = repo.strip()
    if not o or not r:
        return "Error: owner and repo must be non-empty."
    st = state.strip().lower()
    if st not in ("open", "closed", "all"):
        return "Error: state must be open, closed, or all."
    n = max(1, min(_MAX_ISSUES_CAP, int(max_results)))
    params: dict[str, str | int] = {
        "state": st,
        "per_page": n,
        "page": 1,
    }
    labels_clean = labels.strip()
    if labels_clean:
        params["labels"] = labels_clean

    url = f"{_GITHUB_API}/repos/{o}/{r}/issues"
    try:
        with httpx.Client(
            timeout=_DEFAULT_TIMEOUT,
            headers=_github_request_headers(token),
        ) as client:
            response = client.get(url, params=params)
    except httpx.HTTPError as exc:
        return f"Error: GitHub HTTP request failed: {exc}"

    if response.status_code == 403:
        hint = _format_rate_limit_hint(response)
        body = _github_error_body(response)
        return (
            "Error: GitHub returned 403 (often rate limit or missing permissions). "
            f"{body}. Headers: {hint}. "
            "Set GITHUB_TOKEN or use --token for higher limits."
        )
    if response.status_code != 200:
        return (
            f"Error: GitHub issues API status {response.status_code}: "
            f"{_github_error_body(response)}"
        )

    data = response.json()
    if not isinstance(data, list):
        return "Error: unexpected GitHub API response shape."

    remaining_hint = _format_rate_limit_hint(response)
    lines: list[str] = [
        f"Issues for {o}/{r} (state={st}, showing up to {n}):",
    ]
    if remaining_hint:
        lines.append(f"(API rate limit: {remaining_hint})")
    count = 0
    for item in data:
        if not isinstance(item, dict):
            continue
        if "pull_request" in item:
            continue
        count += 1
        num = item.get("number")
        title = item.get("title") or ""
        istate = item.get("state") or ""
        user = (item.get("user") or {}) if isinstance(item.get("user"), dict) else {}
        login = user.get("login", "")
        html_url = item.get("html_url", "")
        labels_raw = item.get("labels") or []
        label_names: list[str] = []
        if isinstance(labels_raw, list):
            for lab in labels_raw:
                if isinstance(lab, dict) and lab.get("name"):
                    label_names.append(str(lab["name"]))
        lab_line = ", ".join(label_names) if label_names else "(no labels)"
        lines.append(
            f"- #{num} [{istate}] {title}\n"
            f"  author={login} labels={lab_line}\n"
            f"  url={html_url}",
        )
    if count == 0:
        lines.append("(No issues matched; note: pull requests are excluded.)")
    return "\n".join(lines)


def read_milestones(
    owner: str,
    repo: str,
    *,
    state: str = "open",
    max_results: int = 20,
    token: str | None = None,
) -> str:
    """List GitHub milestones for a repository.

    Args:
        owner: GitHub organization or user login.
        repo: Repository name.
        state: ``open``, ``closed``, or ``all``.
        max_results: Maximum milestones (capped at 50).
        token: Optional bearer token for private repos / higher rate limits.

    Returns:
        Text summary or an error string with rate-limit guidance when relevant.
    """
    o = owner.strip()
    r = repo.strip()
    if not o or not r:
        return "Error: owner and repo must be non-empty."
    st = state.strip().lower()
    if st not in ("open", "closed", "all"):
        return "Error: state must be open, closed, or all."
    n = max(1, min(_MAX_MILESTONES_CAP, int(max_results)))
    params: dict[str, str | int] = {
        "state": st,
        "per_page": n,
        "page": 1,
    }
    url = f"{_GITHUB_API}/repos/{o}/{r}/milestones"
    try:
        with httpx.Client(
            timeout=_DEFAULT_TIMEOUT,
            headers=_github_request_headers(token),
        ) as client:
            response = client.get(url, params=params)
    except httpx.HTTPError as exc:
        return f"Error: GitHub HTTP request failed: {exc}"

    if response.status_code == 403:
        hint = _format_rate_limit_hint(response)
        body = _github_error_body(response)
        return (
            "Error: GitHub returned 403 (often rate limit or missing permissions). "
            f"{body}. Headers: {hint}. "
            "Set GITHUB_TOKEN or use --token for higher limits."
        )
    if response.status_code != 200:
        return (
            f"Error: GitHub milestones API status {response.status_code}: "
            f"{_github_error_body(response)}"
        )

    raw = response.json()
    if not isinstance(raw, list):
        return "Error: unexpected GitHub API response shape."

    remaining_hint = _format_rate_limit_hint(response)
    lines: list[str] = [
        f"Milestones for {o}/{r} (state={st}, showing up to {n}):",
    ]
    if remaining_hint:
        lines.append(f"(API rate limit: {remaining_hint})")
    for ms in raw:
        if not isinstance(ms, dict):
            continue
        title = ms.get("title") or ""
        desc = (ms.get("description") or "").strip()
        if len(desc) > 400:
            desc = desc[:397] + "..."
        ms_state = ms.get("state") or ""
        open_issues = ms.get("open_issues")
        closed_issues = ms.get("closed_issues")
        due = ms.get("due_on") or "(no due date)"
        html_url = ms.get("html_url", "")
        lines.append(
            f"- [{ms_state}] {title}\n"
            f"  open_issues={open_issues} closed_issues={closed_issues} due={due}\n"
            f"  url={html_url}\n"
            f"  description: {desc or '(none)'}",
        )
    if len(lines) <= 2:
        lines.append("(No milestones returned.)")
    return "\n".join(lines)


def read_markdown(root: Path, path: str, *, max_chars: int = 120_000) -> str:
    """Read a markdown file under ``root`` and return its text (UTF-8).

    Optional YAML front matter delimited by ``---`` lines is stripped from the
    returned body. Only files ending in ``.md`` or ``.markdown`` are allowed.

    Args:
        root: Directory that bounds relative ``path`` resolution.
        path: File path relative to ``root``.
        max_chars: Maximum characters returned from the body after stripping.

    Returns:
        File contents (possibly truncated) or an error message.
    """
    rel = path.strip().replace("\\", "/")
    if not rel or rel.startswith("/"):
        return "Error: path must be a relative file path."
    suffix = Path(rel).suffix.lower()
    if suffix not in {".md", ".markdown"}:
        return "Error: only .md and .markdown files are allowed."
    try:
        full = _safe_resolve_under(root, rel)
    except ValueError as exc:
        return f"Error: {exc}"
    if not full.is_file():
        return f"Error: not a file: {rel}"
    try:
        raw = full.read_text(encoding="utf-8")
    except OSError as exc:
        return f"Error: failed to read file: {exc}"
    body = _strip_optional_yaml_front_matter(raw)
    limit = max(1000, min(500_000, int(max_chars)))
    if len(body) > limit:
        body = body[: limit - 3] + "..."
    return f"Markdown file {rel} ({len(body)} chars):\n\n{body}"
