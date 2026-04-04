# Agentic Dev Tool (adt)

[![CI](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A context-oriented AI assistant CLI built with a simplified Model Context Protocol (MCP). The project is designed for extensibility, real-world engineering use, and professional demonstration.

## Status

**Phase 0 — Project Bootstrap:** repository structure, tooling, and CI are in place. Application features land in later phases (see project planning docs if available locally).

## Quick start (development)

```bash
# Requires Python 3.11 or newer
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
make install
make lint test typecheck
```

Configure API access when you implement LLM-backed commands:

```bash
cp .env.example .env
# Set OPENAI_API_KEY (and optionally GITHUB_TOKEN) in .env
```

## CLI entry point

After install, the `adt` command is available (bootstrap placeholder until Phase 2):

```bash
adt --help
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
