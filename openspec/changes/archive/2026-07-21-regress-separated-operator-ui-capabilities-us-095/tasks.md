## 1. Branch and baseline

- [x] 1.1 Create/switch to `feat/us-095-regress-separated-operator-ui` (or equivalent) from an integration base that already includes US-093 + US-094; do not implement on `main`
- [x] 1.2 Confirm US-093/US-094 hooks present: separated UI `:8011`, `SILVERMAN_OPERATOR_UI_API_BASE_URL`, pairing label + health `deployment_environment`, `ConfigBlockedScreen`, typed `SupervisionApiClient`, CORS allowlist—verify hold only (no packaging/pairing redesign)

## 2. Absolute-base client regression (matrix R1–R4)

- [x] 2.1 Add or extend focused Vitest (`us095.*` and/or targeted `us093` extensions) proving separated-mode `joinApiUrl` / client uses absolute worker origin with **no** relative same-origin fallback when base URL is valid
- [x] 2.2 Assert authenticated `getScheduleVisibility` issues `GET {apiBaseUrl}/flow-a/schedule-visibility?...`
- [x] 2.3 Assert authenticated `getPendingSupervision` issues `GET {apiBaseUrl}/flow-a/linkedin-variants/pending-supervision`
- [x] 2.4 Assert a representative BL-032 mutation with `dry_run: true` (prefer `deferVariant` postpone/reschedule) posts to `{apiBaseUrl}` + existing route; do not invent endpoints; do not require live LinkedIn publish

## 3. Auth session gating and fail-closed holds (matrix R5–R7)

- [x] 3.1 Add or extend Vitest proving US-040D sign-in / `canMutate` / clear-session still work on the separated UI bootstrap path without Google/OIDC; preserve injectable `AuthProvider` boundary
- [x] 3.2 Re-run existing `us093.operator-ui-config` (or equivalent) and confirm missing/invalid API base URL still fail-closed with operator-visible block and no relative API traffic
- [x] 3.3 Re-run existing `us094.environment-pairing` (or equivalent) and confirm mismatch / missing label / unreadable health still fail-closed with no authenticated supervision/mutation

## 4. Operator-visible outcome and optional smoke (matrix R8)

- [x] 4.1 Ensure Vitest (and/or a short documented local/LAN smoke checklist) shows successful paired separated path surfaces understandable schedule/control-center outcomes (including empty states) and that blocked states remain clear (env var names only; no secrets)
- [x] 4.2 If optional LAN smoke is run (`:8011` → `:8010`): Bearer paste, schedule + pending reads, one dry-run postpone when safe fixtures exist; record pass/fail without claiming public exposure beyond BL-026 or Story accepted

  - **Optional LAN smoke:** not run this session. Primary evidence is Vitest `us095.separated-capability-regression.test.tsx` (R1–R8). No public-exposure or Story-accepted claim.

## 5. Invariants, docs, and business validation (matrix R9)

- [x] 5.1 Confirm no n8n Execute Command introduced; no mutation of `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; no Flow/LinkedIn business-logic rewrites; US-096 embedded-console removal not started
- [x] 5.2 Run targeted Vitest for US-095 matrix suites (and keep US-093/US-094 auth-related suites green); fix warnings attributable to this change; add pytest only if a worker/CORS defect blocks the matrix
- [x] 5.3 `git diff --check` clean; secrets audit on new/modified files (env var names and placeholders only)
- [x] 5.4 Update `docs/CURRENT-STATE.md` for US-095 regression evidence (local and/or controlled LAN); update `docs/RUNTIME-STATE.md` only if live flags/topology changed during optional smoke
- [x] 5.5 Update `docs/product/user-stories.md` / `docs/product/progress-checklist.md` (and backlog status line if needed) only for US-095 ACs actually demonstrated; leave Story-accepted / deploy gates honest; leave US-096 unchecked
