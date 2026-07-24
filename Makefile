# Developer entry points. Mirrors the required automated checks so what runs in CI
# runs locally too (docs/governance/required-automated-checks.md).

BACKEND := backend
PY := $(BACKEND)/.venv/bin

.PHONY: help setup backend-setup frontend-setup check backend-check frontend-check \
        test migrate rollback seed run-backend run-frontend

help:
	@echo "make setup           - install backend + frontend dependencies"
	@echo "make check           - run ALL required automated checks"
	@echo "make backend-check   - format, lint, typecheck, tests, migration round-trip"
	@echo "make frontend-check  - typecheck, tests, production build"
	@echo "make migrate         - alembic upgrade head"
	@echo "make rollback        - alembic downgrade -1"
	@echo "make seed            - load synthetic demo data"
	@echo "make run-backend     - start the API (uvicorn) on :8000"
	@echo "make run-frontend    - start the React dev server on :5173"

setup: backend-setup frontend-setup

backend-setup:
	python3 -m venv $(BACKEND)/.venv
	$(PY)/pip install --upgrade pip
	$(PY)/pip install -r $(BACKEND)/requirements.txt
	$(PY)/pip install ruff==0.8.4 mypy==1.14.0

frontend-setup:
	cd frontend && npm install

check: backend-check frontend-check

backend-check:
	cd $(BACKEND) && .venv/bin/ruff format --check .
	cd $(BACKEND) && .venv/bin/ruff check .
	cd $(BACKEND) && .venv/bin/mypy app
	cd $(BACKEND) && .venv/bin/python -m pytest
	cd $(BACKEND) && rm -f setlist.db && .venv/bin/alembic upgrade head && .venv/bin/alembic downgrade base && .venv/bin/alembic upgrade head

frontend-check:
	cd frontend && npm run typecheck && npm run test && npm run build

migrate:
	cd $(BACKEND) && .venv/bin/alembic upgrade head

rollback:
	cd $(BACKEND) && .venv/bin/alembic downgrade -1

seed:
	cd $(BACKEND) && .venv/bin/python -m app.seed

run-backend:
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev
