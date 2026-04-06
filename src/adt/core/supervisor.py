"""Rule-based intent routing to specialized agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adt.models.schemas import QueryRequest, RoutedRequest

if TYPE_CHECKING:
    from adt.tracing.context import TraceContext

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

    def __init__(self, *, trace: TraceContext | None = None) -> None:
        self._trace = trace

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

        matched: list[str] = [k for k in _PROJECT_KEYWORDS if k in text]
        if matched:
            enriched.options = {**enriched.options, "route": "project_keywords"}
            routed = RoutedRequest(agent_name="project_agent", request=enriched)
            self._emit_routing(routed, matched)
            return routed

        matched = [k for k in _RESEARCH_KEYWORDS if k in text]
        if matched:
            enriched.options = {**enriched.options, "route": "research_keywords"}
            routed = RoutedRequest(agent_name="research_agent", request=enriched)
            self._emit_routing(routed, matched)
            return routed

        matched = [k for k in _REPO_KEYWORDS if k in text]
        if matched:
            enriched.options = {**enriched.options, "route": "repo_keywords"}
            routed = RoutedRequest(agent_name="repo_agent", request=enriched)
            self._emit_routing(routed, matched)
            return routed

        enriched.options = {**enriched.options, "route": "default"}
        routed = RoutedRequest(agent_name=default_agent, request=enriched)
        self._emit_routing(routed, [])
        return routed

    def _emit_routing(self, routed: RoutedRequest, matched_keywords: list[str]) -> None:
        if self._trace is None:
            return
        self._trace.emit(
            "supervisor",
            "routing_decision",
            agent=routed.agent_name,
            method="keyword",
            route=routed.request.options.get("route", ""),
            matched_keywords=matched_keywords,
        )
