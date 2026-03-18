.PHONY: lint test check-all

lint:
	ruff check .
	mypy loadout

test:
	pytest

check-all: lint test
