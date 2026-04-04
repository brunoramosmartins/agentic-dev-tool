"""Rule-based intent routing to specialized agents."""

from __future__ import annotations

from adt.models.schemas import QueryRequest, RoutedRequest

_PROJECT_KEYWORDS = (
    "issue",
    "milestone",
    "roadmap",
    "project",
    "sprint",
    "backlog",
)
_RESEARCH_KEYWORDS = (
    "paper",
    "article",
    "research",
    "search",
    "study",
    "literature",
)
_REPO_KEYWORDS = (
    "repo",
    "code",
    "architecture",
    "explain",
    "file",
    "function",
)


class Supervisor:
    """Classifies a query and selects an agent using lightweight keyword rules."""

    def route(self, request: QueryRequest) -> RoutedRequest:
        """Return the agent name and a possibly enriched ``QueryRequest``.

        Precedence: project keywords, then research, then repository, then default
        ``repo_agent``. Matching is case-insensitive via substring search.
        """
        text = request.query.lower()
        enriched = request.model_copy(deep=True)

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
        return RoutedRequest(agent_name="repo_agent", request=enriched)
