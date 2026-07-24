# Policy: harassment & fabricated records

**Question answered:** what are the rules against harassment and fabricated records,
and how are they enforced?

Setlist Ethiopia is a shared historical record. Its value depends on being *accurate*
and *safe to contribute to*. This policy defines the rules and maps each to the code
and workflow that enforce it.

## Principles

1. **Prevent the obvious, review the subtle.** Cheap, high-signal abuse is blocked at
   write time; anything context-dependent is routed to human curators — never silently
   accepted or silently deleted.
2. **Nothing is destroyed.** Bad records are *archived*, not erased. The immutable
   revision history preserves who did what, so decisions are auditable and reversible.
3. **Attribution everywhere.** Every contribution carries its author, which deters
   abuse and makes patterns visible.

## Rules against harassment

- Free-text fields (performance notes, song titles) are screened for slurs and
  targeted-abuse patterns before they are stored.
- Screening is resistant to trivial evasion: text is accent-folded, case-folded, and
  whitespace-collapsed before matching (so `k y s` is caught the same as `kys`).
- Violations return **HTTP 422** with a machine code `harassment_blocked` and a
  non-accusatory message asking the contributor to revise.
- The blocklist is data, not code: in production it is a curated, localised list
  (Amharic + English + transliterations) owned by the moderation team and updated
  **without a deploy**.

**Enforced by:** `backend/app/moderation.py` (`screen_text`), called from
`routers/performances.py` and `routers/setlist.py`. Tested in
`tests/test_moderation.py`.

## Rules against fabricated records

Automated guards reject records that are physically impossible or clearly duplicated:

| Rule | Rejection code |
| --- | --- |
| A performance date cannot be in the future | `future_performance` |
| A performance date before the configured floor (`1930`) is not accepted | `implausible_date` |
| A performance needs both a venue and a city | `incomplete_record` |
| One artist cannot have two records for the same venue on the same day | `duplicate_performance` |
| A song cannot appear twice in the same setlist | `duplicate_song` |

Subtler fabrication (plausible-but-false details) is handled by the community:

- **Anyone signed in can report** a record (`POST /api/v1/reports`, reasons:
  `harassment`, `fabricated`, `spam`, `other`).
- **Only curators/admins** can act on reports or archive records
  (`require_curator`); contributors attempting this get **HTTP 403**.
- Archiving is a **soft delete**: the record leaves public/API views but its full
  history remains queryable at `/performances/{id}/revisions`.

**Enforced by:** `moderation.check_performance_plausibility`, DB `UniqueConstraint`s in
`models.py`, `routers/reports.py`, and the `/archive` endpoints. Tested in
`tests/test_moderation.py` (`test_report_and_curator_archive`).

## Curator guidance (operational)

1. Triage `open` reports oldest-first: `GET /api/v1/reports?status=open`.
2. Confirm against external evidence where possible before upholding.
3. If a record is fabricated/abusive, **archive it** (do not ask for deletion) and
   resolve the report as `upheld`.
4. If the record is legitimate, resolve as `dismissed` — the report itself stays on
   file as history.
5. Repeated abuse from one account is escalated to account review (out of scope for
   slice 1; the attribution trail makes it possible).

## Out of scope for slice 1

Rate limiting, automated reputation scoring, ML-based toxicity detection, and account
suspension flows. The data model (attribution + reports + immutable history) is
designed so these can be added without schema changes.
