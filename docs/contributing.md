# Contributing

## Local setup

1. Use **Python 3.10+** and a virtual environment.
2. Install dev dependencies: `pip install -e ".[dev]"` (or `make install` where `make` is available).
3. Run **`ruff check .`**, **`ruff format .`**, **`mypy src/`**, and **`pytest`** before opening a PR.
4. Enable pre-commit: `pre-commit install`.

Pull requests should follow the template in [`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md).

## Optional API development

The HTTP API is optional. Install extras:

```bash
pip install -e ".[dev]"
# dev already includes fastapi + uvicorn; or: pip install -e ".[api]"
adt serve --port 8765
```

Open `http://127.0.0.1:8765/docs` for OpenAPI.

## Packaging and PyPI

- **Build locally:** `python -m pip install build && python -m build` (artifacts in `dist/`).
- **Smoke-install wheel:** `pip install dist/*.whl` then `adt version`.
- **TestPyPI (manual):** `python -m twine upload --repository testpypi dist/*` (configure `~/.pypirc` or use `twine` with API token).
- **Production release:** Push tag `v1.0.0` (etc.); [`.github/workflows/release.yml`](../.github/workflows/release.yml) builds and publishes.

### PyPI authentication in CI

Either:

1. **Trusted publishing (recommended):** In PyPI project settings, add a trusted publisher for this GitHub repository and workflow `release.yml`. The workflow uses `permissions: id-token: write` and `pypa/gh-action-pypi-publish`.

2. **API token:** Add repository secret **`PYPI_API_TOKEN`** and extend the publish step with:

   ```yaml
   with:
     password: ${{ secrets.PYPI_API_TOKEN }}
   ```

   (See [PyPI publish action](https://github.com/pypa/gh-action-pypi-publish) docs for the exact inputs your org uses.)

## GitHub labels, milestones, and issues

Optional automation for maintainers (requires `gh auth login`). Scripts live under `scripts/`; re-running is safe and skips existing GitHub entities.

- `scripts/setup_all.sh` — runs `setup_labels.sh`, `setup_milestones.sh`, and `setup_issues.sh` in order.
- `ADT_DELETE_DEFAULT_LABELS=1 ./scripts/setup_labels.sh` — opt-in removal of GitHub’s stock labels before creating the project label set.

## Style

- Prefer focused changes; match existing naming and typing (`mypy --strict`).
- New public functions/classes should have concise **docstrings** (what + non-obvious side effects).
