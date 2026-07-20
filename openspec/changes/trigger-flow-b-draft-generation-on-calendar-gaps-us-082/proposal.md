## Why

US-076–US-081 are implemented: operators can persist gap settings, inspect next-week LinkedIn gaps, discover topics, generate drafts into `pending-approval/`, approve/reject, and promote with spill A. Without US-082, a detected empty next week never starts Flow B automatically — operators must manually chain discovery + draft generation, so cadence gaps stay silent.

## Goals

- When `gap_trigger_enabled` is true and the sensor reports one or more gaps for the target week, trigger Flow B discovery + draft generation up to **`max_drafts_per_weekly_run` (default 2)** into `pending-approval/` without auto-publishing.
- When there is no gap, trigger is disabled, or an idempotent batch already exists for that ISO week (`flow_b_gap_week:{operator_tz}:{YYYY}-W{ww}`), perform a clean no-op (no duplicate draft spam).
- Orchestration MUST use **n8n Schedule → worker HTTP** (ADR-0001; no Execute Command); worker enforces local day/time / enablement from US-076 (no-op outside window); repo n8n export stays `active: false` until operator activation.
- Pass gap context (ISO week, `empty_days[]`) into US-078/US-079; leave drafts for US-080/US-081; do not skip the blog gate.
- Surplus LinkedIn scheduling after approve/promote remains owned by US-081 (spill A); this story MUST NOT mark LinkedIn API published.
- Tests + CURRENT-STATE as **implemented** (not Story accepted); do **not** close BL-019 without Story accepted for the BL-019 stories that apply.

## Non-goals

- Auto-publish blog or LinkedIn without Flow A guards / enablement flags.
- Re-implement detect (US-077), settings (US-076), discovery (US-078), draft gen (US-079), approve (US-080), or promote/spill (US-081).
- Enable `gap_trigger_enabled` by default (remain fail-closed).
- Mark US-082 Story accepted without operator walkthrough.
- Close BL-018 / BL-017 / BL-019 without their Story accepted gates.
- Redefine gap as density capacity (US-040K max 2 remains scheduling capacity only; gap=0 stays US-077).

## What Changes

- Add authenticated worker HTTP **gap trigger** that loads US-076 settings, enforces local weekly window + `gap_trigger_enabled`, calls US-077 detect, and on gaps runs US-078 discovery then US-079 draft generation (capped by `max_drafts_per_weekly_run`) with gap context into `pending-approval/`.
- Persist ISO-week idempotency for key `flow_b_gap_week:{operator_tz}:{YYYY}-W{ww}` so re-runs no-op when a batch is pending or completed.
- Clean no-op responses when disabled, outside window, no gaps, or idempotent hit — no duplicate drafts.
- Add repo **n8n Schedule → HTTP** workflow export calling the trigger endpoint; export MUST ship with `active: false`.
- Update CURRENT-STATE / Flow B policy cross-links as implemented (not Story accepted); leave BL-019 open until applicable Story accepted gates.
- Tests covering enablement window, no-gap/disabled/idempotent no-ops, successful trigger batch ≤ max drafts, gap context passthrough, auth, and no LinkedIn/blog auto-publish.

## Capabilities

### New Capabilities

- `flow-b-calendar-gap-trigger`: Authenticated weekly gap-trigger orchestration (settings window + enablement → detect → discover → generate into `pending-approval/`); ISO-week idempotency; clean no-ops; inactive n8n Schedule→HTTP export; ADR-0001 HTTP-only; no auto-publish / no LinkedIn API publish; does not implement US-076–US-081 internals.

### Modified Capabilities

- `flow-b-simplified-process`: Cross-link that US-082 runtime gap trigger now exists as a separate capability (policy defaults unchanged; docs MUST NOT claim Story accepted / BL-019 closed; MUST NOT claim LinkedIn API published).
- `flow-b-calendar-gap-detect`: Clarify detect remains non-mutating and MAY be consumed by the gap-trigger capability; trigger ownership stays US-082 (detect MUST NOT itself start discovery/drafts).

## Impact

- **Code:** New Flow B gap-trigger module(s); thin FastAPI route (e.g. `POST /flow-b/gap-trigger`); idempotency store/record for ISO-week batch keys; reuse `load_gap_operator_settings()`, detect, discover-topics, generate-blog-drafts services; tests; n8n workflow JSON under `n8n/workflows/`.
- **APIs:** New authenticated trigger endpoint; existing settings/detect/discover/generate/approve/promote contracts unchanged in purpose (trigger consumes them).
- **Deps:** US-076 settings (`gap_trigger_enabled` default false, weekly local day/time, `max_drafts_per_weekly_run`); US-077 detect result (`gaps[]`, target ISO week); US-078/US-079 optional gap context; same worker API-key auth; DeepSeek/ComfyUI only via existing generate path (mocked in unit tests).
- **Ops:** CURRENT-STATE + Flow B policy note gap trigger implemented; n8n export inactive until operator activation; Story accepted / BL-019 close remain operator gates.
- **Product:** **BL-019 / US-082** primary (trigger). Does not close BL-019; does not close BL-017/BL-018; does not mark US-082 Story accepted.
- **Acceptance criteria addressed (US-082):** Enabled+gaps → discovery+drafts ≤ max; no-gap/disabled/idempotent no-op; n8n→HTTP + worker window enforcement + inactive export; gap context into US-078/US-079; leave US-080/US-081 gate; no LinkedIn API published; outcome/failures communicable; no unintended re-implementation.
- **Acceptance criteria excluded / deferred:** Operator walkthrough Story accepted gate; enabling `gap_trigger_enabled` by default; closing BL-019 (and sibling BL-017/BL-018) without Story accepted.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-019 / US-082** | Primary — trigger Flow B draft generation on calendar gaps |
| US-077 | Prerequisite — detect-only sensor (consume) |
| US-076 | Prerequisite — settings + fail-closed enablement (consume) |
| US-078 / US-079 | Prerequisite — discover + generate into `pending-approval/` (consume) |
| US-080 / US-081 | Downstream — approve / promote + spill A (leave drafts; do not skip gate) |
| US-074 / US-075 / BL-016 | Prerequisite policy (Story accepted; closed) |
| US-040K | Scheduling density max 2 elsewhere — do not redefine gap=0 |
| ADR-0001 | n8n → worker HTTP only |
