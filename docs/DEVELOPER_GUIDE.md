# Developer Guide

## Local Setup

```bash
cp .env.example .env

# Option A — Docker
docker-compose up -d db
pip install -e ".[dev]"
alembic upgrade head
python scripts/seed_reference_data.py
uvicorn api.main:app --reload

# Option B — local Postgres + pgvector
createdb rawasi_pricing
psql rawasi_pricing -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; CREATE EXTENSION IF NOT EXISTS "pg_trgm"; CREATE EXTENSION IF NOT EXISTS vector;'
alembic upgrade head
python scripts/seed_reference_data.py
uvicorn api.main:app --reload
```

## Repository Layout

```
api/
  core/        ── config, db, logging, errors
  models/      ── SQLAlchemy ORM models (19 tables)
  schemas/     ── Pydantic request/response models
  services/    ── business logic (one file per engine)
  routers/     ── FastAPI endpoints
  utils/       ── Arabic-text, embeddings, stats helpers
  main.py      ── FastAPI app factory + exception handlers
migrations/    ── Alembic versioned migrations
scripts/       ── one-shot scripts (bulk import, seed data)
prompts/       ── Claude prompts (versioned with the code)
tests/         ── unit / integration / e2e
odoo_module/   ── Odoo customization
docs/          ── user-facing documentation
```

## Coding Conventions

- Python 3.11, type-hinted, ruff/black formatted.
- All services are pure functions of the data they receive — DB access
  is injected through a `Session`.
- Domain errors live in `api/core/errors.py` and are mapped to HTTP
  status codes in `api/main.py`.
- Tests:
  - **Unit** tests have no DB or HTTP dependencies.
  - **Integration** tests use an in-memory SQLite via `conftest.py`.
  - **E2E** tests run the FastAPI app against the same SQLite.

## Running Tests

```bash
# Whole suite
pytest

# Unit only (fast)
pytest tests/unit -q

# A single test
pytest tests/integration/test_normalizer.py::test_keyword_match_via_synonyms -v
```

## Adding a New Engine

1. Add the SQLAlchemy models if new tables are needed.
2. Write the Pydantic schemas in `api/schemas/`.
3. Implement the service in `api/services/<name>.py` — pure logic only.
4. Expose endpoints in `api/routers/<name>.py`.
5. Wire the router in `api/main.py`.
6. Write unit + integration tests.
7. Document the engine in `docs/SPECIFICATION.md`.

## Database Migrations

```bash
# Generate a new migration after model changes
alembic revision --autogenerate -m "add foo to bar"

# Apply
alembic upgrade head

# Roll back one
alembic downgrade -1
```

**Never edit a migration that has already been applied to staging or
production** — write a new one.

## Claude API

Prompts are stored as Markdown in `prompts/` and version-controlled. To
tune a prompt:

1. Edit the Markdown.
2. Add or update fixtures in `tests/` that exercise the new behavior.
3. Run on a sample of historic documents to compare outputs.

Cost guardrails:
- `CLAUDE_MAX_TOKENS` caps each call.
- The normalizer attempts local matches first; Claude is the third stage.
- For bulk imports, prefer Anthropic's Batch API (not implemented yet).
