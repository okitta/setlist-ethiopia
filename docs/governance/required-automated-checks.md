# Required automated checks

Every pull request must pass these before review is complete. They are enforced in CI
(`.github/workflows/ci.yml`) and runnable locally via the `Makefile`. Generated code
is subject to exactly the same gates as hand-written code.

## Backend (Python / FastAPI)

| Check | Command | Why |
| --- | --- | --- |
| Formatting | `ruff format --check .` | Consistent, reviewable diffs |
| Lint | `ruff check .` | Catches bugs, unused code, import order |
| Type check | `mypy app` | Verifies contracts before runtime |
| Tests | `pytest` | Happy paths + important failures (auth, moderation, reuse) |
| Migrations round-trip | `alembic upgrade head` then `alembic downgrade base` | Proves migrations are reversible |
| Dependency audit | `pip-audit` | Rejects known-vulnerable dependencies |

## Frontend (React / TypeScript)

| Check | Command | Why |
| --- | --- | --- |
| Type check | `npm run typecheck` | Strict TS, no `any` leaks across the API boundary |
| Tests | `npm run test` | Client behaviour incl. auth header + error typing |
| Production build | `npm run build` | Ensures the app actually ships |
| Dependency audit | `npm audit --audit-level=high` | Rejects high-severity advisories |

## Manual review gates (checklist, not automated)

For any change — and especially AI-generated ones — a human reviewer confirms:

- The code is understood, not just green.
- Library/API names are real (verified against official docs); no invented packages.
- Authentication, authorisation, DB queries, file handling, and error paths were read
  line by line.
- No secrets, production records, or private user data were placed in an AI prompt.
- No security control was "invented" (e.g. a fake sanitiser); controls map to real,
  documented mechanisms.

## Running everything locally

```bash
make check   # backend + frontend checks in one go
```

See the repository root `Makefile` for individual targets.
