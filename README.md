# Agentic Dev Tool (adt)

[![CI](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agentic-dev-tool.svg)](https://pypi.org/project/agentic-dev-tool/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Context-oriented **CLI** (and optional **HTTP API**) for working with repositories, GitHub project data, and research sources—using OpenAI tool calling and an **MCP-style** in-process tool layer (registry, JSON Schema, bounded context packing with **tiktoken**).

## Demo

Record a terminal session (e.g. [asciinema](https://asciinema.org/)) and link it here or in your portfolio. Suggested flow: `adt ask "…" --repo .`, then multi-repo `--repo a --repo b`, then `adt config show`. See [docs/portfolio.md](docs/portfolio.md).

## Status (v1.0.0)

**Production release** on PyPI as **`agentic-dev-tool`**. Features: multi-repo **`--repo`**, **`compare_repos`**, hybrid **LLM + keyword routing**, **`~/.adt/config.toml`**, optional **`agent_chain`**, JSON logs, tree cache, and optional **`adt serve`** (FastAPI). Documentation: [docs/architecture.md](docs/architecture.md), [docs/mcp.md](docs/mcp.md), [docs/agents.md](docs/agents.md), [CHANGELOG.md](CHANGELOG.md).

## Installation

Requires **Python 3.10+**.

### From PyPI (users)

```bash
pip install agentic-dev-tool
adt version
```

Optional HTTP API:

```bash
pip install "agentic-dev-tool[api]"
adt serve --port 8765
# OpenAPI: http://127.0.0.1:8765/docs
```

### From source (contributors)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
# optional: pre-commit install
```

Or with Make (Unix-like shell):

```bash
make install
```

## Configuration

Copy the example env file and set your keys:

```bash
cp .env.example .env
# Edit .env: OPENAI_API_KEY=..., optional GITHUB_TOKEN=...
```

`adt` reads `OPENAI_API_KEY` from the process environment. Load `.env` with your shell or a tool such as [direnv](https://direnv.net/) if you use one.

Persistent CLI defaults live in **`~/.adt/config.toml`** (see `adt config show`). Environment variables override file values when set.

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes, for `ask` | OpenAI API key for chat completions. |
| `GITHUB_TOKEN` | No | GitHub PAT for `read_issues` / `read_milestones` (higher rate limits, private repos). |
| `ADT_LIVE_MODEL` | No | Optional model override for `pytest -m live` (default `gpt-4o-mini`). |
| `ADT_TOKEN_BUDGET` | No | Logical token window for one `ask` turn (default `16384`). |
| `ADT_CACHE_TTL` | No | Repo tree cache TTL in seconds (default `300`). |
| `ADT_DEFAULT_MODEL` | No | Overrides `[adt] default_model` in config. |
| `ADT_LOG_LEVEL` | No | Overrides config log level for file logging. |
| `ADT_USE_LLM_ROUTING` | No | `0`/`1` — disable or enable LLM intent routing. |
| `ADT_ROUTING_MODEL` | No | Model name for the routing JSON call. |
| `ADT_MAX_TOOL_ITERATIONS` | No | Max LLM/tool rounds per agent step. |

## Usage

### Local repository (code analysis)

```bash
adt ask "What does this project do?" --repo .
```

### Multi-repository (e.g. fork vs upstream)

```bash
adt ask "Compare dependency files in these two trees" --repo ./my-fork --repo ../upstream
```

Each checkout gets a session id (`r0`, `r1`, …). Tools default to `r0` unless you pass **`repo_key`**. Use **`compare_repos`** for a structured tree/manifest diff.

### GitHub project (`owner/repo`)

If `--repo` is a slug like `octocat/Hello-World` (and that path is **not** an existing folder), the CLI uses the **current working directory** as the **markdown root** for `read_markdown`, and sets the **default GitHub** target for the session context:

```bash
cd ~/my-clone   # optional: where ROADMAP.md / README.md live
adt ask "Summarize open issues" --repo octocat/Hello-World
adt ask "What milestones are open?" --repo myorg/my-repo --token ghp_xxx
```

Without a token, unauthenticated calls are limited to about **60 requests/hour** per IP; the tools return a clear message when GitHub responds with **403** rate-limit errors.

### Research (arXiv / web)

```bash
adt ask "Recent papers on retrieval augmented generation" --repo .
```

### Force a specific agent

```bash
adt ask "Explain src layout" --repo . --agent repo_agent
adt ask "List issues" --repo myorg/repo --agent project_agent
```

### Options

- `--repo`, `-r` — Repeatable. **Local directory** (must exist) **or** **`owner/repo`** slug. Slug form uses `cwd` as the markdown root for the first slug.
- `--token` — GitHub PAT for this run (overrides `GITHUB_TOKEN` when set).
- `--agent`, `-a` — `repo_agent`, `research_agent`, or `project_agent` (skips routing and **`agent_chain`**).
- `--verbose`, `-v` — debug logging, last token usage, estimated token budget, and a truncated context summary.
- `--log-level` — `DEBUG`, `INFO`, `WARNING`, or `ERROR` for JSON file logging (default from config; `--verbose` forces `DEBUG`).
- `--no-cache` — skip reading/writing the repo tree cache for this run.
- `--model`, `-m` — OpenAI model (default from **`~/.adt/config.toml`** or `gpt-4o-mini`).

### HTTP API (optional)

With `[api]` installed, **`adt serve`** binds to **127.0.0.1:8765** by default:

- **`GET /healthz`** — liveness JSON (`status`, `version`).
- **`POST /ask`** — JSON body: `query`, optional `repo` (list), `github_token`, `agent`, `no_cache`, `model`. Same orchestration as **`adt ask`**; requires **`OPENAI_API_KEY`** in the server environment.

### Command summary

| Command | Purpose |
|--------|---------|
| `adt ask …` | Main agent loop (routing, tools, answer). |
| `adt serve` | Start FastAPI + uvicorn (`[api]` extra). |
| `adt config show` / `path` / `set` | Manage `~/.adt/config.toml`. |
| `adt version` | Package version. |
| `adt info` | Short feature blurb. |

```bash
adt --help
adt ask --help
adt serve --help
adt config show
adt config set default_model gpt-4o-mini
adt version
adt info
```

## Architecture (overview)

```text
CLI / HTTP
    → ask_session.run_ask
    → build_runner (tools + HybridSupervisor + LLMClient + ContextBuilder)
    → Runner (budget, context, chat + tool loop)
    → AgentResponse
```

Details: [docs/architecture.md](docs/architecture.md). MCP-style tools: [docs/mcp.md](docs/mcp.md).

### Example session (shape of output)

You will see an **Agent:** line, an **Answer** panel (green text, cyan Markdown for research, magenta Markdown for project), and **Tools used** (e.g. `read_issues`, `read_milestones`, `read_markdown`, `read_repo_tree`). With `--verbose`, extra debug lines follow.

## Development

```bash
make lint      # ruff check
make format    # ruff format
make test      # pytest with coverage (excludes live LLM tests by default)
make typecheck # mypy src/
python -m build   # sdist + wheel into dist/ (requires `pip install build`)
```

Default pytest runs exclude tests marked `@pytest.mark.live`. For live OpenAI (and real GitHub when tests call the network):

```bash
export OPENAI_API_KEY=...
pytest -m live
```

## GitHub automation (optional)

If you use the [GitHub CLI](https://cli.github.com/) (`gh`) and want to provision **labels**, **milestones**, and **issues** (Phases 0–7) in one go, run from the repository root (Git Bash, WSL, or macOS/Linux):

```bash
chmod +x scripts/*.sh
./scripts/setup_all.sh
```

- Scripts live only under `scripts/` and are **idempotent** (safe to re-run).
- To remove GitHub’s default labels before creating the project set, run `setup_labels.sh` with `ADT_DELETE_DEFAULT_LABELS=1` (optional; can affect existing issues).

## License

MIT — see [LICENSE](LICENSE).
