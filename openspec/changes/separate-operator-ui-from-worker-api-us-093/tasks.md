## 1. Branch and frontend API base URL

- [x] 1.1 Create/switch to `feat/us-093-separate-operator-ui` (or equivalent) from current integration base; do not implement on `main`
- [x] 1.2 Add runtime config loader for `SILVERMAN_OPERATOR_UI_API_BASE_URL` (and optional reserved env label hook) into the Vite SPA without embedding secrets
- [x] 1.3 Extend `SupervisionApiClient` with injectable absolute `apiBaseUrl`; join all existing route paths to that base for separated-UI mode
- [x] 1.4 Add operator-visible fail-closed blocked UI when separated mode has missing/invalid API base URL (no silent relative fallback)
- [x] 1.5 Add Vitest coverage for base-URL join, missing/invalid config blocked state, and unchanged auth-gated client behavior

## 2. Separated UI packaging

- [x] 2.1 Add standalone Vite build path (`base: '/'`, output consumed by UI image) while retaining optional embedded `build:embedded` (or equivalent) for worker compatibility
- [x] 2.2 Add UI Dockerfile (Node build stage + nginx/static serve stage) with entrypoint that injects non-secret `config.js` from env
- [x] 2.3 Verify UI image contains no API keys / secret-like placeholders in built assets

## 3. Worker CORS and compatibility route

- [x] 3.1 Add worker env `SILVERMAN_OPERATOR_UI_ORIGINS` allowlist; enable CORS only for listed origins (no wildcard when unset)
- [x] 3.2 Add/adjust tests for allowlisted origin vs empty allowlist behavior
- [x] 3.3 Keep `GET /flow-a/console/linkedin-variant-supervision` as optional compatibility (or documented notice/redirect); do not remove without an explicit follow-up

## 4. Server compose and env docs

- [x] 4.1 Add `silverman-operator-ui` (or equivalent) service to `deploy/server/` compose with distinct LAN port (default `8011` unless conflict documented)
- [x] 4.2 Update `deploy/server/` env examples for UI API base URL + worker origin allowlist (placeholders only)
- [x] 4.3 Update `docs/deployment/ubuntu-server-worker-deployment.md` for dual-service topology and ADR-0001 reminder (n8n → worker HTTP only)

## 5. Operator docs and CURRENT-STATE

- [x] 5.1 Update `docs/CURRENT-STATE.md` runtime topology for worker `:8010` + operator UI port; note US-094 pairing not done
- [x] 5.2 Thin pointer in BL-026 exposure inventory / ops doc if needed: new LAN UI port only; no public console claim
- [x] 5.3 Confirm n8n workflow exports unchanged (no Execute Command introduced)

## 6. Verification

- [x] 6.1 Run frontend Vitest for touched console suites
- [x] 6.2 Run targeted pytest for CORS / console route compatibility coverage
- [x] 6.3 Locally (or LAN) smoke: UI serves SPA; authenticated worker read via configured base URL succeeds; missing base URL shows blocked state
- [x] 6.4 `git diff --check` clean; secrets audit on new/modified files

## 7. Business validation (post-apply / Story accepted gate)

- [x] 7.1 Demonstrate US-093 ACs with evidence (distinct UI artifact/service; browser→worker HTTP via typed client; n8n still worker-only; operator-visible outcomes and failures)
- [x] 7.2 Update `docs/product/user-stories.md` US-093 status only when ACs demonstrated; leave US-094/US-095 unchecked
- [x] 7.3 Update `docs/product/progress-checklist.md` for US-093 progress without closing BL-034 until remaining stories accepted
