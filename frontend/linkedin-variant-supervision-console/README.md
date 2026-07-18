# LinkedIn variant supervision console (US-040A)

React + TypeScript + Vite frontend for Flow A LinkedIn variant supervision.
Production build emits static assets served by the existing Python worker — no
separate frontend server.

## Production dependencies

| Package | Why |
|---------|-----|
| `react` | Component model for list, scaffolds, and confirmation flows |
| `react-dom` | Browser rendering of the React tree |

All other packages are **devDependencies** (Vite, TypeScript, Vitest, Testing Library).
Calendar UI libraries are deferred to US-040B.

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

- **In:** list parity (Stories 1–3), typed client, shared model, scaffolds for calendar/detail/schedule/filters/status
- **Out:** US-040B full calendar, US-040C schedule mutations, US-040D public auth, Flow B
