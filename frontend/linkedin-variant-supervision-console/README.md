# LinkedIn variant supervision console (US-040A–US-040D)

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
npm run dev     # local Vite dev server (same-origin relative API paths in production)
```

## Build before deploy

The Docker image copies `src/` and does **not** run Node. Before `docker build` / deploy:

```bash
cd frontend/linkedin-variant-supervision-console
npm ci && npm run build
```

Operator URL (unchanged): `GET /flow-a/console/linkedin-variant-supervision`

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

## Same-origin default and CORS (documented only)

**Default (current and preferred for any future public URL):** the worker serves the
SPA and APIs on one origin. Console calls use **relative same-origin paths** only
(e.g. `/flow-a/linkedin-variants/pending-supervision`). Prefer terminating TLS at a
reverse proxy that serves console + API together.

**If a future architecture serves the SPA from a distinct origin**, CORS MUST be an
explicit allowlist of console origins, restricted methods/headers, and MUST NOT use
`*` with credentials. That policy lands only in a **separate security / public-exposure
OpenSpec change** — US-040D does **not** enable permissive CORS middleware.

## Public URL and Google authentication (deferred)

**Out of scope for US-040D / this BL slice:**

- Activating public URL hosting / internet exposure of the console
- Live Google OAuth / OIDC identity-provider integration

Both require a **separate approved security OpenSpec change** before internet exposure.
Local operations continue to use worker API-key auth through the injectable provider.

## Scope

- **In (US-040A):** list parity (Stories 1–3), typed client, shared model, console route
- **In (US-040B):** dual first-class List + Month calendar, schedule-visibility GET client,
  filters with discoverable critical failures, dark theme, UTC + local times, mobile agenda
- **In (US-040C):** shared ScheduleEditor mutations (LinkedIn defer + blog calendar schedule-update)
- **In (US-040D):** auth-session UI, mutation gating, OIDC/cookie swap readiness, CORS docs;
  public URL + Google **not activated**
- **Out:** US-040E polish beyond auth-readiness UX, Flow B, BFF/DB/user-management,
  LinkedIn API publish from the console
