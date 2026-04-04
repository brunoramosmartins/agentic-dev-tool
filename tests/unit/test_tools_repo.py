"""Unit tests for repository tool functions."""

from __future__ import annotations

from pathlib import Path

from adt.tools import repo as repo_tools


def test_read_repo_tree_lists_sample_files(sample_repo_path: str) -> None:
    """``read_repo_tree`` should list known files in the fixture repo."""
    root = Path(sample_repo_path)
    out = repo_tools.read_repo_tree(root, path=".", max_depth=4)
    assert "main.py" in out
    assert "utils.py" in out


def test_read_file_numbered_lines(sample_repo_path: str) -> None:
    """``read_file`` should prefix lines and respect ``max_lines``."""
    root = Path(sample_repo_path)
    out = repo_tools.read_file(root, "main.py", max_lines=5)
    assert "def main" in out or "main" in out
    assert "   1 |" in out


def test_search_code_finds_pattern(sample_repo_path: str) -> None:
    """``search_code`` should return matching lines with paths."""
    root = Path(sample_repo_path)
    out = repo_tools.search_code(root, ".", r"def\s+add", max_results=10)
    assert "utils.py" in out
    assert "def add" in out


def test_safe_resolve_rejects_traversal(sample_repo_path: str) -> None:
    """Paths that escape the repo root must be rejected."""
    root = Path(sample_repo_path)
    out = repo_tools.read_file(root, "../../etc/passwd", max_lines=5)
    assert "error" in out.lower()


def test_read_repo_tree_missing_dir(tmp_path: Path) -> None:
    out = repo_tools.read_repo_tree(tmp_path, path="no_such_dir", max_depth=3)
    assert "error" in out.lower() or "not" in out.lower()


def test_read_file_not_a_file(tmp_path: Path) -> None:
    sub = tmp_path / "subdir"
    sub.mkdir()
    out = repo_tools.read_file(tmp_path, "subdir", max_lines=10)
    assert "error" in out.lower() or "not a file" in out.lower()


def test_read_file_missing(tmp_path: Path) -> None:
    out = repo_tools.read_file(tmp_path, "ghost.py", max_lines=10)
    assert "error" in out.lower() or "not" in out.lower()


def test_search_code_invalid_regex(sample_repo_path: str) -> None:
    root = Path(sample_repo_path)
    out = repo_tools.search_code(root, ".", r"[invalid", max_results=5)
    assert "error" in out.lower()


def test_search_code_missing_dir(tmp_path: Path) -> None:
    out = repo_tools.search_code(tmp_path, "no_dir", r"foo", max_results=5)
    assert "error" in out.lower() or "not" in out.lower()


def test_read_repo_tree_traversal_rejected(tmp_path: Path) -> None:
    out = repo_tools.read_repo_tree(tmp_path, path="../../etc", max_depth=2)
    assert "error" in out.lower()


def test_search_code_traversal_rejected(tmp_path: Path) -> None:
    out = repo_tools.search_code(tmp_path, "../../etc", r"x", max_results=5)
    assert "error" in out.lower()


def test_read_repo_tree_with_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("ignored_dir/\n", encoding="utf-8")
    (tmp_path / "kept.py").write_text("x = 1\n", encoding="utf-8")
    ig = tmp_path / "ignored_dir"
    ig.mkdir()
    (ig / "hidden.py").write_text("y = 2\n", encoding="utf-8")
    out = repo_tools.read_repo_tree(tmp_path, path=".", max_depth=3)
    assert "kept.py" in out
    assert "hidden.py" not in out


def test_search_code_binary_skip(tmp_path: Path) -> None:
    (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02\x03binary")
    (tmp_path / "text.py").write_text("# match_me\n", encoding="utf-8")
    out = repo_tools.search_code(tmp_path, ".", r"match_me", max_results=10)
    assert "text.py" in out
