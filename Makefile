help:
	cat Makefile

################################################################################
accept:
	behave --no-skipped --stop

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

.PHONY: \
	accept \
	build \
	help \
	lint \
	reformat \
	setup \
	test \
	type_check
