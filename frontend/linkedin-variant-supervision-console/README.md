# LinkedIn variant supervision console (US-040A + US-040B)

React + TypeScript + Vite frontend for Flow A LinkedIn variant supervision.
Production build emits static assets served by the existing Python worker — no
separate frontend server.

## Production dependencies

| Package | Why |
|---------|-----|
| `react` | Component model for list, month calendar, filters, and confirmation flows |
| `react-dom` | Browser rendering of the React tree |

All other packages are **devDependencies** (Vite, TypeScript, Vitest, Testing Library).

**Calendar UI:** US-040B uses a pure CSS grid month layout plus local UTC day-bucketing
helpers (`src/models/dateHelpers.ts`). No production calendar library was added.

## Scripts

```bash
npm ci
npm run build   # writes into src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/
npm test
npm run dev     # local Vite dev server (proxies not required; call worker APIs with CORS/auth as needed)
```

## Build before deploy

The Docker image copies `src/` and does **not** run Node. Before `docker build` / deploy:

```bash
cd frontend/linkedin-variant-supervision-console
npm ci && npm run build
```

Operator URL (unchanged): `GET /flow-a/console/linkedin-variant-supervision`

## Auth

API credentials are held **in memory only** (prompt when needed). They are never
embedded in source, built assets, logs, or browser storage. Future OIDC (US-040D)
swaps the auth provider at the API-client boundary without changing list/calendar
components.

## Scope

- **In (US-040A):** list parity (Stories 1–3), typed client, shared model, console route
- **In (US-040B):** dual first-class List + Month calendar, schedule-visibility GET client,
  filters with discoverable critical failures, dark theme, UTC + local times, mobile agenda
- **Out:** US-040C schedule mutations, US-040D public auth, US-040E polish beyond visibility, Flow B
