help:
	cat Makefile

################################################################################
accept:
	poetry run behave --no-skipped --stop

accept_wip:
	poetry run behave --no-skipped --stop --tags=wip

build:
	poetry install
	make reformat
	make lint
	make type_check
	make test
	make accept

lint:
	poetry run flake8 src tests

reformat:
	poetry run black src tests

setup:
	pre-commit install --install-hooks
	poetry install

test:
	poetry run pytest -x --cov

type_check:
	poetry run mypy src tests --ignore-missing-import

################################################################################

dist:
	poetry build --format wheel

ship:
	make build
	nox -s test_build_from_wheel

################################################################################

.PHONY: \
	accept \
	build \
	dist \
	help \
	lint \
	reformat \
	setup \
	ship \
	test \
	type_check
