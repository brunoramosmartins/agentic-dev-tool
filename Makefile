.PHONY: install lint format test typecheck run clean

PYTHON ?= python
PIP ?= $(PYTHON) -m pip

install:
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"
	pre-commit install

lint:
	ruff check .

format:
	ruff format .

test:
	pytest --cov=adt --cov-report=term-missing

typecheck:
	mypy src/

run:
	$(PYTHON) -m adt.cli.app --help

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
