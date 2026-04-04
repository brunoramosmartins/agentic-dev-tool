"""Heuristic relevance scoring for repository files used in context packing."""

from __future__ import annotations

import re
from pathlib import Path

_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "have",
        "what",
        "when",
        "where",
        "does",
        "how",
        "why",
        "into",
        "your",
        "about",
        "code",
        "file",
        "repo",
    },
)

# Lower tier = higher priority for project metadata / entrypoints.
_TYPE_TIERS: dict[str, int] = {
    "readme": 0,
    "license": 1,
    "changelog": 1,
    "contributing": 1,
    "pyproject.toml": 2,
    "setup.cfg": 2,
    "setup.py": 2,
    "requirements.txt": 2,
    "makefile": 3,
    "dockerfile": 3,
    "package.json": 3,
    "__init__.py": 4,
    "main.py": 4,
    "app.py": 4,
    "conftest.py": 5,
    ".md": 6,
    ".toml": 7,
    ".py": 8,
    ".yaml": 9,
    ".yml": 9,
    ".json": 10,
    ".txt": 11,
    ".cfg": 12,
    ".ini": 12,
}


def extract_query_keywords(query: str | None, *, min_len: int = 3) -> frozenset[str]:
    """Lowercase alphanumeric tokens from ``query``, dropping short stopwords."""
    if not query:
        return frozenset()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", query.lower())
    out = {t for t in tokens if len(t) >= min_len and t not in _STOPWORDS}
    return frozenset(out)


def _type_tier(path: Path) -> int:
    """Return a numeric tier for path suffix / well-known names (smaller is better)."""
    name = path.name.lower()
    if name in _TYPE_TIERS:
        return _TYPE_TIERS[name]
    if name.startswith("readme"):
        return _TYPE_TIERS["readme"]
    suf = path.suffix.lower()
    return _TYPE_TIERS.get(suf, 20)


_KEYWORD_MATCH_BONUS = 12.0
_MAX_TYPE_TIER_BONUS = 25.0
_FILE_SIZE_BONUS = 15.0


def score_candidate_file(path: Path, root: Path, keywords: frozenset[str]) -> float:
    """Score a text file for inclusion in ranked context (higher is better).

    Combines keyword overlap on the relative path, type priority, and a mild
    preference for smaller files (focused snippets).

    Args:
        path: Absolute file path under ``root``.
        root: Repository root.
        keywords: Normalized query keywords.

    Returns:
        A sortable relevance score (not normalized to [0,1]).
    """
    rel = path.relative_to(root)
    rel_s = rel.as_posix().lower()
    name_l = path.name.lower()
    score = 0.0
    for kw in keywords:
        if kw in name_l or kw in rel_s:
            score += _KEYWORD_MATCH_BONUS
    tier = _type_tier(path)
    score += max(0.0, _MAX_TYPE_TIER_BONUS - float(tier))
    try:
        kb = path.stat().st_size / 1024.0
    except OSError:
        kb = 1024.0
    score += _FILE_SIZE_BONUS / (1.0 + kb)
    return score


def sort_paths_by_relevance(
    paths: list[Path],
    root: Path,
    keywords: frozenset[str],
) -> list[Path]:
    """Return ``paths`` sorted by descending :func:`score_candidate_file`."""
    scored = [(score_candidate_file(p, root, keywords), p) for p in paths]
    scored.sort(key=lambda t: (-t[0], str(t[1])))
    return [p for _, p in scored]
