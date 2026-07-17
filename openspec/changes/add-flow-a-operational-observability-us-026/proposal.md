## Why

BL-010 / US-026 requires one operator-readable view of persisted Flow A execution health and campaign progress. Today the evidence is split across worker run records, campaign metadata, the editorial calendar, and LinkedIn variant scheduling/publication fields, so an operator must inspect and correlate multiple raw JSON files.

## What Changes

- Add one API-key-protected, read-only worker HTTP endpoint that aggregates persisted execution, campaign, calendar, and LinkedIn variant evidence into structured JSON.
- Define deterministic classifications for successful and failed persisted executions, blocked and stale campaigns, and delayed calendar items.
- Reuse existing lifecycle states, operational recovery classifications, stale-processing configuration, calendar statuses and due timestamps, variant `publish_state` values, and cadence anchors without introducing new persisted state.
- Return aggregate counts plus per-item evidence and stable reason codes so failures and attention-required states are understandable without opening raw files.
- Keep all reads confined to the configured editorial base and guarantee that observation performs no writes, lifecycle moves, API calls, Git operations, or pipeline execution.

## Goals

- Satisfy US-026 by identifying successful and failed persisted executions, blocked or stale campaigns, and delayed calendar items in one response.
- Make the evidence and classification reason for each failure, block, stale claim, or delay explicit.
- Preserve existing completed work and side-effect boundaries by deriving status only from authoritative on-disk evidence.
- Keep n8n integration HTTP-only under ADR-0001; n8n may consume the endpoint but does not read files or execute shell commands.

## Non-goals

- US-027 stage-duration measurement or failure aggregation by external dependency.
- BL-011 notifications, alerts, polling, webhooks, or background monitoring.
- The BL-015 supervision console or any other UI.
- Recovery, reconciliation, queueing, publication, calendar mutation, or any new pipeline side effect.
- New lifecycle states, calendar statuses, `publish_state` values, campaign fields, run fields, or observability persistence.
- Claiming that legacy `metadata/runs/` records are complete Flow A campaign-attempt history when they do not contain campaign linkage; the endpoint reports their persisted trigger and status separately from campaign operational evidence.

## Acceptance Criteria Coverage

- **Identify successful and failed executions:** classify valid records under `metadata/runs/` from their persisted `status`, while separately exposing current Flow A campaign attempt evidence from `source_file_status`.
- **Identify blocked or stale campaigns:** derive attention states from existing campaign lifecycle, source location, execution state, recovery classification, last-error, and canonical stale-clock evidence.
- **Show delayed calendar items:** compare non-terminal calendar items with their canonical `due_at_utc` at one request-level UTC observation time.
- **Visible and understandable outcome / clear failures and blocks:** provide counts, item summaries, evidence timestamps, and stable reason codes in structured JSON.
- **No duplication or unintended change:** make the capability strictly read-only and regression-test filesystem and metadata byte identity.

The US-027 criteria to capture stage duration, break failures down by external dependency, and provide that later analytical layer are intentionally excluded from this change.

## Capabilities

### New Capabilities

- `flow-a-operational-status`: Read-only aggregation contract, deterministic health classifications, endpoint response, safety boundaries, and operator-visible evidence for US-026.

### Modified Capabilities

None.

## Impact

- **API:** one new authenticated `GET /flow-a/operational-status` endpoint returning structured JSON; no request body and no dry-run mode because the operation is intrinsically read-only.
- **Worker:** a focused aggregation service plus route wiring following existing FastAPI and API-key conventions.
- **Data sources:** read-only access to `metadata/runs/*.json`, `metadata/campaigns/*.json`, and `editorial-calendar/calendar.json` under `SILVERMAN_BLOG_LINKEDIN_BASE_PATH`; LinkedIn variant status and scheduling/cadence evidence are read from campaign documents.
- **Tests and documentation:** behavioral tests for classifications, malformed/unreadable evidence, path confinement, secret/body exclusion, deterministic ordering, and zero mutation; operator and current-state documentation updated only after implementation.
- **Dependencies and operations:** no new runtime dependency, UI, n8n workflow, environment variable, external API call, deployment action, alerting path, or background process.
