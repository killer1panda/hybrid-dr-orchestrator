.PHONY: setup orch-test orch-lint orch-format run-dry

VENV := ./venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
PYTEST := $(VENV)/bin/pytest

setup:
	@if [ ! -d $(VENV) ]; then \
		echo "Creating virtualenv with uv..."; \
		uv venv $(VENV) --python 3.11 || python3 -m venv $(VENV); \
	fi
	@echo "Installing dependencies..."
	@if command -v uv >/dev/null 2>&1; then \
		uv pip install -r requirements.txt --python $(PYTHON); \
	else \
		$(PIP) install -r requirements.txt; \
	fi

orch-format:
	$(RUFF) format src tests
	$(RUFF) check --fix src tests

orch-lint:
	$(RUFF) check src tests
	$(RUFF) format --check src tests
	$(MYPY) --strict src tests

orch-test:
	$(PYTEST) -v tests
	$(MYPY) --strict src tests

run-dry:
	PYTHONPATH=src $(PYTHON) -m hybrid_dr.cli drill --dry-run

dashboard:
	PYTHONPATH=src $(PYTHON) -m hybrid_dr.cli dashboard --host 0.0.0.0 --port 8500
