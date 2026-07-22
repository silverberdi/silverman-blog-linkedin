## 1. Branch and baseline

- [x] 1.1 Create/switch to `feat/us-094-pair-operator-ui-api-environments` (or equivalent) from current integration base; do not implement on `main`
- [x] 1.2 Confirm US-093 hooks present: runtime `config.js` / `SILVERMAN_OPERATOR_UI_API_BASE_URL`, reserved `SILVERMAN_OPERATOR_UI_ENV_LABEL`, `ConfigBlockedScreen`, CORS allowlist, compose UI service on `:8011`

## 2. Worker deployment environment identity

- [x] 2.1 Add non-secret `SILVERMAN_DEPLOYMENT_ENVIRONMENT` (`uat` | `prod`, lowercase-normalized) to worker settings/config validation with actionable errors (no secrets in messages)
- [x] 2.2 Advertise `deployment_environment` on `GET /health` when configured; do not invent a fake identity when unset
- [x] 2.3 Add/adjust pytest for valid load, invalid value fail-closed, and health field (no secret leakage)
- [x] 2.4 Verify CORS allowlist still permits separated-UI `GET /health` from configured UI origins; extend if needed without wildcard CORS

## 3. Separated UI pairing gate

- [x] 3.1 Require `SILVERMAN_OPERATOR_UI_ENV_LABEL` as `uat` | `prod` in separated-UI mode (activate US-093 hook); fail closed with operator-visible blocked state when missing/invalid
- [x] 3.2 After base-URL validation, fetch `{apiBaseUrl}/health`, compare `deployment_environment` to UI env label; fail closed on mismatch or unreadable identity (no authenticated supervision/mutation; no relative same-origin fallback)
- [x] 3.3 Show active environment in console chrome when pairing succeeds; extend blocked UX for pairing failures (env var names only)
- [x] 3.4 Leave embedded compatibility mode without pairing enforcement
- [x] 3.5 Add Vitest coverage: matching uat/prod proceed; mismatch blocks; missing label blocks; unreadable health blocks

## 4. Deploy defaults and docs

- [x] 4.1 Add UAT and prod env example overlays (or clearly separated sections) in `deploy/server/` with matching worker/UI tokens and distinct API base URL placeholders (UAT UI → UAT API; prod UI → prod API); no secrets
- [x] 4.2 Wire compose/runtime injection so UI `config.js` receives env label alongside API base URL for the selected profile
- [x] 4.3 Update `docs/deployment/ubuntu-server-worker-deployment.md` for pairing vocabulary, env var names, and ADR-0001 (n8n → worker only); do not claim public console exposure or full BL-029 stand-up
- [x] 4.4 Update `docs/CURRENT-STATE.md` topology for US-094 pairing model; update `docs/RUNTIME-STATE.md` only when a live stack applies pairing

## 5. Verification and business validation

- [x] 5.1 Run targeted pytest for worker env/health changes and Vitest for UI pairing; fix warnings attributable to this change
- [x] 5.2 Smoke (local or documented): matching pair loads a core HTTP path (e.g. schedule visibility or pending-supervision read); forced mismatch blocks authenticated use
- [x] 5.3 Confirm no n8n Execute Command introduced; no mutation of `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; no Flow/LinkedIn business-logic rewrites
- [x] 5.4 `git diff --check` clean; secrets audit on new/modified files (env var names and placeholders only)
- [x] 5.5 Update `docs/product/user-stories.md` / `docs/product/progress-checklist.md` only for US-094 ACs actually demonstrated; leave US-095 and Story-accepted gates honest (operator gate / deploy as applicable)
