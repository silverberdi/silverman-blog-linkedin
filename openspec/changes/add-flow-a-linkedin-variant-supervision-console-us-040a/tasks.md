## 1. Scaffold React + TypeScript + Vite app

- [x] 1.1 Create `frontend/linkedin-variant-supervision-console/` (or equivalent) with Vite + React + TypeScript using the stack decision from `proposal.md` (AC: stack defined before impl — already decided; scaffold matches it)
- [x] 1.2 Add minimal dependencies (`react`, `react-dom`, TypeScript, Vite, Vitest + Testing Library) and document each production dependency justification in a short frontend README
- [x] 1.3 Configure Vite `base` for same-origin asset URLs under the console route prefix; set `outDir` to `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/` (or design-equivalent)
- [x] 1.4 Confirm production `npm run build` emits `index.html` + hashed assets (AC: static artifacts; AC: frontend validation build success)

## 2. Typed API client and shared model

- [x] 2.1 Implement typed API client for `GET /flow-a/linkedin-variants/pending-supervision` and US-017 `POST /correct-linkedin-variant`, `POST /defer-linkedin-variant`, `POST /cancel-linkedin-publication` (AC: centralized typed client; no new mutation SoT)
- [x] 2.2 Implement injectable auth header provider (in-memory / prompt only; no secrets in source, HTML, logs, or browser storage) ready for later OIDC swap without changing business components (AC: US-040D readiness boundary)
- [x] 2.3 Implement shared error mapping for 401/422 and known US-017 supervision/cancel codes into operator-facing `ApiError` states (AC: failures clearly communicated; AC: API error mapping validation)
- [x] 2.4 Implement shared normalized frontend model (`campaign_id` + `variant_id` identity, schedule, state, actions, issues) fed by pending-supervision responses (AC: list/calendar cannot disagree)

## 3. Componentized screens — list parity + scaffolds

- [x] 3.1 Implement `AppShell` with dry-run default banner, enablement display-only context, and qualified language (`pending` / `cancelled` / `flow_a_complete` ≠ LinkedIn API published) (AC: outcome understandable; console-layer only)
- [x] 3.2 Port list-oriented pending-variant supervision as a first-class `ListView` with Stories 1–3 fields and edit/defer/cancel via the typed client (AC: preserve list experience; reuse US-017)
- [x] 3.3 Implement confirmation flow for real cancel (and real mutations) matching existing dry-run vs real semantics (AC: confirmation; preserve mutation semantics)
- [x] 3.4 Scaffold `MonthCalendarView`, `ItemDetail`, `ScheduleEditor`, `StatusSummary`, and `Filters` with clear extension boundaries; wire calendar scaffold to the shared model without implementing US-040B/US-040C behavior (AC: componentized scaffolds; defer full calendar/schedule)
- [x] 3.5 Add view-switcher stub so list remains first-class and calendar scaffold is reachable without replacing list (AC: list preserved; calendar scaffold only)

## 4. Worker static serving and migration cutover

- [x] 4.1 Update worker console route `GET /flow-a/console/linkedin-variant-supervision` to serve Vite `index.html` and mount same-origin static assets safely (no path traversal) (AC: preserve route or compatible replacement; no separate frontend server)
- [x] 4.2 Stop serving / remove legacy monolithic `linkedin_variant_supervision_console.html` once cutover works (AC: no duplicated console SoT)
- [x] 4.3 Document build-before-deploy (`npm ci && npm run build`) so Docker `COPY src` includes current assets without a Node runtime in the image (AC: worker/deployment path; small justified deps)
- [x] 4.4 Verify no BFF, database, user-management, public hosting, LinkedIn API calls, enablement bypass, n8n Execute Command, or browser mount-path reads were introduced (AC: explicit non-goals)

## 5. Frontend and worker verification

- [x] 5.1 Add Vitest/Testing Library tests for key list component behavior (load rows, dry-run default, action wiring mocks) (AC: key component behavior)
- [x] 5.2 Add tests for API client error mapping (401, 422, known supervision codes) (AC: API error mapping)
- [x] 5.3 Add desktop and mobile viewport validation evidence for the list-oriented console (AC: desktop + mobile viewports)
- [x] 5.4 Update Python console/secrets-audit tests for new static asset layout; ensure secrets audit passes on source + built assets (AC: secrets; existing work not broken)
- [x] 5.5 Run targeted pytest for pending-supervision/console serving plus frontend test/build scripts; fix warnings attributable to this change; run `git diff --check`

## 6. Docs and business progress (demonstrated only)

- [x] 6.1 Update `docs/CURRENT-STATE.md` for US-040A console delivery (React/Vite static build served by worker; list parity; scaffolds for B/C; US-040B–US-040E still not implemented; not Story accepted / not BL-015 closed)
- [x] 6.2 Update `docs/product/progress-checklist.md` US-040A marks only for criteria actually demonstrated (story reviewed / work started / outcome demonstrated as appropriate — do not mark Story accepted or BL-015 closed from apply alone)
- [x] 6.3 Update `docs/product/user-stories.md` US-040A acceptance checkboxes only when each criterion is demonstrated with evidence
- [x] 6.4 Final business-validation pass against US-040A acceptance criteria in `docs/product/user-stories.md`: confirm stack decision recorded, console-layer-only scope held, route preserved, list first-class, scaffolds present, typed client, static serving, shared model, deps justified, frontend validation evidence, outcomes/failures clear, no unintentional duplication of Stories 1–3 or Flow B
