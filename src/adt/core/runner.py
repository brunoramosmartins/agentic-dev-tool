"""Orchestrates routing, context, LLM calls, and the tool execution loop."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from adt.agents.base import BaseAgent
from adt.logging.json_log import log_adt
from adt.mcp.budget import allocate_budget
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
    from adt.core.hybrid_supervisor import HybridSupervisor
    from adt.core.supervisor import Supervisor

logger = logging.getLogger(__name__)


class LLMBackend(Protocol):
    """Minimal interface for anything that can run a chat completion."""

    def chat(
        self,
        messages: Sequence[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        *,
        max_completion_tokens: int | None = None,
    ) -> LLMMessage: ...


class Runner:
    """Wires supervisor, context, LLM, registry, and executor into one request path."""

    def __init__(
        self,
        supervisor: Supervisor | HybridSupervisor,
        llm: LLMBackend,
        context_builder: ContextBuilder,
        executor: ExecutionController,
        registry: ToolRegistry,
        agents: dict[str, BaseAgent],
        *,
        max_tool_iterations: int = 5,
        repo_roots: dict[str, Path] | None = None,
        agent_chain: list[str] | None = None,
    ) -> None:
        self._supervisor = supervisor
        self._llm = llm
        self._context = context_builder
        self._executor = executor
        self._registry = registry
        self._agents = agents
        self._max_tool_iterations = max_tool_iterations
        self._repo_roots: dict[str, Path] = dict(repo_roots or {})
        self._agent_chain: list[str] = list(agent_chain or [])
        self.last_budget_report: dict[str, Any] = {}

    @property
    def last_token_usage(self) -> dict[str, int]:
        """Return token counts from the last LLM call when the backend exposes them."""
        raw = getattr(self._llm, "last_usage", None)
        if isinstance(raw, dict):
            return raw
        return {}

    def run(self, request: QueryRequest) -> AgentResponse:
        """Route the query, build context, run the LLM/tool loop, return an answer."""
        use_cache = not bool(request.options.get("no_cache", False))
        if self._agent_chain and request.force_agent is None:
            return self._run_agent_chain(request, use_cache=use_cache)

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
        return self._execute_routed(routed, use_cache=use_cache)

    def _run_agent_chain(
        self,
        request: QueryRequest,
        *,
        use_cache: bool,
    ) -> AgentResponse:
        """Run configured agents sequentially and merge answers."""
        chunks: list[str] = []
        tools_all: list[str] = []
        summaries: list[str] = []
        chain_label = ",".join(self._agent_chain)
        for name in self._agent_chain:
            if name not in self._agents:
                return AgentResponse(
                    answer=f"Unknown agent in agent_chain: {name!r}.",
                    tools_used=[],
                    context_summary="",
                    routed_agent=f"chain:{chain_label}",
                )
            sub = request.model_copy(deep=True)
            sub.force_agent = name
            sub.options = {**sub.options, "route": "chain"}
            routed = RoutedRequest(agent_name=name, request=sub)
            resp = self._execute_routed(routed, use_cache=use_cache)
            chunks.append(f"### {name}\n{resp.answer}")
            tools_all.extend(resp.tools_used)
            if resp.context_summary:
                summaries.append(resp.context_summary)
        return AgentResponse(
            answer="\n\n".join(chunks),
            tools_used=tools_all,
            context_summary=(summaries[0][:400] if summaries else ""),
            routed_agent=f"chain:{chain_label}",
        )

    def _execute_routed(
        self,
        routed: RoutedRequest,
        *,
        use_cache: bool,
    ) -> AgentResponse:
        """Build context and run the tool loop for one routed agent."""
        t0 = time.perf_counter()
        self.last_budget_report = {}
        agent = self._agents[routed.agent_name]
        req = routed.request
        multi = len(self._repo_roots) > 1

        if routed.agent_name == "research_agent":
            raw_context = self._context.build_from_text("")
        elif routed.agent_name == "project_agent":
            parts: list[str] = []
            if req.github_owner and req.github_repo:
                parts.append(
                    f"Default GitHub repository: {req.github_owner}/{req.github_repo}. "
                    "Use these owner and repo values in read_issues and "
                    "read_milestones unless the user specifies another repository."
                )
            paths = req.effective_repo_paths()
            if paths:
                parts.append(
                    "Local markdown root for read_markdown (relative paths): "
                    f"{paths[0]}"
                )
            if len(paths) > 1:
                parts.append("Additional repository roots: " + ", ".join(paths[1:]))
            meta = "\n".join(parts)
            if req.github_owner and req.github_repo:
                raw_context = self._context.build_from_text(meta)
            elif paths:
                if multi:
                    repo_blob = self._context.build_from_repos(
                        self._repo_roots,
                        query=req.query,
                        use_cache=use_cache,
                    )
                else:
                    repo_blob = self._context.build_from_repo(
                        paths[0],
                        query=req.query,
                        use_cache=use_cache,
                    )
                raw_context = f"{meta}\n\n{repo_blob}" if meta else repo_blob
            else:
                raw_context = self._context.build_from_text(meta)
        elif req.effective_repo_paths():
            paths = req.effective_repo_paths()
            if multi:
                raw_context = self._context.build_from_repos(
                    self._repo_roots,
                    query=req.query,
                    use_cache=use_cache,
                )
            else:
                raw_context = self._context.build_from_repo(
                    paths[0],
                    query=req.query,
                    use_cache=use_cache,
                )
        else:
            raw_context = self._context.build_from_text("")

        alloc = allocate_budget(self._context.total_token_budget)
        sys_prompt = agent.system_prompt
        if self._context.count_text_tokens(sys_prompt) > alloc["system"]:
            sys_prompt = self._context.trim_context(sys_prompt, alloc["system"])

        user_content = (
            f"{raw_context}\n\nUser question:\n{routed.request.query.strip()}\n"
        )
        if self._context.count_text_tokens(user_content) > alloc["context"]:
            user_content = self._context.trim_context(user_content, alloc["context"])

        context_summary = raw_context[:400]
        messages: list[LLMMessage] = [
            LLMMessage(role="system", content=sys_prompt),
            LLMMessage(role="user", content=user_content),
        ]

        tools_openai = self._tools_for_agent(agent)
        tools_json = json.dumps(tools_openai or [], default=str)
        tools_tok = self._context.count_text_tokens(tools_json)
        if tools_tok > alloc["tools"]:
            log_adt(
                logger,
                logging.WARNING,
                event="tools_schema_over_budget",
                estimated_tokens=tools_tok,
                budget=alloc["tools"],
            )

        self.last_budget_report = {
            "allocated": alloc,
            "estimated_system_tokens": self._context.count_text_tokens(sys_prompt),
            "estimated_user_tokens": self._context.count_text_tokens(user_content),
            "estimated_tools_schema_tokens": tools_tok,
        }

        tools_used: list[str] = []

        log_adt(
            logger,
            logging.INFO,
            event="agent_selected",
            agent=routed.agent_name,
            route=routed.request.options.get("route"),
            query_preview=routed.request.query[:500],
            force_agent=routed.request.force_agent,
        )

        for _ in range(self._max_tool_iterations):
            try:
                reply = self._llm.chat(
                    messages,
                    tools_openai or None,
                    max_completion_tokens=alloc["response"],
                )
            except Exception as exc:  # noqa: BLE001 — user-facing fallback
                log_adt(
                    logger,
                    logging.ERROR,
                    event="llm_failure",
                    error=str(exc),
                    error_type=type(exc).__name__,
                    agent=routed.agent_name,
                )
                return AgentResponse(
                    answer=(
                        "The language model request failed or timed out. "
                        f"({type(exc).__name__}: {exc}). "
                        "Check OPENAI_API_KEY, network connectivity, and quota."
                    ),
                    tools_used=tools_used,
                    context_summary=context_summary,
                    routed_agent=routed.agent_name,
                )

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
                    log_adt(
                        logger,
                        logging.INFO,
                        event="tool_called",
                        tool=tc.name,
                        success=result.success,
                    )
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

            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            usage = self.last_token_usage
            log_adt(
                logger,
                logging.INFO,
                event="request_completed",
                agent=routed.agent_name,
                duration_ms=elapsed_ms,
                tools_used=tools_used,
                **usage,
            )
            return AgentResponse(
                answer=reply.content.strip(),
                tools_used=tools_used,
                context_summary=context_summary,
                routed_agent=routed.agent_name,
            )

        logger.warning("runner_max_iterations exceeded agent=%s", routed.agent_name)
        log_adt(
            logger,
            logging.WARNING,
            event="runner_max_iterations",
            agent=routed.agent_name,
            tools_used=tools_used,
        )
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
