## 1. Confirm reuse of US-017 cancel / defer contracts

- [x] 1.1 Confirm `POST /cancel-linkedin-publication` request body (`campaign_id`, `variant`, `dry_run` default `true`, optional `reason` / `idempotency_key`), auth, and stable error codes match design consumption (no new mutation routes)
- [x] 1.2 Confirm existing console defer wiring to `POST /defer-linkedin-variant` remains the defer half of cancel-or-defer (no second defer SoT)
- [x] 1.3 Implement against fixed surfaces only: extend `GET /flow-a/console/linkedin-variant-supervision` + `GET /flow-a/linkedin-variants/pending-supervision`; call existing US-017 cancel POST from the browser

## 2. Pending-supervision blocked-state enrichment (read-only)

- [x] 2.1 Keep response `linkedin_publication_enabled` and strengthen console presentation as display-only blocked context (do not filter pending rows; do not change the env flag)
- [x] 2.2 Ensure pending rows expose deferred eligibility context (`operator_supervision_last_action`, `auto_queue_eligible`; optional nullable reason from `operator_supervision` when present)
- [x] 2.3 While scanning campaigns for pending aggregation, collect compact secret-safe `integration_failures[]` (or equivalent) for sibling variants with `publish_state=failed` (at least campaign id, variant id, `publish_state`; include `last_error_code` / `http_status` when present)
- [x] 2.4 Preserve zero server-side mutation on the GET path (no campaign/calendar writes; no US-017 POST invocations server-side; no LinkedIn/DeepSeek/ComfyUI/Git)

## 3. Console cancel action + blocked-state UI (Story 3)

- [x] 3.1 Extend static HTML/JS at `GET /flow-a/console/linkedin-variant-supervision` with Cancel control for pending rows (no frontend framework; retain Edit/Defer)
- [x] 3.2 Wire Cancel to authenticated `POST /cancel-linkedin-publication` using session API key; optional reason; explicit dry-run control defaulting on; confirm before real cancel
- [x] 3.3 On success, show clear dry-run vs real outcome; on real success, refresh pending-supervision so the cancelled variant leaves the list; explain BL-007 eligibility exclusion; keep `pending`/`cancelled` ≠ LinkedIn API published language
- [x] 3.4 Surface blocked/deferred context on the page: enablement banner, per-row deferred/`auto_queue_eligible` copy, and integration-failure summary from the read API
- [x] 3.5 Surface cancel failures clearly for 401, 422, and existing codes (`linkedin_publish_cancel_not_allowed`, `linkedin_supervision_variant_not_pending`, `linkedin_supervision_action_not_allowed`, `linkedin_supervision_idempotency_conflict` when returned); retain Story 2 edit/defer error mapping
- [x] 3.6 Remove “cancel remains US-040” deferral copy; note Story 3 cancel + blocked context; extend secrets audit (no keys/tokens/`CHANGE_ME`/secret-like placeholders in committed HTML)

## 4. Tests

- [x] 4.1 Extend pending-supervision tests: deferred eligibility fields visible; `integration_failures` populated for failed siblings; enablement still display-only; GET still non-mutating
- [x] 4.2 Behavioral coverage for console/action contracts: cancel dry-run default; real cancel calls cancel endpoint shape; cancelled variant absent after refresh; error-code display paths (at least cancel-not-allowed and auth failure)
- [x] 4.3 Assert committed console HTML still passes secrets/placeholder audit; assert cancel wires only to `POST /cancel-linkedin-publication` (no parallel mutation route); assert edit/defer wiring preserved
- [x] 4.4 Run targeted pytest for touched modules/tests; fix new warnings attributable to this change; run `git diff --check`

## 5. Docs and progress (leave Story accepted / BL-015 closed unchecked)

- [x] 5.1 Update `docs/CURRENT-STATE.md` to record US-040 / BL-015 Story 3 console cancel + blocked-state surfacing as implemented or in progress (not Story accepted; not BL-015 closed; not unattended production)
- [x] 5.2 Optionally update `docs/operations/linkedin-variant-supervision-mechanics.md` (and policy cross-links if stale) that Story 3 console exercises cancel — do not rewrite US-017 normative contracts
- [x] 5.3 Update `docs/product/progress-checklist.md` for US-040 in-progress items only when demonstrated (e.g. Story reviewed, Work started, Business outcome demonstrated) — **do not** check Story accepted, All user stories completed, or BL-015 closed
- [x] 5.4 Update `docs/product/user-stories.md` US-040 acceptance-criteria checkboxes only for criteria actually demonstrated — leave undemonstrated criteria and Story accepted unchecked

## 6. Business validation gate

- [x] 6.1 Map demonstrated outcomes to US-040 acceptance criteria (cancel or defer before queue; blocked-state surfacing; HTTP-only / no guard bypass; visible outcome; failure communication; no duplication of closed work)
- [x] 6.2 Confirm BL-007 implementation, publication guards, US-015 default, US-038/US-039 contracts, and Flow B remain untouched beyond consuming existing cancel/defer eligibility effects
- [x] 6.3 Stop short of claiming US-040 Story accepted or BL-015 closed pending explicit operator acceptance after review
