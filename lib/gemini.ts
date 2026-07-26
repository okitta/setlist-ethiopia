const MODEL = process.env.GEMINI_MODEL || "gemini-2.5-flash-lite";
const RPM_LIMIT = Number(process.env.GEMINI_APP_RPM_LIMIT || 5);
const DAILY_LIMIT = Number(process.env.GEMINI_APP_DAILY_LIMIT || 100);

type UsageWindow = { minute: string; minuteCalls: number; day: string; dayCalls: number };
const globalUsage = globalThis as typeof globalThis & { __zemaGeminiUsage?: UsageWindow };

export function normalizeIdentity(value: string) {
  return value.normalize("NFKC").trim().replace(/\s+/g, " ").toLocaleLowerCase("und");
}

function reserveRequest() {
  const now = new Date();
  const minute = now.toISOString().slice(0, 16);
  const day = now.toISOString().slice(0, 10);
  const usage = globalUsage.__zemaGeminiUsage ?? { minute, minuteCalls: 0, day, dayCalls: 0 };
  if (usage.minute !== minute) {
    usage.minute = minute;
    usage.minuteCalls = 0;
  }
  if (usage.day !== day) {
    usage.day = day;
    usage.dayCalls = 0;
  }
  if (usage.minuteCalls >= RPM_LIMIT || usage.dayCalls >= DAILY_LIMIT) return false;
  usage.minuteCalls += 1;
  usage.dayCalls += 1;
  globalUsage.__zemaGeminiUsage = usage;
  return true;
}

export async function generateStructured<T>(prompt: string, responseSchema: Record<string, unknown>): Promise<T | null> {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey || !reserveRequest()) return null;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8_000);
  try {
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(MODEL)}:generateContent`,
      {
        method: "POST",
        headers: { "x-goog-api-key": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: prompt.slice(0, 12_000) }] }],
          generationConfig: {
            temperature: 0.1,
            maxOutputTokens: 700,
            responseMimeType: "application/json",
            responseSchema,
          },
        }),
        signal: controller.signal,
      },
    );
    if (!response.ok) return null;
    const result = await response.json() as { candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }> };
    const text = result.candidates?.[0]?.content?.parts?.[0]?.text;
    return text ? JSON.parse(text) as T : null;
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

export type PerformanceEnrichment = {
  artistName: string;
  aliases: Array<{ name: string; language: string; script: string }>;
  genre: string;
  description: string;
  venueName: string;
  city: string;
  country: string;
};

export async function enrichPerformance(input: { artist: string; venue: string; source: string; knownArtists: string[]; knownVenues: string[] }) {
  const schema = {
    type: "object",
    properties: {
      artistName: { type: "string" },
      aliases: {
        type: "array",
        maxItems: 4,
        items: {
          type: "object",
          properties: { name: { type: "string" }, language: { type: "string" }, script: { type: "string" } },
          required: ["name", "language", "script"],
        },
      },
      genre: { type: "string" },
      description: { type: "string" },
      venueName: { type: "string" },
      city: { type: "string" },
      country: { type: "string" },
    },
    required: ["artistName", "aliases", "genre", "description", "venueName", "city", "country"],
  };
  return generateStructured<PerformanceEnrichment>(
    `Resolve an Ethiopian live-music contribution into conservative archive metadata.
Never invent facts. Prefer an exact known entity even when capitalization, spacing, transliteration, or script differs.
Input artist: ${input.artist}
Input venue: ${input.venue}
Context: ${input.source || "none"}
Known artists: ${input.knownArtists.join(" | ") || "none"}
Known venues: ${input.knownVenues.join(" | ") || "none"}
For every artist spelling, classify language (for example Amharic, English, Oromo, Tigrinya, Other) and script (Ethiopic, Latin, Other).
Use an empty string when genre, description, city, or country is not supported by the input.`,
    schema,
  );
}
