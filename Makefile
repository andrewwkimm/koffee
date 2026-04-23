help:
	cat Makefile

################################################################################

ci:
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
	uv sync
	uv run pre-commit install --install-hooks

test:
	uv run pytest -x --cov

type_check:
	uv run ty check tests

################################################################################

accept:
	uv run behave --no-skipped --stop

accept_wip:
	uv run behave --no-skipped --stop --tags=wip

################################################################################

docs:
	mkdir -p scratch/tmp/site
	uv run mkdocs build --clean -d scratch/tmp/site

serve:
	uv run mkdocs serve

################################################################################

dist:
	uv build --wheel

build:
	make ci
	make dist
	pip install --force-reinstall dist/*.whl
	koffee --help

ship:
	make build
	make accept
	make dist
	nox -s test_build_from_wheel

################################################################################

.PHONY: \
	accept \
	accept_wip \
	build \
	docs \
	dist \
	help \
	lint \
	reformat \
	serve \
	setup \
	ship \
	test \
	type_check
