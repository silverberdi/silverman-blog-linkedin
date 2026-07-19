## 1. Settings store and validation

- [x] 1.1 Add `flow_b_gap_operator_settings` store module (Postgres `silverman_linkedin_db` via existing calendar DB URL or documented alias; `memory://` for tests) with idempotent `ensure_schema` and singleton load/save
- [x] 1.2 Implement documented defaults and `load_gap_operator_settings()` that returns DB values when present and defaults when the row is missing (`gap_trigger_enabled=false`, `gap_scan_mode=next_week`, friday/`15:00`, `min_lead_days=5`, `gap_posts_threshold=0`, `max_drafts_per_weekly_run=2`, `density_max_per_local_day=2`)
- [x] 1.3 Implement write-path validation: IANA `operator_timezone`, `HH:MM` time, weekday/`gap_scan_mode` enums, non-negative integers, boolean enablement; reject invalid writes without partial persist

## 2. Authenticated HTTP API

- [x] 2.1 Add authenticated `GET /flow-b/gap-operator-settings` returning effective settings + metadata (`source`, `updated_at_utc`); reject unauthenticated callers; never expose secrets
- [x] 2.2 Add authenticated `PUT /flow-b/gap-operator-settings` for full-document update with structured 422 validation errors; optional optimistic concurrency if low-cost
- [x] 2.3 Prove save does not enable LinkedIn API publish / does not mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; `gap_trigger_enabled=false` introduces no auto-trigger side effects
- [x] 2.4 Confirm no US-077 detect, US-082 trigger, discovery/draft, or approve/promote routes are added; no n8n Execute Command

## 3. Silverman Authority Manager UI

- [x] 3.1 Extend the existing supervision console with an authenticated Gap / Flow B settings surface (not a separate app) using the typed API client + session/`canMutate` patterns
- [x] 3.2 Wire form fields for all US-076 keys with client-side cues and worker validation error display; warn that auto-trigger stays fail-closed when disabled and that save ≠ LinkedIn publish
- [x] 3.3 Rebuild/publish static console assets into worker static path and ensure console HTML route still serves them

## 4. Tests

- [x] 4.1 Unit/API tests: defaults-when-missing, round-trip persist, validation failures, auth required, secret-free responses, LinkedIn publish guard untouched
- [x] 4.2 Frontend tests: settings view load/save happy path and validation/auth failure messaging
- [x] 4.3 Run targeted pytest (and frontend tests as applicable); fix warnings attributable to this change; `git diff --check` clean

## 5. Docs and product status

- [x] 5.1 Update `docs/operations/flow-b-simplified-policy.md` (and planning notes if needed) so US-076 settings are DB+UI SoT with defaults, without claiming detect/trigger implemented
- [x] 5.2 Update `docs/CURRENT-STATE.md` to record settings persistence **implemented** (not Story accepted / not deployed unless separately approved)
- [x] 5.3 After demonstrated AC (local), update `docs/product/user-stories.md` US-076 and `docs/product/progress-checklist.md` only to the validated state — do not mark Story accepted without operator walkthrough; do not close BL-019

## 6. Business validation gate

- [x] 6.1 Walk US-076 acceptance criteria against running local worker + console evidence (persist keys, UI edit/validation, defaults when missing, no secrets, fail-closed enablement, calendar SoT untouched)
- [x] 6.2 Record any remaining gaps explicitly; leave US-077+ unchecked
