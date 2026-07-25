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
4. Configure the Supabase authentication settings described below.
5. Deploy.

Vercel will detect Next.js automatically; no custom build command is required.

### Supabase email confirmation codes

The application asks Supabase to send an email OTP and verifies the code in the `/auth` UI. Supabase controls whether that email contains a code or a magic link.

1. Open **Supabase → Authentication → Email Templates**.
2. Edit both **Confirm signup** and **Magic Link**.
3. Replace links using `{{ .ConfirmationURL }}` with a visible code using `{{ .Token }}`. For example: `<p>Your Zema Archive confirmation code is: <strong>{{ .Token }}</strong></p>`.
4. Open **Authentication → URL Configuration**.
5. Set **Site URL** to the production Vercel domain, not localhost.
6. Add `https://YOUR-DOMAIN/auth` to **Redirect URLs**. Add preview URLs separately only when preview authentication is required.

### Google and GitHub sign-in

The `/auth` page supports Google and GitHub OAuth through Supabase.

1. Open **Supabase → Authentication → Providers** and enable Google or GitHub.
2. Create the corresponding OAuth application with the provider.
3. Use the Supabase callback URL shown on that provider’s settings page as the provider application’s authorized callback URL.
4. Add the provider client ID and secret in Supabase.
5. Keep `https://YOUR-DOMAIN/auth` in Supabase’s redirect allow list.

OAuth secrets belong in Supabase and must never use a `NEXT_PUBLIC_` environment variable.

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
