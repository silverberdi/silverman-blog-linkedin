## Context

US-076–US-081 are implemented and deployed on `192.168.0.194:8010`: gap operator settings (Postgres + GET/PUT), detect-only `GET /flow-b/calendar-gaps`, `POST /flow-b/discover-topics`, `POST /flow-b/generate-blog-drafts` → `pending-approval/`, approve/reject presentation, and promote + spill A. Policy locks weekly gap trigger semantics in `docs/operations/flow-b-simplified-policy.md` (Friday afternoon intent, `gap_trigger_enabled` default false, ISO-week idempotency `flow_b_gap_week:{operator_tz}:{YYYY}-W{ww}`, n8n Schedule → worker HTTP).

There is still no runtime that, when enabled and gaps exist, starts discovery + draft generation. Operators must manually chain US-078/US-079. US-076 tests explicitly assert `/flow-b/gap-trigger` does not exist yet.

Constraints: ADR-0001 (n8n → HTTP only; no Execute Command); fail-closed `gap_trigger_enabled=false`; do not auto-publish; do not re-implement US-076–US-081; do not redefine gap=0 vs US-040K density; do not close BL-019 or mark Story accepted without operator walkthrough; repo n8n export stays `active: false`.

Stakeholders: content operator (approvable drafts appear when next week has empty LinkedIn days); system operator (authenticated HTTP, inactive-until-activated n8n); US-080/US-081 (consume drafts after gate).

## Goals / Non-Goals

**Goals:**

- Authenticated gap-trigger endpoint that enforces US-076 enablement + local day/time window, consumes US-077 detect, and on gaps runs US-078 → US-079 up to `max_drafts_per_weekly_run` with gap context into `pending-approval/`.
- Clean no-ops: disabled, outside window, no gaps, or ISO-week idempotent batch already pending/completed.
- Inactive n8n Schedule → HTTP workflow export.
- CURRENT-STATE as implemented (not Story accepted); BL-019 remains open.

**Non-Goals:**

- Re-implement settings/detect/discover/generate/approve/promote.
- Default-enable `gap_trigger_enabled`.
- Auto-publish blog/LinkedIn or mark LinkedIn API published.
- Skip blog approval gate (US-080/US-081).
- Close BL-017 / BL-018 / BL-019 or Story-accept US-082 without walkthrough.
- Redefine gap as density capacity.

## Decisions

### D1 — Single authenticated orchestrator: `POST /flow-b/gap-trigger`

**Choice:** Add authenticated `POST /flow-b/gap-trigger` as the only new worker surface for this story. Optional body fields:

| Field | Purpose |
|-------|---------|
| `now_utc` | Diagnostic clock override (tests / inspection), same spirit as detect |
| `dry_run` | Validate gates + would-be batch without claiming idempotency or writing drafts |
| `force_window` | Optional diagnostic to bypass local day/time window only (MUST NOT bypass `gap_trigger_enabled`) — default false; document as non-production |

Response MUST include a clear `status` (e.g. `triggered`, `noop_disabled`, `noop_outside_window`, `noop_no_gap`, `noop_idempotent`, `blocked`, `failed`) plus operator-visible fields: effective timezone, target ISO week, gaps/empty_days echoed when known, idempotency key, draft ids/paths when triggered, error codes when blocked/failed. Never return secrets.

**Why:** Matches US-076 foreshadowed path; ADR-0001 HTTP boundary; one call from n8n.

**Alternatives rejected:** n8n chaining detect→discover→generate itself (duplicates window/idempotency; harder fail-closed); separate GET trigger (side-effectful GET).

### D2 — Compose internal services (do not HTTP self-call)

**Choice:** Trigger module calls existing Python entry points:

1. `load_gap_operator_settings()`
2. `detect_next_week_calendar_gaps(...)`
3. `discover_flow_b_topics(..., target_week=..., empty_days=...)`
4. draft generation entry point from `flow_b_blog_draft_generation` with the same gap context and topic payloads

Do **not** re-implement detect/discover/generate logic. Do **not** loopback HTTP to the worker.

**Why:** Smallest coherent composition; avoids auth recursion and double transport; keeps unit tests mockable at service boundaries.

### D3 — Window enforcement on the worker (n8n is coarse)

**Choice:** After loading settings:

1. If `gap_trigger_enabled` is false → `noop_disabled` (no detect side effects required beyond optional echo; prefer still cheap — may skip detect).
2. Else compute operator-local weekday and clock from `now_utc` (or server now) in `operator_timezone`.
3. If local weekday ≠ `weekly_run_local_day` → `noop_outside_window`.
4. If local time-of-day is before `weekly_run_local_time` → `noop_outside_window`.
5. If local time-of-day is after end of the configured run window → `noop_outside_window`.

**Run window end:** from `weekly_run_local_time` through end of that local calendar day (23:59:59.999999). Rationale: Friday afternoon intent; n8n may fire periodically; worker remains fail-closed before the clock and after midnight local.

`force_window=true` (diagnostic only) skips steps 3–5 but never step 1.

**Why:** Policy “worker no-ops outside window”; timezone-correct vs fixed UTC cron alone.

**Alternatives rejected:** Trust n8n cron only (operator TZ drift); ±15-minute-only window (misses late manual/schedule fires same day).

### D4 — Happy path: detect → discover → generate ≤ max drafts

**Choice:** When enabled + inside window:

1. Run detect. If `status=no_gap` or `gaps` empty → `noop_no_gap` (no idempotency claim).
2. Build `target_week` string from detect (`target_week.iso_week`, e.g. `2026-W30`) and `empty_days[]` from gap `local_date` values.
3. Resolve idempotency key `flow_b_gap_week:{operator_tz}:{iso_week}` (use effective IANA timezone string from settings).
4. If batch already `in_progress` or `completed` → `noop_idempotent`.
5. Claim batch `in_progress` (exclusive).
6. Discover topics with count ≤ `max_drafts_per_weekly_run`, passing `target_week` + `empty_days`.
7. Generate blog drafts from those topics into `pending-approval/` with same gap context.
8. Mark batch `completed` with draft ids / artifact paths; return `triggered`.

On discovery/generate hard failure after claim: mark batch `failed` with structured error so a later run MAY retry (failed ≠ idempotent no-op). Do not leave silent `in_progress` forever without a documented reclaim rule (see D5).

MUST NOT: write `blog-posts/ready/`, call publish/package/schedule, call LinkedIn API, enable publication flags, or approve/promote drafts.

**Why:** US-082 AC; consumes US-078/US-079 gap context contracts already implemented.

### D5 — Idempotency store (Postgres + memory tests)

**Choice:** Persist batch records in `silverman_linkedin_db` via the same `SILVERMAN_CALENDAR_DATABASE_URL` used by US-076/US-041, table e.g. `flow_b_gap_trigger_batches`:

| Column | Notes |
|--------|-------|
| `idempotency_key` | PK — `flow_b_gap_week:{tz}:{YYYY}-W{ww}` |
| `status` | `in_progress` \| `completed` \| `failed` |
| `operator_timezone` | Echo |
| `iso_week` | Echo |
| `empty_days` | JSON |
| `draft_ids` / result summary | JSON nullable |
| `created_at_utc` / `updated_at_utc` | UTC |
| `error_code` | Nullable on failed |

Provide `memory://` store for tests (mirror gap settings store pattern). Exclusive claim = insert-if-absent or conditional update from absent/failed → in_progress.

**Stale `in_progress`:** If `updated_at_utc` older than a documented TTL (e.g. 2 hours), treat as reclaimable (`failed` or allow re-claim). Prevents crash mid-run from permanent no-op.

**Why:** Policy requires durable ISO-week idempotency across n8n re-fires; Postgres matches settings SoT; filesystem scan of `pending-approval/` is insufficient (operator deletes / partial batches).

**Alternatives rejected:** Filesystem-only under `metadata/` (weaker multi-instance); treat any pending-approval sidecar with matching `target_week` as sole proof (can false-positive after reject/delete).

### D6 — n8n Schedule → HTTP export (`active: false`)

**Choice:** Add `n8n/workflows/silverman-blog-linkedin-flow-b-gap-trigger.json` (name TBD consistent with existing exports):

- Schedule Trigger: periodic cron (e.g. every 15–30 minutes daily, or Friday-focused UTC approximation) — worker enforces true local window.
- Manual Trigger for operator test.
- Set Configuration: `worker_base_url`, `worker_api_key` placeholders (same pattern as operational alerts).
- HTTP Request: `POST {worker_base_url}/flow-b/gap-trigger` with Bearer auth and JSON body `{}` (or dry_run for a documented test variant — prefer single production path; dry_run via manual body edit).
- Workflow `active: false` in repo export.

MUST NOT use Execute Command nodes.

**Why:** ADR-0001 + US-082 AC; matches existing n8n export conventions.

### D7 — Module layout

**Choice:**

- `flow_b_calendar_gap_trigger.py` — window checks, orchestration, response shaping.
- `flow_b_gap_trigger_batch_store.py` — Postgres + memory batch idempotency store.
- Thin FastAPI route in `main.py`: `POST /flow-b/gap-trigger`.
- Tests: `tests/test_flow_b_calendar_gap_trigger.py`.
- Update US-076 route-absence test: `/flow-b/gap-trigger` MAY exist; settings save still MUST NOT start trigger/discovery as a side effect.
- Docs: CURRENT-STATE, Flow B policy cross-link, glossary Flow B line if needed.

### D8 — Auth, secrets, dry-run

**Choice:** Same worker API-key auth as other `/flow-b/*` routes. Structured JSON errors (401/422/5xx). Never return secrets. `dry_run=true`: evaluate enablement/window/detect/idempotency and return would-be action **without** claiming batch or writing drafts (detect remains non-mutating as today).

### D9 — Docs / product status

**Choice:** Update `docs/CURRENT-STATE.md` and Flow B policy/glossary to **implemented** for gap trigger. Update user-stories/progress only for demonstrated automated AC; leave Story accepted unchecked; do **not** close BL-019 (US-076/US-077/US-082 Story accepted still pending); do not close BL-017/BL-018.

### D10 — Tests

**Choice:** Cover (mock DeepSeek/ComfyUI):

- Disabled → `noop_disabled`; no drafts.
- Outside window → `noop_outside_window`; no drafts.
- Enabled + inside window + no gaps → `noop_no_gap`.
- Enabled + gaps → ≤ `max_drafts_per_weekly_run` drafts in `pending-approval/` with `target_week` / `empty_days` sidecars; status `triggered`.
- Second call same ISO week → `noop_idempotent`; no duplicate spam.
- Failed batch may retry; completed may not.
- Auth required; dry_run no writes / no claim.
- No LinkedIn API / publish / promote invoked.
- n8n export present, `active: false`, HTTP-only nodes.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| n8n cron TZ ≠ operator TZ | Worker window enforcement (D3); frequent schedule + no-op |
| Crash leaves `in_progress` forever | TTL reclaim (D5) |
| Duplicate drafts if claim races | Exclusive DB insert on idempotency key |
| Operators think trigger = published | Response + CURRENT-STATE: drafts in `pending-approval/` only |
| US-076 test breaks when route appears | Update test to side-effect assertion (D7) |
| Scope creep into approve/promote | Hard non-goals; no calls into US-080/US-081 |
| Enabling trigger by accident in defaults | Keep `gap_trigger_enabled` default false; tests assert |

## Migration Plan

1. Implement after explicit `/opsx-apply` approval.
2. `/opsx-verify` → implementation commit → sync → archive (separate commits).
3. Deploy only with explicit approval; import n8n workflow **inactive**; do not set `gap_trigger_enabled=true` without operator decision.
4. Rollback: revert worker build; batch rows remain harmless; pending drafts already written stay for US-080.
5. No migration of historical weeks required.

## Open Questions

None blocking. Resolved by AC/proposal:

- Endpoint `POST /flow-b/gap-trigger` (D1).
- Internal composition (D2).
- Window = local day match + time ≥ configured through end of local day (D3).
- Postgres batch idempotency with failed-retry + stale reclaim (D5).
- n8n export inactive (D6).
