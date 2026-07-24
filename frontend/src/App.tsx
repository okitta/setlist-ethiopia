import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import type { Artist, Features, Performance } from "./types";
import { PerformancePanel } from "./PerformancePanel";

/**
 * The first vertical slice, end to end:
 *   find an artist -> open a performance -> mark attendance / add a song ->
 *   see the contribution and revision history.
 *
 * Every async view renders explicit loading / empty / error / success states, and
 * write actions surface permission-denied clearly (Definition of Ready).
 */
const DEMO_USERS = ["fan_hana", "curator_sam"];

export function App() {
  // Identity is a demo user switcher standing in for real auth in slice 1.
  const [user, setUser] = useState(DEMO_USERS[0]);
  const [features, setFeatures] = useState<Features | null>(null);

  const [query, setQuery] = useState("");
  const [artists, setArtists] = useState<Artist[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);

  const [selectedArtist, setSelectedArtist] = useState<Artist | null>(null);
  const [performances, setPerformances] = useState<Performance[] | null>(null);
  const [selectedPerformanceId, setSelectedPerformanceId] = useState<number | null>(null);

  useEffect(() => {
    api.features().then(setFeatures).catch(() => setFeatures(null));
  }, []);

  async function runSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearching(true);
    setSearchError(null);
    setSelectedArtist(null);
    setPerformances(null);
    setSelectedPerformanceId(null);
    try {
      setArtists(await api.searchArtists(query));
    } catch (err) {
      setSearchError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSearching(false);
    }
  }

  async function openArtist(artist: Artist) {
    setSelectedArtist(artist);
    setSelectedPerformanceId(null);
    setPerformances(null);
    try {
      setPerformances(await api.performances(artist.id));
    } catch {
      setPerformances([]);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1>🎵 Setlist Ethiopia</h1>
        <label className="user-switch">
          Signed in as{" "}
          <select value={user} onChange={(e) => setUser(e.target.value)}>
            {DEMO_USERS.map((u) => (
              <option key={u} value={u}>
                {u}
              </option>
            ))}
          </select>
        </label>
      </header>

      <main className="layout">
        <section className="col" aria-label="Discover artists">
          <form onSubmit={runSearch} className="search">
            <label htmlFor="q">Find an artist</label>
            <div className="search-row">
              <input
                id="q"
                value={query}
                placeholder="e.g. Aster"
                onChange={(e) => setQuery(e.target.value)}
              />
              <button type="submit" disabled={searching}>
                {searching ? "Searching…" : "Search"}
              </button>
            </div>
          </form>

          {searchError && <p className="error" role="alert">{searchError}</p>}
          {artists === null && !searchError && (
            <p className="muted">Search for an artist to begin.</p>
          )}
          {artists?.length === 0 && <p className="muted">No artists matched “{query}”.</p>}
          <ul className="list">
            {artists?.map((a) => (
              <li key={a.id}>
                <button
                  className={selectedArtist?.id === a.id ? "row active" : "row"}
                  onClick={() => openArtist(a)}
                >
                  {a.name}
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="col" aria-label="Performances">
          {!selectedArtist && <p className="muted">Select an artist to see performances.</p>}
          {selectedArtist && performances === null && <p className="muted">Loading performances…</p>}
          {selectedArtist && performances?.length === 0 && (
            <p className="muted">No performances documented yet for {selectedArtist.name}.</p>
          )}
          <ul className="list">
            {performances?.map((p) => (
              <li key={p.id}>
                <button
                  className={selectedPerformanceId === p.id ? "row active" : "row"}
                  onClick={() => setSelectedPerformanceId(p.id)}
                >
                  <strong>{p.performed_on}</strong> — {p.venue}, {p.city}
                  <span className="badge">{p.attendance_count} attending</span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="col" aria-label="Performance detail">
          {selectedPerformanceId ? (
            <PerformancePanel
              performanceId={selectedPerformanceId}
              user={user}
              features={features}
              onChanged={() => selectedArtist && openArtist(selectedArtist)}
            />
          ) : (
            <p className="muted">Open a performance to view its setlist and history.</p>
          )}
        </section>
      </main>
    </div>
  );
}
