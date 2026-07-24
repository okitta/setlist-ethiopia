# Deploying `claude` to Vercel (with Supabase)

This branch deploys as one Vercel project: the React app is served as static files and
the FastAPI backend runs as a Python serverless function.

## What's wired up

| Piece | File |
| --- | --- |
| Build + routing | `vercel.json` (builds `frontend/dist`, rewrites API paths to the function) |
| Serverless entrypoint | `api/index.py` (exposes the FastAPI ASGI `app`) |
| Function dependencies | `api/requirements.txt` (adds `psycopg` for Postgres) |
| Excluded from the bundle | `.vercelignore` |
| Postgres/Supabase support | `backend/app/config.py` + `backend/app/database.py` |

Routing: `/`, `/assets/*` → static React build; `/api/*`, `/health`, `/features` →
FastAPI function. The frontend calls same-origin relative paths, so no API base URL is
needed in production.

## One-time setup

1. **Import the repo in Vercel** and select the `claude` branch (or make a Preview
   deployment from the PR).
2. Vercel auto-detects `vercel.json`; leave the Build & Output settings as defined
   there (do not override the output directory).
3. **Add environment variables** (Project → Settings → Environment Variables):

   | Variable | Value | Notes |
   | --- | --- | --- |
   | `SETLIST_DATABASE_URL` | Supabase connection string | Use the **Transaction pooler** URL (port `6543`) for serverless |
   | `SETLIST_ENVIRONMENT` | `preview` or `production` | |
   | `SETLIST_FEATURE_PUBLIC_API` | `true` / `false` | Optional; flags default on |

   The app also accepts a plain `DATABASE_URL` / `POSTGRES_URL` (what Supabase's Vercel
   integration injects) and rewrites `postgres://` → `postgresql+psycopg://`
   automatically.

4. **Supabase pooler:** prefer the transaction pooler for serverless. The engine
   already disables server-side prepared statements (`prepare_threshold=None`) and uses
   a tiny pool, which is what pgbouncer transaction mode needs.

## Create this branch's tables in Supabase (one-time)

This branch uses its own **`sl_`-prefixed** tables that coexist with the deployed
app's tables without touching them (see
[`database/schema-comparison.md`](database/schema-comparison.md)). Before the API can
serve data, create them once:

- Supabase Dashboard → **SQL Editor** → paste
  [`database/supabase_slice1.sql`](database/supabase_slice1.sql) → **Run**, or
- `psql "$SUPABASE_DB_URL" -f docs/database/supabase_slice1.sql`

The script is idempotent (`IF NOT EXISTS`) and includes a commented teardown block.
No existing table is altered. Optionally seed demo rows afterwards with
`SETLIST_DATABASE_URL=... backend/.venv/bin/python -m app.seed`.

## Local production-like check

```bash
npm --prefix frontend run build      # produces frontend/dist
backend/.venv/bin/python -c "import sys; sys.path.insert(0,'api'); import index; print(index.app.title)"
```

## Notes / limits

- Serverless functions are stateless and cold-start; keep pool small (already set).
- Do **not** run Alembic migrations against Supabase from this branch until the schema
  reconciliation is settled — Drizzle migrations are the source of truth for Supabase.
- SQLite remains the default for local dev; nothing here changes that.
