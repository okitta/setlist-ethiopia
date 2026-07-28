-- ============================================================================
-- Canonical (deployed app) Supabase schema — reference copy.
-- This is the schema the Next.js/Drizzle app owns. The scraper in `scraper/`
-- normalises data into THESE tables. Kept here so the loader and its tests have a
-- source of truth; Drizzle remains the migration authority for the deployed app.
-- (Plain SQL: the Drizzle `--> statement-breakpoint` markers have been removed.)
-- ============================================================================

-- NOTE: normalized_name (NOT NULL) and artists.description were added by the
-- deployed app's migration drizzle/0001_ai_identity.sql. The scraper's loader
-- populates normalized_name = lower(collapse_whitespace(trim(display_name|name))).
CREATE TABLE IF NOT EXISTS "artist_names" (
    "id" serial PRIMARY KEY NOT NULL,
    "artist_id" integer NOT NULL,
    "name" text NOT NULL,
    "normalized_name" text NOT NULL,
    "language" text,
    "script" text,
    "kind" text DEFAULT 'alias' NOT NULL
);

CREATE TABLE IF NOT EXISTS "artists" (
    "id" serial PRIMARY KEY NOT NULL,
    "slug" text NOT NULL,
    "display_name" text NOT NULL,
    "native_name" text,
    "normalized_name" text NOT NULL,
    "description" text,
    "genre" text,
    "status" text DEFAULT 'community' NOT NULL,
    "created_at" timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "attendance" (
    "id" serial PRIMARY KEY NOT NULL,
    "user_id" integer NOT NULL,
    "performance_id" integer NOT NULL,
    "visibility" text DEFAULT 'private' NOT NULL,
    "created_at" timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "events" (
    "id" serial PRIMARY KEY NOT NULL,
    "slug" text NOT NULL,
    "title" text NOT NULL,
    "event_date" timestamp with time zone NOT NULL,
    "venue_id" integer,
    "status" text DEFAULT 'announced' NOT NULL,
    "source_url" text,
    "created_by" integer,
    "created_at" timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "performances" (
    "id" serial PRIMARY KEY NOT NULL,
    "event_id" integer,
    "artist_id" integer,
    "submitted_artist" text,
    "submitted_venue" text,
    "performance_date" timestamp with time zone NOT NULL,
    "status" text DEFAULT 'community' NOT NULL,
    "evidence" text,
    "submitted_by" integer,
    "created_at" timestamp with time zone DEFAULT now() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "reports" (
    "id" serial PRIMARY KEY NOT NULL,
    "entity_type" text NOT NULL,
    "entity_id" integer NOT NULL,
    "reporter_id" integer,
    "category" text NOT NULL,
    "detail" text,
    "status" text DEFAULT 'open' NOT NULL,
    "created_at" timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "revisions" (
    "id" serial PRIMARY KEY NOT NULL,
    "entity_type" text NOT NULL,
    "entity_id" integer NOT NULL,
    "actor_id" integer,
    "reason" text,
    "before_json" text,
    "after_json" text NOT NULL,
    "created_at" timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "setlist_items" (
    "id" serial PRIMARY KEY NOT NULL,
    "performance_id" integer NOT NULL,
    "position" integer NOT NULL,
    "title" text NOT NULL,
    "section" text DEFAULT 'main' NOT NULL,
    "note" text,
    "confidence" text DEFAULT 'community' NOT NULL
);

CREATE TABLE IF NOT EXISTS "users" (
    "id" serial PRIMARY KEY NOT NULL,
    "email" text NOT NULL,
    "display_name" text,
    "role" text DEFAULT 'contributor' NOT NULL,
    "created_at" timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "venues" (
    "id" serial PRIMARY KEY NOT NULL,
    "slug" text NOT NULL,
    "display_name" text NOT NULL,
    "native_name" text,
    "normalized_name" text NOT NULL,
    "city" text NOT NULL,
    "country" text DEFAULT 'Ethiopia' NOT NULL,
    "address" text,
    "created_at" timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
    ALTER TABLE "artist_names" ADD CONSTRAINT "artist_names_artist_id_artists_id_fk" FOREIGN KEY ("artist_id") REFERENCES "public"."artists"("id") ON DELETE cascade ON UPDATE no action;
    ALTER TABLE "attendance" ADD CONSTRAINT "attendance_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE cascade ON UPDATE no action;
    ALTER TABLE "attendance" ADD CONSTRAINT "attendance_performance_id_performances_id_fk" FOREIGN KEY ("performance_id") REFERENCES "public"."performances"("id") ON DELETE cascade ON UPDATE no action;
    ALTER TABLE "events" ADD CONSTRAINT "events_venue_id_venues_id_fk" FOREIGN KEY ("venue_id") REFERENCES "public"."venues"("id") ON DELETE no action ON UPDATE no action;
    ALTER TABLE "events" ADD CONSTRAINT "events_created_by_users_id_fk" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;
    ALTER TABLE "performances" ADD CONSTRAINT "performances_event_id_events_id_fk" FOREIGN KEY ("event_id") REFERENCES "public"."events"("id") ON DELETE no action ON UPDATE no action;
    ALTER TABLE "performances" ADD CONSTRAINT "performances_artist_id_artists_id_fk" FOREIGN KEY ("artist_id") REFERENCES "public"."artists"("id") ON DELETE no action ON UPDATE no action;
    ALTER TABLE "performances" ADD CONSTRAINT "performances_submitted_by_users_id_fk" FOREIGN KEY ("submitted_by") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;
    ALTER TABLE "reports" ADD CONSTRAINT "reports_reporter_id_users_id_fk" FOREIGN KEY ("reporter_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;
    ALTER TABLE "revisions" ADD CONSTRAINT "revisions_actor_id_users_id_fk" FOREIGN KEY ("actor_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;
    ALTER TABLE "setlist_items" ADD CONSTRAINT "setlist_items_performance_id_performances_id_fk" FOREIGN KEY ("performance_id") REFERENCES "public"."performances"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS "artist_names_artist_idx" ON "artist_names" USING btree ("artist_id");
CREATE INDEX IF NOT EXISTS "artist_names_name_idx" ON "artist_names" USING btree ("name");
CREATE UNIQUE INDEX IF NOT EXISTS "artists_slug_idx" ON "artists" USING btree ("slug");
CREATE INDEX IF NOT EXISTS "artists_name_idx" ON "artists" USING btree ("display_name");
CREATE UNIQUE INDEX IF NOT EXISTS "attendance_user_performance_idx" ON "attendance" USING btree ("user_id","performance_id");
CREATE UNIQUE INDEX IF NOT EXISTS "events_slug_idx" ON "events" USING btree ("slug");
CREATE INDEX IF NOT EXISTS "events_date_idx" ON "events" USING btree ("event_date");
CREATE INDEX IF NOT EXISTS "performances_event_idx" ON "performances" USING btree ("event_id");
CREATE INDEX IF NOT EXISTS "performances_artist_idx" ON "performances" USING btree ("artist_id");
CREATE INDEX IF NOT EXISTS "performances_date_idx" ON "performances" USING btree ("performance_date");
CREATE INDEX IF NOT EXISTS "reports_status_idx" ON "reports" USING btree ("status");
CREATE INDEX IF NOT EXISTS "revisions_entity_idx" ON "revisions" USING btree ("entity_type","entity_id");
CREATE INDEX IF NOT EXISTS "setlist_performance_idx" ON "setlist_items" USING btree ("performance_id");
CREATE UNIQUE INDEX IF NOT EXISTS "users_email_idx" ON "users" USING btree ("email");
CREATE UNIQUE INDEX IF NOT EXISTS "venues_slug_idx" ON "venues" USING btree ("slug");
CREATE INDEX IF NOT EXISTS "venues_city_idx" ON "venues" USING btree ("city");
