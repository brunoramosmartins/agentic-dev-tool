#!/usr/bin/env bash
# ==============================================================================
# setup_issues.sh — Create GitHub issues for the Agentic Dev Tool project
#
# Usage:
#   chmod +x scripts/setup_issues.sh
#   ./scripts/setup_issues.sh
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - Labels must exist (run setup_labels.sh first)
#   - Milestones must exist (run setup_milestones.sh first)
#   - Run from the repository root directory
#
# This script is idempotent: issues with the same title are skipped.
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null)

if [[ -z "$REPO" ]]; then
    echo "ERROR: Could not detect repository. Are you in a git repo with a GitHub remote?"
    exit 1
fi

echo "==> Setting up issues for repository: $REPO"
echo ""

# ------------------------------------------------------------------------------
# Helper function
# ------------------------------------------------------------------------------

create_issue_if_not_exists() {
    local title="$1"
    local body="$2"
    local labels="$3"
    local milestone="$4"

    # Check if issue with this title already exists
    if gh issue list --repo "$REPO" --state all --json title -q '.[].title' 2>/dev/null | grep -qxF "$title"; then
        echo "  Skipping (already exists): $title"
    else
        echo "  Creating issue: $title"
        gh issue create \
            --repo "$REPO" \
            --title "$title" \
            --body "$body" \
            --label "$labels" \
            --milestone "$milestone" \
            2>/dev/null
    fi
}

# ==============================================================================
# PHASE 0 — Project Bootstrap
# ==============================================================================

echo "==> Creating Phase 0 issues..."
echo ""

create_issue_if_not_exists \
    "chore(repo): initialize repository with license and gitignore" \
    "## Context

The project needs a clean starting point with proper licensing and ignore rules.
This is the first commit to the repository and establishes the legal and hygiene
foundation for all future work.

## Tasks

- [ ] Create GitHub repository named \`agentic-dev-tool\`
- [ ] Add MIT LICENSE file
- [ ] Create \`.gitignore\` with Python template and \`.env\` exclusion
- [ ] Create initial \`README.md\` with project title, one-line description, and status badge placeholder
- [ ] Push initial commit to \`main\` branch

## Definition of Done

- [ ] Repository is public on GitHub
- [ ] LICENSE file is present and correct
- [ ] \`.gitignore\` excludes \`__pycache__\`, \`.env\`, \`*.pyc\`, \`.mypy_cache\`, \`.ruff_cache\`
- [ ] README.md exists with project title

## References

- [GitHub gitignore templates](https://github.com/github/gitignore/blob/main/Python.gitignore)
- [MIT License](https://opensource.org/licenses/MIT)" \
    "chore,phase-0" \
    "Phase 0 — Project Bootstrap"

create_issue_if_not_exists \
    "chore(build): configure pyproject.toml with dependencies and tooling" \
    "## Context

A single \`pyproject.toml\` file should define all project metadata, dependencies,
build configuration, and tool settings (Ruff, mypy, pytest). This replaces the
need for \`setup.py\`, \`setup.cfg\`, \`requirements.txt\`, and separate config files.

## Tasks

- [ ] Create \`pyproject.toml\` with \`[build-system]\` using hatchling
- [ ] Add \`[project]\` section with name, version, description, authors, Python requirement
- [ ] Add runtime dependencies: \`typer>=0.9\`, \`pydantic>=2.0\`, \`httpx>=0.25\`, \`openai>=1.0\`, \`rich>=13.0\`
- [ ] Add \`[project.optional-dependencies]\` dev group: \`pytest\`, \`pytest-cov\`, \`ruff\`, \`mypy\`, \`pre-commit\`
- [ ] Add \`[project.scripts]\` entry point: \`adt = \"adt.cli.app:app\"\`
- [ ] Configure \`[tool.ruff]\` with line-length=88, target-version=\"py311\"
- [ ] Configure \`[tool.mypy]\` with strict mode
- [ ] Configure \`[tool.pytest.ini_options]\` with testpaths and markers

## Definition of Done

- [ ] \`pip install -e \".[dev]\"\` installs all dependencies without errors
- [ ] \`ruff check .\` runs without configuration errors
- [ ] \`mypy src/\` runs without configuration errors
- [ ] \`pytest\` runs (even if no tests exist yet)

## References

- [PEP 621](https://peps.python.org/pep-0621/)
- [Hatchling docs](https://hatch.pypa.io/latest/)
- [Ruff configuration](https://docs.astral.sh/ruff/configuration/)" \
    "chore,phase-0" \
    "Phase 0 — Project Bootstrap"

create_issue_if_not_exists \
    "chore(tooling): set up pre-commit hooks and Makefile" \
    "## Context

Automated code quality checks on every commit prevent style drift and catch
issues early. A Makefile provides a consistent interface for common development
commands regardless of developer environment.

## Tasks

- [ ] Create \`.pre-commit-config.yaml\` with hooks: ruff (lint + format), mypy, trailing-whitespace, end-of-file-fixer
- [ ] Create \`Makefile\` with targets: \`install\`, \`lint\`, \`format\`, \`test\`, \`typecheck\`, \`run\`, \`clean\`
- [ ] Create \`.env.example\` with documented environment variables
- [ ] Install pre-commit hooks and verify they run on commit
- [ ] Verify \`make lint\`, \`make test\`, \`make typecheck\` all work

## Definition of Done

- [ ] \`pre-commit run --all-files\` passes
- [ ] All Makefile targets execute without errors
- [ ] \`.env.example\` documents \`OPENAI_API_KEY\` and \`GITHUB_TOKEN\`

## References

- [pre-commit docs](https://pre-commit.com/)
- [Makefile tutorial](https://makefiletutorial.com/)" \
    "chore,phase-0" \
    "Phase 0 — Project Bootstrap"

create_issue_if_not_exists \
    "chore(github): create issue templates, PR template, and CI workflow" \
    "## Context

Standardized templates ensure consistency across all issues and PRs. A CI
pipeline catches regressions immediately on every push and pull request.

## Tasks

- [ ] Create \`.github/ISSUE_TEMPLATE/task.md\` with Context, Tasks, Definition of Done, References sections
- [ ] Create \`.github/ISSUE_TEMPLATE/bug.md\` with Description, Steps to Reproduce, Expected/Actual Behavior
- [ ] Create \`.github/PULL_REQUEST_TEMPLATE.md\` with Description, Related Issues, Changes, Testing, Checklist
- [ ] Create \`.github/workflows/ci.yml\` that runs on push and PR to main:
  - Install Python 3.11
  - Install dependencies
  - Run \`ruff check .\`
  - Run \`mypy src/\`
  - Run \`pytest --cov\`
- [ ] Verify CI runs successfully on a test push

## Definition of Done

- [ ] Issue templates appear when creating new issues on GitHub
- [ ] PR template auto-fills when opening a new PR
- [ ] CI workflow passes on push to main

## References

- [GitHub issue templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests)
- [GitHub Actions for Python](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python)" \
    "chore,phase-0" \
    "Phase 0 — Project Bootstrap"

create_issue_if_not_exists \
    "chore(structure): create directory skeleton with init files" \
    "## Context

A well-defined directory structure makes the codebase navigable from day one.
Empty \`__init__.py\` files establish Python packages, and placeholder docs set
expectations for future documentation.

## Tasks

- [ ] Create full \`src/adt/\` directory tree as defined in the roadmap
- [ ] Add \`__init__.py\` to every Python package directory
- [ ] Add \`__version__ = \"0.1.0\"\` to \`src/adt/__init__.py\`
- [ ] Create \`tests/\` directory with \`conftest.py\` and subdirectories (\`unit/\`, \`integration/\`, \`fixtures/\`)
- [ ] Create \`tests/fixtures/sample_repo/\` with a minimal fake Python project
- [ ] Create \`docs/\` with placeholder markdown files
- [ ] Create \`scripts/\` directory

## Definition of Done

- [ ] \`python -c \"import adt; print(adt.__version__)\"\` prints \`0.1.0\`
- [ ] All directories exist as specified in the roadmap
- [ ] \`tests/fixtures/sample_repo/\` contains a valid mini Python project
- [ ] No import errors when running \`pytest\`

## References

- [Python packaging guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- Repository structure section in ROADMAP.md" \
    "chore,phase-0" \
    "Phase 0 — Project Bootstrap"

create_issue_if_not_exists \
    "chore(automation): run GitHub setup scripts for labels, milestones, and issues" \
    "## Context

The roadmap defines specific labels, milestones, and issues. Bash scripts using
the \`gh\` CLI automate this setup to ensure consistency and save time.

## Tasks

- [ ] Create \`scripts/setup_labels.sh\`
- [ ] Create \`scripts/setup_milestones.sh\`
- [ ] Create \`scripts/setup_issues.sh\`
- [ ] Create \`scripts/setup_all.sh\`
- [ ] Run \`scripts/setup_all.sh\` against the repository
- [ ] Verify all labels, milestones, and issues appear correctly on GitHub

## Definition of Done

- [ ] All labels from the roadmap exist on GitHub with correct colors
- [ ] All milestones (Phase 0 through Phase 7) exist on GitHub
- [ ] All Phase 0 issues are created and assigned to the Phase 0 milestone
- [ ] Scripts are idempotent (running twice does not create duplicates)

## References

- [gh CLI reference](https://cli.github.com/manual/)
- GitHub Automation Scripts section in ROADMAP.md" \
    "chore,phase-0" \
    "Phase 0 — Project Bootstrap"

# ==============================================================================
# PHASE 1 — Core Infrastructure
# ==============================================================================

echo ""
echo "==> Creating Phase 1 issues..."
echo ""

create_issue_if_not_exists \
    "feat(models): define Pydantic schemas for core data structures" \
    "## Context

Every component communicates through well-defined data structures. Pydantic models
provide runtime validation, serialization, and documentation for all data flowing
through the pipeline.

## Tasks

- [ ] Create \`src/adt/models/schemas.py\`
- [ ] Define \`QueryRequest(query, repo_path, options)\`
- [ ] Define \`ToolCall(name, arguments, agent)\`
- [ ] Define \`ToolResult(name, output, success, error)\`
- [ ] Define \`AgentResponse(answer, tools_used, context_summary)\`
- [ ] Define \`LLMMessage(role, content, tool_calls)\`
- [ ] Add comprehensive docstrings to every model and field
- [ ] Add field validators where appropriate
- [ ] Write unit tests in \`tests/unit/test_schemas.py\`

## Definition of Done

- [ ] All models instantiate correctly with valid data
- [ ] All models raise \`ValidationError\` with invalid data
- [ ] Docstrings explain each model's purpose and fields
- [ ] 100% test coverage on schema module

## References

- [Pydantic v2 docs](https://docs.pydantic.dev/latest/)" \
    "feature,phase-1" \
    "Phase 1 — Core Infrastructure"

create_issue_if_not_exists \
    "feat(core): implement LLM client with OpenAI function calling" \
    "## Context

The LLM client bridges the agent system and the language model. It handles prompt
formatting, tool/function calling, retries, and token tracking. Uses gpt-4o-mini
for cost efficiency.

## Tasks

- [ ] Create \`src/adt/core/llm.py\`
- [ ] Implement \`LLMClient\` class with \`chat(messages, tools)\` method
- [ ] Format tools as OpenAI function-calling schema
- [ ] Parse responses that include \`tool_calls\`
- [ ] Implement retry logic with exponential backoff (max 3 retries)
- [ ] Track and log token usage per call
- [ ] Load API key from \`OPENAI_API_KEY\` environment variable
- [ ] Write unit tests with mocked API responses

## Definition of Done

- [ ] \`LLMClient.chat()\` returns parsed \`LLMMessage\` objects
- [ ] Tool calls are correctly parsed into \`ToolCall\` objects
- [ ] Retry logic triggers on 429 and 500 responses
- [ ] Token usage is logged for every call
- [ ] All tests pass with mocked responses

## References

- [OpenAI function calling](https://platform.openai.com/docs/guides/function-calling)
- [OpenAI Python SDK](https://github.com/openai/openai-python)" \
    "feature,phase-1,priority:high" \
    "Phase 1 — Core Infrastructure"

create_issue_if_not_exists \
    "feat(mcp): build tool registry with permission system" \
    "## Context

The tool registry is the central catalog of all available tools. It maps tool names
to implementations and tracks which agents can use which tools.

## Tasks

- [ ] Create \`src/adt/mcp/registry.py\`
- [ ] Define \`ToolDefinition\` Pydantic model
- [ ] Implement \`ToolRegistry\` class with \`register()\`, \`get()\`, \`list_for_agent()\`, \`to_openai_format()\`
- [ ] Add docstrings to all methods
- [ ] Write unit tests in \`tests/unit/test_registry.py\`

## Definition of Done

- [ ] Tools can be registered and retrieved by name
- [ ] \`list_for_agent()\` correctly filters by allowed agents
- [ ] \`to_openai_format()\` produces valid OpenAI function schemas
- [ ] Duplicate registration raises error
- [ ] All tests pass

## References

- [OpenAI function schema](https://platform.openai.com/docs/guides/function-calling)" \
    "feature,phase-1" \
    "Phase 1 — Core Infrastructure"

create_issue_if_not_exists \
    "feat(mcp): implement context builder with token estimation" \
    "## Context

The context builder gathers relevant information from various sources and packages
it into structured context that fits within the LLM's token budget.

## Tasks

- [ ] Create \`src/adt/mcp/context.py\`
- [ ] Implement \`ContextBuilder\` with \`build_from_repo()\`, \`build_from_text()\`, \`estimate_tokens()\`, \`truncate()\`
- [ ] Add docstrings
- [ ] Write unit tests using \`tests/fixtures/sample_repo/\`

## Definition of Done

- [ ] \`build_from_repo()\` returns structured string with tree and file contents
- [ ] Token estimation is within 20% accuracy
- [ ] Truncation preserves beginning and end of text
- [ ] All tests pass

## References

- [OpenAI tokenizer](https://platform.openai.com/tokenizer)" \
    "feature,phase-1" \
    "Phase 1 — Core Infrastructure"

create_issue_if_not_exists \
    "feat(mcp): implement execution controller with logging" \
    "## Context

The execution controller is the gatekeeper for all tool executions. It resolves
tool names, validates inputs, calls tool functions, captures results, and logs
everything.

## Tasks

- [ ] Create \`src/adt/mcp/executor.py\`
- [ ] Implement \`ExecutionController\` with \`execute(tool_call) -> ToolResult\`
- [ ] Validate arguments against tool JSON schema
- [ ] Wrap tool failures (never crash)
- [ ] Log every execution with timing
- [ ] Write unit tests with mock tools

## Definition of Done

- [ ] \`execute()\` correctly calls registered tool functions
- [ ] Invalid arguments produce \`ToolResult(success=False)\`
- [ ] Tool exceptions are caught and wrapped
- [ ] Execution duration is measured and logged
- [ ] All tests pass

## References

- Agent Governance section in ROADMAP.md" \
    "feature,phase-1" \
    "Phase 1 — Core Infrastructure"

create_issue_if_not_exists \
    "feat(core): implement supervisor with rule-based routing" \
    "## Context

The supervisor classifies user intent and selects the appropriate agent. Initial
implementation uses keyword matching — fast, free, and sufficient for three agents.

## Tasks

- [ ] Create \`src/adt/core/supervisor.py\`
- [ ] Implement \`Supervisor.route(query) -> str\` with keyword classification
- [ ] Keywords for repo_agent, project_agent, research_agent
- [ ] Default fallback to repo_agent
- [ ] Write unit tests covering all routing paths

## Definition of Done

- [ ] All keyword categories route correctly
- [ ] Default fallback works
- [ ] Case-insensitive matching works
- [ ] Edge cases tested (mixed keywords, empty query)
- [ ] All tests pass

## References

- Supervisor section in ROADMAP.md" \
    "feature,phase-1" \
    "Phase 1 — Core Infrastructure"

create_issue_if_not_exists \
    "feat(core): implement runner orchestrator with tool-call loop" \
    "## Context

The runner wires all components together. It takes a QueryRequest, routes it,
builds context, calls the LLM, handles the tool-call loop, and returns the
final AgentResponse.

## Tasks

- [ ] Create \`src/adt/core/runner.py\`
- [ ] Implement \`Runner.run(request) -> AgentResponse\`
- [ ] Implement tool-call loop with max iterations (default: 5)
- [ ] Handle max iteration exceeded gracefully
- [ ] Write integration test with mocked LLM

## Definition of Done

- [ ] Full lifecycle works: query -> route -> context -> LLM -> tools -> response
- [ ] Tool-call loop correctly iterates until final answer
- [ ] Max iteration limit prevents infinite loops
- [ ] Integration test passes

## References

- Architecture Overview in ROADMAP.md" \
    "feature,phase-1,priority:high" \
    "Phase 1 — Core Infrastructure"

create_issue_if_not_exists \
    "feat(agents): create abstract base agent class" \
    "## Context

All agents share a common interface. The base class defines this contract and
provides shared functionality, making it easy to add new agents.

## Tasks

- [ ] Create \`src/adt/agents/base.py\`
- [ ] Implement \`BaseAgent\` as abstract class with \`system_prompt\`, \`tools\`, \`handle()\`
- [ ] Add comprehensive docstrings explaining the contract
- [ ] Add type hints

## Definition of Done

- [ ] \`BaseAgent\` cannot be instantiated directly
- [ ] Subclasses must implement all abstract members
- [ ] Docstrings clearly explain how to create a new agent

## References

- [Python ABC docs](https://docs.python.org/3/library/abc.html)" \
    "feature,phase-1" \
    "Phase 1 — Core Infrastructure"

# ==============================================================================
# PHASE 2 — MVP: Repo Agent
# ==============================================================================

echo ""
echo "==> Creating Phase 2 issues..."
echo ""

create_issue_if_not_exists \
    "feat(cli): implement ask command with Typer and Rich output" \
    "## Context

The CLI is the user's entry point. It must be intuitive, provide helpful feedback,
and produce well-formatted output.

## Tasks

- [ ] Create \`src/adt/cli/app.py\` with Typer application
- [ ] Implement \`ask\` command: query (str), --repo (path), --verbose (flag), --model (str)
- [ ] Wire to \`Runner.run()\`
- [ ] Use Rich for formatted output
- [ ] Display token usage in verbose mode
- [ ] Handle errors gracefully
- [ ] Add docstrings

## Definition of Done

- [ ] \`adt ask \"test query\" --repo .\` executes full pipeline
- [ ] Output is readable and well-formatted
- [ ] \`--verbose\` shows debug info
- [ ] \`--help\` is clear and complete

## References

- [Typer docs](https://typer.tiangolo.com/)
- [Rich docs](https://rich.readthedocs.io/)" \
    "feature,phase-2,priority:high" \
    "Phase 2 — MVP: Repo Agent"

create_issue_if_not_exists \
    "feat(tools): implement repo tools — read_repo_tree, read_file, search_code" \
    "## Context

Repo tools are the core functions allowing the repo_agent to interact with local
codebases. They provide structured access without sending entire repos to the LLM.

## Tasks

- [ ] Create \`src/adt/tools/repo.py\`
- [ ] Implement \`read_repo_tree(path, max_depth=3)\` — respects .gitignore
- [ ] Implement \`read_file(path, max_lines=200)\` — with line numbers
- [ ] Implement \`search_code(path, pattern, max_results=20)\` — regex search
- [ ] Register all tools in ToolRegistry
- [ ] Write unit tests using \`tests/fixtures/sample_repo/\`

## Definition of Done

- [ ] \`read_repo_tree\` produces readable tree respecting ignore patterns
- [ ] \`read_file\` returns content with line numbers, handles missing files
- [ ] \`search_code\` finds matches across files, skips binaries
- [ ] All tools registered and accessible via ToolRegistry
- [ ] All tests pass

## References

- [pathlib docs](https://docs.python.org/3/library/pathlib.html)" \
    "feature,phase-2" \
    "Phase 2 — MVP: Repo Agent"

create_issue_if_not_exists \
    "feat(agent): implement repo_agent for codebase analysis" \
    "## Context

The repo_agent is the first specialized agent. It analyzes local codebases to answer
questions about architecture, code structure, dependencies, and implementations.

## Tasks

- [ ] Create \`src/adt/agents/repo_agent.py\`
- [ ] Inherit from BaseAgent
- [ ] Define system prompt following Agent System Prompt Specification
- [ ] Declare tools: read_repo_tree, read_file, search_code
- [ ] Implement \`handle()\` method
- [ ] Write unit tests

## Definition of Done

- [ ] repo_agent correctly uses all three repo tools
- [ ] System prompt follows specification
- [ ] Agent produces useful answers about test fixture repo
- [ ] All tests pass

## References

- Agent System Prompt Specification in ROADMAP.md" \
    "feature,phase-2,priority:high" \
    "Phase 2 — MVP: Repo Agent"

create_issue_if_not_exists \
    "test(integration): end-to-end test for CLI to response pipeline" \
    "## Context

An end-to-end test verifies the entire pipeline: CLI -> supervisor -> agent ->
tools -> LLM -> response. Catches integration issues unit tests miss.

## Tasks

- [ ] Create \`tests/integration/test_full_flow.py\`
- [ ] Write test with mocked LLM simulating tool-call loop
- [ ] Test supervisor routing for repo queries
- [ ] Add \`@pytest.mark.live\` for tests with real LLM calls
- [ ] Write one live test for manual verification

## Definition of Done

- [ ] Mocked integration test passes in CI
- [ ] Live test passes manually with real API key
- [ ] Full lifecycle covered from input to output

## References

- [pytest markers](https://docs.pytest.org/en/latest/how-to/mark.html)" \
    "test,phase-2" \
    "Phase 2 — MVP: Repo Agent"

create_issue_if_not_exists \
    "docs(readme): write installation and usage documentation" \
    "## Context

The README must clearly communicate what the tool does, how to install it, and
how to use it with real examples and expected output.

## Tasks

- [ ] Write project overview section
- [ ] Write installation instructions
- [ ] Write environment setup (.env, API key)
- [ ] Write usage examples with expected output
- [ ] Add architecture diagram link
- [ ] Add contributing and license sections

## Definition of Done

- [ ] A new user can install and use the tool from README alone
- [ ] All example commands are tested
- [ ] No broken links

## References

- [Awesome README examples](https://github.com/matiassingers/awesome-readme)" \
    "docs,phase-2" \
    "Phase 2 — MVP: Repo Agent"

# ==============================================================================
# PHASE 3 — Research Agent
# ==============================================================================

echo ""
echo "==> Creating Phase 3 issues..."
echo ""

create_issue_if_not_exists \
    "feat(tools): implement search_papers with arXiv API" \
    "## Context

The search_papers tool enables finding relevant academic papers via arXiv's free API.

## Tasks

- [ ] Create \`src/adt/tools/research.py\`
- [ ] Implement \`search_papers(query, max_results=5)\` using arXiv API
- [ ] Implement \`fetch_article(url)\` for URL text extraction
- [ ] Register tools for research_agent
- [ ] Write unit tests with mocked HTTP responses

## Definition of Done

- [ ] \`search_papers\` returns relevant paper summaries
- [ ] \`fetch_article\` extracts readable text from web pages
- [ ] API errors handled gracefully
- [ ] All tests pass

## References

- [arXiv API](https://arxiv.org/help/api)
- [httpx docs](https://www.python-httpx.org/)" \
    "feature,phase-3" \
    "Phase 3 — Research Agent"

create_issue_if_not_exists \
    "feat(agent): implement research_agent for technical paper search" \
    "## Context

The research_agent helps users find and summarize technical content from arXiv
and web articles.

## Tasks

- [ ] Create \`src/adt/agents/research_agent.py\`
- [ ] Inherit from BaseAgent
- [ ] Define system prompt for technical research
- [ ] Declare tools: search_papers, fetch_article
- [ ] Implement \`handle()\` method
- [ ] Write unit tests

## Definition of Done

- [ ] \`adt ask \"recent papers on RAG\"\` returns paper summaries
- [ ] Agent correctly uses research tools
- [ ] All tests pass

## References

- Agent System Prompt Specification in ROADMAP.md" \
    "feature,phase-3" \
    "Phase 3 — Research Agent"

create_issue_if_not_exists \
    "feat(cli): add --agent flag for manual routing" \
    "## Context

The --agent flag allows users to bypass automatic routing and directly specify
which agent to use.

## Tasks

- [ ] Add \`--agent\` option to ask command (choices: repo, project, research)
- [ ] When provided, skip supervisor routing
- [ ] Update help text
- [ ] Write tests

## Definition of Done

- [ ] \`adt ask \"query\" --agent research\` uses research_agent
- [ ] Invalid agent names produce clear errors
- [ ] Help text documents agent choices

## References

- [Typer options](https://typer.tiangolo.com/tutorial/options/)" \
    "feature,phase-3" \
    "Phase 3 — Research Agent"

# ==============================================================================
# PHASE 4 — Project Agent
# ==============================================================================

echo ""
echo "==> Creating Phase 4 issues..."
echo ""

create_issue_if_not_exists \
    "feat(tools): implement project tools with GitHub API" \
    "## Context

Project tools connect to GitHub's project management features — issues,
milestones, and labels.

## Tasks

- [ ] Create \`src/adt/tools/project.py\`
- [ ] Implement \`read_issues(owner, repo, state, labels)\` via GitHub REST API
- [ ] Implement \`read_milestones(owner, repo)\` via GitHub REST API
- [ ] Implement \`read_markdown(path)\` for local markdown files
- [ ] Handle rate limiting with wait-and-retry
- [ ] Support \`GITHUB_TOKEN\` for authenticated requests
- [ ] Register tools for project_agent
- [ ] Write unit tests with mocked API responses

## Definition of Done

- [ ] \`read_issues\` returns formatted issue list
- [ ] \`read_milestones\` returns milestone summary
- [ ] Rate limiting handled gracefully
- [ ] Works with and without authentication
- [ ] All tests pass

## References

- [GitHub REST API - Issues](https://docs.github.com/en/rest/issues/issues)
- [GitHub REST API - Milestones](https://docs.github.com/en/rest/issues/milestones)" \
    "feature,phase-4" \
    "Phase 4 — Project Agent"

create_issue_if_not_exists \
    "feat(agent): implement project_agent for issue and roadmap analysis" \
    "## Context

The project_agent completes the three-agent set, providing project management
insights from GitHub issues, milestones, and local documentation.

## Tasks

- [ ] Create \`src/adt/agents/project_agent.py\`
- [ ] Inherit from BaseAgent
- [ ] Define system prompt for project analysis
- [ ] Declare tools: read_issues, read_milestones, read_markdown
- [ ] Support \`--repo owner/repo\` format
- [ ] Implement \`handle()\` method
- [ ] Write unit tests

## Definition of Done

- [ ] \`adt ask \"summarize open issues\" --repo owner/repo\` works
- [ ] Agent interprets milestone progress
- [ ] Local markdown analysis works
- [ ] All tests pass

## References

- Agent System Prompt Specification in ROADMAP.md" \
    "feature,phase-4" \
    "Phase 4 — Project Agent"

# ==============================================================================
# PHASE 5 — MCP Hardening
# ==============================================================================

echo ""
echo "==> Creating Phase 5 issues..."
echo ""

create_issue_if_not_exists \
    "feat(mcp): implement context ranking by file relevance" \
    "## Context

Sending all files to the LLM wastes tokens. Context ranking scores files by
likely relevance and includes only the most useful ones.

## Tasks

- [ ] Add file relevance scoring (keyword match, file type priority, size penalty, depth penalty)
- [ ] Sort files by score, include top-N within token budget
- [ ] Add \`rank_files(files, query, max_tokens)\` method
- [ ] Write unit tests

## Definition of Done

- [ ] README and entry-point files rank higher than utility files
- [ ] Query keyword matches rank highest
- [ ] Token budget is respected
- [ ] All tests pass

## References

- MCP Hardening phase in ROADMAP.md" \
    "feature,phase-5" \
    "Phase 5 — MCP Hardening"

create_issue_if_not_exists \
    "feat(mcp): implement accurate token budgeting with tiktoken" \
    "## Context

Replace the word-count heuristic with tiktoken for exact token counts.

## Tasks

- [ ] Add \`tiktoken\` to dependencies
- [ ] Replace word-count with tiktoken encoding
- [ ] Define budget allocation: system 20%, context 50%, tools 10%, response 20%
- [ ] Implement \`TokenBudget\` class
- [ ] Add budget reporting in verbose mode
- [ ] Write unit tests

## Definition of Done

- [ ] Token counts are accurate
- [ ] Context always within budget
- [ ] Verbose mode shows allocation breakdown
- [ ] All tests pass

## References

- [tiktoken](https://github.com/openai/tiktoken)" \
    "feature,phase-5" \
    "Phase 5 — MCP Hardening"

create_issue_if_not_exists \
    "feat(logging): implement structured JSON logging" \
    "## Context

Structured logging enables system behavior analysis, debugging, and health monitoring.

## Tasks

- [ ] Create \`src/adt/logging/logger.py\`
- [ ] Implement JSON logger writing to \`~/.adt/logs/adt.log\`
- [ ] Log: timestamp, request_id, query, agent, tools_called, tokens, duration, success
- [ ] Support log levels: DEBUG, INFO, WARNING, ERROR
- [ ] Add \`--log-level\` CLI flag
- [ ] Implement log rotation (max 10MB, keep 5 files)
- [ ] Write unit tests

## Definition of Done

- [ ] Every request generates a structured log entry
- [ ] Log format matches Agent Governance specification
- [ ] Log rotation works
- [ ] All tests pass

## References

- Agent Governance section in ROADMAP.md
- [Python logging](https://docs.python.org/3/library/logging.html)" \
    "feature,phase-5" \
    "Phase 5 — MCP Hardening"

create_issue_if_not_exists \
    "feat(mcp): implement file-based context cache" \
    "## Context

A file-based cache avoids redundant file system scans for repeated queries
against the same repository.

## Tasks

- [ ] Implement cache with key = hash(repo_path + git_commit_hash)
- [ ] Storage in \`~/.adt/cache/\`
- [ ] TTL: 5 minutes (configurable)
- [ ] Invalidate on commit hash change
- [ ] Add \`--no-cache\` CLI flag
- [ ] Write unit tests

## Definition of Done

- [ ] Second query against same repo is faster (cache hit)
- [ ] Cache invalidates on new commits
- [ ] \`--no-cache\` bypasses cache
- [ ] All tests pass

## References

- MCP Hardening phase in ROADMAP.md" \
    "feature,phase-5" \
    "Phase 5 — MCP Hardening"

# ==============================================================================
# PHASE 6 — Advanced Features
# ==============================================================================

echo ""
echo "==> Creating Phase 6 issues..."
echo ""

create_issue_if_not_exists \
    "feat(tools): implement multi-repo support and diff comparison" \
    "## Context

Multi-repo support enables comparison workflows such as fork vs upstream analysis.

## Tasks

- [ ] Allow \`--repo\` to accept multiple paths/URLs
- [ ] Update ContextBuilder to label context by source repo
- [ ] Implement \`compare_repos(repo_a, repo_b)\` tool
- [ ] Register tool for repo_agent
- [ ] Write unit tests

## Definition of Done

- [ ] Multi-repo queries work
- [ ] Comparison output shows differences clearly
- [ ] Context labeled by source
- [ ] All tests pass

## References

- Phase 6 description in ROADMAP.md" \
    "feature,phase-6" \
    "Phase 6 — Advanced Features"

create_issue_if_not_exists \
    "feat(core): implement LLM-based supervisor routing" \
    "## Context

LLM-based routing improves intent classification accuracy for ambiguous queries.

## Tasks

- [ ] Add LLM classification to Supervisor using minimal prompt
- [ ] Keep rule-based as fallback
- [ ] Add \`--routing\` CLI flag: rule | llm
- [ ] Measure and log routing accuracy
- [ ] Write unit tests with mocked LLM

## Definition of Done

- [ ] LLM routing classifies ambiguous queries correctly
- [ ] Fallback works when LLM unavailable
- [ ] Minimal latency added (< 500ms)
- [ ] All tests pass

## References

- Supervisor section in ROADMAP.md" \
    "feature,phase-6" \
    "Phase 6 — Advanced Features"

create_issue_if_not_exists \
    "feat(cli): add configuration file support" \
    "## Context

A TOML config file at ~/.adt/config.toml stores persistent user preferences.

## Tasks

- [ ] Create config loading logic (TOML format)
- [ ] Support: default_model, log_level, cache_ttl, routing_mode
- [ ] Add \`adt config show\` and \`adt config set\` subcommands
- [ ] CLI flags override config values
- [ ] Write unit tests

## Definition of Done

- [ ] Config file loaded on every command
- [ ] \`adt config show\` displays settings
- [ ] \`adt config set\` persists changes
- [ ] CLI flags take precedence
- [ ] All tests pass

## References

- [tomllib docs](https://docs.python.org/3/library/tomllib.html)" \
    "feature,phase-6" \
    "Phase 6 — Advanced Features"

# ==============================================================================
# PHASE 7 — Production Release
# ==============================================================================

echo ""
echo "==> Creating Phase 7 issues..."
echo ""

create_issue_if_not_exists \
    "chore(build): package for PyPI distribution" \
    "## Context

Publishing to PyPI allows anyone to install the tool with pip install.

## Tasks

- [ ] Finalize pyproject.toml metadata
- [ ] Test pip install in fresh virtual environment
- [ ] Build with python -m build
- [ ] Publish to TestPyPI then PyPI
- [ ] Verify global install works

## Definition of Done

- [ ] Package available on PyPI
- [ ] \`pip install agentic-dev-tool\` installs cleanly
- [ ] \`adt --help\` works after install

## References

- [PyPI publishing guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)" \
    "chore,phase-7" \
    "Phase 7 — Production Release"

create_issue_if_not_exists \
    "feat(api): create FastAPI server with /ask endpoint" \
    "## Context

An HTTP API makes the tool accessible to other applications and team members.

## Tasks

- [ ] Create \`src/adt/api/server.py\` with FastAPI
- [ ] Implement POST /ask endpoint
- [ ] Implement GET /health endpoint
- [ ] Add \`adt serve\` CLI subcommand
- [ ] Add \`--port\` option
- [ ] Write API tests

## Definition of Done

- [ ] \`adt serve\` starts HTTP server
- [ ] POST /ask mirrors CLI functionality
- [ ] /health returns status ok
- [ ] API tests pass

## References

- [FastAPI docs](https://fastapi.tiangolo.com/)
- [uvicorn docs](https://www.uvicorn.org/)" \
    "feature,phase-7" \
    "Phase 7 — Production Release"

create_issue_if_not_exists \
    "docs(all): finalize documentation for portfolio" \
    "## Context

Complete documentation is essential for portfolio presentation and future maintenance.

## Tasks

- [ ] Complete README: badges, demo, installation, all commands
- [ ] Write docs/architecture.md
- [ ] Write docs/agents.md
- [ ] Write docs/mcp.md
- [ ] Write docs/contributing.md
- [ ] Audit all public functions for docstrings
- [ ] Record terminal demo with asciinema
- [ ] Add demo GIF to README

## Definition of Done

- [ ] All docs written and linked from README
- [ ] All public functions have docstrings
- [ ] Demo recording embedded in README
- [ ] No broken links

## References

- [asciinema](https://asciinema.org/)
- [Google docstring style](https://google.github.io/styleguide/pyguide.html)" \
    "docs,phase-7,priority:high" \
    "Phase 7 — Production Release"

create_issue_if_not_exists \
    "chore(release): create v1.0.0 production release" \
    "## Context

The v1.0.0 release is the portfolio milestone — the complete, public-facing version.

## Tasks

- [ ] Ensure all Phase 0-7 issues are closed
- [ ] Ensure all milestones are 100% complete
- [ ] Write CHANGELOG.md
- [ ] Create release workflow (.github/workflows/release.yml)
- [ ] Tag v1.0.0 on main
- [ ] Create GitHub release with changelog
- [ ] Verify PyPI package matches release tag
- [ ] Add project to personal portfolio

## Definition of Done

- [ ] v1.0.0 tag exists on main
- [ ] GitHub release published with changelog
- [ ] PyPI package version matches
- [ ] All milestones show 100% completion
- [ ] Project listed in portfolio

## References

- [Semantic Versioning](https://semver.org/)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)" \
    "chore,phase-7" \
    "Phase 7 — Production Release"

# ==============================================================================
# Summary
# ==============================================================================

echo ""
echo "========================================"
echo "==> Issues setup complete!"
echo "========================================"
echo ""
echo "Verify at: https://github.com/$REPO/issues"
echo ""

# Count issues
TOTAL=$(gh issue list --repo "$REPO" --state all --json title -q 'length' 2>/dev/null || echo "?")
echo "Total issues in repository: $TOTAL"
