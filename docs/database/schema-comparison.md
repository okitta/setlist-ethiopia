# Schema comparison: this branch vs. the Supabase (deployed) database

**Short answer: no — the schemas are not the same.** This branch (`claude`) uses a
simpler slice-1 schema authored with SQLAlchemy/Alembic. The deployed branch's
Supabase database uses a richer schema authored with Drizzle. They overlap in spirit
(same domain) but differ in table names, columns, and modelling choices.

This document maps the differences so we can decide how to reconcile them. **Do not
push this branch's tables into Supabase as-is** — several would collide with existing
tables that share a name but have different columns (see "Conflicts" below).

## Table-by-table

| Concept | Supabase (deployed) | This branch (`claude`) | Same? |
| --- | --- | --- | --- |
| Artists | `artists` (slug, display_name, native_name, genre, status) | `artists` (name, slug, bio, is_archived) | ⚠️ different columns |
| Artist aliases | `artist_names` (multilingual: name, language, script, kind) | — (none) | ❌ missing here |
| Venues | `venues` (slug, display_name, native_name, city, country, address) | folded into `performances.venue` + `.city` | ❌ no venue table |
| Events | `events` (slug, title, event_date, venue_id, status, source_url) | — (none) | ❌ missing here |
| Performances | `performances` (event_id, artist_id, submitted_artist/venue, performance_date, status, evidence, submitted_by) | `performances` (artist_id, venue, city, performed_on, notes, is_archived) | ⚠️ different columns |
| Setlist | `setlist_items` (performance_id, position, **title**, section, note, confidence) | `setlist_entries` (performance_id, **song_id**, position) + `songs` table | ⚠️ different name & model |
| Attendance | `attendance` (user_id, performance_id, **visibility**) | `attendances` (performance_id, user_id, is_archived) | ⚠️ name + columns |
| Reports | `reports` (entity_type, entity_id, reporter_id, **category**, **detail**, status) | `reports` (entity_type, entity_id, reporter_id, **reason**, **details**, status, resolver_id, resolved_at) | ⚠️ different columns |
| Revisions | `revisions` (entity_type, entity_id, actor_id, reason, **before_json**, **after_json**) | `revisions` (entity_type, entity_id, actor_id, **action**, **summary**) | ⚠️ different model |
| Users | `users` (**email**, display_name, role) | `users` (**handle**, display_name, role, is_active) | ⚠️ identity key differs |

## Key modelling differences

1. **Events & venues are first-class in Supabase.** An `event` (a show at a venue on a
   date) groups one or more `performances` (an artist's set). This branch collapses
   venue/city into the performance and has no event grouping.
2. **Multilingual names.** Supabase's `artist_names` supports Amharic/native scripts
   and aliases (`language`, `script`, `kind`). This is important for Ethiopian names
   and is absent here.
3. **Moderation-queue fields.** Supabase performances carry `submitted_artist`,
   `submitted_venue`, `evidence`, and a `status` workflow (e.g. `community`) — a
   submission/verification pipeline. This branch uses `is_archived` soft-delete instead
   of a status workflow.
4. **Setlist stores titles directly.** Supabase `setlist_items.title` is free text with
   `section`/`confidence`; this branch normalises songs into a `songs` table referenced
   by `song_id`.
5. **Revisions are full snapshots.** Supabase stores `before_json`/`after_json`; this
   branch stores a human `action` + `summary`. Both are append-only history.
6. **Identity.** Supabase users are keyed by `email`; this branch by `handle`.

## Conflicts if we blindly "add this branch's schema" to Supabase

`artists`, `performances`, `reports`, `revisions`, `users` already exist in Supabase
with **different columns**. Creating them again would fail (name clash) or, if forced,
break the deployed app. `attendance` vs `attendances` and `setlist_items` vs
`setlist_entries` would create confusing near-duplicates. So a straight "apply our
schema on top" is not safe.

## Recommended reconciliation

**Treat the Supabase schema as canonical and adapt this branch to it** (Option A in the
PR discussion). Concretely:

- Point SQLAlchemy models at the existing tables/columns (`display_name`, `email`,
  `event`/`venue`, `setlist_items.title`, `reports.category/detail`,
  `revisions.before_json/after_json`, `attendance.visibility`).
- Manage schema with the **existing Drizzle migrations** as the source of truth; this
  branch's Alembic migration becomes local-only (SQLite dev) or is retired.
- Add the missing product concepts here (events, venues, artist_names) rather than
  forking the schema.

The alternative — adding net-new, non-conflicting tables to Supabase — is only
appropriate for genuinely new concepts this branch introduces that Supabase lacks, and
should be additive migrations reviewed against the deployed app.

## `attendance.visibility` — privacy note

Supabase models attendance privacy with a `visibility` column (`private` by default).
Our data-reuse policy (only aggregate counts, no personal data) already aligns with
this; when we adapt, the public API must additionally never expose `private`
attendance beyond counts. See [`../policies/data-reuse-and-api.md`](../policies/data-reuse-and-api.md).
