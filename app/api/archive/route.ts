import { getSupabaseAdminHeaders, getSupabaseRestUrl } from "../../../db";

async function read(path: string) {
  const response = await fetch(getSupabaseRestUrl(path), {
    headers: getSupabaseAdminHeaders(),
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Supabase returned ${response.status}.`);
  return response.json();
}

async function count(table: string) {
  const response = await fetch(getSupabaseRestUrl(`${table}?select=id&limit=1`), {
    headers: { ...getSupabaseAdminHeaders(), Prefer: "count=exact" },
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Unable to count ${table}.`);
  const contentRange = response.headers.get("content-range");
  return Number(contentRange?.split("/")[1] ?? 0);
}

export async function GET() {
  try {
    const [events, performances, artists, venues, performanceCount, artistCount, venueCount] = await Promise.all([
      read("events?select=id,slug,title,event_date,status,venues(display_name,city,country)&order=event_date.asc&limit=100"),
      read("performances?select=id,submitted_artist,submitted_venue,performance_date,status,created_at,artists(display_name,native_name,genre),events(title,venues(display_name,city,country)),setlist_items(id)&order=performance_date.desc&limit=100"),
      read("artists?select=id,slug,display_name,native_name,genre,status,performances(id)&order=display_name.asc&limit=100"),
      read("venues?select=id,slug,display_name,native_name,city,country,address,events(id)&order=display_name.asc&limit=100"),
      count("performances"),
      count("artists"),
      count("venues"),
    ]);

    const countries = new Set(
      (venues as Array<{ country?: string }>).map((venue) => venue.country).filter(Boolean),
    ).size;

    return Response.json({
      events,
      performances,
      artists,
      venues,
      stats: { performances: performanceCount, artists: artistCount, venues: venueCount, countries },
    });
  } catch {
    return Response.json({ error: "The archive is temporarily unavailable." }, { status: 503 });
  }
}
