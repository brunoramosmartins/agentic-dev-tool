# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-04-03

### Added

- **PyPI distribution** as `agentic-dev-tool` with stable metadata and `hatchling` builds.
- **GitHub Actions** `release.yml`: on `v*` tags, build wheels/sdists, publish to PyPI (trusted publishing or token), create a GitHub Release with generated notes.
- **Optional HTTP API** (`pip install 'agentic-dev-tool[api]'`): FastAPI app with `GET /healthz`, `POST /ask`, OpenAPI at `/docs`; **`adt serve`** CLI to run **uvicorn**.
- **Shared ask pipeline** in `adt.ask_session.run_ask` for CLI and API.
- **Documentation:** `docs/architecture.md`, `docs/mcp.md`, expanded `docs/contributing.md` and `docs/agents.md` (prompt notes), `docs/portfolio.md` (external portfolio checklist).

### Changed

- **Development Status** classifier set to **Production/Stable**; version **1.0.0**.
- README oriented toward **install from PyPI**, badges, command reference, architecture links, and demo placeholder.

### Notes

- Publishing to PyPI requires a [trusted publisher](https://docs.pypi.org/trusted-publishers/) or `PYPI_API_TOKEN` secret; see `docs/contributing.md`.

[1.0.0]: https://github.com/brunoramosmartins/agentic-dev-tool/releases/tag/v1.0.0
