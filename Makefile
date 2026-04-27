.PHONY: setup compile lint test check
VENV_BIN ?= .venv/bin

setup:
	@command -v uv >/dev/null 2>&1 || pip install uv --break-system-packages
	@[ -d .venv ] || uv venv .venv --python 3.13
	. .venv/bin/activate && uv pip install -r requirements.txt

compile:
	$(VENV_BIN)/uv pip compile requirements.in -o requirements.txt

lint:
	$(VENV_BIN)/ruff check --fix
	$(VENV_BIN)/mypy .

test:
	$(VENV_BIN)/python -m pytest . -q

check: lint test