# Zema Archive

Zema Archive is a community-powered Ethiopian live-music archive and discovery platform. This `vercel` branch runs on standard Next.js and is ready for Vercel with Supabase authentication and serverless Postgres.

## Product surface

- Mobile-first discovery homepage
- Search across Ethiopic and Latin names
- Upcoming and historic performance cards
- Artist, venue, city, archive, and diaspora exploration
- Device-local saved events and private attendance history
- Guided contribution workflow
- Source and confidence indicators
- Passwordless Supabase email authentication
- Postgres schema for artists, aliases, venues, events, performances, setlists, attendance, revisions, reports, and roles
- Authenticated contribution API
- Responsive and accessible interaction design

## Local setup

Requirements: Node.js 22.13 or newer.

```bash
cp .env.example .env.local
npm install
npm run dev
```

Add values from your Supabase project to `.env.local`.

## Database

Create a free Supabase project and use its pooled Postgres connection string for `DATABASE_URL`. Generate a Postgres migration with:

```bash
npm run db:generate
```

Apply the generated SQL from `drizzle/` using the Supabase SQL Editor before accepting contributions.

## Deploy to Vercel

1. Import `okitta/setlist-ethiopia` in Vercel.
2. Set the production branch to `vercel`.
3. Add `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, and `DATABASE_URL`.
4. In Supabase’s email authentication template, include the one-time token so users receive a verification code.
5. Deploy.

Vercel will detect Next.js automatically; no custom build command is required.

## Validation

```bash
npm run db:generate
npm test
npm run lint
```

## Security defaults

- Supabase verifies user sessions server-side before contribution writes.
- Database credentials remain server-only.
- Inputs are length-limited and parameterised through Drizzle.
- Attendance is private by default.
- Material contributions create attributable revision records.
- Secrets are excluded from source control.
