import { desc, eq } from "drizzle-orm";
import { getDb } from "../../../db";
import { performances, revisions, setlistItems, users } from "../../../db/schema";
import { getChatGPTUser } from "../../chatgpt-auth";

const MAX_TEXT = 5000;

function clean(value: unknown, max = 200) {
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}

export async function GET() {
  try {
    const db = getDb();
    const rows = await db
      .select({
        id: performances.id,
        artist: performances.submittedArtist,
        venue: performances.submittedVenue,
        date: performances.performanceDate,
        status: performances.status,
        createdAt: performances.createdAt,
      })
      .from(performances)
      .orderBy(desc(performances.createdAt))
      .limit(20);

    return Response.json({ performances: rows });
  } catch {
    return Response.json(
      { error: "The archive is temporarily unavailable." },
      { status: 503 },
    );
  }
}

export async function POST(request: Request) {
  const user = await getChatGPTUser();
  if (!user) {
    return Response.json({ error: "Sign in is required to contribute." }, { status: 401 });
  }

  let payload: Record<string, unknown>;
  try {
    payload = await request.json() as Record<string, unknown>;
  } catch {
    return Response.json({ error: "Invalid request body." }, { status: 400 });
  }

  const artist = clean(payload.artist);
  const venue = clean(payload.venue);
  const date = clean(payload.date, 10);
  const evidence = clean(payload.source, MAX_TEXT);
  const songLines = Array.isArray(payload.songs)
    ? payload.songs.map((song) => clean(song)).filter(Boolean).slice(0, 100)
    : clean(payload.songs, MAX_TEXT).split("\n").map((song) => song.trim()).filter(Boolean).slice(0, 100);

  if (artist.length < 2 || venue.length < 2 || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return Response.json(
      { error: "Artist, venue, and a valid date are required." },
      { status: 400 },
    );
  }

  try {
    const db = getDb();
    await db
      .insert(users)
      .values({ email: user.email, displayName: user.fullName })
      .onConflictDoUpdate({
        target: users.email,
        set: { displayName: user.fullName },
      });

    const [account] = await db.select().from(users).where(eq(users.email, user.email)).limit(1);
    const [performance] = await db.insert(performances).values({
      submittedArtist: artist,
      submittedVenue: venue,
      performanceDate: date,
      evidence,
      submittedBy: account.id,
      status: evidence ? "source_backed" : "community",
    }).returning();

    if (songLines.length) {
      await db.insert(setlistItems).values(
        songLines.map((title, index) => ({
          performanceId: performance.id,
          position: index + 1,
          title,
        })),
      );
    }

    await db.insert(revisions).values({
      entityType: "performance",
      entityId: performance.id,
      actorId: account.id,
      reason: "Initial community submission",
      afterJson: JSON.stringify({ artist, venue, date, songs: songLines, evidence }),
    });

    return Response.json(
      { performance: { id: performance.id, status: performance.status } },
      { status: 201 },
    );
  } catch {
    return Response.json(
      { error: "The contribution could not be saved. Please try again." },
      { status: 500 },
    );
  }
}
