# Agentic Dev Tool (`adt`)

[![CI](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agentic-dev-tool.svg)](https://pypi.org/project/agentic-dev-tool/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://brunoramosmartins.github.io/agentic-dev-tool)

A **production-grade CLI and HTTP API** that turns natural-language questions into actionable answers by routing them to **specialized AI agents** — repository analysis, GitHub project context, and technical research — powered by **OpenAI tool calling** and an **MCP-style** orchestration layer.

<p align="center">
  <img src="docs/assets/demo.gif" alt="adt ask demo" width="800">
</p>

---

## Highlights

- **Multi-agent routing** — A hybrid supervisor (LLM intent classifier + keyword fallback) picks the best agent for each query
- **Tool-calling loop** — Agents invoke registered tools (file reading, code search, GitHub API, arXiv) through a validated JSON Schema pipeline with token budgets
- **Supervised learning mode** — Step-by-step teaching with `beginner` / `intermediate` / `advanced` difficulty levels, session persistence, and structured code review
- **Learning analytics** — Track progress over time with `adt stats`, export to CSV/JSON/Markdown, or generate a standalone HTML dashboard
- **Request tracing** — `--trace` reveals the full chain: routing → context build → LLM/tool calls → token + USD cost estimates
- **Interactive REPL** — `adt shell` opens a persistent terminal with history, autocomplete, slash commands, and supervised practice — all in one session
- **Internationalization** — Full `en` and `pt_BR` locale support via `ADT_LANG` or `adt config set lang pt_BR`
- **Extensible** — Community plugins (skills + tools) loaded from `~/.adt/plugins/`, plus an optional FastAPI HTTP surface

---

## Quick Start

```bash
pip install agentic-dev-tool
export OPENAI_API_KEY="sk-..."
adt ask "What does this codebase do?" --repo .
```

---

## Installation

Requires **Python 3.10+**.

```bash
# Core CLI
pip install agentic-dev-tool

# With HTTP API server
pip install "agentic-dev-tool[api]"

# With interactive REPL
pip install "agentic-dev-tool[shell]"

# From source (contributors)
pip install -e ".[dev]"
```

---

## Architecture

```
User query → Hybrid Supervisor → Agent (repo / project / research)
                                      ↓
                              Tool Registry + Executor
                                      ↓
                              LLM (OpenAI) ← token budgets + context ranking
                                      ↓
                              AgentResponse → Rich panel / JSON API
```

The supervisor picks an agent; `ContextBuilder` packs bounded, ranked context; the `Runner` drives the LLM/tool loop through a validated registry; tracing and analytics wrap the pipeline. In supervised mode, the skill system overrides prompts with teaching heuristics and difficulty directives.

Full architecture docs: [`docs/reference/architecture.md`](docs/reference/architecture.md)

---

## Commands

| Command | What it does |
|---------|-------------|
| `adt ask "..."` | Route a question to the best agent. Supports `--repo`, `--agent`, `--mode supervised`, `--level`, `--trace`, `--yes`, `--no-stream` |
| `adt review <file>` | Structured code review with issues, strengths, next step, and verdict |
| `adt stats` | Learning analytics panel. Flags: `--last N`, `--export csv\|json\|md`, `--html <dir>`, `--classifier keyword\|embedding` |
| `adt shell` | Interactive REPL with history, autocomplete, and slash commands (`/help`, `/trace`, `/session`, `/start`, `/submit`, etc.) |
| `adt guide` | Static quick-reference cheat sheet (no API key needed) |
| `adt config show\|set\|path` | View or edit `~/.adt/config.toml` |
| `adt session show\|list\|clear\|export` | Manage supervised sessions |
| `adt runs list\|show\|delete` | Manage interrupted run snapshots |
| `adt plugins list\|validate` | Manage community plugins |
| `adt serve` | FastAPI HTTP API (`[api]` extra). Endpoints: `/ask`, `/review`, `/stats`, `/sessions`, `/healthz` |
| `adt version` | Print installed version |

---

## Configuration

Settings live in `~/.adt/config.toml` and can be overridden by `ADT_*` environment variables or CLI flags.

| Key | Default | Description |
|-----|---------|-------------|
| `default_model` | `gpt-4o-mini` | OpenAI chat model |
| `log_level` | `INFO` | File log level |
| `use_llm_routing` | `true` | Enable LLM intent routing |
| `max_tool_iterations` | `5` | Max LLM/tool rounds per agent |
| `token_budget` | `none` | Logical token window |
| `cost_confirm_threshold` | `0.05` | USD threshold for cost confirmation prompt |
| `lang` | `en` | UI locale (`en`, `pt_BR`) |
| `cache_ttl_seconds` | `300` | Repo tree cache TTL |

```bash
adt config set default_model gpt-4o
adt config set lang pt_BR
adt config show
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes (for `ask`/`serve`) | OpenAI API key |
| `GITHUB_TOKEN` | No | GitHub PAT for project_agent |
| `ADT_LANG` | No | UI locale override |
| `ADT_NO_PROGRESS` | No | `1` to disable spinners/progress bars |
| `ADT_NO_CONFIRM` | No | `1` to skip cost confirmation prompts |

---

## Development

```bash
make lint       # ruff check
make format     # ruff format
make test       # pytest + coverage
make typecheck  # mypy src/
```

---

## Documentation

Full documentation is available at [brunoramosmartins.github.io/agentic-dev-tool](https://brunoramosmartins.github.io/agentic-dev-tool), covering installation, guides (supervised mode, tracing, analytics, plugins), architecture reference, and API docs.

| Resource | Link |
|----------|------|
| MkDocs site | [brunoramosmartins.github.io/agentic-dev-tool](https://brunoramosmartins.github.io/agentic-dev-tool) |
| Architecture | [`docs/reference/architecture.md`](docs/reference/architecture.md) |
| Roadmap | [`ROADMAP.md`](ROADMAP.md) |
| Changelog | [`CHANGELOG.md`](CHANGELOG.md) |

---

## License

MIT — see [`LICENSE`](LICENSE).
