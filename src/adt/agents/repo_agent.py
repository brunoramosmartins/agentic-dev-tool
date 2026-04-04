"""Repository analysis agent with repo-scoped tools (MVP)."""

from __future__ import annotations

from adt.agents.base import BaseAgent
from adt.mcp.context import ContextBuilder
from adt.models.schemas import AgentResponse, QueryRequest

_REPO_SYSTEM_PROMPT = """You are a senior software engineer analyzing a codebase.

## Workflow
1. Call read_repo_tree first (path '.' = repo root) for overall structure.
2. Identify the most relevant files based on the user's question.
3. Read files with read_file; prefer at most a few files per answer.
4. For symbols or patterns, use search_code with a focused regex.
5. Synthesize findings into a clear, actionable answer.

## Analytical principles
- Start with the big picture (directory structure) before diving into files.
- Prioritize entry points (main.py, app.py, __init__.py) for architecture questions.
- Look at pyproject.toml, requirements, or package files for stack questions.
- Read tests to understand expected behavior when relevant.

## Tool usage
- Always begin with read_repo_tree unless the user already provided exact file paths.
- Do not read more than five files in a single request unless strictly necessary.
- Prefer search_code for locating symbols instead of reading large files blindly.

## Stopping criteria
- Stop when you can answer confidently from the files you inspected.
- If information is missing, say what you checked and what is still unknown.

## Response format
- Lead with a direct answer, then cite evidence (paths, brief snippets).
- Do not dump the entire tree; summarize structure instead.

## Exclusions
- Do not invent files or APIs you did not observe in tool output.
- Do not execute shell commands or modify the filesystem.
"""


class RepoAgent(BaseAgent):
    """Agent for local repository analysis using read/search tools."""

    @property
    def system_prompt(self) -> str:
        """Return the system message guiding repository-focused tool use."""
        return _REPO_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        """Names of tools registered for this agent in :mod:`adt.bootstrap`."""
        return ["read_repo_tree", "read_file", "search_code"]

    def handle(self, request: QueryRequest, context: str) -> AgentResponse:
        """Build a short preview of context without invoking the LLM.

        The interactive ``adt ask`` command uses :class:`~adt.core.runner.Runner`, which
        performs the full LLM and tool loop. This method supports unit tests and future
        orchestration that may call agents directly.

        Args:
            request: Original user query and optional ``repo_path``.
            context: Pre-built context string when the caller already assembled it.

        Returns:
            A response describing preview length and declared tool names.
        """
        builder = ContextBuilder()
        if request.repo_path:
            built = builder.build_from_repo(request.repo_path)
        else:
            built = builder.build_from_text(context or "")
        return AgentResponse(
            answer=(
                "repo_agent: use `adt ask` (Runner) for LLM-backed answers. "
                f"Context preview length: {len(built)} characters."
            ),
            tools_used=list(self.tools),
            context_summary=built[:400],
            routed_agent=self.name,
        )
