## Why

US-093 delivered a separated operator UI (`:8011`) with injectable `SILVERMAN_OPERATOR_UI_API_BASE_URL` and a reserved `SILVERMAN_OPERATOR_UI_ENV_LABEL`, but nothing yet **pairs** a UAT UI with a UAT API (or prod with prod). After the UI/API split, a mis-pointed base URL could silently drive the console against the wrong environment. **BL-034 / US-094** (Story 2) closes that gap with declared environment identity, deploy-time defaults per environment, and fail-closed mismatch behavior—without standing up full BL-029 CI/UAT infrastructure or Google login (BL-035).

## What Changes

- Activate and normatively define **UI↔API environment pairing** on top of US-093 hooks: UI declares its intended environment; worker declares its deployment environment; separated UI validates agreement before using the API for supervision/mutation traffic.
- Ship **per-environment deploy defaults** (UAT profile → UAT API; prod profile → prod API) via runtime/non-secret env config and example overlays—not hosts baked into hashed JS.
- **Fail closed** with an operator-visible blocked state when environment labels disagree, when required pairing config is missing/invalid, or when the API’s advertised environment cannot be read for pairing—**no silent cross-environment writes**.
- Surface the active environment so operators can see which stack the console is bound to.
- Update operator topology docs and CURRENT-STATE / RUNTIME-STATE pointers when the pairing model is live (placeholders and env var names only; no secrets).
- Preserve ADR-0001 (n8n → worker HTTP only), US-040D Bearer paste, embedded console compatibility, and do **not** mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or rewrite Flow/LinkedIn/n8n business logic.

### Goals (US-094 acceptance criteria)

1. UAT UI is configured to call the UAT API (not prod) by default.
2. Prod UI is configured to call the prod API (not UAT) by default.
3. Misconfiguration fails closed with a clear operator-visible error (no silent cross-environment writes).
4. Document topology updates in CURRENT-STATE / RUNTIME-STATE when live.
5. Outcome visible and understandable to the operator; failures clearly communicated.
6. Existing completed work is not duplicated or unintentionally changed.

### Non-goals / intentionally excluded

- **US-095** full capability regression program (beyond noting pairing does not break core HTTP paths).
- **BL-035** Google/OIDC login (US-040D Bearer paste remains).
- **BL-029** CI/UAT stand-up beyond the minimum pairing config/docs this story needs (no full second-stack automation or CI gates).
- Public console exposure beyond BL-026 LAN acceptance.
- n8n Execute Command; n8n workflow rewrites; LinkedIn/Flow A–B business-logic rewrites.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

## Capabilities

### New Capabilities

- `operator-ui-api-environment-pairing`: Normative UAT/prod environment identity for the separated operator UI and worker API—declaration via non-secret deploy config, default per-environment pairing overlays, startup validation that UI and API environments agree, and fail-closed operator-visible blocked states on mismatch or missing pairing config (BL-034 / US-094).

### Modified Capabilities

- `operator-ui-deployment`: Supersede “ENV_LABEL reserved / US-094 not done” language; require activated environment-label config for separated-UI mode as part of supported production pairing; keep US-093 packaging/CORS/base-URL behavior intact.
- `linkedin-variant-supervision-console`: Require operator-visible environment identity and pairing-blocked UX in separated-UI mode; forbid proceeding with supervision/mutation API use when pairing fails.
- `ubuntu-server-worker-deployment`: Document UAT vs prod UI/API pairing defaults, env var names, and topology pointers without claiming public exposure or full BL-029 stand-up.
- `worker-foundation`: Extend `GET /health` (or an equivalent documented non-secret read) to advertise the worker’s deployment environment for UI pairing checks without exposing secrets.

## Impact

- **Frontend:** Activate `SILVERMAN_OPERATOR_UI_ENV_LABEL` (`uat` | `prod`); pairing check against API-advertised environment after base-URL validation; env badge / blocked screen; Vitest coverage. No business-screen rewrite.
- **Worker:** Non-secret `SILVERMAN_DEPLOYMENT_ENVIRONMENT` (or equivalent documented key); include value on health (or documented pairing read); pytest for config + health field. No LinkedIn enablement or Flow pipeline changes.
- **Deploy / docs:** UAT and prod env example overlays with matching UI base URL + env label + worker environment defaults (placeholders only); CURRENT-STATE / RUNTIME-STATE / ubuntu deploy topology updates when live.
- **n8n / publication / Flow A–B:** unchanged contracts; n8n still targets worker HTTP only (ADR-0001).
- **Auth:** US-040D Bearer paste unchanged; BL-035 out of scope.
- **Branch:** implement later on `feat/us-094-pair-operator-ui-api-environments` (or equivalent); do not implement on `main`.

## Backlog / story mapping

| ID | Role in this change |
|----|---------------------|
| **BL-034** | Parent epic — UI/API separation |
| **US-093** | Precondition — archived; hooks already exist |
| **US-094** | **In scope** — Story 2 (this change) |
| **US-095** | Out of scope beyond “core HTTP paths still work” |
| **BL-029** | Aligns only — no CI/UAT stand-up beyond pairing needs |
| **BL-035** | Out of scope |
