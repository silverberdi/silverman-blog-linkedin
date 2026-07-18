## Why

BL-012 / US-031 requires operators to identify the last valid stage of an incomplete Flow A campaign and resume or repair it safely. Today recovery cues exist as scattered lifecycle fields (`state`, `state_history`, `source_file_status`, stage evidence, `recovery_classification`) and as implicit idempotent re-run rules inside queue/claim/connector paths, but there is no single ADR-0001-safe HTTP contract that derives last-valid-stage, resumes without repeating durable work, or repairs inconsistent metadata with operator-visible outcomes.

## What Changes

- Add an authenticated Flow A incomplete-campaign recovery capability on the HTTP worker: inspect last-valid-stage from persisted campaign evidence; resume from the next unfinished stage without repeating successful durable side effects; repair allowlisted metadata inconsistencies when evidence is unambiguous.
- Derive last-valid-stage from existing campaign pipeline state, `state_history`, physical source location, and durable stage evidence — do not invent new lifecycle states unless a later change proves that strictly necessary (this change does not).
- Reuse the canonical `recovery_classification` vocabulary from `flow-a-operational-queue-lifecycle`; extend it only if a gap is proven and justified in design.
- Keep `GET /flow-a/operational-status`, operational-alerts evaluate/report contracts, and LinkedIn publication recovery (BL-008 / US-021–US-022) intact unless a narrow, justified delta is required.
- Update CURRENT-STATE and product progress only to the demonstrated implementation level; do not mark US-031 accepted, US-032 started, or BL-012 closed from proposal or code alone.

## Goals

- Satisfy US-031 acceptance criteria: identify last valid stage; resume without repeating successful work; repair inconsistent metadata; make outcomes visible; communicate failures/blocks clearly; avoid duplicating or unintentionally changing completed work.
- Prefer an authenticated, ADR-0001-safe HTTP worker contract over n8n Execute Command or filesystem scraping.
- Fail closed when ambiguity would risk double blog publish, package regeneration, distribution reschedule, or false `flow_a_complete`.
- Keep scope to the smallest coherent worker capability for US-031 only.

## Non-goals

- US-032: classify recovery actions as a new action taxonomy, preserve attempt history as a dedicated recovery ledger, or support safe cancellation when recovery is inappropriate.
- BL-013 concurrency/duplicate protection (beyond reusing existing claim/stale/idempotency guards already required by queue lifecycle).
- BL-014 backup/restore.
- BL-015 UI/console.
- LinkedIn API publish, Git push, live-site mutation, deploy, or production enablement as part of this change.
- Shipping or activating production n8n workflows (n8n may call the worker over HTTP later).
- Reworking LinkedIn publication recovery (BL-008) as the primary surface.
- Broad auto-healing that silently mutates campaigns without clear operator-visible outcomes.
- Closing BL-012 or marking US-031 accepted from proposal/code alone.

## Acceptance Criteria Coverage

- **Identify the last valid stage:** derive and return an explicit last-valid-stage from persisted campaign evidence (`state` / `state_history`, location/execution evidence, durable stage markers).
- **Resume without repeating successful work:** resume invokes only unfinished stage work; already-completed blog publish, package, and distribution schedule paths short-circuit via existing idempotency contracts.
- **Repair inconsistent metadata:** explicit repair mode reconciles allowlisted metadata/filesystem mismatches when evidence is unambiguous; otherwise fail closed with a stable code.
- **Visible and understandable outcome:** structured JSON with campaign identity, last-valid-stage, next action or blocked reason, recovery classification, and safe evidence summary.
- **Failures or blocked states clearly communicated:** stable error/block codes for missing campaign, ambiguous evidence, active non-stale claim, unsafe repair, auth failure, and validation failure.
- **Existing completed work not duplicated or unintentionally changed:** inspect is read-only; resume/repair must not rewrite durable side-effect evidence or re-run completed stages; completed `flow_a_complete` campaigns are no-op or explicit skip, not reprocessed.

US-032 criteria (classify recovery actions / preserve attempt history / safe cancellation) are intentionally excluded.

## Capabilities

### New Capabilities

- `flow-a-incomplete-campaign-recovery`: Operator-facing incomplete Flow A campaign recovery contract for US-031 — last-valid-stage derivation, inspect, idempotent resume, explicit metadata repair, secret-safe operator-visible outcomes, and fail-closed ambiguity handling.

### Modified Capabilities

- `flow-a-operational-queue-lifecycle`: Narrow alignment so incomplete-campaign recovery inspect/resume/repair reuses existing `recovery_classification`, claim/stale/reclaim, and idempotent re-run rules rather than inventing a parallel recovery ontology. No change to LinkedIn publication recovery semantics.
- `flow-a-lifecycle`: Narrow clarification that last-valid-stage for incomplete-campaign recovery is derived from existing pipeline `state`, `state_history`, and durable stage evidence without adding new lifecycle state values.

## Impact

- **API:** new authenticated worker HTTP surface(s) for inspect (read-only) and resume/repair (mutating, with dry-run); existing Flow A pipeline endpoints remain the stage executors that resume may invoke or short-circuit through.
- **Worker:** focused recovery service that reads/writes only approved campaign metadata and editorial paths under the configured base; reuses existing publish/package/schedule/lifecycle completion idempotency and queue claim/release helpers.
- **Data:** no new lifecycle states; optional additive operator-visible recovery summary fields only if design proves they are required for auditability without becoming US-032 attempt history.
- **n8n:** may call the worker over HTTP later; no production workflow ship/activation in this change.
- **Tests and docs:** behavioral tests for stage derivation, resume short-circuits, repair allowlist, ambiguity fail-closed, auth, dry-run, and zero unintended mutation; CURRENT-STATE / operator docs / product progress updated only after demonstrated implementation.
- **Out of scope systems:** no LinkedIn API publish path changes; no Git/live-site mutation; no BL-015 UI; no deploy as part of this change.
