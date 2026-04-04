"""Rule-based intent routing to specialized agents."""

from __future__ import annotations

from adt.models.schemas import QueryRequest, RoutedRequest

_PROJECT_KEYWORDS = (
    "issue",
    "issues",
    "milestone",
    "milestones",
    "roadmap",
    "project",
    "sprint",
    "backlog",
    "github",
    "epic",
    "ticket",
    "release",
    "kanban",
    "board",
    "assignee",
    "pull request",
    "triaged",
)
_RESEARCH_KEYWORDS = (
    "paper",
    "papers",
    "arxiv",
    "article",
    "research",
    "study",
    "literature",
    "literature review",
    "publication",
    "survey",
    "citation",
    "journal",
    "preprint",
    "doi",
)
_REPO_KEYWORDS = (
    "repo",
    "code",
    "codebase",
    "architecture",
    "explain",
    "file",
    "function",
    "implementation",
    "search",
)


class Supervisor:
    """Classifies a query and selects an agent using lightweight keyword rules."""

    def route(self, request: QueryRequest) -> RoutedRequest:
        """Return the agent name and a possibly enriched ``QueryRequest``.

        Precedence: project keywords, then research, then repository, then default.
        The default is ``repo_agent`` for local sessions and ``project_agent`` when
        ``github_owner`` / ``github_repo`` are set (``--repo owner/repo``). The word
        ``search`` maps to the repository agent so codebase queries are not sent to
        research.
        """
        text = request.query.lower()
        enriched = request.model_copy(deep=True)
        default_agent = (
            "project_agent"
            if (enriched.github_owner and enriched.github_repo)
            else "repo_agent"
        )

        if any(k in text for k in _PROJECT_KEYWORDS):
            enriched.options = {**enriched.options, "route": "project_keywords"}
            return RoutedRequest(agent_name="project_agent", request=enriched)

        if any(k in text for k in _RESEARCH_KEYWORDS):
            enriched.options = {**enriched.options, "route": "research_keywords"}
            return RoutedRequest(agent_name="research_agent", request=enriched)

        if any(k in text for k in _REPO_KEYWORDS):
            enriched.options = {**enriched.options, "route": "repo_keywords"}
            return RoutedRequest(agent_name="repo_agent", request=enriched)

        enriched.options = {**enriched.options, "route": "default"}
        return RoutedRequest(agent_name=default_agent, request=enriched)
