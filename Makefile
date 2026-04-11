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
	uv run properdocs build -f properdocs.yml --clean

serve:
	uv run properdocs serve -f properdocs.yml --livereload -o

################################################################################

dist:
	uv build --wheel

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
	dist \
	help \
	lint \
	reformat \
	setup \
	ship \
	test \
	type_check
