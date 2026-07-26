import { getSupabaseAdminHeaders, getSupabaseRestUrl } from "../../../../db";
import { generateStructured, normalizeIdentity } from "../../../../lib/gemini";

type Kind = "artist" | "venue" | "performance";
type Suggestion = { value: string; meta: string };

async function authorized(request: Request) {
  const bearer = request.headers.get("authorization");
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!bearer?.startsWith("Bearer ") || !url || !key) return false;
  const response = await fetch(`${url}/auth/v1/user`, { headers: { apikey: key, Authorization: bearer }, cache: "no-store" });
  return response.ok;
}

async function read(path: string) {
  const response = await fetch(getSupabaseRestUrl(path), { headers: getSupabaseAdminHeaders(), cache: "no-store" });
  return response.ok ? response.json() : [];
}

export async function GET(request: Request) {
  if (!await authorized(request)) return Response.json({ error: "Sign in is required." }, { status: 401 });
  const url = new URL(request.url);
  const query = (url.searchParams.get("q") || "").trim().slice(0, 120);
  const kind = (url.searchParams.get("kind") || "artist") as Kind;
  if (query.length < 2 || !["artist", "venue", "performance"].includes(kind)) return Response.json({ suggestions: [] });

  let candidates: Suggestion[] = [];
  if (kind === "artist") {
    const [artists, aliases] = await Promise.all([
      read("artists?select=display_name,native_name,genre&limit=200"),
      read("artist_names?select=name,language,script,artists(display_name)&limit=300"),
    ]);
    candidates = [
      ...(artists as Array<{ display_name: string; native_name?: string; genre?: string }>).map((item) => ({ value: item.display_name, meta: [item.native_name, item.genre].filter(Boolean).join(" · ") })),
      ...(aliases as Array<{ name: string; language?: string; script?: string }>).map((item) => ({ value: item.name, meta: [item.language, item.script].filter(Boolean).join(" · ") })),
    ];
  } else if (kind === "venue") {
    const venues = await read("venues?select=display_name,city,country&limit=200");
    candidates = (venues as Array<{ display_name: string; city: string; country: string }>).map((item) => ({ value: item.display_name, meta: `${item.city} · ${item.country}` }));
  } else {
    const performances = await read("performances?select=submitted_artist,submitted_venue,performance_date,artists(display_name)&order=performance_date.desc&limit=200");
    candidates = (performances as Array<{ submitted_artist?: string; submitted_venue?: string; performance_date: string; artists?: { display_name?: string } }>).map((item) => ({
      value: item.artists?.display_name || item.submitted_artist || "Unknown artist",
      meta: [item.submitted_venue, item.performance_date?.slice(0, 10)].filter(Boolean).join(" · "),
    }));
  }

  const normalizedQuery = normalizeIdentity(query);
  const unique = [...new Map(candidates.map((item) => [normalizeIdentity(`${item.value}|${item.meta}`), item])).values()];
  const lexical = unique
    .map((item) => ({ item, score: normalizeIdentity(item.value).startsWith(normalizedQuery) ? 3 : normalizeIdentity(`${item.value} ${item.meta}`).includes(normalizedQuery) ? 2 : 0 }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score)
    .map(({ item }) => item)
    .slice(0, 8);

  if (lexical.length >= 5 || unique.length === 0) return Response.json({ suggestions: lexical, source: "archive" });

  const pool = unique.slice(0, 60);
  const ranked = await generateStructured<{ indexes: number[] }>(
    `Rank only the supplied ${kind} candidates for the query "${query}". Account for capitalization, Ethiopic/Latin script, spelling variants, and transliteration. Do not invent candidates. Return up to 8 zero-based indexes.\n${pool.map((item, index) => `${index}: ${item.value} — ${item.meta}`).join("\n")}`,
    { type: "object", properties: { indexes: { type: "array", maxItems: 8, items: { type: "integer" } } }, required: ["indexes"] },
  );
  const aiSuggestions = (ranked?.indexes || []).map((index) => pool[index]).filter((item): item is Suggestion => Boolean(item));
  return Response.json({ suggestions: aiSuggestions.length ? aiSuggestions : lexical, source: aiSuggestions.length ? "ai-ranked" : "archive" });
}
