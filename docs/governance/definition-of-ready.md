# Definition of Ready

A story is **ready** to be picked up only when it has all of the following. Use this
as a checklist on the issue/PR before work starts.

- [ ] **A clear user benefit** — who is helped and how.
- [ ] **Acceptance criteria** — observable, testable statements.
- [ ] **All UI states designed**: loading, empty, error, success, and
      permission-denied.
- [ ] **Mobile and keyboard expectations** — responsive layout intent; focus order
      and accessible names.
- [ ] **Privacy and abuse considerations** — what data is collected, how it can be
      misused, and the mitigation.
- [ ] **Analytics / success signals** — the events or metrics that show it works.
- [ ] **Copy in supported languages** where user-facing text is required (English +
      Amharic for launch surfaces).

## Worked example — "Add one missing song" (slice 1)

| Field | Value |
| --- | --- |
| User & benefit | A fan who remembers a song that's missing from a setlist can add it, improving documentation completeness. |
| Acceptance criteria | Signed-in user can add a song to a non-archived performance; duplicates are rejected; the addition appears in the setlist and in the revision history with attribution. |
| Loading | "Add" button shows disabled/busy state while saving. |
| Empty | Empty setlist shows "No songs recorded yet. Add the first one below." |
| Error | Server `{code,message}` surfaced inline; harassment in a title returns a friendly rejection. |
| Success | Green "Song added — thank you for contributing." + list refresh. |
| Permission-denied | 401 → "Please sign in to contribute."; feature-off → control hidden. |
| Mobile / keyboard | Single-column layout < 900px; label bound to input via `htmlFor`. |
| Privacy / abuse | Only a song title is collected; screened by `moderation.screen_text`; duplicates blocked. |
| Success signal | `song_added` structured log event (`performance_id`, `actor_id`). |
| Out of scope (v1) | Editing/reordering existing entries; per-song timestamps; encores. |
