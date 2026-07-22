## Why

The Silverman Authority Manager console today ships only as Vite static assets inside the FastAPI worker image (`GET /flow-a/console/linkedin-variant-supervision`). That couples UI and API versioning/rollout and blocks independent operator-console deploys. **BL-034 / US-093** (Story 1) needs a supported production path where the UI is a distinct deployable artifact while the browser still talks to the worker over HTTP (ADR-0001 unchanged).

## What Changes

- Publish a **deployable operator UI artifact/service** (separate container serving the existing React + TypeScript + Vite build) that is not solely “static files inside the API image” as the only supported production path.
- Configure the UI with an explicit **worker API base URL** (and related auth/CORS prerequisites) so `SupervisionApiClient` calls absolute worker HTTP endpoints instead of assuming same-origin relative paths.
- Fail closed with **operator-visible errors** when API base URL / required UI↔API configuration is missing or invalid.
- Allow the worker to accept browser calls from the separated UI origin (CORS allowlist) without changing n8n→worker HTTP orchestration or introducing n8n Execute Command.
- Document the new topology briefly in operator docs and CURRENT-STATE pointers.
- Keep the existing embedded console route as an **optional compatibility path** during migration; it MUST NOT remain the only supported production delivery mode after this change.
- **Non-goals / intentionally excluded ACs:** US-094 UAT↔API / prod↔API pairing (config hooks MAY be reserved); US-095 full capability regression program; BL-035 Google/OIDC login; BL-029 CI/UAT automation; mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; public internet exposure beyond BL-026 accepted LAN exposure; LinkedIn/Flow A/B business-logic rewrites; n8n workflow rewrites.

### Goals (US-093 acceptance criteria)

1. Publish a deployable UI artifact/service that is not solely static files inside the API image as the only supported production path.
2. Browser calls the worker API over HTTP using the typed client boundary (no filesystem SoT in the browser).
3. n8n continues to call the worker API only (ADR-0001); UI separation MUST NOT introduce n8n Execute Command.
4. Outcome visible/understandable to the operator.
5. Failures or blocked states clearly communicated.
6. Existing completed work is not duplicated or unintentionally changed.

## Capabilities

### New Capabilities

- `operator-ui-deployment`: Normative packaging, configuration, and LAN deployment of the Authority Manager console as a distinct service/artifact from the FastAPI worker, including API base URL configuration, fail-closed misconfig behavior, and topology documentation pointers (US-093 only; US-094 pairing reserved).

### Modified Capabilities

- `linkedin-variant-supervision-console`: Supersede US-040A requirements that production MUST NOT require a separate frontend server and that the console is delivered only as worker-served static assets; require configurable HTTP API base URL on the typed client; require operator-visible blocked states for missing/invalid API/auth configuration when running as the separated UI.
- `ubuntu-server-worker-deployment`: Extend server compose/deploy guidance so the isolated Ubuntu deployment can run the separated operator UI service alongside the worker on LAN without changing n8n→worker HTTP-only orchestration.

## Impact

- **Frontend:** `frontend/linkedin-variant-supervision-console/` — Vite `base`/build output path for the separated artifact; `SupervisionApiClient` API base URL resolution; startup fail-closed UX; no business-screen rewrite.
- **Worker:** CORS (or equivalent browser cross-origin policy) allowlist for configured UI origins; optional retention of embedded console route as compatibility only.
- **Deploy:** New UI Dockerfile / compose service (recommended nginx serving Vite build); env examples for API base URL and allowed origins; brief operator docs + CURRENT-STATE topology pointers.
- **n8n / publication / Flow A–B:** unchanged contracts; n8n still targets worker HTTP only.
- **Auth:** US-040D injectable auth boundary preserved; BL-035 Google login out of scope.
- **Branch:** implement later on `feat/us-093-…` after proposal approval (branch-per-US); do not commit product work directly on `main`.

## Backlog / story mapping

| ID | Role in this change |
|----|---------------------|
| **BL-034** | Parent epic — UI/API separation |
| **US-093** | **In scope** — Story 1 (this change) |
| **US-094** | Out of scope — design MAY reserve config hooks only |
| **US-095** | Out of scope beyond “core paths still work via HTTP” |
