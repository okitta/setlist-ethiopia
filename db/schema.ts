import { sql } from "drizzle-orm";
import { index, integer, sqliteTable, text, uniqueIndex } from "drizzle-orm/sqlite-core";

export const users = sqliteTable("users", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  email: text("email").notNull(),
  displayName: text("display_name"),
  role: text("role", { enum: ["contributor", "steward", "moderator", "admin"] }).notNull().default("contributor"),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
}, (table) => [uniqueIndex("users_email_idx").on(table.email)]);

export const artists = sqliteTable("artists", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  slug: text("slug").notNull(),
  displayName: text("display_name").notNull(),
  nativeName: text("native_name"),
  genre: text("genre"),
  status: text("status").notNull().default("community"),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
}, (table) => [uniqueIndex("artists_slug_idx").on(table.slug), index("artists_name_idx").on(table.displayName)]);

export const artistNames = sqliteTable("artist_names", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  artistId: integer("artist_id").notNull().references(() => artists.id),
  name: text("name").notNull(),
  language: text("language"),
  script: text("script"),
  kind: text("kind").notNull().default("alias"),
}, (table) => [index("artist_names_artist_idx").on(table.artistId), index("artist_names_name_idx").on(table.name)]);

export const venues = sqliteTable("venues", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  slug: text("slug").notNull(),
  displayName: text("display_name").notNull(),
  nativeName: text("native_name"),
  city: text("city").notNull(),
  country: text("country").notNull().default("Ethiopia"),
  address: text("address"),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
}, (table) => [uniqueIndex("venues_slug_idx").on(table.slug), index("venues_city_idx").on(table.city)]);

export const events = sqliteTable("events", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  slug: text("slug").notNull(),
  title: text("title").notNull(),
  eventDate: text("event_date").notNull(),
  venueId: integer("venue_id").references(() => venues.id),
  status: text("status", { enum: ["announced", "completed", "cancelled", "postponed"] }).notNull().default("announced"),
  sourceUrl: text("source_url"),
  createdBy: integer("created_by").references(() => users.id),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
}, (table) => [uniqueIndex("events_slug_idx").on(table.slug), index("events_date_idx").on(table.eventDate)]);

export const performances = sqliteTable("performances", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  eventId: integer("event_id").references(() => events.id),
  artistId: integer("artist_id").references(() => artists.id),
  submittedArtist: text("submitted_artist"),
  submittedVenue: text("submitted_venue"),
  performanceDate: text("performance_date").notNull(),
  status: text("status", { enum: ["draft", "community", "source_backed", "reviewed", "disputed"] }).notNull().default("community"),
  evidence: text("evidence"),
  submittedBy: integer("submitted_by").references(() => users.id),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
}, (table) => [index("performances_event_idx").on(table.eventId), index("performances_artist_idx").on(table.artistId), index("performances_date_idx").on(table.performanceDate)]);

export const setlistItems = sqliteTable("setlist_items", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  performanceId: integer("performance_id").notNull().references(() => performances.id),
  position: integer("position").notNull(),
  title: text("title").notNull(),
  section: text("section").notNull().default("main"),
  note: text("note"),
  confidence: text("confidence").notNull().default("community"),
}, (table) => [index("setlist_performance_idx").on(table.performanceId)]);

export const attendance = sqliteTable("attendance", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  userId: integer("user_id").notNull().references(() => users.id),
  performanceId: integer("performance_id").notNull().references(() => performances.id),
  visibility: text("visibility", { enum: ["private", "followers", "public"] }).notNull().default("private"),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
}, (table) => [uniqueIndex("attendance_user_performance_idx").on(table.userId, table.performanceId)]);

export const revisions = sqliteTable("revisions", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  entityType: text("entity_type").notNull(),
  entityId: integer("entity_id").notNull(),
  actorId: integer("actor_id").references(() => users.id),
  reason: text("reason"),
  beforeJson: text("before_json"),
  afterJson: text("after_json").notNull(),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
}, (table) => [index("revisions_entity_idx").on(table.entityType, table.entityId)]);

export const reports = sqliteTable("reports", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  entityType: text("entity_type").notNull(),
  entityId: integer("entity_id").notNull(),
  reporterId: integer("reporter_id").references(() => users.id),
  category: text("category").notNull(),
  detail: text("detail"),
  status: text("status").notNull().default("open"),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
}, (table) => [index("reports_status_idx").on(table.status)]);
