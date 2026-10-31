PYTHON ?= python3
export PYTHONPATH := src
export LOKY_MAX_CPU_COUNT := 2
.PHONY: all import prepare evaluate forecast check test lint ci-docker
all:
	$(PYTHON) -m national_selection.cli all
import:
	$(PYTHON) -m national_selection.cli import
prepare:
	$(PYTHON) -m national_selection.cli prepare
evaluate:
	$(PYTHON) -m national_selection.cli evaluate
forecast:
	$(PYTHON) -m national_selection.cli forecast
lint:
	ruff check src tests
	ruff format --check src tests
test:
	$(PYTHON) -m pytest -q
check: lint test
ci-docker:
	docker run --rm -v "$(CURDIR):/work" -w /work python:3.12-slim sh -c 'pip install -e ".[dev]" && ruff check src tests && ruff format --check src tests && python -m pytest -q'
