"""Build text context from repositories or raw strings with token heuristics."""

from __future__ import annotations

import os
from pathlib import Path

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


class ContextBuilder:
    """Assembles bounded context strings for LLM prompts."""

    def estimate_tokens(self, text: str) -> int:
        """Rough token count using the roadmap heuristic (1 token ≈ 0.75 words)."""
        words = len(text.split())
        return max(1, int(words / 0.75))

    def truncate(self, text: str, max_tokens: int) -> str:
        """Trim text to an approximate token budget, keeping start and end."""
        if self.estimate_tokens(text) <= max_tokens:
            return text
        max_words = max(1, int(max_tokens * 0.75))
        words = text.split()
        if len(words) <= max_words:
            return text
        head = max_words // 2
        tail = max_words - head
        beginning = " ".join(words[:head])
        ending = " ".join(words[-tail:])
        return f"{beginning}\n...\n{ending}"

    def build_from_text(self, text: str, *, max_tokens: int | None = None) -> str:
        """Wrap arbitrary text as a labeled context block."""
        body = text.strip()
        if max_tokens is not None:
            body = self.truncate(body, max_tokens)
        return f"[context:text]\n{body}\n[/context:text]"

    def build_from_repo(
        self,
        path: str,
        *,
        max_depth: int = 4,
        max_files: int = 24,
        max_chars_per_file: int = 4000,
        max_total_tokens: int = 8000,
    ) -> str:
        """Walk a repository: tree listing plus a slice of readable text files."""
        root = Path(path).resolve()
        if not root.is_dir():
            return self.build_from_text(f"(missing directory: {path})")

        lines: list[str] = [f"[context:repo path={root}]"]

        tree_lines = self._walk_tree(root, max_depth=max_depth)
        lines.append("[tree]")
        lines.extend(tree_lines)
        lines.append("[/tree]")

        files_read = 0
        for fp in self._iter_text_files(root, max_depth=max_depth):
            if files_read >= max_files:
                break
            rel = fp.relative_to(root)
            try:
                raw = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            snippet = raw[:max_chars_per_file]
            if len(raw) > max_chars_per_file:
                snippet += "\n... (truncated)"
            lines.append(f"[file:{rel.as_posix()}]")
            lines.append(snippet)
            lines.append(f"[/file:{rel.as_posix()}]")
            files_read += 1

        body = "\n".join(lines) + "\n[/context:repo]"
        return self.truncate(body, max_total_tokens)

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
        """Prefer shallow, small, common source files."""
        candidates: list[tuple[int, int, Path]] = []
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
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                priority = 0 if name.lower().startswith("readme") else 1
                candidates.append((priority, size, path))

        candidates.sort(key=lambda t: (t[0], t[1], str(t[2])))
        return [p for _, _, p in candidates]
