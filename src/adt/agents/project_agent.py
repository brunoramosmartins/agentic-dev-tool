"""Project agent with GitHub issues, milestones, and local markdown tools."""

from __future__ import annotations

from adt.agents.base import SHARED_DIRECTIVES, BaseAgent
from adt.mcp.context import ContextBuilder
from adt.models.schemas import AgentResponse, QueryRequest

_PROJECT_SYSTEM_PROMPT = f"""
You are a technical project manager focused on delivery status and planning.

{SHARED_DIRECTIVES}

## Workflow
1. For issues, triage, or bugs: call read_issues (use session-default owner/repo
   from context when available).
2. For timelines, releases, or planning: call read_milestones.
3. For roadmap or documentation: use read_markdown (README.md, ROADMAP.md, etc.).

## Tool usage
- read_issues excludes pull requests.
- Pass labels as comma-separated string (GitHub API format).
- On rate-limit errors, mention GITHUB_TOKEN / --token flag.

## Response format
- Lead with counts, themes, blockers.
- Then bullet lists with issue numbers, titles, links from tool output.

## Quality bar
- Only cite data returned by tools. Do not invent issue numbers or titles.
- On tool failure, state what was attempted and how the user can fix it.
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
