.PHONY: lint test build check

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/
	mypy src/

test:
	pytest --cov=book_match --cov-report=term-missing

build:
	python -m build
	twine check dist/*

## Run all CI checks locally before pushing
check: lint test build
