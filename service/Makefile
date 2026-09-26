.PHONY: install lint test migrate run

install:
	python3.12 -m venv .venv
	.venv/bin/pip install -e '.[dev]'

lint:
	.venv/bin/ruff check src tests scripts alembic/env.py

test:
	.venv/bin/pytest

migrate:
	.venv/bin/alembic upgrade head

run:
	.venv/bin/uvicorn ncpc_service.api:app --reload --port 8080
