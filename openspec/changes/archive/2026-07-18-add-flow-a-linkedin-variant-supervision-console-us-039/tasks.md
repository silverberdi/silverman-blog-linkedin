## 1. Confirm reuse of US-017 mutation contracts

- [x] 1.1 Confirm `POST /correct-linkedin-variant` and `POST /defer-linkedin-variant` request bodies, dry-run default (`true`), auth, and stable error codes match design consumption (no new mutation routes)
- [x] 1.2 Confirm draft artifact path used by correction (`linkedin-posts/generated/<campaign_id>/<variant_id>.md`) for pending-supervision `draft_content` reads
- [x] 1.3 Implement against fixed surfaces only: extend `GET /flow-a/console/linkedin-variant-supervision` + `GET /flow-a/linkedin-variants/pending-supervision`; call existing US-017 POSTs from the browser

## 2. Pending-supervision draft_content extension (read-only)

- [x] 2.1 Extend pending-supervision aggregation to include nullable `draft_content` from the generated draft artifact when readable
- [x] 2.2 When the artifact is missing/unreadable, set `draft_content` null, append a structured `issues[]` entry, and still return the pending row
- [x] 2.3 Preserve zero server-side mutation on the GET path (no campaign/calendar writes; no US-017 POST invocations server-side; no LinkedIn/DeepSeek/ComfyUI/Git)

## 3. Console edit and defer actions (Story 2)

- [x] 3.1 Extend static HTML/JS at `GET /flow-a/console/linkedin-variant-supervision` with Edit and Defer controls for pending rows (no frontend framework; no cancel control)
- [x] 3.2 Wire Edit to authenticated `POST /correct-linkedin-variant` using session API key; populate textarea from `draft_content`; optional reason; explicit dry-run control defaulting on; confirm before real write
- [x] 3.3 Wire Defer to authenticated `POST /defer-linkedin-variant` with future `new_scheduled_at_utc`; same dry-run/confirm posture; do not claim calendar auto-update
- [x] 3.4 On success, show clear dry-run vs real outcome; on real success, refresh pending-supervision so schedule / supervision display fields update; keep `pending` ≠ LinkedIn API published language
- [x] 3.5 Surface failures clearly for 401, 422, and US-017 codes (`linkedin_supervision_variant_not_pending`, `linkedin_supervision_defer_time_invalid`, `linkedin_supervision_edit_unchanged`, `linkedin_supervision_idempotency_conflict`, `linkedin_supervision_action_not_allowed`)
- [x] 3.6 Remove Story 1 “actions not available” copy; keep US-015/US-016 guidance links; note cancel remains US-040; extend secrets audit (no keys/tokens/`CHANGE_ME`/secret-like placeholders in committed HTML)

## 4. Tests

- [x] 4.1 Extend pending-supervision tests: `draft_content` present when artifact exists; null + issue when missing; GET still non-mutating
- [x] 4.2 Behavioral coverage for console/action contracts: edit dry-run default; real edit calls correct endpoint shape; defer future schedule; error-code display paths (at least not-pending and invalid defer time)
- [x] 4.3 Assert committed console HTML still passes secrets/placeholder audit; assert no cancel UI wiring to `POST /cancel-linkedin-publication`
- [x] 4.4 Run targeted pytest for touched modules/tests; fix new warnings attributable to this change; run `git diff --check`

## 5. Docs and progress (leave Story accepted / BL-015 closed unchecked)

- [x] 5.1 Update `docs/CURRENT-STATE.md` to record US-039 / BL-015 Story 2 console edit/defer as implemented or in progress (not Story accepted; not BL-015 closed; not unattended production)
- [x] 5.2 Optionally update `docs/operations/linkedin-variant-supervision-mechanics.md` cross-link that Story 2 console exercises edit/defer — do not rewrite US-017 normative contracts
- [x] 5.3 Update `docs/product/progress-checklist.md` for US-039 in-progress items only when demonstrated (e.g. Story reviewed, Work started, Business outcome demonstrated) — **do not** check Story accepted, All user stories completed, or BL-015 closed
- [x] 5.4 Update `docs/product/user-stories.md` US-039 acceptance-criteria checkboxes only for criteria actually demonstrated — leave undemonstrated criteria and Story accepted unchecked

## 6. Business validation gate

- [x] 6.1 Map demonstrated outcomes to US-039 acceptance criteria (edit before queue; defer/reschedule; traceable US-017 persistence; visible outcome; failure communication; no duplication of closed work)
- [x] 6.2 Confirm US-040 cancel UI, BL-007 implementation changes, publication guards, US-015 default, and Flow B remain untouched
- [x] 6.3 Stop short of claiming US-039 Story accepted or BL-015 closed pending explicit operator acceptance after review
