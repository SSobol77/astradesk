# AstraDesk Admin Panel

Strict OpenAPI-driven admin console built with Next.js 16 (App Router) and React 19. All UI flows, filters, and mutations map directly to operations defined in `openapi/OpenAPI.yaml`.

## Requirements

- Node.js 22 LTS
- npm 10+

## Quick start

```bash
npm install
npm run dev
```

Visit http://localhost:3000 and set `NEXT_PUBLIC_API_BASE_URL` + optional `ASTRADESK_API_TOKEN` in `.env.local` to point at the AstraDesk Admin API.

## Project layout

```
app/                 # App Router pages grouped under (shell)
components/          # In-house UI primitives (no external kit)
hooks/               # Reusable client hooks (toast, debounce)
lib/                 # Fetch wrapper, SSE helper, formatters, guards
offigi/openapi/      # OpenAPI spec + generated client/types + guards
scripts/             # OpenAPI tooling (generate + sync check)
public/              # Static assets (logo, robots)
tests/unit/          # Vitest suites for regressions
```

Key principles:

- **OpenAPI as SSOT** – UI surfaces (tabs, buttons, filters) exist only if the corresponding path/method is defined in `OpenAPI.yaml`.
- **Generated typing enforced** – `openapi/openapi-types.d.ts` and `openapi/openapi-client.ts` must be regenerated after spec changes (CI checks staleness).
- **Guards & filters** – `lib/guards.ts` + `openapi/paths-map.ts` prevent rendering unsupported controls.
- **SSE single-integration point** – `/runs/stream` handled in `lib/sse.ts` with reconnection logic and unit tests.

## NPM scripts

- `npm run dev` – Next dev server (@3000)
- `npm run build` / `npm start` – production build & start
- `npm run lint` / `npm run typecheck` – ESLint + `tsc --noEmit`
- `npm run format` / `npm run format:write` – Prettier in check or write mode
- `npm run test` / `npm run test:watch` – Vitest suites under `tests/unit`
- `npm run openapi:gen` – placeholder hook to integrate your preferred generator
- `npm run openapi:check` – ensures generated artifacts are newer than `OpenAPI.yaml`

## OpenAPI workflow

1. Update `openapi/OpenAPI.yaml` with the latest backend contract.
2. Run `npm run openapi:gen` (implement generation when ready).
3. Commit regenerated `openapi/openapi-client.ts`, `openapi/openapi-types.d.ts`, and optional guard updates.
4. `npm run openapi:check` is executed in CI to block stale artifacts.

## Testing

Vitest covers:

- `lib/api` mapping of `application/problem+json` errors
- Auto-reconnect behaviour for `/runs/stream`
- Filter allow-lists sourced from `paths-map.ts`

Run locally with `npm test` (single pass) or `npm run test:watch`.

## Continuous integration

`.github/workflows/ci.yml` provisions Node 22, installs dependencies, and runs lint → typecheck → OpenAPI sync check → build → tests on every push/PR touching this workspace.

## Docker (optional)

A minimal Dockerfile and docker-compose definition are provided to bundle the Next.js standalone output. Adjust the compose file to point at your backend reverse proxy once ready.
