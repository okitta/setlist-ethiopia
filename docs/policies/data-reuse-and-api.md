# Policy: reusing contributed structured data through an API

**Question answered:** can contributed structured data be reused through an API?

**Decision: yes — with guard-rails.** Setlist Ethiopia is a community archive; its
non-personal, structured data (artists, performances, setlists, aggregate attendance)
is openly reusable through a read-only public API so researchers, journalists, and
other communities can build on it.

## What is reusable

- Artists (name, slug, bio).
- Performances (venue, city, date, notes).
- Setlists (song order and titles).
- **Aggregate** attendance counts.

## What is *not* exposed

- No personal data of any kind: no user handles, no per-user attendance, no reporter
  identities, no email/contact data.
- No archived records (e.g. those removed as fabricated or abusive).
- No moderation internals (reports, curator notes).

## Guarantees (enforced in code)

| Guarantee | How |
| --- | --- |
| **Read-only** | The public router exposes only `GET`; a `POST` to a public path returns 405 |
| **No personal data** | Attendance returned as a count only; no user fields serialised |
| **Public records only** | Archived rows are excluded from every public query |
| **Self-describing licence** | Every response carries a `meta` block with licence + attribution |
| **Killable** | The whole surface is behind `feature_public_api`; disable instantly |

**Enforced by:** `backend/app/routers/public_api.py`. Tested in
`tests/test_public_api.py` (incl. an explicit assertion that no user handle leaks into
a payload, and that archived records 404).

## Licence

Reuse is granted under **CC BY-SA 4.0** (configurable via `SETLIST_DATA_LICENSE`):

- **BY** — attribute "Setlist Ethiopia contributors".
- **SA** — derived datasets are shared under the same terms.
- Personal data is excluded from the licence grant entirely.

The machine-readable statement is served at `GET /api/v1/public/license` and embedded
in the `meta` of every data response, so downstream consumers can detect the terms
programmatically.

## Endpoints (v1)

| Endpoint | Returns |
| --- | --- |
| `GET /api/v1/public/license` | Licence + attribution terms |
| `GET /api/v1/public/artists?q=&limit=` | Public artists with licence meta |
| `GET /api/v1/public/performances/{id}` | One performance: setlist + aggregate attendance |

## Contributor consent & expectations

Contributors are told at contribution time that structured facts they add become part
of the open dataset under the licence above, while their identity and activity remain
private. This separation — **open facts, private people** — is the core of the policy.

## Out of scope for slice 1

API keys / per-consumer rate limits, bulk export dumps, pagination cursors, and
webhook/streaming access. The response envelope (`meta` + `data`) is versioned under
`/api/v1/` so these can be added compatibly.
