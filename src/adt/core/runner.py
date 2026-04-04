"""Orchestrates routing, context, LLM calls, and the tool execution loop."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Protocol

from adt.agents.base import BaseAgent
from adt.mcp.context import ContextBuilder
from adt.mcp.executor import ExecutionController
from adt.mcp.registry import ToolRegistry
from adt.models.schemas import (
    AgentResponse,
    LLMMessage,
    QueryRequest,
    RoutedRequest,
    ToolCall,
)

if TYPE_CHECKING:
    from adt.core.supervisor import Supervisor

logger = logging.getLogger(__name__)


class LLMBackend(Protocol):
    """Minimal interface for anything that can run a chat completion."""

    def chat(
        self,
        messages: Sequence[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMMessage: ...


class Runner:
    """Wires supervisor, context, LLM, registry, and executor into one request path."""

    def __init__(
        self,
        supervisor: Supervisor,
        llm: LLMBackend,
        context_builder: ContextBuilder,
        executor: ExecutionController,
        registry: ToolRegistry,
        agents: dict[str, BaseAgent],
        *,
        max_tool_iterations: int = 5,
    ) -> None:
        self._supervisor = supervisor
        self._llm = llm
        self._context = context_builder
        self._executor = executor
        self._registry = registry
        self._agents = agents
        self._max_tool_iterations = max_tool_iterations

    @property
    def last_token_usage(self) -> dict[str, int]:
        """Return token counts from the last LLM call when the backend exposes them."""
        raw = getattr(self._llm, "last_usage", None)
        if isinstance(raw, dict):
            return raw
        return {}

    def run(self, request: QueryRequest) -> AgentResponse:
        """Route the query, build context, run the LLM/tool loop, return an answer."""
        if request.force_agent is not None:
            if request.force_agent not in self._agents:
                unknown = request.force_agent
                known = ", ".join(sorted(self._agents))
                return AgentResponse(
                    answer=(f"Unknown agent {unknown!r}. Valid choices: {known}."),
                    tools_used=[],
                    context_summary="",
                    routed_agent=request.force_agent or "",
                )
            enriched = request.model_copy(deep=True)
            enriched.options = {**enriched.options, "route": "forced"}
            routed = RoutedRequest(agent_name=request.force_agent, request=enriched)
        else:
            routed = self._supervisor.route(request)
        agent = self._agents[routed.agent_name]

        if routed.agent_name == "research_agent":
            raw_context = self._context.build_from_text("")
        elif routed.request.repo_path:
            raw_context = self._context.build_from_repo(routed.request.repo_path)
        else:
            raw_context = self._context.build_from_text("")

        context_summary = raw_context[:400]
        user_content = (
            f"{raw_context}\n\nUser question:\n{routed.request.query.strip()}\n"
        )

        messages: list[LLMMessage] = [
            LLMMessage(role="system", content=agent.system_prompt),
            LLMMessage(role="user", content=user_content),
        ]

        tools_openai = self._tools_for_agent(agent)
        tools_used: list[str] = []

        for _ in range(self._max_tool_iterations):
            reply = self._llm.chat(messages, tools_openai or None)

            if reply.tool_calls:
                assistant_tc = [
                    ToolCall(
                        id=tc.id,
                        name=tc.name,
                        arguments=tc.arguments,
                        agent=routed.agent_name,
                    )
                    for tc in reply.tool_calls
                ]
                messages.append(
                    LLMMessage(
                        role="assistant",
                        content=reply.content,
                        tool_calls=assistant_tc,
                    ),
                )
                for tc in assistant_tc:
                    result = self._executor.execute(tc)
                    tools_used.append(tc.name)
                    messages.append(
                        LLMMessage(
                            role="tool",
                            content=result.output
                            if result.success
                            else (result.error or "error"),
                            tool_call_id=tc.id or f"call_{tc.name}",
                        ),
                    )
                continue

            return AgentResponse(
                answer=reply.content.strip(),
                tools_used=tools_used,
                context_summary=context_summary,
                routed_agent=routed.agent_name,
            )

        logger.warning("runner_max_iterations exceeded agent=%s", routed.agent_name)
        return AgentResponse(
            answer=(
                "Stopped after maximum tool iterations "
                f"({self._max_tool_iterations}). Partial tool trail: {tools_used}."
            ),
            tools_used=tools_used,
            context_summary=context_summary,
            routed_agent=routed.agent_name,
        )

    def _tools_for_agent(self, agent: BaseAgent) -> list[dict[str, Any]]:
        all_tools = self._registry.to_openai_format(agent.name)
        if not agent.tools:
            return []
        allowed = set(agent.tools)
        return [t for t in all_tools if t["function"]["name"] in allowed]
