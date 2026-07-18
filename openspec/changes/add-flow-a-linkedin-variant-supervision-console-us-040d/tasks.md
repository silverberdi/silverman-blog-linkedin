## 1. Auth session and capability model

- [x] 1.1 Extend `AuthProvider` (and/or store) with explicit session signals and capabilities: anonymous / authenticated / expired / forbidden / service-unavailable mapping inputs plus `canRead` / `canMutate` (MemoryBearer: credential ⇒ both true; none ⇒ both false) without browser storage (AC: auth behind client boundary; session states; OIDC-swappable)
- [x] 1.2 Extend typed `SupervisionApiClient` error mapping for 401 → expired (clear credential), 403 → forbidden, network/5xx → service-unavailable; keep 422 distinct; never echo secrets (AC: session states; failures communicated)
- [x] 1.3 Ensure all console worker calls (pending-supervision, schedule-visibility, correct/defer/cancel, calendar schedule-update) remain on the typed client with injectable auth; relative same-origin paths only (AC: client boundary; same-origin; ADR-0001)

## 2. UI session presentation and mutation gating

- [x] 2.1 Surface anonymous, authenticated, expired-session, forbidden, and service-unavailable states in AppShell/status banners with qualified language (`pending`/`queued`/`cancelled`/`flow_a_complete`/blog handoff ≠ LinkedIn API published) (AC: represent five states; outcomes understandable)
- [x] 2.2 Gate edit/defer/cancel and ScheduleEditor commit controls so anonymous and read-only (`!canMutate`) sessions cannot execute mutations; worker remains authoritative rejector (AC: prevent unauthenticated/read-only mutations)
- [x] 2.3 On session expiry mid-edit: preserve visible list/calendar context and unsaved schedule draft; show re-auth guidance; after re-auth allow resume without silently clearing the draft (AC: mobile session expiry graceful)
- [x] 2.4 Add a clear re-auth control that uses the injectable provider (prompt/sign-in) without persisting credentials to `localStorage`/`sessionStorage` (AC: no secrets in browser storage; guide re-auth)

## 3. CORS / public-exposure documentation (no activation)

- [x] 3.1 Document same-origin default and restrictable CORS allowlist strategy for a future distinct-origin SPA in frontend README (and ops note if needed); do not enable permissive CORS middleware in this slice (AC: same-origin or documented CORS; no public activation)
- [x] 3.2 Document that public URL hosting and Google/OIDC authentication activation are out of scope and require a separate security OpenSpec change before internet exposure (AC: document activation deferred)

## 4. Provider swap readiness without calendar churn

- [x] 4.1 Keep list / Month calendar / ScheduleEditor free of auth-header construction; verify a mock alternate provider (OIDC-style bearer or cookie/`credentials` style) can be injected without editing those components (AC: request layer swappable without calendar component changes)
- [x] 4.2 Confirm no hardcoded API keys, tokens, mount paths, LAN-only hosts, or secret-like placeholders in frontend source, built HTML/JS, or logs (AC: no hardcoded secrets/local-only assumptions)

## 5. Frontend and worker verification

- [x] 5.1 Vitest: session-state mapping (anonymous/authenticated/expired/forbidden/unavailable); mutation controls disabled when `!canMutate`; expiry mid-edit preserves draft; 403/5xx mapping; provider-swap smoke (AC: frontend validation for auth-readiness)
- [x] 5.2 Desktop + mobile viewport checks for expired-session banner + draft preservation on schedule editor (AC: mobile expiry UX; US-040E polish beyond this not required)
- [x] 5.3 Rebuild static assets into worker static path; console route still serves SPA same-origin; secrets audit on source + built assets passes (AC: static serving; secrets)
- [x] 5.4 Run targeted pytest for console route / secrets audit and any touched worker surfaces; run frontend test/build; fix warnings attributable to this change; run `git diff --check`
- [x] 5.5 Verify no public URL activation, no live Google IdP, no BFF/DB/user-mgmt, no LinkedIn API publish, no enablement bypass, no n8n Execute Command, no browser mount writes, US-040A–C preserved, US-040E not implemented (AC: non-goals)

## 6. Docs and business progress (demonstrated only)

- [x] 6.1 Update `docs/CURRENT-STATE.md` for US-040D auth readiness (preserve US-040A–C; public URL + Google not activated; US-040E not done; not Story accepted; not BL-015 closed)
- [x] 6.2 Update `docs/product/progress-checklist.md` US-040D marks only for criteria actually demonstrated (do not mark Story accepted or BL-015 closed from apply alone)
- [x] 6.3 Update `docs/product/user-stories.md` US-040D acceptance checkboxes only when each criterion is demonstrated with evidence
- [x] 6.4 Final business-validation pass against US-040D acceptance criteria in `docs/product/user-stories.md`: client+middleware boundary; five session states; no hardcoded secrets/local-only assumptions; same-origin or documented CORS; OIDC/cookie-swappable request layer without calendar churn; unauthenticated/read-only cannot mutate; mobile expiry preserves context/drafts; public deploy + Google activation documented out of scope; understandable outcomes/failures; no unintentional duplication of US-040A–C / US-040E / Flow B
