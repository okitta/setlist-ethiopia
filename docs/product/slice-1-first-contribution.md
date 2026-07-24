# Slice 1 — first contribution

The first vertical slice, framed with the "start with user outcomes" checklist.

## User outcomes

| Field | Answer |
| --- | --- |
| **User & problem** | An Ethiopian live-music fan wants to find an artist and correct or enrich the record of a show they know about — today that knowledge lives only in memory and social posts. |
| **Simplest successful journey** | Search an artist → open a performance → mark that they attended, or add one song that's missing → see their contribution recorded in the history. |
| **Measurable result** | A contribution (attendance edge or setlist entry) is stored and visible, with an entry in the revision history attributed to the user. |
| **Data it collects** | Artist/performance facts, a song title, an attendance edge (user↔performance), and revision metadata (actor, action, summary, timestamp). |
| **Abuse & privacy risks** | Fabricated shows/songs; harassing free text; scraping of *who attended what*. Mitigations: fabrication guards + moderation + reports; text screening; personal data excluded from the public API. |
| **Out of scope (v1)** | Real auth/OIDC, editing or reordering setlist entries, encores/timestamps, images/uploads, notifications, i18n beyond launch copy, API keys. |

## Slice completeness (the "each slice works across every layer" test)

| Layer | Evidence |
| --- | --- |
| UI | `frontend/src/App.tsx`, `PerformancePanel.tsx` (search → list → detail, all states) |
| Validation | Pydantic schemas + `moderation.py` |
| Permissions | `dependencies.py` (server-side, 401/403) |
| Database | `models.py` + Alembic migration (constraints, soft delete, revisions) |
| Observability | `logging_config.py` + request-id middleware |
| Tests | `backend/tests/*` (20) + `frontend/src/api.test.ts` (2) |

## Threat model (STRIDE-lite)

The change touches **identity, permissions, and moderation**, so it is threat-modelled
(per the release flow).

| Threat | Vector | Mitigation |
| --- | --- | --- |
| Spoofing | Anyone could claim to be another user via `X-User` | Documented as slice-1 stand-in; server verifies the handle exists and is active; real auth is a named prerequisite before public launch |
| Tampering | Editing/erasing history to hide abuse | History is append-only; records are archived, not deleted |
| Repudiation | "I didn't add that" | Every mutation attributed in `revisions` |
| Information disclosure | Scraping who attended | Public API exposes aggregate counts only; no user fields serialised |
| Denial of service | Spam contributions | Duplicate constraints + reports; rate limiting named as next step |
| Elevation of privilege | Contributor archiving records | `require_curator` enforced server-side; tested (403) |

## Known slice-1 limitation

`X-User` header identity is **not** production auth. It is an explicit, documented
placeholder so the slice can be complete end-to-end; replacing it with real session
auth (OIDC) is the first item before any public release.
