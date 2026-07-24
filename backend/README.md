# Setlist Ethiopia — backend

FastAPI + SQLAlchemy + Alembic. A community archive of live music performances.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head          # create the schema
python -m app.seed            # optional: synthetic demo data
uvicorn app.main:app --reload # http://localhost:8000/docs
```

Identify yourself to write endpoints with the `X-User` header (a slice-1 stand-in for
real auth), e.g. `X-User: fan_hana` or `X-User: curator_sam` after seeding.

## Layout

| Path | Responsibility |
| --- | --- |
| `app/config.py` | Settings + feature flags |
| `app/models.py` | Schema (soft delete, immutable `revisions`, constraints) |
| `app/moderation.py` | Anti-harassment + anti-fabrication rules |
| `app/dependencies.py` | Server-side auth / authorisation |
| `app/routers/` | Endpoints (artists, performances, setlist, attendance, reports, public API) |
| `app/logging_config.py` | Structured JSON logging |
| `alembic/` | Reversible migrations |
| `tests/` | Pytest suite (slice, moderation, public API) |

## Checks

```bash
ruff format --check . && ruff check . && mypy app && pytest
```

See [`../docs/governance/required-automated-checks.md`](../docs/governance/required-automated-checks.md).
