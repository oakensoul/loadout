.PHONY: lint format test check-all

lint:
	ruff check .
	ruff format --check .
	mypy loadout

format:
	ruff check --fix .
	ruff format .

test:
	pytest

check-all: lint test
