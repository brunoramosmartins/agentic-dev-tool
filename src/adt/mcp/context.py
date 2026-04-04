"""Build text context from repositories or raw strings with tiktoken budgets."""

from __future__ import annotations

import os
from pathlib import Path

from adt.mcp.budget import read_total_budget_from_environ
from adt.mcp.cache import RepoTreeCache
from adt.mcp.ranking import extract_query_keywords, sort_paths_by_relevance
from adt.mcp.tokens import (
    count_tokens,
    get_encoder_for_model,
    trim_context,
    truncate_head_tail,
)

_SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".eggs",
}
_TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".toml",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".cfg",
    ".ini",
}


def default_cache_dir() -> Path:
    """Return ``~/.adt/cache`` (expanded)."""
    return Path.home() / ".adt" / "cache"


def default_cache_ttl() -> float:
    """Return TTL seconds from ``ADT_CACHE_TTL`` or 300."""
    raw = os.environ.get("ADT_CACHE_TTL", "").strip()
    if not raw:
        return 300.0
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 300.0


class ContextBuilder:
    """Assembles bounded context strings for LLM prompts."""

    def __init__(
        self,
        *,
        tiktoken_model: str = "gpt-4o-mini",
        use_repo_tree_cache: bool = True,
        cache_ttl_seconds: float | None = None,
        cache_dir: Path | None = None,
        total_token_budget: int | None = None,
    ) -> None:
        """Configure encoding, optional tree cache, and default total budget.

        Args:
            tiktoken_model: Model name for :func:`get_encoder_for_model`.
            use_repo_tree_cache: When True, persist tree walks under ``cache_dir``.
            cache_ttl_seconds: Override tree cache TTL (default from env or 300s).
            cache_dir: Cache root (default ``~/.adt/cache``).
            total_token_budget: Override default token window for context slice.
        """
        self._enc = get_encoder_for_model(tiktoken_model)
        ttl = (
            cache_ttl_seconds if cache_ttl_seconds is not None else default_cache_ttl()
        )
        self._tree_cache: RepoTreeCache | None
        if use_repo_tree_cache:
            cdir = cache_dir if cache_dir is not None else default_cache_dir()
            self._tree_cache = RepoTreeCache(cdir, ttl_seconds=ttl)
        else:
            self._tree_cache = None
        self._total_budget = (
            total_token_budget
            if total_token_budget is not None
            else read_total_budget_from_environ()
        )

    @property
    def total_token_budget(self) -> int:
        """Configured logical token window for budgeting (see :mod:`adt.mcp.budget`)."""
        return self._total_budget

    def estimate_tokens(self, text: str) -> int:
        """Return an accurate token count for ``text`` using tiktoken."""
        return count_tokens(text, self._enc)

    def truncate(self, text: str, max_tokens: int) -> str:
        """Trim text to ``max_tokens`` while keeping head and tail runs."""
        return truncate_head_tail(text, max_tokens, self._enc)

    def trim_context(self, text: str, max_tokens: int) -> str:
        """Trim to ``max_tokens`` tokens, keeping the start of ``text``."""
        return trim_context(text, max_tokens, self._enc)

    def count_text_tokens(self, text: str) -> int:
        """Return the tiktoken length of ``text`` using this builder's encoding."""
        return count_tokens(text, self._enc)

    def build_from_text(self, text: str, *, max_tokens: int | None = None) -> str:
        """Wrap arbitrary text as a labeled context block."""
        body = text.strip()
        if max_tokens is not None:
            body = self.trim_context(body, max_tokens)
        return f"[context:text]\n{body}\n[/context:text]"

    def build_from_repo(
        self,
        path: str,
        *,
        query: str | None = None,
        max_depth: int = 4,
        max_files: int = 48,
        max_chars_per_file: int = 4000,
        max_context_tokens: int | None = None,
        use_cache: bool = True,
    ) -> str:
        """Walk a repository: ranked files plus tree listing within token budget.

        Args:
            path: Repository root path.
            query: Optional user query for keyword ranking.
            max_depth: Directory walk depth cap.
            max_files: Upper bound on files to consider (after ranking).
            max_chars_per_file: Per-file character cap before token packing.
            max_context_tokens: Hard cap on returned context tokens (defaults to
                50%% of :attr:`_total_budget`).
            use_cache: When False, skip reading/writing the tree line cache.
        """
        root = Path(path).resolve()
        if not root.is_dir():
            return self.build_from_text(f"(missing directory: {path})")

        ctx_budget = (
            max_context_tokens
            if max_context_tokens is not None
            else int(self._total_budget * 0.50)
        )
        ctx_budget = max(256, ctx_budget)

        keywords = extract_query_keywords(query)

        def walk_tree() -> list[str]:
            return self._walk_tree(root, max_depth=max_depth)

        if use_cache and self._tree_cache is not None:
            tree_lines = self._tree_cache.get_or_build(root, max_depth, walk_tree)
        else:
            tree_lines = walk_tree()

        lines: list[str] = [f"[context:repo path={root}]"]
        lines.append("[tree]")
        lines.extend(tree_lines)
        lines.append("[/tree]")

        candidates = self._iter_text_files(root, max_depth=max_depth)
        ranked = sort_paths_by_relevance(candidates, root, keywords)[:max_files]

        header = "\n".join(lines)
        used = count_tokens(header, self._enc)
        remaining = max(0, ctx_budget - used)

        for fp in ranked:
            rel = fp.relative_to(root)
            try:
                raw = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            snippet = raw[:max_chars_per_file]
            if len(raw) > max_chars_per_file:
                snippet += "\n... (truncated)"
            block = f"[file:{rel.as_posix()}]\n{snippet}\n[/file:{rel.as_posix()}]"
            need = count_tokens(block + "\n", self._enc)
            if need > remaining:
                if remaining > 64:
                    partial = self.trim_context(block, remaining)
                    lines.append(partial)
                break
            lines.append(block)
            remaining -= need

        body = "\n".join(lines) + "\n[/context:repo]"
        if count_tokens(body, self._enc) > ctx_budget:
            body = self.trim_context(body, ctx_budget)
        return body

    def _walk_tree(self, root: Path, *, max_depth: int) -> list[str]:
        lines: list[str] = []

        def walk(current: Path, prefix: str, depth: int) -> None:
            if depth > max_depth:
                return
            try:
                entries = sorted(current.iterdir(), key=lambda p: p.name.lower())
            except OSError:
                return
            for p in entries:
                if p.name in _SKIP_DIR_NAMES or p.name.endswith(".egg-info"):
                    continue
                lines.append(f"{prefix}{p.name}")
                if p.is_dir():
                    walk(p, prefix + "  ", depth + 1)

        walk(root, "", 0)
        return lines

    def _iter_text_files(self, root: Path, *, max_depth: int) -> list[Path]:
        """Collect readable text-like files under ``root`` (unordered)."""
        found: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d
                for d in dirnames
                if d not in _SKIP_DIR_NAMES and not d.endswith(".egg-info")
            ]
            rel_depth = len(Path(dirpath).relative_to(root).parts)
            if rel_depth > max_depth:
                dirnames[:] = []
                continue
            for name in filenames:
                path = Path(dirpath) / name
                suf = path.suffix.lower()
                if suf not in _TEXT_SUFFIXES and name not in {
                    "Dockerfile",
                    "Makefile",
                    "LICENSE",
                }:
                    continue
                found.append(path)
        return found
