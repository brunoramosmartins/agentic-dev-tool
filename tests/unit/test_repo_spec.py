"""Tests for :mod:`adt.repo_spec` CLI target parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from adt.repo_spec import resolve_repo_target


def test_resolve_local_directory(tmp_path) -> None:
    """Existing directories resolve as local roots without GitHub coordinates."""
    d = tmp_path / "proj"
    d.mkdir()
    r = resolve_repo_target(str(d))
    assert r.local_root == d.resolve()
    assert r.github_owner is None
    assert r.github_repo is None


def test_resolve_github_slug(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``owner/repo`` uses cwd as markdown root when the path is not a directory."""
    monkeypatch.chdir(tmp_path)
    r = resolve_repo_target("myorg/my-repo")
    assert r.local_root == Path.cwd().resolve()
    assert r.github_owner == "myorg"
    assert r.github_repo == "my-repo"


def test_resolve_invalid_raises() -> None:
    """Missing paths and invalid slugs raise ``ValueError``."""
    with pytest.raises(ValueError, match="Not a directory"):
        resolve_repo_target("does-not-exist-dir-xyz123")
