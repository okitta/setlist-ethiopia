-- ============================================================================
-- Setlist Ethiopia — slice 1 tables for the shared Supabase database
-- ============================================================================
-- These are NET-NEW, non-conflicting tables. Every table is prefixed `sl_` so it
-- cannot collide with the deployed app's existing tables (artists, performances,
-- users, reports, revisions, attendance, setlist_items, events, venues,
-- artist_names). Both applications can share the same database.
--
-- Source of truth: backend/app/models.py. Columns/indexes/constraints mirror the
-- Alembic migration in backend/alembic/versions/. The only addition here is
-- server-side DEFAULTs (now(), booleans, 'open') so rows inserted by hand outside the
-- ORM still get sane values; the app always sets these explicitly, so there is no
-- behavioural drift.
--
-- HOW TO RUN (you run this — I never see production credentials):
--   • Supabase Dashboard → SQL Editor → paste → Run, OR
--   • psql "$SUPABASE_DB_URL" -f docs/database/supabase_slice1.sql
--
-- Safe to re-run: every statement uses IF NOT EXISTS.
-- Rollback: see the teardown block at the bottom (commented out).
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS sl_songs (
	id SERIAL NOT NULL,
	title VARCHAR(240) NOT NULL,
	slug VARCHAR(260) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS ix_sl_songs_title ON sl_songs (title);
CREATE UNIQUE INDEX IF NOT EXISTS ix_sl_songs_slug ON sl_songs (slug);

CREATE TABLE IF NOT EXISTS sl_users (
	id SERIAL NOT NULL,
	handle VARCHAR(64) NOT NULL,
	display_name VARCHAR(120) NOT NULL,
	role VARCHAR(20) NOT NULL,
	is_active BOOLEAN NOT NULL DEFAULT true,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_sl_users_handle ON sl_users (handle);

CREATE TABLE IF NOT EXISTS sl_artists (
	id SERIAL NOT NULL,
	name VARCHAR(200) NOT NULL,
	slug VARCHAR(220) NOT NULL,
	bio TEXT,
	is_archived BOOLEAN NOT NULL DEFAULT false,
	archived_at TIMESTAMP WITH TIME ZONE,
	created_by INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(created_by) REFERENCES sl_users (id)
);
CREATE INDEX IF NOT EXISTS ix_sl_artists_name ON sl_artists (name);
CREATE UNIQUE INDEX IF NOT EXISTS ix_sl_artists_slug ON sl_artists (slug);
CREATE INDEX IF NOT EXISTS ix_sl_artists_is_archived ON sl_artists (is_archived);

CREATE TABLE IF NOT EXISTS sl_reports (
	id SERIAL NOT NULL,
	entity_type VARCHAR(40) NOT NULL,
	entity_id INTEGER NOT NULL,
	reason VARCHAR(40) NOT NULL,
	details TEXT,
	status VARCHAR(20) NOT NULL DEFAULT 'open',
	reporter_id INTEGER,
	resolver_id INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	resolved_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(reporter_id) REFERENCES sl_users (id),
	FOREIGN KEY(resolver_id) REFERENCES sl_users (id)
);
CREATE INDEX IF NOT EXISTS ix_sl_reports_entity_id ON sl_reports (entity_id);
CREATE INDEX IF NOT EXISTS ix_sl_reports_status ON sl_reports (status);
CREATE INDEX IF NOT EXISTS ix_sl_reports_entity_type ON sl_reports (entity_type);

CREATE TABLE IF NOT EXISTS sl_revisions (
	id SERIAL NOT NULL,
	entity_type VARCHAR(40) NOT NULL,
	entity_id INTEGER NOT NULL,
	action VARCHAR(20) NOT NULL,
	summary VARCHAR(280) NOT NULL,
	actor_id INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(actor_id) REFERENCES sl_users (id)
);
CREATE INDEX IF NOT EXISTS ix_sl_revisions_created_at ON sl_revisions (created_at);
CREATE INDEX IF NOT EXISTS ix_sl_revisions_entity_id ON sl_revisions (entity_id);
CREATE INDEX IF NOT EXISTS ix_sl_revisions_entity_type ON sl_revisions (entity_type);

CREATE TABLE IF NOT EXISTS sl_performances (
	id SERIAL NOT NULL,
	artist_id INTEGER NOT NULL,
	venue VARCHAR(200) NOT NULL,
	city VARCHAR(120) NOT NULL,
	performed_on DATE NOT NULL,
	notes TEXT,
	is_archived BOOLEAN NOT NULL DEFAULT false,
	archived_at TIMESTAMP WITH TIME ZONE,
	created_by INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_perf_artist_venue_date UNIQUE (artist_id, venue, performed_on),
	FOREIGN KEY(artist_id) REFERENCES sl_artists (id),
	FOREIGN KEY(created_by) REFERENCES sl_users (id)
);
CREATE INDEX IF NOT EXISTS ix_sl_performances_is_archived ON sl_performances (is_archived);
CREATE INDEX IF NOT EXISTS ix_sl_performances_performed_on ON sl_performances (performed_on);
CREATE INDEX IF NOT EXISTS ix_sl_performances_artist_id ON sl_performances (artist_id);

CREATE TABLE IF NOT EXISTS sl_attendances (
	id SERIAL NOT NULL,
	performance_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	is_archived BOOLEAN NOT NULL DEFAULT false,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_attendance_once UNIQUE (performance_id, user_id),
	FOREIGN KEY(performance_id) REFERENCES sl_performances (id),
	FOREIGN KEY(user_id) REFERENCES sl_users (id)
);
CREATE INDEX IF NOT EXISTS ix_sl_attendances_performance_id ON sl_attendances (performance_id);
CREATE INDEX IF NOT EXISTS ix_sl_attendances_user_id ON sl_attendances (user_id);

CREATE TABLE IF NOT EXISTS sl_setlist_entries (
	id SERIAL NOT NULL,
	performance_id INTEGER NOT NULL,
	song_id INTEGER NOT NULL,
	position INTEGER NOT NULL,
	is_archived BOOLEAN NOT NULL DEFAULT false,
	archived_at TIMESTAMP WITH TIME ZONE,
	created_by INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_setlist_perf_position UNIQUE (performance_id, position),
	FOREIGN KEY(performance_id) REFERENCES sl_performances (id),
	FOREIGN KEY(song_id) REFERENCES sl_songs (id),
	FOREIGN KEY(created_by) REFERENCES sl_users (id)
);
CREATE INDEX IF NOT EXISTS ix_sl_setlist_entries_is_archived ON sl_setlist_entries (is_archived);
CREATE INDEX IF NOT EXISTS ix_sl_setlist_entries_performance_id ON sl_setlist_entries (performance_id);

COMMIT;

-- ============================================================================
-- ROLLBACK / teardown (run only if you need to remove slice-1 tables).
-- Drops in FK-safe order. Uncomment to use.
-- ============================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS sl_setlist_entries;
-- DROP TABLE IF EXISTS sl_attendances;
-- DROP TABLE IF EXISTS sl_performances;
-- DROP TABLE IF EXISTS sl_revisions;
-- DROP TABLE IF EXISTS sl_reports;
-- DROP TABLE IF EXISTS sl_artists;
-- DROP TABLE IF EXISTS sl_users;
-- DROP TABLE IF EXISTS sl_songs;
-- COMMIT;
