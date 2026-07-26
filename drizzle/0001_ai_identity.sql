ALTER TABLE "artists" ADD COLUMN IF NOT EXISTS "normalized_name" text;
ALTER TABLE "artists" ADD COLUMN IF NOT EXISTS "description" text;
ALTER TABLE "artist_names" ADD COLUMN IF NOT EXISTS "normalized_name" text;
ALTER TABLE "venues" ADD COLUMN IF NOT EXISTS "normalized_name" text;

UPDATE "artists" SET "normalized_name" = lower(regexp_replace(trim("display_name"), '\s+', ' ', 'g')) WHERE "normalized_name" IS NULL;
UPDATE "artist_names" SET "normalized_name" = lower(regexp_replace(trim("name"), '\s+', ' ', 'g')) WHERE "normalized_name" IS NULL;
UPDATE "venues" SET "normalized_name" = lower(regexp_replace(trim("display_name"), '\s+', ' ', 'g')) WHERE "normalized_name" IS NULL;

WITH duplicates AS (
  SELECT id, min(id) OVER (PARTITION BY normalized_name) AS canonical_id
  FROM artists
)
UPDATE performances p SET artist_id = d.canonical_id FROM duplicates d WHERE p.artist_id = d.id AND d.id <> d.canonical_id;

WITH duplicates AS (
  SELECT id, min(id) OVER (PARTITION BY normalized_name) AS canonical_id
  FROM artists
)
UPDATE artist_names n SET artist_id = d.canonical_id FROM duplicates d WHERE n.artist_id = d.id AND d.id <> d.canonical_id;

DELETE FROM artists a USING artists canonical
WHERE a.normalized_name = canonical.normalized_name AND a.id > canonical.id;

WITH duplicates AS (
  SELECT id, min(id) OVER (PARTITION BY normalized_name) AS canonical_id
  FROM venues
)
UPDATE events e SET venue_id = d.canonical_id FROM duplicates d WHERE e.venue_id = d.id AND d.id <> d.canonical_id;

DELETE FROM venues v USING venues canonical
WHERE v.normalized_name = canonical.normalized_name AND v.id > canonical.id;

DELETE FROM artist_names a USING artist_names canonical
WHERE a.artist_id = canonical.artist_id AND a.normalized_name = canonical.normalized_name AND a.id > canonical.id;

ALTER TABLE "artists" ALTER COLUMN "normalized_name" SET NOT NULL;
ALTER TABLE "artist_names" ALTER COLUMN "normalized_name" SET NOT NULL;
ALTER TABLE "venues" ALTER COLUMN "normalized_name" SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "artists_normalized_name_idx" ON "artists" ("normalized_name");
CREATE UNIQUE INDEX IF NOT EXISTS "artist_names_artist_normalized_idx" ON "artist_names" ("artist_id", "normalized_name");
CREATE UNIQUE INDEX IF NOT EXISTS "venues_normalized_name_idx" ON "venues" ("normalized_name");
