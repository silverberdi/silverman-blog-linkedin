## Context

Today Silverman Authority Manager (`frontend/linkedin-variant-supervision-console/`) builds into `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/` and is served same-origin by the FastAPI worker at `GET /flow-a/console/linkedin-variant-supervision`. `SupervisionApiClient` uses root-relative paths (`/flow-a/...`, `/publish-linkedin-due-variants`, …) that only work when the browser origin is the worker.

US-093 (BL-034 Story 1) requires a supported production path where the UI is a distinct deployable artifact so UI and API can version/roll out independently, while the browser continues to call the worker over HTTP and n8n continues to call the worker only (ADR-0001). US-094 environment pairing is out of scope but config MUST be injectable so pairing can land later without redesign.

Stakeholders: system owner (deployability), content operator (reachable console + clear errors). Constraints: reuse existing React+Vite console; no LinkedIn/Flow A–B/n8n rewrites; no Google login; no public exposure beyond BL-026 LAN acceptance; no secrets in docs/assets; branch-per-US for apply.

## Goals / Non-Goals

**Goals:**

- Ship a separate UI container (or equivalent service) serving the Vite production build.
- Configure API base URL for the UI at deploy time; typed client prefixes all worker calls.
- Fail closed with operator-visible blocked UI when API base URL (or required auth config for the separated mode) is missing/invalid.
- Enable worker CORS for explicitly allowlisted UI origins (LAN).
- Document topology (worker + UI ports) in operator docs / CURRENT-STATE.
- Preserve embedded worker console as optional compatibility only — not the sole supported production path.

**Non-Goals:**

- US-094 UAT/prod pairing enforcement or cross-env detection.
- US-095 full regression suite beyond smoke that core HTTP paths still work.
- BL-035 Google/OIDC; BL-029 CI/UAT automation; public console exposure.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or LinkedIn/Flow business logic.
- Replacing n8n HTTP orchestration or introducing Execute Command.

## Decisions

### D1 — Packaging: separate nginx container serving Vite static build

**Choice:** Multi-stage Dockerfile for the operator UI: Node stage runs `npm ci && npm run build` with `base: /` (or `/` root SPA); final stage is `nginx:alpine` (or equivalent static server) that only serves built assets. Add a compose service (e.g. `silverman-operator-ui`) on a dedicated LAN host port (recommend **8011** → container 80) alongside the existing worker on **8010**.

**Why:** Matches existing Docker-on-Ubuntu topology (ADR-0003); UI image has no Python/editorial mounts; UI and worker rebuild independently; smallest operational surface (static files only).

**Alternatives considered:**

| Alternative | Why not for US-093 |
|-------------|-------------------|
| CDN / object storage | Extra infra; not needed for LAN-first BL-026 |
| Worker still primary + “copy assets out” without a UI process | Does not create a distinct deployable *service* operators can roll independently |
| Node `vite preview` in prod | Heavier and less conventional than nginx for static SPA |
| Greenfield UI | Explicitly rejected — reuse existing console |

### D2 — API base URL: runtime `config.js` injected at container start

**Choice:** At UI container start, render a small non-secret `config.js` (or `config.json`) from environment, e.g.:

- `SILVERMAN_OPERATOR_UI_API_BASE_URL` — absolute worker origin, e.g. `http://192.168.0.194:8010` (no trailing path that duplicates route prefixes)
- Optional display label hook reserved for US-094 (e.g. `SILVERMAN_OPERATOR_UI_ENV_LABEL`) — **documented as reserved; unused for pairing enforcement in US-093**

The SPA loads config before mounting React. `SupervisionApiClient` gains an injectable `apiBaseUrl` (empty/relative only when deliberately same-origin compatibility mode). Requests become `new URL(path, apiBaseUrl).toString()` (or equivalent join).

**Why:** Runtime config avoids baking a single API host into hashed JS (supports US-094 later without rebuild-per-env). Build-time `VITE_*` alone would couple image tags to environments.

**Fail closed:** If separated-UI mode is active and `SILVERMAN_OPERATOR_UI_API_BASE_URL` is missing, empty, or not an absolute `http(s)` URL, the console shows a clear blocked state and MUST NOT silently call relative same-origin paths (which would hit nginx, not the API).

**Alternatives considered:** Build-time only `VITE_API_BASE_URL`; reverse-proxy same host with path split (`/api` → worker) — deferred (more gateway coupling; US-093 prefers explicit UI→API HTTP).

### D3 — Worker CORS allowlist (fail closed default)

**Choice:** Add optional env `SILVERMAN_OPERATOR_UI_ORIGINS` (comma-separated absolute origins, e.g. `http://192.168.0.194:8011`). When non-empty, worker enables CORS for those origins on browser-facing API routes (credentials mode aligned with existing Bearer header auth — no cookies required for US-040D key paste). When empty/unset, behavior remains same-origin / no broad CORS (embedded console continues to work).

**Why:** Separated UI is cross-origin; without CORS, browser calls fail opaquely. Explicit allowlist avoids `*` and matches LAN exposure policy.

### D4 — Vite `base` and dual build outputs

**Choice:** Separated UI builds with SPA `base: '/'` into a UI-dedicated `dist/` (or `frontend/.../dist-standalone/`) consumed only by the UI Dockerfile. Worker-embedded build MAY remain as a second npm script (`build:embedded`) writing to the historical static path for compatibility — or the worker route MAY serve a thin redirect/notice to the separated UI URL. Prefer **keeping embedded assets build optional** so existing tests that hit `GET /flow-a/console/...` do not all break at once; document that **supported production path = separated UI service**.

**Why:** Satisfies “not solely static-in-API as only supported production path” without forcing a big-bang delete of the embedded route in the same change.

### D5 — Auth and n8n unchanged

**Choice:** Keep `AuthProvider` / Bearer paste (US-040D). No Google login. n8n continues `worker_base_url` → `:8010` HTTP Request only. UI never becomes an orchestration target for n8n.

### D6 — Docs / CURRENT-STATE

**Choice:** Brief topology section: worker `:8010` (API SoT) + operator UI `:8011` (static client); pointer from CURRENT-STATE Runtime topology; thin addition to ubuntu deploy doc / env example. Update BL-026 exposure inventory only to note the new LAN UI port — do not claim public console exposure.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operators bookmark old worker console URL | Keep embedded route or redirect/notice pointing to `:8011`; document new URL in CURRENT-STATE |
| Mis-set API base URL → silent wrong host | Fail closed on parse; show operator-visible blocked panel with env var *names* only (no secret values) |
| CORS misconfig → opaque browser failures | Map network/CORS failures to existing client error vocabulary + clear “API unreachable / origin not allowed” copy |
| Dual build scripts drift | Single source package; shared Vitest; CI/tasks run both builds when both retained |
| Port 8011 already used | Document conflict; make host port configurable via compose env |
| Accidental public tunnel of UI | Out of scope; BL-026 remains LAN-first; do not add Cloudflare hostname for console |

## Migration Plan

1. Implement client `apiBaseUrl` + config loader + fail-closed UI (works in Vitest with injected base).
2. Add UI Dockerfile + compose service; worker CORS env; env examples.
3. Deploy worker (with CORS allowlist) then UI on LAN; verify browser on `:8011` loads calendar/supervision via HTTP to `:8010`.
4. Smoke: authenticated schedule-visibility or pending-supervision read + one non-destructive load path; confirm n8n still hits worker only.
5. Update CURRENT-STATE / deploy docs; leave embedded route as compatibility until a later cleanup story if desired.
6. Rollback: stop UI container; operators use embedded console if still present; unset CORS allowlist if needed.

## Open Questions

1. Exact host port default (**8011** recommended) — confirm at apply if 8011 is free on `192.168.0.194`.
2. Whether embedded route becomes a hard redirect vs continued dual-serve — default dual-serve + docs; redirect optional polish if low-cost.
3. US-094 will own pairing validation; US-093 only reserves env label / base URL hooks — no further open design needed for pairing logic.
