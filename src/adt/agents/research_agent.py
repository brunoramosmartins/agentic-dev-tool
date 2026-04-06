"""Technical research agent with arXiv search and article fetching tools."""

from __future__ import annotations

from adt.agents.base import SHARED_DIRECTIVES, BaseAgent
from adt.mcp.context import ContextBuilder
from adt.models.schemas import AgentResponse, QueryRequest

_RESEARCH_SYSTEM_PROMPT = f"""
You are a technical researcher specializing in academic literature.

{SHARED_DIRECTIVES}

## Workflow
1. For paper discovery: call search_papers with focused keywords.
2. For full text from a specific URL: use fetch_article.
3. Synthesize: key claims, methods, limitations, relation to the question.

## Tool usage
- Prefer search_papers first for surveys, recent work, arXiv queries.
- Use fetch_article when abstracts are insufficient.
- Only cite titles, authors, URLs that appear in tool output.

## Response format
- Executive summary (2-4 sentences) first.
- Then bullet list: title, one-line takeaway, URL.

## Quality bar
- Distinguish consensus from single-paper claims.
- Note uncertainty on tool errors or empty results.
- Do not access local files; use only the provided tools.
""".strip()


class ResearchAgent(BaseAgent):
    """Agent for literature search (arXiv) and reading public web articles."""

    @property
    def system_prompt(self) -> str:
        """Return instructions for grounded, tool-backed research answers."""
        return _RESEARCH_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        """Tool names registered for this agent in :mod:`adt.bootstrap`."""
        return ["search_papers", "fetch_article"]

    def handle(self, request: QueryRequest, context: str) -> AgentResponse:
        """Summarize declared tools without calling the LLM (for tests and direct use).

        Interactive ``adt ask`` uses :class:`~adt.core.runner.Runner` for the full loop.

        Args:
            request: User query (repository path is ignored for research-only previews).
            context: Optional pre-built context string when the caller supplies it.

        Returns:
            A short preview response listing research tool names.
        """
        builder = ContextBuilder()
        built = builder.build_from_text(context or "")
        return AgentResponse(
            answer=(
                "research_agent: use `adt ask` (Runner) for LLM-backed answers. "
                f"Context preview length: {len(built)} characters."
            ),
            tools_used=list(self.tools),
            context_summary=built[:400],
            routed_agent=self.name,
        )
