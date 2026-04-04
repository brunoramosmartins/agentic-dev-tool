"""File relevance scoring for context packing."""

from __future__ import annotations

from adt.mcp.ranking import (
    extract_query_keywords,
    score_candidate_file,
    sort_paths_by_relevance,
)


def test_extract_query_keywords_filters_stopwords() -> None:
    """Short and stop tokens should be removed."""
    k = extract_query_keywords("What is the roadmap for this project?")
    assert "roadmap" in k
    assert "what" not in k


def test_score_prefers_readme_and_keywords(tmp_path) -> None:
    """README and keyword matches should outrank arbitrary files."""
    root = tmp_path
    readme = root / "README.md"
    readme.write_text("x", encoding="utf-8")
    other = root / "zzz_dump.txt"
    other.write_text("y" * 1000, encoding="utf-8")
    kw = extract_query_keywords("readme documentation")
    assert score_candidate_file(readme, root, kw) > score_candidate_file(
        other, root, kw
    )


def test_sort_paths_by_relevance_orders_desc(tmp_path) -> None:
    """Higher scores should appear first."""
    root = tmp_path
    a = root / "a.txt"
    b = root / "README.md"
    a.write_text("x", encoding="utf-8")
    b.write_text("y", encoding="utf-8")
    paths = [a, b]
    ordered = sort_paths_by_relevance(paths, root, frozenset({"readme"}))
    assert ordered[0].name == "README.md"
