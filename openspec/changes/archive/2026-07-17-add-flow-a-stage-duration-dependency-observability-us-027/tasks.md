## 1. Response contract and helpers

- [x] 1.1 Extend operational-status dataclasses/response builders in `flow_a_operational_status.py` to include `duration_seconds` on executions, `stage_durations` / optional `attempt_duration_seconds` / per-campaign `dependency_failures` on campaigns, top-level `dependency_failures`, and summary counts for stage durations and dependency buckets — without changing the existing route path or auth wiring
- [x] 1.2 Implement whole-second duration helpers that accept canonical UTC timestamps, reject inverted/unparsable clocks with stable data-issue codes, and never invent missing timestamps
- [x] 1.3 Implement `state_history` stage-interval derivation (completed pairs + one open interval relative to `observed_at_utc`) with deterministic sort by `started_at` then `stage`
- [x] 1.4 Implement dependency-bucket classification (`comfyui`, `deepseek`, `linkedin`, `github_pages_checkout`, `unclassified`) from validated error-code families with per-artifact code dedupe and deterministic ordering

## 2. Aggregation wiring

- [x] 2.1 Wire execution duration into existing run summarization without altering US-026 outcome classification or safe-field whitelist beyond the approved duration field
- [x] 2.2 Wire campaign stage-duration and dependency-failure derivation into campaign summarization while preserving independent successful/failed/blocked/stale/in_progress flags
- [x] 2.3 Aggregate top-level `dependency_failures` and summary counts from run and campaign evidence without calling ComfyUI, DeepSeek, LinkedIn, OAuth, Git, or live-site clients
- [x] 2.4 Confirm the FastAPI handler still returns one consolidated JSON body including US-026 fields plus the new US-027 fields, with `read_only: true` and unchanged zero-mutation guarantees

## 3. Tests

- [x] 3.1 Add focused tests for completed lifecycle stage intervals, open-stage duration against supplied `now_utc`, and execution `duration_seconds`
- [x] 3.2 Add focused tests for each dependency bucket plus unclassified codes, checkout-named LinkedIn preview codes mapped to `github_pages_checkout`, and no-external-call aggregation
- [x] 3.3 Add tests for inverted/missing timestamps and inconsistent history producing stable `data_issues` while preserving valid partial results
- [x] 3.4 Extend zero-mutation, auth, deterministic ordering, and safe-output assertions to cover the new fields; keep existing US-026 classification assertions intact (no weakened expectations)
- [x] 3.5 Run targeted `tests/test_flow_a_operational_status.py` (and any affected regression set required by local practice) and resolve warnings attributable to this change

## 4. Documentation and progress

- [x] 4.1 Update `docs/operations/flow-a-operational-status.md` with stage-duration derivation, dependency-bucket mapping, open-stage observation relativity, and execution-vs-lifecycle duration distinction
- [x] 4.2 Update `docs/CURRENT-STATE.md` to the demonstrated US-027 implementation level only; do not claim US-026 business acceptance or BL-010 closure
- [x] 4.3 Update `docs/product/user-stories.md` US-027 status and `docs/product/progress-checklist.md` only for criteria actually demonstrated; leave US-026 acceptance and BL-010 closure unchanged unless separately accepted

## 5. Business validation

- [x] 5.1 Demonstrate against controlled fixtures that an authenticated operator can see stage durations and dependency-failure buckets in one `GET /flow-a/operational-status` response without opening multiple raw files
- [x] 5.2 Confirm failures/blocked states remain clearly communicated (bucket counts, safe codes, unclassified visibility) and that existing US-026 classifications are unchanged
- [x] 5.3 Confirm out-of-scope items remain absent (no alerts, UI, n8n changes, live probes, mutations, or new persisted timing schema) and record any remaining acceptance gaps explicitly
