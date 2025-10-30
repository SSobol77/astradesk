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