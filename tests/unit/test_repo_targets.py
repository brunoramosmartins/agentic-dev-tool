"""Multi-value ``--repo`` resolution."""

from __future__ import annotations

from pathlib import Path

from adt.repo_spec import resolve_repo_targets


def test_resolve_repo_targets_dedupes_same_path(tmp_path: Path) -> None:
    a = tmp_path / "a"
    a.mkdir()
    r = resolve_repo_targets([str(a), str(a)])
    assert list(r.roots.keys()) == ["r0"]
    assert r.roots["r0"] == a.resolve()


def test_resolve_repo_targets_two_distinct(tmp_path: Path) -> None:
    one = tmp_path / "one"
    two = tmp_path / "two"
    one.mkdir()
    two.mkdir()
    r = resolve_repo_targets([str(one), str(two)])
    assert set(r.roots.keys()) == {"r0", "r1"}
    assert r.roots["r0"] == one.resolve()
    assert r.roots["r1"] == two.resolve()
    assert r.primary_key == "r0"


def test_resolve_repo_targets_empty_uses_dot(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    r = resolve_repo_targets([])
    assert r.roots["r0"] == tmp_path.resolve()


def test_resolve_repo_targets_github_first_slug(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    r = resolve_repo_targets(["acme/demo"])
    assert r.github_owner == "acme"
    assert r.github_repo == "demo"
    assert r.roots["r0"] == tmp_path.resolve()


def test_resolve_repo_targets_mixed_slug_and_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    loc = tmp_path / "loc"
    loc.mkdir()
    r = resolve_repo_targets(["o/r", str(loc)])
    assert r.github_owner == "o"
    assert r.github_repo == "r"
    assert len(r.roots) == 2
    assert tmp_path.resolve() in r.roots.values()
    assert loc.resolve() in r.roots.values()
