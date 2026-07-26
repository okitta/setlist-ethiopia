import { index, integer, pgTable, serial, text, timestamp, uniqueIndex } from "drizzle-orm/pg-core";

const createdAt = timestamp("created_at", { withTimezone: true }).notNull().defaultNow();

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  email: text("email").notNull(),
  displayName: text("display_name"),
  role: text("role", { enum: ["contributor", "steward", "moderator", "admin"] }).notNull().default("contributor"),
  createdAt,
}, (table) => [uniqueIndex("users_email_idx").on(table.email)]);

export const artists = pgTable("artists", {
  id: serial("id").primaryKey(),
  slug: text("slug").notNull(),
  displayName: text("display_name").notNull(),
  normalizedName: text("normalized_name").notNull(),
  nativeName: text("native_name"),
  genre: text("genre"),
  description: text("description"),
  status: text("status").notNull().default("community"),
  createdAt,
}, (table) => [uniqueIndex("artists_slug_idx").on(table.slug), index("artists_name_idx").on(table.displayName), uniqueIndex("artists_normalized_name_idx").on(table.normalizedName)]);

export const artistNames = pgTable("artist_names", {
  id: serial("id").primaryKey(),
  artistId: integer("artist_id").notNull().references(() => artists.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  normalizedName: text("normalized_name").notNull(),
  language: text("language"),
  script: text("script"),
  kind: text("kind").notNull().default("alias"),
}, (table) => [index("artist_names_artist_idx").on(table.artistId), index("artist_names_name_idx").on(table.name), uniqueIndex("artist_names_artist_normalized_idx").on(table.artistId, table.normalizedName)]);

export const venues = pgTable("venues", {
  id: serial("id").primaryKey(),
  slug: text("slug").notNull(),
  displayName: text("display_name").notNull(),
  normalizedName: text("normalized_name").notNull(),
  nativeName: text("native_name"),
  city: text("city").notNull(),
  country: text("country").notNull().default("Ethiopia"),
  address: text("address"),
  createdAt,
}, (table) => [uniqueIndex("venues_slug_idx").on(table.slug), index("venues_city_idx").on(table.city), uniqueIndex("venues_normalized_name_idx").on(table.normalizedName)]);

export const events = pgTable("events", {
  id: serial("id").primaryKey(),
  slug: text("slug").notNull(),
  title: text("title").notNull(),
  eventDate: timestamp("event_date", { withTimezone: true }).notNull(),
  venueId: integer("venue_id").references(() => venues.id),
  status: text("status", { enum: ["announced", "completed", "cancelled", "postponed"] }).notNull().default("announced"),
  sourceUrl: text("source_url"),
  createdBy: integer("created_by").references(() => users.id),
  createdAt,
}, (table) => [uniqueIndex("events_slug_idx").on(table.slug), index("events_date_idx").on(table.eventDate)]);

export const performances = pgTable("performances", {
  id: serial("id").primaryKey(),
  eventId: integer("event_id").references(() => events.id),
  artistId: integer("artist_id").references(() => artists.id),
  submittedArtist: text("submitted_artist"),
  submittedVenue: text("submitted_venue"),
  performanceDate: timestamp("performance_date", { withTimezone: true }).notNull(),
  status: text("status", { enum: ["draft", "community", "source_backed", "reviewed", "disputed"] }).notNull().default("community"),
  evidence: text("evidence"),
  submittedBy: integer("submitted_by").references(() => users.id),
  createdAt,
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
}, (table) => [
  index("performances_event_idx").on(table.eventId),
  index("performances_artist_idx").on(table.artistId),
  index("performances_date_idx").on(table.performanceDate),
]);

export const setlistItems = pgTable("setlist_items", {
  id: serial("id").primaryKey(),
  performanceId: integer("performance_id").notNull().references(() => performances.id, { onDelete: "cascade" }),
  position: integer("position").notNull(),
  title: text("title").notNull(),
  section: text("section").notNull().default("main"),
  note: text("note"),
  confidence: text("confidence").notNull().default("community"),
}, (table) => [index("setlist_performance_idx").on(table.performanceId)]);

export const attendance = pgTable("attendance", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  performanceId: integer("performance_id").notNull().references(() => performances.id, { onDelete: "cascade" }),
  visibility: text("visibility", { enum: ["private", "followers", "public"] }).notNull().default("private"),
  createdAt,
}, (table) => [uniqueIndex("attendance_user_performance_idx").on(table.userId, table.performanceId)]);

export const revisions = pgTable("revisions", {
  id: serial("id").primaryKey(),
  entityType: text("entity_type").notNull(),
  entityId: integer("entity_id").notNull(),
  actorId: integer("actor_id").references(() => users.id),
  reason: text("reason"),
  beforeJson: text("before_json"),
  afterJson: text("after_json").notNull(),
  createdAt,
}, (table) => [index("revisions_entity_idx").on(table.entityType, table.entityId)]);

export const reports = pgTable("reports", {
  id: serial("id").primaryKey(),
  entityType: text("entity_type").notNull(),
  entityId: integer("entity_id").notNull(),
  reporterId: integer("reporter_id").references(() => users.id),
  category: text("category").notNull(),
  detail: text("detail"),
  status: text("status").notNull().default("open"),
  createdAt,
}, (table) => [index("reports_status_idx").on(table.status)]);
