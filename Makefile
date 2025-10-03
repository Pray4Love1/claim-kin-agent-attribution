# Makefile

poetry-download:
	curl -sSL https://install.python-poetry.org | python3 -

install:
	poetry config virtualenvs.in-project true
	poetry install

test:
	PYTHONPATH=. poetry run pytest -c pyproject.toml tests/

pre-commit:
	poetry run pre-commit run --all-files
