# Environments & release flow

Use separate **local, preview, staging, and production** environments. **Never use
production user data in development.**

| Environment | Purpose | Database | Data |
| --- | --- | --- | --- |
| local | Day-to-day dev | SQLite (`setlist.db`) | `python -m app.seed` (synthetic) |
| preview | Per-PR ephemeral deploy | Disposable Postgres | Seed only |
| staging | Pre-production rehearsal | Postgres (prod-like) | Anonymised / synthetic |
| production | Live | Postgres (managed, backed up) | Real contributions |

`SETLIST_ENVIRONMENT` selects the environment; `SETLIST_DATABASE_URL` points at the
right database. Feature flags (`SETLIST_FEATURE_*`) default safe and are enabled per
environment.

## Recommended flow

1. Write a small story and acceptance criteria (Definition of Ready).
2. **Threat-model** the change if it touches identity, permissions, uploads,
   messaging, moderation, payments, or exports.
3. Implement behind a **feature flag** when risk is meaningful.
4. Run automated checks (see [`required-automated-checks.md`](required-automated-checks.md)).
5. Review the change and preview it on mobile and desktop.
6. Test with a small internal or curator group.
7. Release gradually (flag rollout: internal → curators → percentage → all).
8. Watch error rate, latency, abuse signals, and contribution quality.
9. **Roll back or disable** the feature if defined thresholds are crossed.
10. Record what was learned.

## Rollback playbook

Every production migration ships with a tested `downgrade`. Two independent levers:

- **Feature flag off** — instant, no deploy: set `SETLIST_FEATURE_<x>=false`. Use this
  first for behavioural problems.
- **Migration rollback** — `alembic downgrade -1`. Only for schema problems, and only
  because migrations are backward-compatible (new code tolerates old schema for one
  release, so a rollback never corrupts data).

### Rollback thresholds (disable the feature if any is crossed)

- 5xx error rate for the feature's endpoints > 2% over 10 minutes.
- p95 latency > 1s sustained for 10 minutes.
- Spike in `report_filed` events on new records (possible abuse vector).
- Any confirmed leak of personal data in logs or the public API.
