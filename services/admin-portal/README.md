<!--
SPDX-License-Identifier: GPL-2.0-only
Project: AstraDesk
File: services/admin-portal/README.md
Website: https://www.astradesk.dev
Repository: https://github.com/SSobol77/astradesk

Description: Documents AstraDesk architecture, operation, or component behavior.

Copyright (c) 2026 Siergej Sobolewski
This file is part of AstraDesk.

AstraDesk is licensed under the GNU General Public License version 2 only.
See the LICENSE file in the project root for the full license text.
-->

# AstraDesk Admin Dashboard

A Next.js 15 Admin dashboard showcasing the AstraDesk control center with mock ticketing data, activity events, and system health metrics.

## Prerequisites

- Node.js 22 LTS
- npm 10+

## Getting Started

```bash
npm install
npm run dev
```

Visit http://localhost:3000 to view the dashboard.

## Simulation Mode

Set `NEXT_PUBLIC_SIMULATION_MODE=true` in your environment (see `.env.example`) to run the admin dashboard without a live AstraDesk backend. In simulation mode the `apiFetch` helper returns curated fixtures from `lib/simulation-data.ts`, pages render with statically generated data, and you can query the `isSimulationModeEnabled()` helper from `lib/simulation.ts` to branch feature logic. Leave the flag at `false` (default) to reach the real API defined by `NEXT_PUBLIC_API_BASE_URL`. Simulation mode also bypasses the OIDC login requirement below, so it remains the fastest way to preview the UI.

## Authentication (Front-Channel OIDC, ISSUE 021)

Outside simulation mode, every page under `app/(shell)/` requires a signed-in
session. Sign-in uses the standard OAuth 2.0 **Authorization Code + PKCE**
flow against any OIDC-compliant identity provider (Auth0, Keycloak, Okta,
...) — there is no vendor SDK dependency; endpoints are resolved via
`.well-known/openid-configuration` discovery
(`lib/auth/discovery.ts`), and no client secret is used or stored (PKCE
replaces it for this public browser client, `lib/auth/pkce.ts`).

**Setup**: register a public/SPA OIDC client with your identity provider,
using `<portal origin>/callback` as the allowed redirect URI and
`<portal origin>/login` (or the origin itself) as the allowed
post-logout-redirect URI. Then set, in `.env.local`:

```env
NEXT_PUBLIC_OIDC_ISSUER=https://your-issuer.example.com/
NEXT_PUBLIC_OIDC_CLIENT_ID=<public client id>
NEXT_PUBLIC_OIDC_AUDIENCE=astradesk-api
NEXT_PUBLIC_OIDC_REDIRECT_URI=http://localhost:3000/callback
```

`NEXT_PUBLIC_OIDC_AUDIENCE` should match the same audience the Admin API's
own `OIDC_AUDIENCE` (see root `.env.example`) expects, so the access token
this flow obtains is one the Admin API will accept. `NEXT_PUBLIC_OIDC_SCOPE`
and `NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI` are optional (sensible
defaults apply — see `.env.example`).

**Behavior**:

- `NEXT_PUBLIC_OIDC_ISSUER`/`_CLIENT_ID`/`_REDIRECT_URI` unset ⇒ the shell
  reports the session as `unconfigured` and redirects to `/login`, exactly
  like an unauthenticated session — a half-configured deployment fails
  closed rather than silently exposing the console.
- Once signed in, the access token is attached as
  `Authorization: Bearer <token>` to every Admin API call made from the
  browser (`lib/api.ts`'s `apiFetch`, and the SSE runs stream in
  `src/api/client.ts`, via a `token` query param since `EventSource` cannot
  set headers). The session (access/refresh/ID token) lives in
  `sessionStorage`, not `localStorage` — cleared when the tab closes, unlike
  the ad-hoc `localStorage` token this replaces.
- The access token is proactively refreshed shortly before expiry
  (`lib/auth/oidcClient.ts`'s `refreshSession`) when the provider issued a
  refresh token; otherwise the user is returned to `/login`.
- "Sign out" (Topbar user menu) clears the local session and, when the
  provider publishes an `end_session_endpoint`, redirects there too
  (RP-initiated logout), so a stale IdP session cannot silently re-issue a
  new token on the next visit.

Server Component data-loading (the initial SSR fetch in each `page.tsx`)
is unaffected: it continues to use the server-side `ASTRADESK_API_TOKEN`
exactly as before, since Server Components run before any per-user browser
session exists.

## Available Scripts

- `npm run dev` – start the development server
- `npm run build` – create a production build
- `npm start` – run the production server
- `npm run lint` – lint the project with ESLint
- `npm run typecheck` – perform TypeScript checks
- `npm test` – run unit tests with Vitest
