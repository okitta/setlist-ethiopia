import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "./api";
import type { Features, PerformanceDetail, Revision } from "./types";

interface Props {
  performanceId: number;
  user: string;
  features: Features | null;
  onChanged: () => void;
}

/**
 * Detail view for one performance: setlist, attendance, "add one missing song",
 * report, and the contribution & revision history. Handles loading / error /
 * permission-denied for each action.
 */
export function PerformancePanel({ performanceId, user, features, onChanged }: Props) {
  const [perf, setPerf] = useState<PerformanceDetail | null>(null);
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [attending, setAttending] = useState(false);
  const [newSong, setNewSong] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [detail, history] = await Promise.all([
        api.performance(performanceId),
        api.revisions(performanceId),
      ]);
      setPerf(detail);
      setRevisions(history);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load this performance.");
    }
  }, [performanceId]);

  useEffect(() => {
    setPerf(null);
    setNotice(null);
    setAttending(false);
    load();
  }, [load]);

  function handleActionError(err: unknown) {
    if (err instanceof ApiError && err.status === 403) {
      setError("You don't have permission to do that.");
    } else if (err instanceof ApiError && err.status === 401) {
      setError("Please sign in to contribute.");
    } else if (err instanceof ApiError) {
      setError(err.message);
    } else {
      setError("Something went wrong.");
    }
  }

  async function toggleAttendance() {
    setBusy(true);
    setError(null);
    try {
      const res = attending
        ? await api.unmarkAttendance(performanceId, user)
        : await api.markAttendance(performanceId, user);
      setAttending(res.attending);
      setNotice(res.attending ? "Marked as attended." : "Attendance removed.");
      await load();
      onChanged();
    } catch (err) {
      handleActionError(err);
    } finally {
      setBusy(false);
    }
  }

  async function addSong(e: React.FormEvent) {
    e.preventDefault();
    if (!newSong.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.addSong(performanceId, newSong.trim(), user);
      setNewSong("");
      setNotice("Song added — thank you for contributing.");
      await load();
    } catch (err) {
      handleActionError(err);
    } finally {
      setBusy(false);
    }
  }

  async function report() {
    setError(null);
    try {
      await api.report(performanceId, "fabricated", user);
      setNotice("Report submitted. A curator will review it.");
    } catch (err) {
      handleActionError(err);
    }
  }

  if (error && !perf) return <p className="error" role="alert">{error}</p>;
  if (!perf) return <p className="muted">Loading…</p>;

  return (
    <article className="panel">
      <h2>
        {perf.venue}, {perf.city}
      </h2>
      <p className="muted">{perf.performed_on}</p>

      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}

      <div className="actions">
        {features?.attendance && (
          <button onClick={toggleAttendance} disabled={busy}>
            {attending ? "✓ Attending" : "Mark attendance"} ({perf.attendance_count})
          </button>
        )}
        <button className="ghost" onClick={report}>
          Report record
        </button>
      </div>

      <h3>Setlist</h3>
      {perf.setlist.length === 0 ? (
        <p className="muted">No songs recorded yet. Add the first one below.</p>
      ) : (
        <ol className="setlist">
          {perf.setlist.map((s) => (
            <li key={s.id}>{s.song_title}</li>
          ))}
        </ol>
      )}

      {features?.add_song && (
        <form onSubmit={addSong} className="add-song">
          <label htmlFor="song">Add one missing song</label>
          <div className="search-row">
            <input
              id="song"
              value={newSong}
              placeholder="Song title"
              onChange={(e) => setNewSong(e.target.value)}
            />
            <button type="submit" disabled={busy || !newSong.trim()}>
              Add
            </button>
          </div>
        </form>
      )}

      <h3>Contribution &amp; revision history</h3>
      {revisions.length === 0 ? (
        <p className="muted">No history yet.</p>
      ) : (
        <ul className="history">
          {revisions.map((r) => (
            <li key={r.id}>
              <span className={`tag tag-${r.action}`}>{r.action}</span> {r.summary}
              <time>{new Date(r.created_at).toLocaleString()}</time>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
