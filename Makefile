.PHONY: setup fixture all download build validate export excel reports tableau dashboard readme check-readme links lint typecheck test clean

setup:
	uv sync --extra dev

# Hand-calculated fixture pipeline. No download; output goes to build/fixture.
fixture:
	uv run python -m medicare_claims --profile fixture build
	uv run python -m medicare_claims --profile fixture validate
	uv run python -m medicare_claims --profile fixture export
	uv run python -m medicare_claims --profile fixture excel
	uv run python -m medicare_claims --profile fixture reports
	uv run python -m medicare_claims --profile fixture tableau
	uv run python -m medicare_claims --profile fixture dashboard

# Real CMS sample 1: download and verify, build, validate, export, Excel, reports, Tableau extracts, dashboard.
all:
	uv run python -m medicare_claims all

download:
	uv run python -m medicare_claims download

build:
	uv run python -m medicare_claims build

validate:
	uv run python -m medicare_claims validate

export:
	uv run python -m medicare_claims export

excel:
	uv run python -m medicare_claims excel

reports:
	uv run python -m medicare_claims reports

tableau:
	uv run python -m medicare_claims tableau

dashboard:
	uv run python -m medicare_claims dashboard

readme:
	uv run python -m medicare_claims readme

check-readme:
	uv run python -m medicare_claims readme --check

links:
	uv run python scripts/check_official_links.py

lint:
	uv run ruff check src tests scripts

typecheck:
	uv run mypy

test: lint typecheck
	uv run pytest --cov=medicare_claims --cov-report=term-missing:skip-covered

clean:
	rm -rf data/warehouse build exports data/interim
