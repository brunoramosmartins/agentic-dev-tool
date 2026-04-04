"""Validation rules on :class:`~adt.models.schemas.QueryRequest`."""

from __future__ import annotations

import pytest

from adt.models.schemas import QueryRequest


def test_github_owner_and_repo_must_be_paired() -> None:
    """``github_owner`` without ``github_repo`` must fail validation."""
    with pytest.raises(ValueError, match="github_owner and github_repo"):
        QueryRequest(query="x", github_owner="org", github_repo=None)


def test_effective_repo_paths_orders_and_dedupes() -> None:
    q = QueryRequest(
        query="x",
        repo_path="/a",
        additional_repo_paths=["/b", "/a"],
    )
    assert q.effective_repo_paths() == ["/a", "/b"]


def test_github_pair_accepted() -> None:
    """Both GitHub fields may be set together."""
    q = QueryRequest(
        query="issues?",
        repo_path=".",
        github_owner="o",
        github_repo="r",
    )
    assert q.github_owner == "o"
    assert q.github_repo == "r"
