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

Set `NEXT_PUBLIC_SIMULATION_MODE=true` in your environment (see `.env.example`) to run the admin dashboard without a live AstraDesk backend. In simulation mode the `apiFetch` helper returns curated fixtures from `lib/simulation-data.ts`, pages render with statically generated data, and you can query the `isSimulationModeEnabled()` helper from `lib/simulation.ts` to branch feature logic. Leave the flag at `false` (default) to reach the real API defined by `NEXT_PUBLIC_API_BASE_URL`.

## Available Scripts

- `npm run dev` – start the development server
- `npm run build` – create a production build
- `npm start` – run the production server
- `npm run lint` – lint the project with ESLint
- `npm run typecheck` – perform TypeScript checks
- `npm test` – run unit tests with Vitest
- `npm run api:generate` – regenerate the typed Admin API client from the canonical OpenAPI spec
- `make api.clients.gen` – refresh all microservice Admin API clients (including this one)

## Architecture & Conventions

- **Routing**: Pages live under the App Router with a shared `app/(dashboard)/layout.tsx` that renders the sidebar navigation and adaptive top bar. Each feature page (`/`, `/tickets`, `/agents`, `/knowledge`, `/settings`) is a server component that fetches data from mock API routes.
- **Styling**: TailwindCSS drives all styling. Layout primitives (sidebar, top bar, cards) rely on utility classes only—no external UI kits.
- **Data layer**: In-memory datasets are kept in `lib/data.ts`. App routes under `app/api/**` expose filtered JSON responses that mirror likely production contracts (e.g., `/api/tickets` supports filtering and pagination).
- **Components**: Shared presentational pieces live in `components/` and are composed inside pages. Client-side interactivity (filters, pagination, row actions) is encapsulated in client components that interact with Next.js routing.
- **Tooling**: ESLint + Prettier enforce code quality; Vitest covers deterministic helpers (`lib/format.ts`). CI (`.github/workflows/ci.yml`) runs install, type-check, build, and tests on pushes/PRs scoped to this service.
- **API client generation**: `npm run api:generate` can be executed from any working directory (for example `npm run api:generate --prefix services/admin-portal`) and will emit `src/api/types.gen.ts` from `openapi/astradesk-admin.v1.yaml`. Override the spec path with `ASTRA_OPENAPI_SPEC` and ensure CI invokes this script before `npm run build` so the generated client stays in sync with the spec.
- **Admin API wrapper**: Auto-generated helpers live in `src/_gen/admin_api/` and are wrapped by `src/clients/adminApi.ts`. Instantiate via `getAdminApi()`; the helper reads `ADMIN_API_URL`/`ADMIN_API_TOKEN` from the environment.

## Docker

```bash
docker compose up --build
```

## Continuous Integration

GitHub Actions workflow `.github/workflows/ci.yml` installs dependencies, type-checks, builds, and runs tests on every push and pull request touching `services/admin-portal`.
