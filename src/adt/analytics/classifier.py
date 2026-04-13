"""Issue classifier strategies: keyword (default) and embedding-based.

The embedding classifier uses ``text-embedding-3-small`` to compute cosine
similarity against curated prototype phrases for each category. Prototype
embeddings are cached under ``~/.adt/cache/classifier.json`` so subsequent
runs skip the embedding API call.

When the embedding API is unavailable the classifier silently falls back
to the keyword heuristic so analytics never block the user.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Protocol

from adt.config import ensure_adt_dir
from adt.logging.json_log import log_adt
from adt.models.schemas import CodeIssue

logger = logging.getLogger(__name__)

# ── keyword classifier (existing logic, extracted) ─────────────────────

_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "off_by_one",
        ("off-by-one", "off by one", "boundary", "inclusive", "<=", ">="),
    ),
    (
        "edge_case",
        ("edge case", "empty", "null", "none", "zero", "negative", "overflow"),
    ),
    (
        "naming",
        ("name", "naming", "variable name", "rename", "descriptive"),
    ),
    (
        "type_annotation",
        ("type", "annotation", "typing", "hint"),
    ),
    (
        "docstring",
        ("docstring", "documentation", "doc comment"),
    ),
    (
        "error_handling",
        ("error", "exception", "try", "except", "raise", "handle"),
    ),
    (
        "logic",
        ("logic", "incorrect", "wrong", "bug", "condition"),
    ),
    (
        "style",
        ("style", "idiomatic", "pythonic", "readability", "format"),
    ),
    (
        "performance",
        ("performance", "slow", "complexity", "big o", "efficient"),
    ),
    (
        "testing",
        ("test", "coverage", "assertion", "case"),
    ),
)


def keyword_classify(issue: CodeIssue) -> str:
    """Classify via substring keyword match (fast, no API call)."""
    text = (issue.description or "").lower()
    if not text:
        return "other"
    for label, keywords in _CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw in text:
                return label
    return "other"


# ── embedding backend protocol ─────────────────────────────────────────


class EmbeddingBackend(Protocol):
    """Anything that can embed a list of strings into float vectors."""

    def embed(self, texts: list[str]) -> list[list[float]]: ...


# ── prototype definitions ──────────────────────────────────────────────

PROTOTYPES: dict[str, list[str]] = {
    "off_by_one": [
        "boundary error in loop index",
        "off-by-one when comparing length",
        "inclusive vs exclusive range bound",
        "fence-post error in iteration",
    ],
    "edge_case": [
        "empty input not handled",
        "null reference causes crash",
        "zero or negative value edge case",
        "overflow on large input",
    ],
    "naming": [
        "variable name is too short or unclear",
        "rename identifier for clarity",
        "single-letter variable hides intent",
    ],
    "type_annotation": [
        "missing type annotation on function",
        "type hint does not match runtime type",
        "add return type to method signature",
    ],
    "docstring": [
        "function lacks a docstring",
        "documentation is outdated or misleading",
    ],
    "error_handling": [
        "bare except clause swallows errors",
        "exception not logged or re-raised",
        "missing error handling for external call",
    ],
    "logic": [
        "condition is inverted or incorrect",
        "wrong operator in boolean expression",
        "logic bug causes incorrect output",
    ],
    "style": [
        "code is not idiomatic Python",
        "readability could be improved",
        "formatting does not follow conventions",
    ],
    "performance": [
        "algorithm has unnecessary quadratic complexity",
        "repeated computation could be cached",
        "slow loop over large dataset",
    ],
    "testing": [
        "test assertion does not cover this path",
        "missing test for error branch",
        "test coverage gap in edge case",
    ],
}


# ── cache helpers ──────────────────────────────────────────────────────


def _cache_path() -> Path:
    cache_dir = ensure_adt_dir() / "cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir / "classifier.json"


def _load_cached_embeddings() -> dict[str, list[list[float]]] | None:
    p = _cache_path()
    if not p.exists():
        return None
    try:
        data: Any = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _save_cached_embeddings(embeddings: dict[str, list[list[float]]]) -> None:
    try:
        _cache_path().write_text(
            json.dumps(embeddings, default=str),
            encoding="utf-8",
        )
    except OSError as exc:
        log_adt(
            logger,
            logging.WARNING,
            event="classifier_cache_write_failed",
            error=str(exc),
        )


# ── cosine similarity ──────────────────────────────────────────────────


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ── embedding classifier ──────────────────────────────────────────────


class EmbeddingClassifier:
    """Classify issues by cosine similarity to curated prototype embeddings.

    On first use, embeds all prototype phrases and caches the result.
    Subsequent calls only embed the query text and compare against cache.
    Falls back to :func:`keyword_classify` on any error.
    """

    def __init__(self, backend: EmbeddingBackend) -> None:
        self._backend = backend
        self._proto_embeddings: dict[str, list[list[float]]] = {}
        self._initialized = False

    def _ensure_prototypes(self) -> None:
        if self._initialized:
            return
        cached = _load_cached_embeddings()
        if cached is not None and set(cached.keys()) == set(PROTOTYPES.keys()):
            self._proto_embeddings = cached
            self._initialized = True
            return

        # Build all prototype embeddings in one batch
        all_texts: list[str] = []
        index_map: list[tuple[str, int]] = []  # (category, position)
        for cat, phrases in PROTOTYPES.items():
            for phrase in phrases:
                index_map.append((cat, len(all_texts)))
                all_texts.append(phrase)

        all_embeddings = self._backend.embed(all_texts)

        result: dict[str, list[list[float]]] = {cat: [] for cat in PROTOTYPES}
        for cat, idx in index_map:
            result[cat].append(all_embeddings[idx])

        self._proto_embeddings = result
        self._initialized = True
        _save_cached_embeddings(result)

    def classify(self, issue: CodeIssue) -> str:
        """Return the best-matching category for *issue*.

        Falls back to :func:`keyword_classify` on any error.
        """
        text = (issue.description or "").strip()
        if not text:
            return "other"
        try:
            self._ensure_prototypes()
            query_emb = self._backend.embed([text])[0]
        except Exception:  # noqa: BLE001
            log_adt(
                logger,
                logging.WARNING,
                event="embedding_classify_fallback",
                reason="embed_failed",
            )
            return keyword_classify(issue)

        best_cat = "other"
        best_score = -1.0
        for cat, proto_embs in self._proto_embeddings.items():
            for emb in proto_embs:
                score = _cosine_similarity(query_emb, emb)
                if score > best_score:
                    best_score = score
                    best_cat = cat

        # Require a minimum similarity threshold
        if best_score < 0.3:
            return "other"
        return best_cat
