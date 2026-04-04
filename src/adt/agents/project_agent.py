"""Project agent with GitHub issues, milestones, and local markdown tools."""

from __future__ import annotations

from adt.agents.base import BaseAgent
from adt.mcp.context import ContextBuilder
from adt.models.schemas import AgentResponse, QueryRequest

_PROJECT_SYSTEM_PROMPT = """
You are a technical project manager helping with delivery status and planning.

## Workflow
1. When the user asks about issues, triage, or bugs, call read_issues with the
   correct owner and repo (use the session default if provided in context).
2. For timelines, releases, or planning buckets, call read_milestones.
3. For roadmap or documentation questions, use read_markdown on paths such as
   README.md or ROADMAP.md relative to the local markdown root.

## Tool usage
- read_issues excludes pull requests; mention that distinction when listing work.
- Pass labels as a comma-separated string when filtering (GitHub API format).
- If GitHub returns rate-limit errors, explain that setting GITHUB_TOKEN or
  using the CLI --token flag increases limits.

## Response format
- Summaries first: counts, themes, blockers, and next steps.
- Then bullet lists with issue numbers, titles, and links when present in tool
  output.

## Quality bar
- Do not invent issue numbers or milestone titles; only use tool output.
- If tools fail, say what you attempted and what the user can fix (token, slug).
""".strip()


class ProjectAgent(BaseAgent):
    """Agent for GitHub project data and local markdown roadmaps."""

    @property
    def system_prompt(self) -> str:
        """Return instructions for issues, milestones, and markdown roadmaps."""
        return _PROJECT_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        """Tool names registered for this agent in :mod:`adt.bootstrap`."""
        return ["read_issues", "read_milestones", "read_markdown"]

    def handle(self, request: QueryRequest, context: str) -> AgentResponse:
        """Describe tools and context preview without invoking the LLM.

        The interactive ``adt ask`` path uses :class:`~adt.core.runner.Runner`.

        Args:
            request: User query plus optional GitHub and path metadata.
            context: Optional caller-provided context string.

        Returns:
            Short preview listing project tool names.
        """
        builder = ContextBuilder()
        built = builder.build_from_text(context or "")
        return AgentResponse(
            answer=(
                "project_agent: use `adt ask` (Runner) for LLM-backed answers. "
                f"Context preview length: {len(built)} characters."
            ),
            tools_used=list(self.tools),
            context_summary=built[:400],
            routed_agent=self.name,
        )
