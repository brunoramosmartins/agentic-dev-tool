# Agentic Dev Tool (adt)

[![CI](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A context-oriented AI assistant CLI built with a simplified Model Context Protocol (MCP). The project is designed for extensibility, real-world engineering use, and professional demonstration.

## Status

**Phase 5 — MCP hardening:** Context packing uses **tiktoken** budgets (20/50/10/20 split for system/context/tools/response), **ranked** file selection from the user query, and a **disk cache** for repo tree listings under `~/.adt/cache` (keyed by path + `git rev-parse HEAD`, TTL configurable). **JSON logs** append to `~/.adt/logs/adt.jsonl` (`--log-level`). **`Phase 4`** still applies: local/`owner/repo` `--repo`, GitHub project tools, `GITHUB_TOKEN` / `--token`. See [docs/agents.md](docs/agents.md).

## Installation

Requires **Python 3.10+**.

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

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes, for `ask` | OpenAI API key for chat completions. |
| `GITHUB_TOKEN` | No | GitHub PAT for `read_issues` / `read_milestones` (higher rate limits, private repos). |
| `ADT_LIVE_MODEL` | No | Optional model override for `pytest -m live` (default `gpt-4o-mini`). |
| `ADT_TOKEN_BUDGET` | No | Logical token window for one `ask` turn (default `16384`). |
| `ADT_CACHE_TTL` | No | Repo tree cache TTL in seconds (default `300`). |

## Usage

### Local repository (code analysis)

```bash
adt ask "What does this project do?" --repo .
```

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

- `--repo`, `-r` — **Local directory** (must exist) **or** **`owner/repo`** GitHub slug. Slug form uses `cwd` as the markdown root.
- `--token` — GitHub PAT for this run (overrides `GITHUB_TOKEN` when set).
- `--agent`, `-a` — `repo_agent`, `research_agent`, or `project_agent`.
- `--verbose`, `-v` — debug logging, last token usage, estimated token budget, and a truncated context summary.
- `--log-level` — `DEBUG`, `INFO`, `WARNING`, or `ERROR` for JSON file logging (default `INFO`; `--verbose` forces `DEBUG`).
- `--no-cache` — skip reading/writing the repo tree cache for this run.
- `--model`, `-m` — OpenAI model name (default: `gpt-4o-mini`).

Other commands:

```bash
adt --help
adt ask --help
adt version
adt info
```

### Example session (shape of output)

You will see an **Agent:** line, an **Answer** panel (green text, cyan Markdown for research, magenta Markdown for project), and **Tools used** (e.g. `read_issues`, `read_milestones`, `read_markdown`, `read_repo_tree`). With `--verbose`, extra debug lines follow.

## Development

```bash
make lint      # ruff check
make format    # ruff format
make test      # pytest with coverage (excludes live LLM tests by default)
make typecheck # mypy src/
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
