## Why

BL-010 / US-027 is the second observability slice after US-026. Operators can already see successful/failed executions, blocked/stale campaigns, and delayed calendar items via `GET /flow-a/operational-status`, but that view still does not answer how long Flow A stages took or which external dependency caused failures. Without stage duration and dependency-failure breakdown, operators must open multiple raw run and campaign files to diagnose health and progress.

## What Changes

- Extend the existing read-only `GET /flow-a/operational-status` contract so the same consolidated response also reports stage durations and failures grouped by external dependency.
- Derive stage durations read-only from existing persisted evidence (`metadata/runs` start/complete timestamps and campaign `state_history` / lifecycle clocks). Introduce new persisted timing fields only if existing evidence is proven insufficient, and call that out explicitly in design.
- Classify existing failure evidence (run `errors`, campaign `errors` / `last_error` / `state_history.error_code`, LinkedIn variant failure codes) into operator-facing dependency buckets: ComfyUI, DeepSeek, LinkedIn, and GitHub Pages checkout — without calling those integrations.
- Preserve all US-026 invariants: API-key auth, zero mutation, confined reads, safe output, deterministic ordering, and partial-result `data_issues`.
- Update operator documentation and CURRENT-STATE only to the level actually implemented; do not treat US-026 business acceptance as done and do not close BL-010 until US-027 is separately accepted.

## Goals

- Satisfy US-027 by capturing stage duration and surfacing failures by external dependency in the same operational view operators already use.
- Keep status review possible without opening multiple raw files (extends the US-026 single-endpoint requirement).
- Make duration and dependency outcomes visible, understandable, and clearly labeled when missing or blocked.
- Preserve existing completed US-026 behavior and all Flow A lifecycle / publication / scheduling side-effect boundaries.

## Non-goals

- Re-scoping, re-implementing, or duplicating US-026 execution/campaign/calendar classifications.
- BL-011 alerting, notifications, webhooks, or background monitoring.
- BL-015 UI / supervision console.
- Deployment, live validation, n8n workflow changes, or new orchestration steps.
- Mutating recovery, reconciliation, stale-claim writes, publication, queueing, calendar completion, Git, or external API health probes.
- Percentile/histogram analytics platforms, time-series databases, or new observability sidecar processes.
- Claiming that stage duration equals live-site publication latency or LinkedIn API network RTT when evidence is only campaign lifecycle clocks.

## Acceptance Criteria Coverage

- **Capture stage duration:** derive per-stage and/or per-execution durations from existing persisted timestamps and expose them in the operational-status response with stable stage identifiers.
- **Surface failures by external dependency:** map validated machine-readable error codes to ComfyUI, DeepSeek, LinkedIn, and GitHub Pages checkout buckets; include counts and safe example codes without raw bodies or secrets.
- **Allow status review without opening multiple raw files:** extend the existing single authenticated endpoint rather than creating a parallel status surface.
- **Visible and understandable outcome / clear failures and blocks:** include summary counts, per-item duration fields where evidence exists, dependency buckets, and stable reason/data-issue codes when evidence is missing or unclassifiable.
- **No duplication or unintended change:** keep observation strictly read-only; regression-test US-026 classifications, ordering, auth, safe output, and byte-for-byte zero mutation.

No US-027 acceptance criteria are intentionally excluded. US-026 business acceptance remains a separate pending gate and is not claimed by this change.

## Capabilities

### New Capabilities

None. US-027 extends the existing observability surface rather than introducing a parallel capability.

### Modified Capabilities

- `flow-a-operational-status`: Add stage-duration derivation and external-dependency failure aggregation to the authenticated read-only operational-status contract while preserving US-026 auth, confinement, partial-result, safe-output, and zero-mutation requirements. Remove the US-026 “out of scope” exclusion for stage durations and dependency-failure breakdown.

## Impact

- **API:** same `GET /flow-a/operational-status` route; response gains stage-duration and dependency-failure fields/summary sections. No new route, request body, or dry-run mode.
- **Worker:** extend `flow_a_operational_status.py` (and its FastAPI wiring only if response shape documentation/tests require it); no new external clients.
- **Data sources:** continue reading only the US-026 confined sources (`metadata/runs/`, `metadata/campaigns/`, `editorial-calendar/calendar.json`). Prefer deriving durations from existing `started_at`/`completed_at`, `state_history[].at`, and campaign lifecycle clocks. New persisted timestamps are a last resort and require an explicit design decision.
- **Tests and documentation:** extend focused operational-status tests; preserve US-026 regression coverage; update operator docs and CURRENT-STATE after implementation to the demonstrated level only.
- **Dependencies and operations:** no new runtime dependency, env flag, UI, n8n workflow, deployment action, alert path, or background process.
