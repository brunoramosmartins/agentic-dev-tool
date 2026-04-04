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
