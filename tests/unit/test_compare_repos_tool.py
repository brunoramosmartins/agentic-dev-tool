"""compare_repos structured diff."""

from __future__ import annotations

from pathlib import Path

from adt.tools.compare import compare_repos


def test_compare_repos_structure(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "only_a.txt").write_text("x", encoding="utf-8")
    (b / "only_b.txt").write_text("y", encoding="utf-8")
    (a / "shared.txt").write_text("same", encoding="utf-8")
    (b / "shared.txt").write_text("same", encoding="utf-8")
    roots = {"r0": a, "r1": b}
    out = compare_repos(roots, "r0", "r1")
    assert "compare_repos" in out
    assert "in_both: 1" in out
    assert "sample_only_r0" in out and "sample_only_r1" in out


def test_compare_repos_pyproject_diff(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "pyproject.toml").write_text("[project]\nname='a'\n", encoding="utf-8")
    (b / "pyproject.toml").write_text("[project]\nname='b'\n", encoding="utf-8")
    roots = {"r0": a, "r1": b}
    out = compare_repos(roots, "r0", "r1")
    assert "pyproject.toml: differ" in out


def test_compare_repos_unknown_key(tmp_path: Path) -> None:
    roots = {"r0": tmp_path}
    out = compare_repos(roots, "r0", "missing")
    assert "error" in out.lower()


def test_compare_repos_identical_keys(tmp_path: Path) -> None:
    roots = {"r0": tmp_path}
    out = compare_repos(roots, "r0", "r0")
    assert "error" in out.lower() or "identical" in out.lower()


def test_compare_repos_non_directory(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("x", encoding="utf-8")
    roots = {"r0": f, "r1": tmp_path}
    out = compare_repos(roots, "r0", "r1")
    assert "error" in out.lower() or "not a directory" in out.lower()


def test_compare_repos_requirements_diff(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "requirements.txt").write_text("flask==2.0\nrequests\n", encoding="utf-8")
    (b / "requirements.txt").write_text("django==4.0\n", encoding="utf-8")
    roots = {"r0": a, "r1": b}
    out = compare_repos(roots, "r0", "r1")
    assert "requirements" in out.lower() or "dep" in out.lower()


def test_compare_repos_with_gitignore(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (a / "app.py").write_text("x = 1\n", encoding="utf-8")
    (a / "debug.log").write_text("log data\n", encoding="utf-8")
    (b / "app.py").write_text("x = 2\n", encoding="utf-8")
    roots = {"r0": a, "r1": b}
    out = compare_repos(roots, "r0", "r1")
    assert "debug.log" not in out
