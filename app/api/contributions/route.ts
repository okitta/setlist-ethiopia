import { getSupabaseAdminHeaders, getSupabaseRestUrl } from "../../../db";

const MAX_TEXT = 5000;

function clean(value: unknown, max = 200) {
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}

function publicHeaders() {
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!key) throw new Error("Supabase is not configured.");
  return { apikey: key, Authorization: `Bearer ${key}` };
}

async function authenticatedUser(request: Request) {
  const bearer = request.headers.get("authorization");
  if (!bearer?.startsWith("Bearer ")) return null;
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  if (!url) return null;
  const response = await fetch(`${url}/auth/v1/user`, {
    headers: { ...publicHeaders(), Authorization: bearer },
    cache: "no-store",
  });
  return response.ok ? response.json() as Promise<{ email?: string; user_metadata?: { full_name?: string } }> : null;
}

export async function GET() {
  try {
    const response = await fetch(
      getSupabaseRestUrl("performances?select=id,submitted_artist,submitted_venue,performance_date,status,created_at&order=created_at.desc&limit=20"),
      { headers: getSupabaseAdminHeaders(), cache: "no-store" },
    );
    if (!response.ok) throw new Error("Database request failed.");
    return Response.json({ performances: await response.json() });
  } catch {
    return Response.json({ error: "The archive is temporarily unavailable." }, { status: 503 });
  }
}

export async function POST(request: Request) {
  const authUser = await authenticatedUser(request);
  if (!authUser?.email) {
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
    return Response.json({ error: "Artist, venue, and a valid date are required." }, { status: 400 });
  }

  try {
    const headers = getSupabaseAdminHeaders();
    const userResponse = await fetch(getSupabaseRestUrl("users?on_conflict=email"), {
      method: "POST",
      headers: { ...headers, Prefer: "resolution=merge-duplicates,return=representation" },
      body: JSON.stringify({ email: authUser.email, display_name: authUser.user_metadata?.full_name ?? null }),
    });
    if (!userResponse.ok) throw new Error("Unable to resolve contributor.");
    const [account] = await userResponse.json() as Array<{ id: number }>;

    const performanceResponse = await fetch(getSupabaseRestUrl("performances"), {
      method: "POST",
      headers,
      body: JSON.stringify({
        submitted_artist: artist,
        submitted_venue: venue,
        performance_date: `${date}T12:00:00Z`,
        evidence,
        submitted_by: account.id,
        status: evidence ? "source_backed" : "community",
      }),
    });
    if (!performanceResponse.ok) throw new Error("Unable to create performance.");
    const [performance] = await performanceResponse.json() as Array<{ id: number; status: string }>;

    if (songLines.length) {
      await fetch(getSupabaseRestUrl("setlist_items"), {
        method: "POST",
        headers,
        body: JSON.stringify(songLines.map((title, index) => ({ performance_id: performance.id, position: index + 1, title }))),
      });
    }

    await fetch(getSupabaseRestUrl("revisions"), {
      method: "POST",
      headers,
      body: JSON.stringify({
        entity_type: "performance",
        entity_id: performance.id,
        actor_id: account.id,
        reason: "Initial community submission",
        after_json: JSON.stringify({ artist, venue, date, songs: songLines, evidence }),
      }),
    });

    return Response.json({ performance }, { status: 201 });
  } catch {
    return Response.json({ error: "The contribution could not be saved. Please try again." }, { status: 500 });
  }
}
