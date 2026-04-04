# Agentic Dev Tool (`adt`)

[![CI](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agentic-dev-tool.svg)](https://pypi.org/project/agentic-dev-tool/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Portfolio-grade CLI** (and optional **HTTP API**) that routes natural-language questions to **specialized agents**—repository analysis, GitHub project context, and technical research—backed by **OpenAI tool calling** and an **MCP-style** in-process layer: tool **registry**, **JSON Schema** validation, **tiktoken** budgets, ranked context, and disk cache.

---

## Contents

- [Why this project](#why-this-project)
- [Features](#features)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Installation](#installation)
- [Setup checklist (keys, env, secrets)](#setup-checklist-keys-env-secrets)
- [Configuration](#configuration)
- [Usage](#usage)
- [HTTP API (optional)](#http-api-optional)
- [Commands](#commands)
- [Development](#development)
- [Releasing (maintainers: PyPI + GitHub)](#releasing-maintainers-pypi--github)
- [Portfolio checklist](#portfolio-checklist)
- [Documentation](#documentation)
- [License](#license)

---

## Why this project

This repo demonstrates **agentic architecture** without a toy script: a real **Typer** CLI, **Pydantic** schemas, **hybrid routing** (LLM JSON classification + keyword fallback), **multi-repo** sessions, **CI** (Ruff, mypy, pytest, package smoke install), and an **optional FastAPI** surface. It maps to a full **phase roadmap** ([`ROADMAP.md`](ROADMAP.md)) from bootstrap through **v1.0.0** on PyPI.

---

## Features

| Area | What you get |
|------|----------------|
| **Agents** | `repo_agent`, `project_agent`, `research_agent` with tool loops |
| **Routing** | `HybridSupervisor`: cheap LLM JSON intent + rule fallback |
| **Repos** | Multi `--repo`, `compare_repos`, tree cache, ranked files |
| **GitHub** | Issues/milestones via API; optional PAT for rate limits |
| **Research** | arXiv + HTTP fetch tools |
| **Config** | `~/.adt/config.toml` + `adt config` |
| **API** | `adt serve` — FastAPI `/healthz`, `/ask` ([`[api]`](https://pypi.org/project/agentic-dev-tool/) extra) |

---

## Architecture

High-level data flow from terminal or HTTP into one shared pipeline (`adt.ask_session.run_ask`), then the runner, tools, and model.

```mermaid
flowchart TB
  subgraph entry["Entry"]
    CLI["Typer CLI<br/>adt ask · config · serve"]
    HTTP["FastAPI optional<br/>POST /ask · GET /healthz"]
  end

  subgraph orch["Orchestration"]
    ASK["ask_session.run_ask"]
    BOOT["bootstrap.build_runner"]
    HYB["HybridSupervisor<br/>LLM JSON + keyword rules"]
    RUN["Runner<br/>chat + tool loop · budgets"]
  end

  subgraph mcp["MCP-style layer"]
    REG["ToolRegistry"]
    EXE["ExecutionController"]
    CTX["ContextBuilder<br/>ranking · tiktoken · cache"]
  end

  subgraph agents["Agents"]
    RA["repo_agent"]
    PA["project_agent"]
    RE["research_agent"]
  end

  LLM["LLMClient<br/>OpenAI"]

  CLI --> ASK
  HTTP --> ASK
  ASK --> BOOT
  BOOT --> HYB
  BOOT --> RUN
  BOOT --> REG
  BOOT --> CTX
  HYB --> RUN
  RUN --> RA
  RUN --> PA
  RUN --> RE
  RUN --> LLM
  RUN --> EXE
  EXE --> REG
  CTX --> RUN
```

**Narrative:** the user’s query and repo hints become a `QueryRequest`; the supervisor picks an agent; `ContextBuilder` packs bounded context; the `Runner` chats with the model, executes **tool calls** through the registry/executor, and returns an `AgentResponse` (answer, tools used, routing metadata). The CLI renders **Rich** panels; the API returns JSON.

Deeper design notes: [`docs/architecture.md`](docs/architecture.md) · tool contracts: [`docs/mcp.md`](docs/mcp.md) · agents/prompts: [`docs/agents.md`](docs/agents.md).

---

## Quick start

```bash
pip install agentic-dev-tool
export OPENAI_API_KEY="sk-..."   # Windows PowerShell: $env:OPENAI_API_KEY="sk-..."
adt ask "What does this codebase do?" --repo .
```

Optional GitHub-backed questions (better with a token):

```bash
export GITHUB_TOKEN="ghp_..."    # fine-grained or classic PAT with repo read
adt ask "Summarize open issues" --repo owner/repo
```

---

## Installation

Requires **Python 3.10+**.

### From PyPI

```bash
pip install agentic-dev-tool
adt version
```

Optional HTTP API:

```bash
pip install "agentic-dev-tool[api]"
adt serve --port 8765
# Docs: http://127.0.0.1:8765/docs
```

### From source (contributors)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install                 # optional
```

With Make (Unix-like):

```bash
make install
```

---

## Setup checklist (keys, env, secrets)

Use this when polishing the project for **local use**, **CI**, and **publishing**.

### 1. OpenAI API key (required for `adt ask` and `adt serve`)

1. Create a key in the [OpenAI API platform](https://platform.openai.com/api-keys) (billing enabled as per your account).
2. **Never commit keys.** Keep them out of git; `.env` is gitignored if you copy from [`.env.example`](.env.example).
3. **Expose the key to the shell** before running `adt`:
   - **macOS / Linux:** `export OPENAI_API_KEY="sk-..."`
   - **Windows CMD:** `set OPENAI_API_KEY=sk-...`
   - **Windows PowerShell:** `$env:OPENAI_API_KEY="sk-..."`
4. **Optional:** put `OPENAI_API_KEY=...` in `.env` and load it with [direnv](https://direnv.net/), your IDE’s env loader, or manual `source`—the CLI does not auto-read `.env`; the process must see the variable.
5. **GitHub Actions CI** in this repo **does not** use `OPENAI_API_KEY` (tests mock the API). You **do not** add this secret to GitHub for the default CI workflow.

### 2. GitHub token (optional, for `project_agent`)

1. Create a [Personal Access Token](https://github.com/settings/tokens) with read access to the repos you query (classic `repo` scope for private repos, or fine-grained “Contents/Issues read” as appropriate).
2. Set `GITHUB_TOKEN` in the environment, or pass `--token` once on the CLI.
3. Without a token, anonymous GitHub API limits apply (~60 requests/hour per IP).

### 3. Persistent CLI settings

1. Run `adt config show` — creates/uses **`~/.adt/config.toml`**.
2. Override file defaults with `ADT_*` variables (see table below) when useful for CI or shells.

### 4. Publishing to PyPI from GitHub (maintainers only)

The workflow [`.github/workflows/release.yml`](.github/workflows/release.yml) runs on tags `v*`.

Pick **one** authentication method:

| Method | What you do |
|--------|-------------|
| **Trusted publishing (recommended)** | In [pypi.org](https://pypi.org) → your project → **Publishing** → add a **trusted publisher** pointing at this GitHub repo and the `Release` workflow. The workflow already sets `id-token: write` for OIDC. Leave `PYPI_API_TOKEN` unset. |
| **API token** | On PyPI, create an API token. In GitHub: **Settings → Secrets and variables → Actions → New repository secret** → name **`PYPI_API_TOKEN`**, value = the token. The publish action uses it as the password. |

After the first successful publish, verify: `pip install agentic-dev-tool` and `adt version`.

### 5. Tag and GitHub Release

1. Merge release work to `main` with `version = "1.0.0"` (or next semver) in [`pyproject.toml`](pyproject.toml) and an entry in [`CHANGELOG.md`](CHANGELOG.md).
2. Create an annotated tag: `git tag -a v1.0.0 -m "Release v1.0.0"` then `git push origin v1.0.0`.
3. The **Release** workflow builds wheels, publishes to PyPI, and creates a GitHub Release (with generated release notes). You may edit the release description to paste the CHANGELOG section.

---

## Configuration

Copy the template and fill values locally (do not commit `.env`):

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes, for `ask` / `serve` | OpenAI API key. |
| `GITHUB_TOKEN` | No | PAT for `read_issues` / `read_milestones`. |
| `ADT_LIVE_MODEL` | No | Model for `pytest -m live` (default `gpt-4o-mini`). |
| `ADT_TOKEN_BUDGET` | No | Logical token window per ask (default `16384`). |
| `ADT_CACHE_TTL` | No | Tree cache TTL in seconds (default `300`). |
| `ADT_DEFAULT_MODEL` | No | Overrides `[adt] default_model` in config. |
| `ADT_LOG_LEVEL` | No | Overrides config log level for file logging. |
| `ADT_USE_LLM_ROUTING` | No | `0` / `1` — LLM intent routing. |
| `ADT_ROUTING_MODEL` | No | Model for routing JSON call. |
| `ADT_MAX_TOOL_ITERATIONS` | No | Max LLM/tool rounds per agent step. |

`adt config show` / `adt config set` manage **`~/.adt/config.toml`**. CLI flags and `ADT_*` override file defaults where documented in code.

---

## Usage

### Local repository

```bash
adt ask "What does this project do?" --repo .
```

### Multi-repository

```bash
adt ask "Compare dependency files in these two trees" --repo ./my-fork --repo ../upstream
```

Checkouts get session ids (`r0`, `r1`, …). Use **`compare_repos`** for a structured diff.

### GitHub project (`owner/repo`)

If `--repo` is a slug like `octocat/Hello-World` and that path is not a local folder, the **current working directory** is the markdown root for `read_markdown`, and the slug sets the default GitHub target:

```bash
cd ~/my-clone
adt ask "Summarize open issues" --repo octocat/Hello-World
adt ask "What milestones are open?" --repo myorg/my-repo --token ghp_xxx
```

### Research

```bash
adt ask "Recent papers on retrieval augmented generation" --repo .
```

### Force an agent

```bash
adt ask "Explain src layout" --repo . --agent repo_agent
adt ask "List issues" --repo myorg/repo --agent project_agent
```

### Common flags

- `--repo`, `-r` — Repeatable: existing directory or `owner/repo` slug.
- `--token` — GitHub PAT for this run (overrides `GITHUB_TOKEN`).
- `--agent`, `-a` — `repo_agent`, `research_agent`, or `project_agent`.
- `--verbose`, `-v` — Debug logging, token usage, budget hint, context snippet.
- `--log-level` — `DEBUG` … `ERROR` for JSON file logs under `~/.adt/logs/`.
- `--no-cache` — Skip repo tree cache.
- `--model`, `-m` — Model override (default from config or `gpt-4o-mini`).

---

## HTTP API (optional)

Install `[api]`, then:

```bash
adt serve --host 127.0.0.1 --port 8765
```

| Endpoint | Purpose |
|----------|---------|
| `GET /healthz` | Liveness JSON (`status`, `version`). |
| `POST /ask` | Body: `query`, optional `repo` (list), `github_token`, `agent`, `no_cache`, `model`. Same pipeline as CLI; **`OPENAI_API_KEY` must be set in the server environment**. |

---

## Commands

| Command | Purpose |
|---------|---------|
| `adt ask …` | Main agent loop. |
| `adt serve` | FastAPI + uvicorn (`[api]`). |
| `adt config show` / `path` / `set` | `~/.adt/config.toml`. |
| `adt version` | Package version. |
| `adt info` | Short feature summary. |

```bash
adt --help && adt ask --help && adt serve --help
```

---

## Development

```bash
make lint       # ruff check
make format     # ruff format
make test       # pytest + coverage (excludes @pytest.mark.live)
make typecheck  # mypy src/
python -m build # sdist + wheel → dist/  (needs: pip install build)
```

Live model tests (manual / optional CI job you add yourself):

```bash
export OPENAI_API_KEY="sk-..."
pytest -m live
```

---

## Releasing (maintainers: PyPI + GitHub)

1. Bump **`pyproject.toml`** version and **`CHANGELOG.md`**.
2. Merge to **`main`**.
3. Tag **`vX.Y.Z`** and push the tag → **`Release`** workflow ([`release.yml`](.github/workflows/release.yml)).
4. Configure PyPI **trusted publisher** or **`PYPI_API_TOKEN`** (see [Setup checklist §4](#4-publishing-to-pypi-from-github-maintainers-only)).

Full contributor notes: [`docs/contributing.md`](docs/contributing.md).

---

## Portfolio checklist

Aligned with **Phase 7** / [`docs/portfolio.md`](docs/portfolio.md):

- [ ] Record a **terminal demo** ([asciinema](https://asciinema.org/) or similar): `adt ask`, multi-repo `--repo`, `adt config show`, optional `curl` to `/ask`.
- [ ] **Embed or link** the demo in this README (replace the placeholder below).
- [ ] Add a **one-paragraph** project card on your personal site with links to GitHub, PyPI, and `docs/architecture.md`.
- [ ] Optional: short **article** (blog/LinkedIn)—problem, architecture, trade-offs.
- [ ] Close or archive **GitHub milestones/issues** when you consider the roadmap complete.

**Demo (placeholder — add your recording URL):** *Coming soon: asciinema / GIF link.*

---

## Documentation

| Doc | Topic |
|-----|--------|
| [`ROADMAP.md`](ROADMAP.md) | Phases, milestones, conventions |
| [`docs/architecture.md`](docs/architecture.md) | Design decisions, module map |
| [`docs/mcp.md`](docs/mcp.md) | Tool registry, context, execution |
| [`docs/agents.md`](docs/agents.md) | Agents and prompts |
| [`docs/contributing.md`](docs/contributing.md) | PRs, packaging, PyPI |
| [`CHANGELOG.md`](CHANGELOG.md) | Release history |

---

## License

MIT — see [`LICENSE`](LICENSE).
