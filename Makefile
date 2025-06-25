help:
	cat Makefile

################################################################################

build:
	uv sync
	make reformat
	make lint
	make type_check
	make test

lint:
	uv run ruff check --fix .

reformat:
	uv run ruff format .

setup:
	pre-commit install --install-hooks
	uv sync

test:
	uv run pytest -x --cov

type_check:
	uv run mypy tests --ignore-missing-import

################################################################################

dist:
	uv build --wheel

ship:
	make build
	make dist
	nox -s test_build_from_wheel

################################################################################

.PHONY: \
	build \
	dist \
	help \
	lint \
	reformat \
	setup \
	ship \
	test \
	type_check
