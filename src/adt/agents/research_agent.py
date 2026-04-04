"""Technical research agent with arXiv search and article fetching tools."""

from __future__ import annotations

from adt.agents.base import BaseAgent
from adt.mcp.context import ContextBuilder
from adt.models.schemas import AgentResponse, QueryRequest

_RESEARCH_SYSTEM_PROMPT = """
You are a technical researcher helping with papers and articles.

## Workflow
1. For paper discovery, call search_papers with focused keywords
   (topics, methods, authors).
2. When the user gives a URL or you need full text from a known page,
   use fetch_article.
3. Synthesize concise answers: key claims, methods, limitations, and
   how results relate to the question.

## Tool usage
- Prefer search_papers first when the user asks for recent work, surveys,
  or arXiv content.
- Use fetch_article for specific URLs or when abstracts are insufficient
  (respect site terms).
- Do not fabricate titles, authors, or URLs; only cite what appears in
  tool output.

## Response format
- Start with a short executive summary (2–4 sentences).
- Then use markdown: ### sections, bullet lists for paper lists with
  **title** and links.
- When listing papers from search_papers, include title, one-line
  takeaway, and the URL line.

## Quality bar
- Distinguish established consensus from single-paper claims.
- Note uncertainty when tools return errors or empty results.
- Do not execute code or access local files; use only the provided tools
  for external content.
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
