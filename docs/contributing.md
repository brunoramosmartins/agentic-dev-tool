# Contributing

1. Use Python 3.11+ and a virtual environment.
2. Install dev dependencies: `pip install -e ".[dev]"` (or `make install` where `make` is available).
3. Run `ruff check .`, `ruff format .`, `mypy src/`, and `pytest` before opening a PR.
4. Enable pre-commit: `pre-commit install`.

Pull requests should follow the template in `.github/PULL_REQUEST_TEMPLATE.md`.

## GitHub labels, milestones, and issues

Optional automation for maintainers (requires `gh auth login`):

- `scripts/setup_all.sh` — runs `setup_labels.sh`, `setup_milestones.sh`, and `setup_issues.sh` in order.
- `ADT_DELETE_DEFAULT_LABELS=1 ./scripts/setup_labels.sh` — opt-in removal of GitHub’s stock labels before creating the project label set.
