help:
	cat Makefile

################################################################################

build:
	uv sync
	make reformat
	make lint
	make type_check
	make test
	make accept

lint:
	uv run ruff check --fix .

reformat:
	uv run ruff format .

setup:
	uv sync
	pre-commit install --install-hooks

test:
	uv run pytest -x --cov

type_check:
	uv run mypy tests --ignore-missing-import

################################################################################

accept:
	uv run behave --no-skipped --stop

accept_wip:
	uv run behave --no-skipped --stop --tags=wip

################################################################################

dist:
	uv build --wheel

ship:
	make build
	make dist
	nox -s test_build_from_wheel

################################################################################

.PHONY: \
	accept \
	accept_wip \
	build \
	dist \
	help \
	lint \
	reformat \
	setup \
	ship \
	test \
	type_check
