"""Runner context selection for the research agent."""

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


class SpyContext(ContextBuilder):
    """Records whether repository or free-form context builders were used."""

    def __init__(self) -> None:
        """Initialize counters for :meth:`build_from_repo` / :meth:`build_from_text`."""
        super().__init__()
        self.repo_calls = 0
        self.text_calls = 0

    def build_from_repo(
        self,
        path: str,
        *,
        query: str | None = None,
        max_depth: int = 4,
        max_files: int = 48,
        max_chars_per_file: int = 4000,
        max_context_tokens: int | None = None,
        use_cache: bool = True,
    ) -> str:
        """Increment repo counter and delegate to the base implementation."""
        self.repo_calls += 1
        return super().build_from_repo(
            path,
            query=query,
            max_depth=max_depth,
            max_files=max_files,
            max_chars_per_file=max_chars_per_file,
            max_context_tokens=max_context_tokens,
            use_cache=use_cache,
        )

    def build_from_text(self, text: str, *, max_tokens: int | None = None) -> str:
        """Increment text counter and delegate to the base implementation."""
        self.text_calls += 1
        return super().build_from_text(text, max_tokens=max_tokens)


def test_research_routing_skips_repo_context(
    tool_registry,
    sample_repo_path: str,
) -> None:
    """Supervisor-chosen research runs should not load the repository tree."""
    spy = SpyContext()
    fake = FakeLLM([LLMMessage(role="assistant", content="ok.")])
    supervisor = Supervisor()
    executor = ExecutionController(tool_registry)
    agents = {
        "repo_agent": RepoAgent(),
        "project_agent": ProjectAgent(),
        "research_agent": ResearchAgent(),
    }
    runner = Runner(
        supervisor,
        fake,
        spy,
        executor,
        tool_registry,
        agents,
    )
    res = runner.run(
        QueryRequest(
            query="recent arxiv papers on retrieval augmented generation",
            repo_path=sample_repo_path,
        ),
    )
    assert res.routed_agent == "research_agent"
    assert spy.repo_calls == 0
    assert spy.text_calls >= 1


def test_force_repo_agent_loads_repo_even_if_query_sounds_like_research(
    tool_registry,
    sample_repo_path: str,
) -> None:
    """``force_agent=repo_agent`` must still attach repository context."""
    spy = SpyContext()
    fake = FakeLLM([LLMMessage(role="assistant", content="ok.")])
    supervisor = Supervisor()
    executor = ExecutionController(tool_registry)
    agents = {
        "repo_agent": RepoAgent(),
        "project_agent": ProjectAgent(),
        "research_agent": ResearchAgent(),
    }
    runner = Runner(
        supervisor,
        fake,
        spy,
        executor,
        tool_registry,
        agents,
    )
    res = runner.run(
        QueryRequest(
            query="papers about python",
            repo_path=sample_repo_path,
            force_agent="repo_agent",
        ),
    )
    assert res.routed_agent == "repo_agent"
    assert spy.repo_calls == 1


def test_runner_unknown_force_agent_short_circuits(
    tool_registry,
    sample_repo_path: str,
) -> None:
    """Invalid ``force_agent`` should return an error without calling the LLM."""
    spy = SpyContext()
    fake = FakeLLM([LLMMessage(role="assistant", content="should not run")])
    supervisor = Supervisor()
    executor = ExecutionController(tool_registry)
    agents = {
        "repo_agent": RepoAgent(),
        "project_agent": ProjectAgent(),
        "research_agent": ResearchAgent(),
    }
    runner = Runner(
        supervisor,
        fake,
        spy,
        executor,
        tool_registry,
        agents,
    )
    res = runner.run(
        QueryRequest(
            query="hello",
            repo_path=sample_repo_path,
            force_agent="ghost_agent",
        ),
    )
    assert "Unknown agent" in res.answer
    assert res.routed_agent == "ghost_agent"
