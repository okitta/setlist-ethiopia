import { getSupabaseAdminHeaders, getSupabaseRestUrl } from "../../../db";
import { enrichPerformance, normalizeIdentity, type PerformanceEnrichment } from "../../../lib/gemini";

const MAX_TEXT = 5000;

function clean(value: unknown, max = 200) {
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}

function publicHeaders() {
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!key) throw new Error("Supabase is not configured.");
  return { apikey: key, Authorization: `Bearer ${key}` };
}

function slugify(value: string) {
  const slug = normalizeIdentity(value).replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "");
  return `${slug || "artist"}-${crypto.randomUUID().slice(0, 8)}`;
}

async function databaseRows(path: string, headers: ReturnType<typeof getSupabaseAdminHeaders>) {
  const response = await fetch(getSupabaseRestUrl(path), { headers, cache: "no-store" });
  if (!response.ok) throw new Error("Archive lookup failed.");
  return response.json() as Promise<Array<Record<string, unknown>>>;
}

async function resolveArtist(headers: ReturnType<typeof getSupabaseAdminHeaders>, submittedName: string, enrichment: PerformanceEnrichment | null) {
  const canonicalName = clean(enrichment?.artistName) || submittedName;
  const normalizedNames = [...new Set([submittedName, canonicalName, ...(enrichment?.aliases || []).map((item) => item.name)].map(normalizeIdentity).filter(Boolean))];

  for (const normalized of normalizedNames) {
    const direct = await databaseRows(`artists?select=id,display_name&normalized_name=eq.${encodeURIComponent(normalized)}&limit=1`, headers);
    if (direct[0]) return direct[0] as { id: number; display_name: string };
    const alias = await databaseRows(`artist_names?select=artists(id,display_name)&normalized_name=eq.${encodeURIComponent(normalized)}&limit=1`, headers);
    const linked = alias[0]?.artists as { id: number; display_name: string } | undefined;
    if (linked) return linked;
  }

  const response = await fetch(getSupabaseRestUrl("artists"), {
    method: "POST",
    headers,
    body: JSON.stringify({
      slug: slugify(canonicalName),
      display_name: canonicalName,
      normalized_name: normalizeIdentity(canonicalName),
      native_name: enrichment?.aliases.find((item) => item.script === "Ethiopic")?.name || null,
      genre: clean(enrichment?.genre) || null,
      description: clean(enrichment?.description, 1000) || null,
      status: "community",
    }),
  });
  if (!response.ok) throw new Error("Unable to create artist.");
  const [artist] = await response.json() as Array<{ id: number; display_name: string }>;

  const aliases = [
    { name: submittedName, language: "Unknown", script: /[\u1200-\u137F]/.test(submittedName) ? "Ethiopic" : "Latin" },
    ...(enrichment?.aliases || []),
  ];
  const uniqueAliases = [...new Map(aliases.filter((item) => clean(item.name)).map((item) => [normalizeIdentity(item.name), item])).values()];
  if (uniqueAliases.length) {
    await fetch(getSupabaseRestUrl("artist_names"), {
      method: "POST",
      headers,
      body: JSON.stringify(uniqueAliases.map((item) => ({
        artist_id: artist.id,
        name: clean(item.name),
        normalized_name: normalizeIdentity(item.name),
        language: clean(item.language) || "Unknown",
        script: clean(item.script) || "Other",
        kind: normalizeIdentity(item.name) === normalizeIdentity(canonicalName) ? "primary" : "alias",
      }))),
    });
  }
  return artist;
}

async function resolveVenue(headers: ReturnType<typeof getSupabaseAdminHeaders>, submittedName: string, enrichment: PerformanceEnrichment | null) {
  const canonicalName = clean(enrichment?.venueName) || submittedName;
  for (const name of [submittedName, canonicalName]) {
    const existing = await databaseRows(`venues?select=id,display_name&normalized_name=eq.${encodeURIComponent(normalizeIdentity(name))}&limit=1`, headers);
    if (existing[0]) return existing[0] as { id: number; display_name: string };
  }
  const response = await fetch(getSupabaseRestUrl("venues"), {
    method: "POST",
    headers,
    body: JSON.stringify({
      slug: slugify(canonicalName),
      display_name: canonicalName,
      normalized_name: normalizeIdentity(canonicalName),
      city: clean(enrichment?.city) || "Unknown",
      country: clean(enrichment?.country) || "Ethiopia",
    }),
  });
  if (!response.ok) throw new Error("Unable to create venue.");
  const [venue] = await response.json() as Array<{ id: number; display_name: string }>;
  return venue;
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
      getSupabaseRestUrl("performances?select=id,submitted_artist,submitted_venue,performance_date,status,created_at,setlist_items(id)&order=created_at.desc&limit=20"),
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

    const [knownArtistRows, knownVenueRows] = await Promise.all([
      databaseRows("artists?select=display_name&limit=100", headers),
      databaseRows("venues?select=display_name&limit=100", headers),
    ]);
    const enrichment = await enrichPerformance({
      artist,
      venue,
      source: evidence,
      knownArtists: knownArtistRows.map((row) => String(row.display_name || "")).filter(Boolean),
      knownVenues: knownVenueRows.map((row) => String(row.display_name || "")).filter(Boolean),
    });
    const [resolvedArtist, resolvedVenue] = await Promise.all([
      resolveArtist(headers, artist, enrichment),
      resolveVenue(headers, venue, enrichment),
    ]);

    const performanceResponse = await fetch(getSupabaseRestUrl("performances"), {
      method: "POST",
      headers,
      body: JSON.stringify({
        artist_id: resolvedArtist.id,
        submitted_artist: artist,
        submitted_venue: resolvedVenue.display_name || venue,
        performance_date: `${date}T12:00:00Z`,
        evidence,
        submitted_by: account.id,
        status: evidence ? "source_backed" : "community",
      }),
    });
    if (!performanceResponse.ok) throw new Error("Unable to create performance.");
    const [performance] = await performanceResponse.json() as Array<{ id: number; status: string }>;

    if (songLines.length) {
      const setlistResponse = await fetch(getSupabaseRestUrl("setlist_items"), {
        method: "POST",
        headers,
        body: JSON.stringify(songLines.map((title, index) => ({ performance_id: performance.id, position: index + 1, title }))),
      });
      if (!setlistResponse.ok) throw new Error("Unable to save the setlist.");
    }

    const revisionResponse = await fetch(getSupabaseRestUrl("revisions"), {
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
    if (!revisionResponse.ok) throw new Error("Unable to record the contribution history.");

    return Response.json({ performance }, { status: 201 });
  } catch {
    return Response.json({ error: "The contribution could not be saved. Please try again." }, { status: 500 });
  }
}
