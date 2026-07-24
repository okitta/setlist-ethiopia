# Definition of Done

A feature is **done** only when every item below is true. The right-hand column shows
how slice 1 satisfies it today.

| Done criterion | Status in slice 1 |
| --- | --- |
| Acceptance criteria pass | ✅ `backend/tests/test_slice.py` covers the full journey |
| Responsive layouts checked | ✅ `frontend/src/styles.css` collapses to one column < 900px |
| Keyboard navigation & accessible names work | ✅ labels bound via `htmlFor`; `role="alert"`/`role="status"`; native controls |
| Authorisation enforced on the server | ✅ `app/dependencies.py` (`get_current_user`, `require_curator`); tested with 401/403 |
| Tests cover happy path and important failures | ✅ 20 backend tests + 2 frontend tests (auth, duplicates, moderation, archive, public API) |
| Logs contain no secrets or unnecessary personal data | ✅ `logging_config.py` logs identifiers/actions only; report details never logged |
| Analytics events documented | ✅ `performance_created`, `song_added`, `attendance_marked`, `report_filed` (see below) |
| DB migrations & rollback tested | ✅ `alembic upgrade head` + `alembic downgrade base` both verified |
| Product / security / accessibility / moderation implications documented | ✅ this docs tree |
| User-facing help / moderation guidance updated | ✅ [`../policies/anti-abuse-and-fabrication.md`](../policies/anti-abuse-and-fabrication.md) |

## Analytics / success signals (structured log events)

| Event | Emitted from | Context fields |
| --- | --- | --- |
| `performance_created` | `routers/performances.py` | `performance_id`, `actor_id` |
| `song_added` | `routers/setlist.py` | `performance_id`, `actor_id` |
| `attendance_marked` | `routers/attendance.py` | `performance_id`, `actor_id` |
| `report_filed` | `routers/reports.py` | `report_id`, `entity_type`, `reason` |
| `request` (access log) | `main.py` middleware | `request_id`, `method`, `path`, `status` |

All events are single-line JSON on stdout, ready to ship to a log store. No secrets,
handles, or free-text personal data are included.
