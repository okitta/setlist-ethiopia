"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type View = "home" | "explore" | "saved" | "profile";
type ExploreFilter = "All" | "Events" | "Artists" | "Venues";
type ContributionInput = { artist: string; date: string; venue: string; songs: string; source: string };
type DbPerformance = {
  id: number;
  submitted_artist: string | null;
  submitted_venue: string | null;
  performance_date: string;
  status: string;
  created_at: string;
  artists: { display_name: string; native_name: string | null; genre: string | null } | null;
  events: { title: string; venues: DbVenue | null } | null;
  setlist_items?: Array<{ id: number }>;
};
type DbEvent = {
  id: number;
  slug: string;
  title: string;
  event_date: string;
  status: string;
  venues: DbVenue | null;
};
type DbArtist = {
  id: number;
  slug: string;
  display_name: string;
  native_name: string | null;
  genre: string | null;
  status: string;
  performances?: Array<{ id: number }>;
};
type DbVenue = {
  id?: number;
  slug?: string;
  display_name: string;
  native_name?: string | null;
  city: string;
  country: string;
  address?: string | null;
  events?: Array<{ id: number }>;
};
type ArchiveData = {
  events: DbEvent[];
  performances: DbPerformance[];
  artists: DbArtist[];
  venues: DbVenue[];
  stats: { performances: number; artists: number; venues: number; countries: number };
};
type EventView = {
  id: string;
  day: string;
  month: string;
  title: string;
  native: string;
  venue: string;
  city: string;
  kind: string;
  songs: number;
  status: string;
  accent: string;
};

async function fetchArchive() {
  const response = await fetch("/api/archive", { cache: "no-store" });
  if (!response.ok) throw new Error("The community feed is unavailable.");
  return response.json() as Promise<ArchiveData>;
}

const collections = [
  { eyebrow: "ARCHIVE COLLECTION", title: "Documented performances", copy: "Explore the performances preserved by the community.", stat: "performances" as const, label: "performances", mark: "፷", tone: "dark" },
  { eyebrow: "ARTIST INDEX", title: "Artists in the archive", copy: "Find performers across generations, genres and scripts.", stat: "artists" as const, label: "artists", mark: "AA", tone: "warm" },
  { eyebrow: "AROUND THE WORLD", title: "Ethiopian music everywhere", copy: "Follow venues and stages in Ethiopia and across the diaspora.", stat: "countries" as const, label: "countries", mark: "✦", tone: "green" },
];

function Icon({ children }: { children: React.ReactNode }) {
  return <span className="icon" aria-hidden="true">{children}</span>;
}

export function ZemaApp() {
  const [view, setView] = useState<View>("home");
  const [language, setLanguage] = useState<"EN" | "አማ">("EN");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<ExploreFilter>("All");
  const [saved, setSaved] = useState<string[]>(() => readDeviceList("zema-saved"));
  const [attended, setAttended] = useState<string[]>(() => readDeviceList("zema-attended"));
  const [showAdd, setShowAdd] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [notice, setNotice] = useState("");
  const [archive, setArchive] = useState<ArchiveData | null>(null);
  const [archiveError, setArchiveError] = useState(false);

  useEffect(() => {
    let active = true;
    void fetchArchive()
      .then((data) => {
        if (active) setArchive(data);
      })
      .catch(() => {
        if (active) setArchiveError(true);
      });
    return () => {
      active = false;
    };
  }, []);

  async function submitContribution(input: ContributionInput) {
    const accessToken = window.localStorage.getItem("zema-access-token");
    if (!accessToken) throw new Error("Please sign in before submitting a contribution.");

    const response = await fetch("/api/contributions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    });
    const body = await response.json().catch(() => ({})) as { error?: string };
    if (!response.ok) {
      if (response.status === 401) {
        window.localStorage.removeItem("zema-access-token");
        window.localStorage.removeItem("zema-refresh-token");
      }
      throw new Error(body.error ?? "The contribution could not be saved.");
    }

    setArchive(await fetchArchive());
    setArchiveError(false);
    setShowAdd(false);
    setNotice("Contribution saved for community review");
  }

  function persist(key: string, value: string[]) {
    window.localStorage.setItem(key, JSON.stringify(value));
  }

  function toggleSaved(id: string) {
    const next = saved.includes(id) ? saved.filter((item) => item !== id) : [...saved, id];
    setSaved(next);
    persist("zema-saved", next);
    setNotice(saved.includes(id) ? "Removed from saved" : "Saved for later");
  }

  function toggleAttendance(id: string) {
    const next = attended.includes(id) ? attended.filter((item) => item !== id) : [...attended, id];
    setAttended(next);
    persist("zema-attended", next);
    setNotice(attended.includes(id) ? "Removed from your concert history" : "Added privately to your concert history");
  }

  const events = useMemo(() => (archive?.events ?? []).map(toEventView), [archive]);
  const upcomingEvents = useMemo(() => events.filter((event) => event.kind === "Upcoming"), [events]);
  const artists = useMemo(() => (archive?.artists ?? []).map(toArtistView), [archive]);
  const recentSets = useMemo(() => (archive?.performances ?? []).map(toRecentSet), [archive]);

  const results = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return [];
    const eventResults = events.filter((event) =>
      `${event.title} ${event.native} ${event.venue} ${event.city}`.toLowerCase().includes(term),
    ).map((event) => ({ type: "Event", title: event.title, meta: `${event.venue} · ${event.city}` }));
    const artistResults = artists.filter((artist) =>
      `${artist.name} ${artist.native} ${artist.genre}`.toLowerCase().includes(term),
    ).map((artist) => ({ type: "Artist", title: artist.name, meta: `${artist.native} · ${artist.genre}` }));
    return [...artistResults, ...eventResults].slice(0, 7);
  }, [artists, events, query]);

  const displayedSaved = events.filter((event) => saved.includes(event.id));

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="site-header">
        <button className="brand" onClick={() => setView("home")} aria-label="Zema Archive home">
          <span className="brand-mark">ዜ</span>
          <span><strong>ZEMA</strong><small>ARCHIVE</small></span>
        </button>
        <nav className="desktop-nav" aria-label="Primary navigation">
          <button className={view === "home" ? "active" : ""} onClick={() => setView("home")}>Home</button>
          <button className={view === "explore" ? "active" : ""} onClick={() => setView("explore")}>Explore</button>
          <button onClick={() => { setView("explore"); setFilter("Events"); }}>Events</button>
          <button onClick={() => { setView("explore"); setFilter("Artists"); }}>Artists</button>
          <button onClick={() => { setView("explore"); setFilter("Venues"); }}>Venues</button>
        </nav>
        <div className="header-actions">
          <button className="language-toggle" onClick={() => setLanguage(language === "EN" ? "አማ" : "EN")} aria-label="Change language">
            {language} <span>⌄</span>
          </button>
          <button className="sign-in" onClick={() => setShowAuth(true)}>Sign in</button>
          <button className="add-button" onClick={() => setShowAdd(true)}><Icon>＋</Icon> Add performance</button>
        </div>
      </header>

      <main id="main">
        {view === "home" && (
          <>
            <section className="hero">
              <div className="hero-orbit orbit-one" />
              <div className="hero-orbit orbit-two" />
              <p className="kicker"><span /> ETHIOPIAN LIVE MUSIC, REMEMBERED</p>
              <h1>Every stage has a story.<br /><em>Help us remember it.</em></h1>
              <p className="hero-copy">
                Discover live music, document what was played, and preserve the stories behind Ethiopian performances—at home and around the world.
              </p>
              <SearchBox query={query} setQuery={setQuery} results={results} />
              <div className="hero-actions">
                <button className="primary-action" onClick={() => setShowAdd(true)}><Icon>＋</Icon> Add a performance</button>
                <button className="text-action" onClick={() => setView("explore")}>Explore the archive <span>→</span></button>
              </div>
              <div className="hero-stats" aria-label="Archive statistics">
                <div><strong>{archive?.stats.performances ?? "—"}</strong><span>Performances</span></div>
                <div><strong>{archive?.stats.artists ?? "—"}</strong><span>Artists</span></div>
                <div><strong>{archive?.stats.venues ?? "—"}</strong><span>Venues</span></div>
                <div><strong>{archive?.stats.countries ?? "—"}</strong><span>Countries</span></div>
              </div>
            </section>

            <section className="content-section upcoming">
              <SectionHeading eyebrow="COMING UP" title="Live music, near and far" action="View all events" onAction={() => { setView("explore"); setFilter("Events"); }} />
              {upcomingEvents.length ? <div className="event-grid">
                {upcomingEvents.slice(0, 3).map((event) => (
                  <EventCard key={event.id} event={event} saved={saved.includes(event.id)} onSave={() => toggleSaved(event.id)} />
                ))}
              </div> : <InlineArchiveState loading={!archive && !archiveError} error={archiveError} empty="No upcoming events have been added yet." />}
            </section>

            <section className="archive-band">
              <div className="content-section">
                <SectionHeading eyebrow="RECENTLY DOCUMENTED" title="Fresh from the archive" action="Explore all setlists" onAction={() => setView("explore")} inverse />
                {recentSets.length ? <div className="setlist-table">
                  {recentSets.slice(0, 20).map((set, index) => (
                    <article className="setlist-row" key={`${set.artist}-${set.date}-${index}`}>
                      <div className="set-number">0{index + 1}</div>
                      <div className="set-identity"><strong>{set.artist}</strong><span>{set.native}</span></div>
                      <div className="set-place"><strong>{set.venue}</strong><span>{set.city}</span></div>
                      <div className="set-date"><strong>{set.date}</strong><span>{set.songs} songs</span></div>
                      <div className="confidence"><span>✓</span>{set.confidence}</div>
                      <button aria-label={`View ${set.artist} performance`}>→</button>
                    </article>
                  ))}
                </div> : <InlineArchiveState inverse loading={!archive && !archiveError} error={archiveError} empty="No performances have been documented yet." />}
              </div>
            </section>

            <section className="content-section collections-section">
              <SectionHeading eyebrow="EXPLORE" title="Find your way into the music" />
              <div className="collection-grid">
                {collections.map((collection) => (
                  <button className={`collection-card ${collection.tone}`} key={collection.title} onClick={() => setView("explore")}>
                    <span className="collection-mark">{collection.mark}</span>
                    <span className="collection-eyebrow">{collection.eyebrow}</span>
                    <strong>{collection.title}</strong>
                    <span className="collection-copy">{collection.copy}</span>
                    <span className="collection-count">{archive?.stats[collection.stat] ?? "—"} {collection.label} <b>→</b></span>
                  </button>
                ))}
              </div>
            </section>

            <section className="content-section artist-section">
              <SectionHeading eyebrow="ARTISTS" title="Voices in the archive" action="Browse all artists" onAction={() => { setView("explore"); setFilter("Artists"); }} />
              {artists.length ? <div className="artist-strip">
                {artists.map((artist) => (
                  <article className="artist-card" key={artist.name}>
                    <div className={`artist-avatar ${artist.tone}`}>{artist.initials}</div>
                    <strong>{artist.name}</strong>
                    <span>{artist.native}</span>
                    <small>{artist.genre}</small>
                    <div><b>{artist.sets}</b> documented performances</div>
                  </article>
                ))}
              </div> : <InlineArchiveState loading={!archive && !archiveError} error={archiveError} empty="No artists have been added yet." />}
            </section>

            <section className="contribution-callout">
              <div className="callout-mark">?</div>
              <div>
                <p className="kicker light"><span /> THE ARCHIVE NEEDS YOU</p>
                <h2>Were you there?</h2>
                <p>One song title, an old ticket, or a memory can help complete Ethiopia&apos;s musical story.</p>
              </div>
              <button onClick={() => setShowAdd(true)}>Make a contribution <span>→</span></button>
            </section>
          </>
        )}

        {view === "explore" && (
          <section className="page-view content-section">
            <p className="kicker"><span /> EXPLORE THE ARCHIVE</p>
            <h1>Find the music you remember</h1>
            <p className="page-intro">Search across Ethiopic and Latin spellings, performers, stages, cities and dates.</p>
            <SearchBox query={query} setQuery={setQuery} results={results} large />
            <div className="filter-row" aria-label="Explore filters">
              {(["All", "Events", "Artists", "Venues"] as ExploreFilter[]).map((item) => (
                <button key={item} className={filter === item ? "selected" : ""} onClick={() => setFilter(item)}>{item}</button>
              ))}
            </div>
            {(filter === "All" || filter === "Events") && (
              <div className="explore-block">
                <h2>Events and performances <span>{archive?.stats.performances ?? 0}</span></h2>
                {events.length ? <div className="event-grid">
                  {events.map((event) => <EventCard key={event.id} event={event} saved={saved.includes(event.id)} onSave={() => toggleSaved(event.id)} onAttend={() => toggleAttendance(event.id)} attended={attended.includes(event.id)} />)}
                </div> : <InlineArchiveState loading={!archive && !archiveError} error={archiveError} empty="No events have been added yet." />}
              </div>
            )}
            {(filter === "All" || filter === "Artists") && (
              <div className="explore-block">
                <h2>Artists <span>{artists.length}</span></h2>
                {artists.length ? <div className="artist-strip">
                  {artists.map((artist) => (
                    <article className="artist-card" key={artist.name}>
                      <div className={`artist-avatar ${artist.tone}`}>{artist.initials}</div>
                      <strong>{artist.name}</strong><span>{artist.native}</span><small>{artist.genre}</small>
                      <div><b>{artist.sets}</b> documented performances</div>
                    </article>
                  ))}
                </div> : <InlineArchiveState loading={!archive && !archiveError} error={archiveError} empty="No artists have been added yet." />}
              </div>
            )}
            {(filter === "All" || filter === "Venues") && (
              <div className="explore-block">
                <h2>Venues <span>{archive?.stats.venues ?? 0}</span></h2>
                {archive?.venues.length ? <div className="venue-list">
                  {archive.venues.map((venue) => (
                    <article key={venue.id ?? venue.display_name}><div className="venue-pin">⌖</div><div><strong>{venue.display_name}</strong><span>{[venue.address, venue.city, venue.country].filter(Boolean).join(", ")}</span></div><small>{venue.events?.length ?? 0} events</small><button>→</button></article>
                  ))}
                </div> : <InlineArchiveState loading={!archive && !archiveError} error={archiveError} empty="No venues have been added yet." />}
              </div>
            )}
          </section>
        )}

        {view === "saved" && (
          <section className="page-view content-section">
            <p className="kicker"><span /> YOUR COLLECTION</p>
            <h1>Saved for later</h1>
            <p className="page-intro">Your saves stay on this device. Sign in to sync them across devices.</p>
            {displayedSaved.length ? (
              <div className="event-grid">{displayedSaved.map((event) => <EventCard key={event.id} event={event} saved onSave={() => toggleSaved(event.id)} />)}</div>
            ) : (
              <EmptyState mark="♡" title="Nothing saved yet" copy="Save an upcoming event or historic performance and it will appear here." action="Explore events" onAction={() => setView("explore")} />
            )}
          </section>
        )}

        {view === "profile" && (
          <section className="page-view content-section">
            <p className="kicker"><span /> YOUR PROFILE</p>
            <h1>Your concert history</h1>
            <p className="page-intro">Attendance is private by default. You decide what becomes visible.</p>
            {attended.length ? (
              <div className="profile-panel">
                <div className="privacy-note"><Icon>◉</Icon><div><strong>Private attendance</strong><span>Only you can see these {attended.length} performances.</span></div><button>Privacy settings</button></div>
                {events.filter((event) => attended.includes(event.id)).map((event) => (
                  <div className="history-row" key={event.id}><span>{event.day} {event.month}</span><div><strong>{event.title}</strong><small>{event.venue}, {event.city}</small></div><button onClick={() => toggleAttendance(event.id)}>Remove</button></div>
                ))}
              </div>
            ) : (
              <EmptyState mark="◎" title="Your history starts here" copy="Mark a performance “I was there” to build your private concert history." action="Find a performance" onAction={() => setView("explore")} />
            )}
          </section>
        )}
      </main>

      <footer>
        <div className="footer-brand"><span className="brand-mark">ዜ</span><div><strong>ZEMA ARCHIVE</strong><p>Ethiopian live music, remembered together.</p></div></div>
        <div><strong>Explore</strong><button onClick={() => setView("explore")}>Events</button><button onClick={() => setView("explore")}>Artists</button><button onClick={() => setView("explore")}>Venues</button></div>
        <div><strong>Contribute</strong><button onClick={() => setShowAdd(true)}>Add performance</button><button>Guidelines</button><button>Community standards</button></div>
        <div><strong>About</strong><button>Our mission</button><button>Privacy</button><button>Contact</button></div>
        <p className="footer-note">Built with and for the Ethiopian music community. © 2026 Zema Archive.</p>
      </footer>

      <nav className="mobile-nav" aria-label="Mobile navigation">
        <button className={view === "home" ? "active" : ""} onClick={() => setView("home")}><Icon>⌂</Icon>Home</button>
        <button className={view === "explore" ? "active" : ""} onClick={() => setView("explore")}><Icon>⌕</Icon>Explore</button>
        <button className="mobile-add" onClick={() => setShowAdd(true)}><Icon>＋</Icon>Add</button>
        <button className={view === "saved" ? "active" : ""} onClick={() => setView("saved")}><Icon>♡</Icon>Saved</button>
        <button className={view === "profile" ? "active" : ""} onClick={() => setView("profile")}><Icon>○</Icon>Profile</button>
      </nav>

      {showAdd && <ContributionModal onClose={() => setShowAdd(false)} onSubmit={submitContribution} onSignIn={() => { setShowAdd(false); setShowAuth(true); }} />}
      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      {notice && <div className="toast" role="status"><span>✓</span>{notice}<button aria-label="Dismiss message" onClick={() => setNotice("")}>×</button></div>}
    </div>
  );
}

function readDeviceList(key: string): string[] {
  if (typeof window === "undefined") return [];
  try {
    const value = JSON.parse(window.localStorage.getItem(key) ?? "[]");
    return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
  } catch {
    return [];
  }
}

function toEventView(event: DbEvent, index: number): EventView {
  const date = new Date(event.event_date);
  const upcoming = date.getTime() >= Date.now() && event.status === "announced";
  return {
    id: `event-${event.id}`,
    day: new Intl.DateTimeFormat("en-GB", { day: "2-digit", timeZone: "UTC" }).format(date),
    month: new Intl.DateTimeFormat("en-GB", { month: "short", timeZone: "UTC" }).format(date).toUpperCase(),
    title: event.title,
    native: "",
    venue: event.venues?.display_name ?? "Venue to be confirmed",
    city: [event.venues?.city, event.venues?.country].filter(Boolean).join(", "),
    kind: upcoming ? "Upcoming" : "Archived event",
    songs: 0,
    status: event.status === "announced" ? "Announced" : sentenceCase(event.status),
    accent: ["gold", "green", "red", "blue"][index % 4],
  };
}

function toArtistView(artist: DbArtist, index: number) {
  const words = artist.display_name.trim().split(/\s+/);
  return {
    name: artist.display_name,
    native: artist.native_name ?? "",
    sets: artist.performances?.length ?? 0,
    genre: artist.genre ?? "Genre not specified",
    initials: words.slice(0, 2).map((word) => word[0]?.toUpperCase()).join(""),
    tone: ["rust", "navy", "plum", "olive", "ochre"][index % 5],
  };
}

function toRecentSet(performance: DbPerformance) {
  const date = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
    .format(new Date(performance.performance_date));
  const linkedVenue = performance.events?.venues;
  return {
    artist: performance.artists?.display_name || performance.submitted_artist || "Unknown artist",
    native: performance.artists?.native_name || "Community contribution",
    venue: linkedVenue?.display_name || performance.submitted_venue || "Unknown venue",
    city: linkedVenue ? [linkedVenue.city, linkedVenue.country].filter(Boolean).join(", ") : "Pending community review",
    date,
    songs: performance.setlist_items?.length ?? 0,
    confidence: sentenceCase(performance.status),
  };
}

function sentenceCase(value: string) {
  return value.replaceAll("_", " ").replace(/^\w/, (letter) => letter.toUpperCase());
}

function SearchBox({ query, setQuery, results, large = false }: { query: string; setQuery: (value: string) => void; results: { type: string; title: string; meta: string }[]; large?: boolean }) {
  return (
    <div className={`search-wrap ${large ? "search-large" : ""}`}>
      <div className="search-box">
        <Icon>⌕</Icon>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search artists, venues, songs, cities..." aria-label="Search the archive" />
        {query && <button onClick={() => setQuery("")} aria-label="Clear search">×</button>}
        <span className="search-hint">Try “Mulatu” or “ሙላቱ”</span>
      </div>
      {query && (
        <div className="search-results">
          {results.length ? results.map((result) => (
            <button key={`${result.type}-${result.title}`}><span>{result.type}</span><strong>{result.title}</strong><small>{result.meta}</small><b>→</b></button>
          )) : <div className="no-results"><strong>No exact match</strong><span>Try another spelling, or add it to the archive.</span></div>}
        </div>
      )}
    </div>
  );
}

function SectionHeading({ eyebrow, title, action, onAction, inverse = false }: { eyebrow: string; title: string; action?: string; onAction?: () => void; inverse?: boolean }) {
  return <div className={`section-heading ${inverse ? "inverse" : ""}`}><div><p className="kicker"><span /> {eyebrow}</p><h2>{title}</h2></div>{action && <button onClick={onAction}>{action} <span>→</span></button>}</div>;
}

function EventCard({ event, saved, onSave, onAttend, attended }: { event: EventView; saved: boolean; onSave: () => void; onAttend?: () => void; attended?: boolean }) {
  return (
    <article className="event-card">
      <div className={`event-date ${event.accent}`}><strong>{event.day}</strong><span>{event.month}</span></div>
      <div className="event-type">{event.kind}</div>
      <button className={`save-button ${saved ? "saved" : ""}`} onClick={onSave} aria-label={saved ? `Remove ${event.title} from saved` : `Save ${event.title}`}>{saved ? "♥" : "♡"}</button>
      <h3>{event.title}</h3><p className="native-name">{event.native}</p>
      <p className="event-location"><Icon>⌖</Icon><span><strong>{event.venue}</strong>{event.city}</span></p>
      <div className="event-footer"><span><b>✓</b>{event.status}</span>{onAttend ? <button onClick={onAttend}>{attended ? "Attended ✓" : "I was there"}</button> : <button>Details →</button>}</div>
    </article>
  );
}

function InlineArchiveState({ loading, error, empty, inverse = false }: { loading: boolean; error: boolean; empty: string; inverse?: boolean }) {
  const message = loading ? "Loading the community archive…" : error ? "The archive could not be loaded. Please refresh and try again." : empty;
  return <p className={`archive-state ${inverse ? "inverse" : ""}`} role={error ? "alert" : "status"}>{message}</p>;
}

function EmptyState({ mark, title, copy, action, onAction }: { mark: string; title: string; copy: string; action: string; onAction: () => void }) {
  return <div className="empty-state"><span>{mark}</span><h2>{title}</h2><p>{copy}</p><button onClick={onAction}>{action} →</button></div>;
}

function ContributionModal({ onClose, onSubmit, onSignIn }: { onClose: () => void; onSubmit: (input: ContributionInput) => Promise<void>; onSignIn: () => void }) {
  const [step, setStep] = useState(1);
  const [artist, setArtist] = useState("");
  const [date, setDate] = useState("");
  const [venue, setVenue] = useState("");
  const [songs, setSongs] = useState("");
  const [source, setSource] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const canContinue = step === 1 ? artist.trim().length > 1 : step === 2 ? Boolean(date && venue.trim()) : true;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (step < 5) {
      setStep(step + 1);
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSubmit({ artist, date, venue, songs, source });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The contribution could not be saved.");
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal contribution-modal" role="dialog" aria-modal="true" aria-labelledby="add-title">
        <button className="modal-close" onClick={onClose} aria-label="Close contribution form">×</button>
        <p className="kicker"><span /> CONTRIBUTE TO THE ARCHIVE</p>
        <h2 id="add-title">Add a performance</h2>
        <div className="step-track" aria-label={`Step ${step} of 5`}>
          {[1, 2, 3, 4, 5].map((item) => <span key={item} className={item <= step ? "complete" : ""}>{item < step ? "✓" : item}</span>)}
        </div>
        <p className="step-label">Step {step} of 5 · {["Who performed?", "When and where?", "What was played?", "What supports this?", "Review"][step - 1]}</p>
        <form onSubmit={submit}>
          {step === 1 && <label>Artist or group<span>Search in Ethiopic or Latin script</span><input autoFocus value={artist} onChange={(e) => setArtist(e.target.value)} placeholder="e.g. Mulatu Astatke / ሙላቱ አስታጥቄ" required /></label>}
          {step === 2 && <div className="form-grid"><label>Date<span>Gregorian date</span><input type="date" value={date} onChange={(e) => setDate(e.target.value)} required /></label><label>Venue<span>Start typing a known venue</span><input value={venue} onChange={(e) => setVenue(e.target.value)} placeholder="Fendika Cultural Center" required /></label></div>}
          {step === 3 && <label>Songs in order<span>One song per line. Partial lists and “unknown song” are welcome.</span><textarea value={songs} onChange={(e) => setSongs(e.target.value)} placeholder={"Tizita\nYègellé Tezeta\nUnknown song\nYekermo Sew"} rows={7} /></label>}
          {step === 4 && <label>Source or memory note<span>A poster, article, video link, ticket, or first-hand memory helps others verify the record.</span><textarea value={source} onChange={(e) => setSource(e.target.value)} placeholder="I attended this performance, or paste a public source link..." rows={5} /></label>}
          {step === 5 && <div className="review-card"><div><span>Artist</span><strong>{artist}</strong></div><div><span>Date & venue</span><strong>{date} · {venue}</strong></div><div><span>Setlist</span><strong>{songs ? `${songs.split("\n").filter(Boolean).length} songs added` : "No songs yet — can be added later"}</strong></div><div><span>Evidence</span><strong>{source || "First-hand community submission"}</strong></div><p>✓ Your contribution will be public and attributed after community review. Your email is never displayed.</p></div>}
          {error && <p className="form-error" role="alert">{error} {error.startsWith("Please sign in") && <button type="button" onClick={onSignIn}>Sign in now</button>}</p>}
          <div className="modal-actions">
            {step > 1 && <button type="button" className="secondary-action" onClick={() => setStep(step - 1)} disabled={saving}>Back</button>}
            <button type="submit" className="primary-action" disabled={!canContinue || saving}>{saving ? "Saving…" : step === 5 ? "Submit for review" : "Continue"} <span>→</span></button>
          </div>
        </form>
        <small className="draft-note">Draft progress is kept while this form is open. Never upload private or copyrighted material without permission.</small>
      </section>
    </div>
  );
}

function AuthModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal auth-modal" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <button className="modal-close" onClick={onClose} aria-label="Close sign in">×</button>
        <span className="brand-mark">ዜ</span><p className="kicker"><span /> JOIN THE COMMUNITY</p>
        <h2 id="auth-title">Keep Ethiopia&apos;s music alive</h2>
        <p>Sign in to contribute, sync saved events, and build a private history of performances you attended.</p>
        <a className="primary-action auth-link" href="/auth">Continue securely <span>→</span></a>
        <small>Public browsing never requires an account. Attendance is private by default.</small>
      </section>
    </div>
  );
}
