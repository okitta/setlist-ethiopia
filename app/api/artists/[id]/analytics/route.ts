import { getSupabaseAdminHeaders, getSupabaseRestUrl } from "../../../../../db";
import { normalizeIdentity } from "../../../../../lib/gemini";

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!/^\d+$/.test(id)) return Response.json({ error: "Invalid artist." }, { status: 400 });
  const headers = getSupabaseAdminHeaders();
  const [artistResponse, performanceResponse] = await Promise.all([
    fetch(getSupabaseRestUrl(`artists?select=id,display_name,native_name,genre,description,status&id=eq.${id}&limit=1`), { headers, cache: "no-store" }),
    fetch(getSupabaseRestUrl(`performances?select=id,performance_date,status,submitted_venue,setlist_items(title,position)&artist_id=eq.${id}&order=performance_date.desc&limit=500`), { headers, cache: "no-store" }),
  ]);
  if (!artistResponse.ok || !performanceResponse.ok) return Response.json({ error: "Artist analytics are unavailable." }, { status: 503 });
  const [artist] = await artistResponse.json() as Array<Record<string, unknown>>;
  if (!artist) return Response.json({ error: "Artist not found." }, { status: 404 });
  const performances = await performanceResponse.json() as Array<{ performance_date: string; submitted_venue?: string; setlist_items?: Array<{ title: string }> }>;

  const cutoff = Date.now() - 365 * 24 * 60 * 60 * 1000;
  const allSongs = new Map<string, { title: string; count: number }>();
  const recentSongs = new Map<string, { title: string; count: number }>();
  const venues = new Map<string, { name: string; count: number }>();
  for (const performance of performances) {
    const recent = new Date(performance.performance_date).getTime() >= cutoff;
    if (performance.submitted_venue) {
      const key = normalizeIdentity(performance.submitted_venue);
      const current = venues.get(key) || { name: performance.submitted_venue, count: 0 };
      current.count += 1;
      venues.set(key, current);
    }
    for (const song of performance.setlist_items || []) {
      const key = normalizeIdentity(song.title);
      const all = allSongs.get(key) || { title: song.title, count: 0 };
      all.count += 1;
      allSongs.set(key, all);
      if (recent) {
        const item = recentSongs.get(key) || { title: song.title, count: 0 };
        item.count += 1;
        recentSongs.set(key, item);
      }
    }
  }
  const top = (map: Map<string, { title: string; count: number }>) => [...map.values()].sort((a, b) => b.count - a.count || a.title.localeCompare(b.title)).slice(0, 10);
  return Response.json({
    artist,
    metrics: {
      performances: performances.length,
      documentedSongs: [...allSongs.values()].reduce((sum, item) => sum + item.count, 0),
      uniqueSongs: allSongs.size,
      recentPerformances: performances.filter((item) => new Date(item.performance_date).getTime() >= cutoff).length,
    },
    topSongs: top(allSongs),
    recentTopSongs: top(recentSongs),
    topVenues: [...venues.values()].sort((a, b) => b.count - a.count).slice(0, 8),
  });
}
