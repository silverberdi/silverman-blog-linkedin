## 1. Idempotency batch store

- [x] 1.1 Add `flow_b_gap_trigger_batch_store` (Postgres on `SILVERMAN_CALENDAR_DATABASE_URL` + `memory://` for tests): table/records keyed by `flow_b_gap_week:{operator_tz}:{YYYY}-W{ww}` with statuses `in_progress` / `completed` / `failed`, timestamps, optional empty_days / draft summary / error_code
- [x] 1.2 Implement exclusive claim (absent or `failed` → `in_progress`), complete, fail, and stale-`in_progress` reclaim after documented TTL; ensure completed blocks duplicates

## 2. Gap-trigger orchestration

- [x] 2.1 Add `flow_b_calendar_gap_trigger` module: load US-076 settings; enforce `gap_trigger_enabled` fail-closed; enforce operator-local weekly window (`weekly_run_local_day` + time ≥ `weekly_run_local_time` through end of local day); support optional `now_utc`, `dry_run`, diagnostic `force_window` (window only — never bypass enablement)
- [x] 2.2 Compose existing services in order: detect → (on gaps) claim idempotency → discover_topics with `target_week` + `empty_days[]` → generate_blog_drafts capped by `max_drafts_per_weekly_run` into `pending-approval/`; mark batch completed/failed; clean no-ops for disabled / outside window / no-gap / idempotent
- [x] 2.3 Ensure trigger NEVER writes `blog-posts/ready/`, NEVER calls publish/package/schedule/promote/approve, NEVER calls LinkedIn API publish, and NEVER enables publication flags; do not re-implement US-076–US-081 internals

## 3. Authenticated HTTP API

- [x] 3.1 Add authenticated `POST /flow-b/gap-trigger` per design; reject unauthenticated callers; structured secret-safe JSON statuses (`triggered`, `noop_*`, `blocked`, `failed`) with operator-visible fields
- [x] 3.2 Expose route in OpenAPI; leave settings/detect/discover/generate/approve/promote contracts unchanged in purpose; no n8n Execute Command (ADR-0001)
- [x] 3.3 Update US-076 route-absence test: `/flow-b/gap-trigger` MAY exist; settings save MUST still not start trigger/discovery as a side effect

## 4. n8n Schedule → HTTP export

- [x] 4.1 Add repo workflow export under `n8n/workflows/` (Schedule + Manual + Set Configuration + HTTP Request to `POST /flow-b/gap-trigger`); placeholders for worker URL/API key; HTTP-only (no Execute Command); export `active: false`

## 5. Tests

- [x] 5.1 Unit/API tests: disabled no-op; outside-window no-op; no-gap no-op; enabled+gaps creates ≤ max drafts with gap context sidecars; idempotent second call no-op; failed batch retry; dry_run no writes/no claim; auth required; mocks for DeepSeek/ComfyUI; no LinkedIn/publish/promote side effects
- [x] 5.2 Assert n8n export exists, `active: false`, and uses HTTP Request only
- [x] 5.3 Run targeted pytest for new + touched Flow B tests; fix warnings attributable to this change; `git diff --check` clean

## 6. Docs and product status

- [x] 6.1 Update `docs/operations/flow-b-simplified-policy.md` (and glossary if needed) so US-082 gap trigger is the runtime path; keep fail-closed default; distinguish detect vs trigger; state pending-approval-only / no LinkedIn API published
- [x] 6.2 Update `docs/CURRENT-STATE.md` to record gap trigger **implemented** (not Story accepted / not deployed unless separately approved); do not claim BL-019 closed
- [x] 6.3 After demonstrated automated AC, update `docs/product/user-stories.md` US-082 and `docs/product/progress-checklist.md` only to the validated state — do not mark Story accepted without operator walkthrough; do not close BL-019 (or BL-017/BL-018) without their Story accepted gates

## 7. Business validation gate

- [x] 7.1 Walk US-082 acceptance criteria against local worker (+ inactive n8n export) evidence: enabled+gaps → drafts ≤ max; no-gap/disabled/idempotent no-ops; n8n→HTTP + worker window; gap context into US-078/US-079; blog gate not skipped; no LinkedIn API published; failures communicated; no re-implementation of US-076–US-081
- [x] 7.2 Record any remaining gaps explicitly; leave Story accepted / BL-019 close / `gap_trigger_enabled` default-true unchecked

### Remaining gaps (explicit — fill after implementation)

- Operator walkthrough / “outcome visible” AC → Story accepted still open
- Deploy to `192.168.0.194` not done (requires separate approval)
- n8n import/activation and setting `gap_trigger_enabled=true` require explicit operator approval
- BL-019 remains open until US-076 + US-077 + US-082 Story accepted
- BL-017 / BL-018 remain open until their Story accepted gates
- `gap_trigger_enabled` remains default **false** (fail-closed)
