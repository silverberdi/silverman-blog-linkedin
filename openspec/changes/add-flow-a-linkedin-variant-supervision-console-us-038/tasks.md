## 1. Inspect and confirm read-API gap

- [x] 1.1 Confirm no existing authenticated GET already returns per-variant `campaign_id`, variant id, `audience`, `scheduled_at_utc`, and `publish_state` for pending variants (re-check `GET /flow-a/operational-status`, `GET /editorial-calendar/status`, and related handlers)
- [x] 1.2 Implement against the fixed paths: `GET /flow-a/linkedin-variants/pending-supervision` (read API) and `GET /flow-a/console/linkedin-variant-supervision` (static console)

## 2. Pending-supervision aggregation (read-only)

- [x] 2.1 Implement a read-only aggregation module that scans confined `metadata/campaigns/*.json` and emits rows only for `publish_state=pending` with required fields
- [x] 2.2 Join editorial calendar items by `campaign_id` when `editorial-calendar/calendar.json` loads; on missing/invalid calendar, still return pending rows and record a clear issue
- [x] 2.3 Include display-only enablement context (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` as boolean) without filtering pending rows and without exposing secrets
- [x] 2.4 Guarantee zero mutation: no campaign/calendar writes, no LinkedIn/DeepSeek/ComfyUI/Git calls, no US-017 POST invocations

## 3. HTTP read API

- [x] 3.1 Expose authenticated `GET /flow-a/linkedin-variants/pending-supervision` wired through existing API-key dependency
- [x] 3.2 Return structured JSON with `variants[]`, calendar join fields when present, and `issues[]` / status for partial or total read failures
- [x] 3.3 Reject unauthenticated requests with existing 401 semantics

## 4. Operator console surface (Story 1)

- [x] 4.1 Add minimal same-origin static HTML at `GET /flow-a/console/linkedin-variant-supervision` that consumes `GET /flow-a/linkedin-variants/pending-supervision` (no frontend framework)
- [x] 4.2 Render campaign- and/or calendar-aligned view showing required fields; empty pending set shows clear non-error copy
- [x] 4.3 Surface read/partial failures and enablement-off context clearly; do not label `pending` / `flow_a_complete` as LinkedIn API published
- [x] 4.4 Omit edit/defer/cancel controls (US-039/US-040); optionally link to US-015/US-016/US-017 ops docs for guidance only
- [x] 4.5 Ensure committed HTML and docs never embed API keys, tokens, or secret-like placeholders (`CHANGE_ME`, `sk-…`, `Bearer …`, hardcoded `X-API-Key` values); operators supply the key at runtime only

## 5. Tests

- [x] 5.1 Behavioral tests: pending rows with required fields; empty pending set; calendar missing/invalid still lists variants; partial campaign read failure; auth 401 against `GET /flow-a/linkedin-variants/pending-supervision`
- [x] 5.2 Prove read path does not mutate campaign or calendar fixtures (byte-identical or equivalent fingerprint assertion)
- [x] 5.3 Assert enablement-off is display context only (pending rows still returned)
- [x] 5.4 Add an explicit static-HTML secrets audit test that fails if the console asset contains API keys, bearer tokens, or secret-like placeholders such as `CHANGE_ME`
- [x] 5.5 Run targeted pytest for new module/route/tests; fix any new warnings attributable to this change; run `git diff --check`

## 6. Docs and progress (leave Story accepted / BL-015 closed unchecked)

- [x] 6.1 Update `docs/CURRENT-STATE.md` to record US-038 / BL-015 Story 1 console as implemented or in progress (not Story accepted; not BL-015 closed; not unattended production), citing the fixed paths
- [x] 6.2 Optionally cross-link policy/mechanics “future console” language to `GET /flow-a/console/linkedin-variant-supervision` without rewriting US-015/US-016/US-017 substance
- [x] 6.3 Update `docs/product/progress-checklist.md` for US-038 in-progress items only when demonstrated (e.g. Story reviewed, Work started, Business outcome demonstrated) — **do not** check Story accepted, All user stories completed, or BL-015 closed
- [x] 6.4 Update `docs/product/user-stories.md` US-038 acceptance-criteria checkboxes only for criteria actually demonstrated by tests/smoke — leave undemonstrated criteria and Story accepted unchecked

## 7. Business validation gate

- [x] 7.1 Map demonstrated outcomes to US-038 acceptance criteria (pending fields, calendar alignment, operator-visible outcome, failure communication, no duplication of closed work)
- [x] 7.2 Confirm US-039/US-040, BL-007 behavior, publication guards, and Flow B remain untouched
- [x] 7.3 Stop short of claiming US-038 Story accepted or BL-015 closed pending explicit operator acceptance after review
