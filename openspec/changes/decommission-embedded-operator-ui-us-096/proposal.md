## Why

US-093 / US-094 / US-095 delivered and LAN-deployed a separated operator UI (`:8011`) that talks to the worker API (`:8010`) over HTTP with prod pairing. The worker still ships and serves the embedded compatibility console (`GET /flow-a/console/linkedin-variant-supervision` + static assets under `src/.../static/`), and the worker Dockerfile still instructs `npm run build:embedded` before image build. **BL-034 / US-096** (Story 4) removes that leftover so production topology is exclusively separated UI → API over HTTP—hard UI/API project independence.

## What Changes

- **BREAKING:** Remove worker shipping/serving of operator-console static assets and former embedded console routes (including `GET /flow-a/console/linkedin-variant-supervision` and its `/assets` paths). Old console URLs MUST fail closed with a clear operator-visible outcome (not a silent partial UI); may point operators toward the separated UI on `:8011` without inventing public hosting.
- **BREAKING:** Remove the worker build/deploy requirement to embed the SPA (`build:embedded`, copying console assets into `src/.../static/`, or equivalent). API image/process builds MUST succeed without a frontend production build step.
- Keep the operator UI as a distinct project/service on `:8011` that consumes the worker only via configured HTTP (`SILVERMAN_OPERATOR_UI_API_BASE_URL` + US-094 pairing). MUST NOT embed worker Python, editorial/data mounts, API business logic, or API secrets.
- Declare supported production topology exclusively as separated UI → API over HTTP (ADR-0001: n8n → worker only; UI is never an n8n target).
- Update CURRENT-STATE / ubuntu deploy docs (and RUNTIME-STATE when live topology notes change) so they no longer present the embedded worker console as a supported or compatibility production path.
- Preserve Flow A/B, LinkedIn publication enablement, n8n HTTP contracts, and US-094 pairing semantics except for intentional removal of the embedded compatibility path.
- Frontend may drop or narrow `deliveryMode=embedded` / `build:embedded` once the worker no longer serves that path; separated delivery remains the only supported mode.
- Product progress: mark US-096 work started / demonstrated only when ACs are evidenced; **do not** mark US-093–US-096 Story accepted solely because code ships.

### Goals (US-096 acceptance criteria)

1. Worker API image/process does **not** ship operator-console static assets and does **not** serve former embedded console routes; old URLs fail closed with clear operator-visible messaging.
2. Worker build/deploy path does **not** require embedding the SPA; API builds succeed without a frontend production build step.
3. Operator UI remains a distinct project/service; consumes worker only via configured HTTP + pairing; no API internals/secrets/mounts in the UI.
4. Supported production topology is exclusively separated UI → API over HTTP; docs no longer present embedded console as supported/compatibility production path.
5. Outcome visible/understandable (operators use `:8011`; API container is API-only).
6. Failures/blocked states clearly communicated (decommissioned-route messaging + existing separated-UI config/pairing blocks).
7. Existing completed work preserved except intentional removal of the embedded compatibility path.

### Non-goals / intentionally excluded

- Do **not** implement Google/OIDC/JWT (BL-035).
- Do **not** redesign US-094 pairing or the US-095 regression matrix (keep holds green where still applicable).
- Do **not** mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Do **not** introduce n8n Execute Command (ADR-0001).
- Do **not** claim public internet exposure beyond BL-026.
- Do **not** mark US-093 / US-094 / US-095 / US-096 Story accepted solely because code ships.
- Do **not** reopen unrelated backlog items.

## Capabilities

### New Capabilities

- *(none)* — hard independence is expressed by modifying existing BL-034 capabilities rather than introducing a new capability id.

### Modified Capabilities

- `linkedin-variant-supervision-console`: Remove optional worker-embedded compatibility serving of the console SPA; require that former console routes fail closed with operator-visible decommission messaging; secrets-audit language MUST target the separated UI artifact (not worker-served static paths); preserve separated-UI HTTP client + supervision behavior.
- `operator-ui-deployment`: Require hard UI/API independence—API artifact has no operator UI surface; UI artifact has no API internals except configured HTTP base URL + pairing; exclusive supported production topology is separated UI → API; docs must not describe embedded console as supported/compatibility production path.
- `operator-ui-api-environment-pairing`: Remove or supersede language that exempts embedded worker-console mode from env-label/pairing requirements (embedded mode is decommissioned).
- `separated-operator-ui-capability-regression`: Supersede US-095 out-of-scope clause that deferred embedded-console decommission; US-096 now removes that path while keeping regression holds applicable to the separated path.
- `ubuntu-server-worker-deployment`: Deploy/docs MUST treat `:8011` separated UI as the exclusive supported console path; worker image MUST NOT require frontend embed steps; former `:8010/.../console/...` URLs are decommissioned (fail closed).

## Impact

- **Worker:** Remove `StaticFiles` mount and `GET /flow-a/console/linkedin-variant-supervision` SPA serving; replace with fail-closed HTML/JSON responses; purge `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/` (and related loaders); update Dockerfile comments/build expectations so API build needs no `build:embedded`.
- **Frontend:** Separated image/service remains the only production delivery; remove or retire `build:embedded` / `deliveryMode=embedded` paths that exist solely for worker embedding; keep US-093/094/095 config/pairing/regression behavior for separated mode.
- **Tests:** Prove API no longer serves console assets/routes; prove API build path does not require frontend prod build; keep US-093/094/095 holds green where still applicable; no publication-flag mutation.
- **Docs:** CURRENT-STATE, ubuntu deploy guide, compose comments; RUNTIME-STATE only if live topology wording must drop embedded compatibility.
- **n8n / Flow A–B / LinkedIn publication:** unchanged contracts and enablement guards.
- **Branch:** implement on current BL-034 branch (`feat/us-095-regress-separated-operator-ui`) or a new `feat/us-096-…` from latest synced HEAD after US-095 / envLabel-narrowing archive—after explicit proposal approval.

## Backlog / story mapping

| ID | Role in this change |
|----|---------------------|
| **BL-034** | Parent epic — Separate Operator UI from Worker API |
| **US-093** | Prerequisite — separated UI artifact (already implemented/LAN-deployed; not Story accepted) |
| **US-094** | Prerequisite — UAT/prod pairing (already implemented/LAN-deployed; not Story accepted) |
| **US-095** | Prerequisite preference — separated-path regression (already implemented/LAN-deployed; not Story accepted) |
| **US-096** | **In scope** — Story 4 hard independence / decommission embedded console |
| **BL-035** | Out of scope — Google login |
