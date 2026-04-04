# Agentic Dev Tool (adt)

[![CI](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A context-oriented AI assistant CLI built with a simplified Model Context Protocol (MCP). The project is designed for extensibility, real-world engineering use, and professional demonstration.

## Status

**Phase 2 — MVP (Repo Agent):** The `adt ask` command analyzes a local repository (directory tree, file reads, regex search) and answers questions via an LLM. Supervisor routing, tool registry, and Rich-formatted output are wired end-to-end.

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

Copy the example env file and set your OpenAI API key:

```bash
cp .env.example .env
# Edit .env: OPENAI_API_KEY=...
```

`adt` reads `OPENAI_API_KEY` from the process environment. Load `.env` with your shell or a tool such as [direnv](https://direnv.net/) if you use one.

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes, for `ask` | OpenAI API key for chat completions. |
| `GITHUB_TOKEN` | No | Reserved for future GitHub-backed agents (see `.env.example`). |

## Usage

### Ask about a repository

```bash
adt ask "What does this project do?" --repo .
```

Options:

- `--repo`, `-r` — repository root (default: current directory; must exist).
- `--verbose`, `-v` — debug logging, last token usage, and a truncated context summary.
- `--model`, `-m` — OpenAI model name (default: `gpt-4o-mini`).

Other commands:

```bash
adt --help
adt ask --help
adt version
adt info
```

### Example session (shape of output)

With a valid key, you will see a green **Answer** panel (Rich), then a dim line listing **Tools used** (for example `read_repo_tree`, `read_file`, `search_code`). With `--verbose`, extra debug lines appear after that.

## Development

```bash
make lint      # ruff check
make format    # ruff format
make test      # pytest with coverage (excludes live LLM tests by default)
make typecheck # mypy src/
```

Default pytest runs exclude tests marked `@pytest.mark.live` (real API calls). To exercise a live OpenAI call locally:

```bash
export OPENAI_API_KEY=...   # Windows PowerShell: $env:OPENAI_API_KEY="..."
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
