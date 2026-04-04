"""Optional agent_chain sequential execution."""

from __future__ import annotations

from adt.agents.project_agent import ProjectAgent
from adt.agents.repo_agent import RepoAgent
from adt.agents.research_agent import ResearchAgent
from adt.core.runner import Runner
from adt.core.supervisor import Supervisor
from adt.mcp.context import ContextBuilder
from adt.mcp.executor import ExecutionController
from adt.models.schemas import LLMMessage, QueryRequest
from tests.fake_llm import FakeLLM


def test_agent_chain_runs_sequentially(
    tool_registry,
    sample_repo_path: str,
) -> None:
    fake = FakeLLM(
        [
            LLMMessage(role="assistant", content="First pass."),
            LLMMessage(role="assistant", content="Second pass."),
        ],
    )
    supervisor = Supervisor()
    context = ContextBuilder()
    executor = ExecutionController(tool_registry)
    agents = {
        "repo_agent": RepoAgent(),
        "project_agent": ProjectAgent(),
        "research_agent": ResearchAgent(),
    }
    runner = Runner(
        supervisor,
        fake,
        context,
        executor,
        tool_registry,
        agents,
        agent_chain=["repo_agent", "repo_agent"],
    )
    res = runner.run(
        QueryRequest(query="what is in main.py", repo_path=sample_repo_path),
    )
    assert "First pass." in res.answer
    assert "Second pass." in res.answer
    assert res.routed_agent.startswith("chain:")
