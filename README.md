# Zema Archive

Zema Archive is a community-powered Ethiopian live-music archive and discovery platform. It helps people find upcoming performances, document what was played, preserve historical concerts, and connect music communities in Ethiopia and across the diaspora.

## Current product surface

- Mobile-first discovery homepage
- Search across Ethiopic and Latin names
- Upcoming and historic performance cards
- Artist, venue, city, archive, and diaspora exploration
- Device-local saved events and private attendance history
- Guided five-step contribution workflow
- Source and confidence indicators
- ChatGPT sign-in handoff for protected contribution APIs
- D1-ready relational schema for artists, aliases, venues, events, performances, setlists, attendance, revisions, reports, and roles
- Authenticated contribution API with validation and revision provenance
- Responsive, keyboard-friendly, reduced-motion-aware UI
- Social sharing preview

## Development

Requirements: Node.js 22.13 or newer.

```bash
npm install
npm run dev
```

Validation:

```bash
npm run db:generate
npm test
npm run lint
```

## Architecture

The application uses Next.js-compatible Vinext, TypeScript, React, Cloudflare D1, Drizzle ORM, and the Sites runtime. Public discovery works anonymously. Write operations require authenticated identity on the server.

`.openai/hosting.json` declares the logical D1 binding as `DB`. Generated migrations live in `drizzle/`.

## Security defaults

- Server-side authentication for contribution writes
- Length-limited, allowlisted input parsing
- Parameterised database access through Drizzle
- Attendance is private by default
- Attributable append-only revision records
- No secrets or service credentials in browser code
- No third-party database scraping

## Branch

The implementation branch is `codex`.
