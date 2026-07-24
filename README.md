# Setlist Ethiopia

A community-built archive of live music performances in Ethiopia — find an artist,
open a show, and help document who played what, when, and where.

This repository implements **slice 1** of the product together with the SDLC and
delivery-governance framework it is built under.

## The first vertical slice

> Find an artist → open a performance → mark attendance or add one missing song → see
> the contribution and revision history.

It works end-to-end across UI, validation, permissions, database, observability, and
tests. Two product policies ship with it:

- **Rules against harassment & fabricated records** — enforced in code and workflow.
  See [`docs/policies/anti-abuse-and-fabrication.md`](docs/policies/anti-abuse-and-fabrication.md).
- **Reuse of contributed structured data through an API** — a read-only, licensed,
  personal-data-free public API. See
  [`docs/policies/data-reuse-and-api.md`](docs/policies/data-reuse-and-api.md).

## Repository layout

```
backend/    FastAPI + SQLAlchemy + Alembic (API, moderation, migrations, tests)
frontend/   React + TypeScript + Vite (the slice-1 UI)
docs/
  governance/  SDLC principles, Definition of Ready/Done, release flow, checks
  policies/    Anti-abuse & data-reuse policies
  product/     Slice-1 outcomes + threat model
.github/    CI running the required automated checks
Makefile    Local entry points mirroring CI
```

## Run it locally

```bash
make setup          # install backend + frontend deps
make migrate seed   # create schema + synthetic demo data
make run-backend    # API on http://localhost:8000  (docs at /docs)
make run-frontend   # UI  on http://localhost:5173
```

Then, in the UI, search `Aster`, open a performance, mark attendance, add a song, and
watch the revision history update. Switch between `fan_hana` (contributor) and
`curator_sam` (curator) to see server-side permissions in action.

## Governance

Start with [`docs/governance/sdlc-principles.md`](docs/governance/sdlc-principles.md),
which maps every principle (vertical slices, feature flags, reversibility, immutable
history, treating generated code as untrusted) to where it lives in the code.

## Verified checks

| Check | Result |
| --- | --- |
| Backend tests | 20 passing |
| Backend lint + format | clean (`ruff`) |
| Backend types | `mypy app` |
| Migrations | `upgrade` **and** `downgrade` verified |
| Frontend types / tests / build | all passing |
