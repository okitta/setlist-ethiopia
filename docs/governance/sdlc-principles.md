# SDLC principles & delivery governance

The development process optimises for **trust, learning, and reversibility**. Vibe
coding can accelerate implementation, but generated code passes the same review and
verification gates as manually written code.

## Operating principles

### 1. Start with user outcomes

Every feature must name: the user and problem; the simplest successful journey; the
measurable result; the data it collects; its abuse and privacy risks; and what is
deliberately out of the first version.

Reject features that do not improve **discovery, documentation, contribution quality,
or community trust**.

> Worked example — slice 1: see [`docs/product/slice-1-first-contribution.md`](../product/slice-1-first-contribution.md).

### 2. Build in vertical slices

Deliver small end-to-end experiences rather than all screens, then all APIs, then all
database work. The first slice is:

> Find an artist → open a performance → mark attendance or add one missing song → see
> the contribution and revision history.

Each slice works across UI, validation, permissions, database, observability, and
tests before the next major slice starts. Slice 1 does exactly this — see the mapping
in the product doc.

### 3. Keep changes small and reversible

- Short-lived branches and small pull requests (this work lives on `claude`).
- Unfinished or risky features sit behind **feature flags** (`app/config.py`).
- Database migrations are backward-compatible (Alembic; `render_as_batch` for SQLite).
- Every production migration defines rollback steps — verified with `alembic downgrade`.
- Contribution history is **never altered or deleted silently** — the `revisions`
  table is append-only and every mutation writes to it.
- Prefer **soft deletion and archival states** (`is_archived` / `archived_at`).

### 4. Treat generated code as untrusted until reviewed

For AI-generated changes:

- understand the code before merging it;
- verify library and API names against official documentation;
- reject invented packages or security controls;
- run formatting, type checking, tests, dependency checks, and production builds;
- inspect authentication, authorisation, file handling, database queries, and error
  paths manually;
- never place secrets, production records, or private user data in an AI prompt.

### 5 & 6. Definition of Ready / Done

See [`definition-of-ready.md`](definition-of-ready.md) and
[`definition-of-done.md`](definition-of-done.md).

## How this repository embodies the principles

| Principle | Where it lives |
| --- | --- |
| Vertical slice | `backend/app/routers/*`, `frontend/src/App.tsx` + `PerformancePanel.tsx` |
| Feature flags | `backend/app/config.py`, `GET /features`, UI reads flags |
| Immutable history | `Revision` model, `crud.record_revision`, `/revisions` endpoint |
| Soft deletion | `is_archived` on artists/performances/setlist entries + `/archive` |
| Anti-abuse | `app/moderation.py`, `routers/reports.py`, [`../policies/anti-abuse-and-fabrication.md`](../policies/anti-abuse-and-fabrication.md) |
| Data reuse | `routers/public_api.py`, [`../policies/data-reuse-and-api.md`](../policies/data-reuse-and-api.md) |
| Observability | `app/logging_config.py`, request-id middleware in `main.py` |
| Reversible migrations | `backend/alembic/` (`upgrade`/`downgrade` both tested) |
