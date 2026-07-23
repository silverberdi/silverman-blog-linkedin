# LinkedIn variant supervision console (Silverman Authority Manager)

React + TypeScript + Vite frontend for Flow A LinkedIn variant supervision.

**Production delivery (US-096 / US-099 / BL-034):** separated UI image/service only
(`frontend/.../Dockerfile`, compose `silverman-operator-ui` on LAN `:8011`).
The worker API does **not** embed or serve this SPA. Browser → worker HTTP uses
`SILVERMAN_OPERATOR_UI_API_BASE_URL` (`/` = same-origin private hop via nginx) +
US-094 pairing. Cloudflare Tunnel may publish the **UI only** (US-099); the worker
API stays private.

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
npm run build   # writes to frontend/.../dist/ for the UI image
npm test
npm run dev     # local Vite; proxy APIs to worker (see vite.config.ts)
```

## Build the separated UI image

```bash
cd frontend/linkedin-variant-supervision-console
npm ci && npm run build
# or: docker build -t silverman-operator-ui:local .
```

Worker API image builds do **not** require this step (US-096).

Operator URL: `http://192.168.0.194:8011` (or configured UI host port).

## Auth (US-040D readiness)

Authentication and authorization stay behind the typed `SupervisionApiClient` and
worker middleware (`require_api_key` for local ops). Credentials are injectable via
`AuthProvider`:

| Provider | Role |
|----------|------|
| `MemoryBearerAuthProvider` | Local ops: in-memory worker API key via prompt; `canRead`/`canMutate` when credential held |
| Future OIDC bearer | Swap provider to return `Authorization: Bearer <access_token>` |
| Future session cookie | Swap provider to `credentials: "include"` with empty/minimal headers |

List, Month calendar, and `ScheduleEditor` call client methods only — they do **not**
construct auth headers. Session UI states: anonymous, authenticated, expired-session,
forbidden, service-unavailable. Unauthenticated and read-only (`!canMutate`) sessions
cannot execute edit/defer/cancel/calendar schedule-update.

Credentials are never embedded in source, built assets, logs, or browser storage APIs.

## Cross-origin CORS

When the browser uses an absolute worker origin, CORS relies on
`SILVERMAN_OPERATOR_UI_ORIGINS` (exact origins; never `*`). Prefer US-099
same-origin private hop (`apiBaseUrl=/`) so console API calls need no CORS.

## Public URL and Google authentication (BL-035)

- **US-097 / US-098:** Google OIDC allowlist + operator JWT cookie on the separated UI.
- **US-099:** Front-only Cloudflare Tunnel (or equivalent) to the UI; private worker API;
  same-origin private hop. Live tunnel activation is an operator deploy step.

## Scope

See OpenSpec `linkedin-variant-supervision-console` and BL-034 operator-ui-deployment.
