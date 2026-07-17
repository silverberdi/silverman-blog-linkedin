## Why

BL-011 / US-030 requires operators to receive timely, actionable alerts when the worker is unhealthy or an n8n workflow needs attention after failure. US-028 and US-029 already deliver authenticated evaluate/emit for campaign, calendar, dependency, and stale attention classes on top of `GET /flow-a/operational-status`, but unhealthy-worker and failed-n8n attention remain observation-only (or invisible to the worker under ADR-0001). Completing US-030 is the remaining BL-011 story before backlog closure can be considered after operator acceptance.

## What Changes

- Extend the existing `flow-a-operational-alerts` capability so `POST /flow-a/operational-alerts/evaluate` also derives US-030 alert candidates:
  - `unhealthy_worker` from the same editorial-folder readiness evidence already used by `GET /health` (in-process; no external provider calls).
  - `failed_n8n_workflow` from worker-persisted orchestration-failure evidence ingested over a narrow authenticated HTTP report contract (ADR-0001-safe; no n8n Execute Command and no n8n API scraping).
- Reuse the US-028/US-029 evaluate/emit contract, fail-closed webhook enablement, secret-safe payloads, and `metadata/operational-alerts/emissions.json` ledger without changing lifecycle immutability invariants.
- Preserve all US-028 and US-029 alert types, behaviors, and prior `summary.counts` keys; extend counts for the two US-030 types.
- Clarify operational-status purpose/out-of-scope so US-030 alerting remains owned by `flow-a-operational-alerts` while the read-only status contract stays unchanged (no request/response shape change beyond that clarification).
- Update CURRENT-STATE, operator alerts docs, and product progress only to the demonstrated implementation level; do not mark US-030 accepted, do not re-accept US-028/US-029, and do not close BL-011 from proposal or code alone.

## Goals

- Satisfy US-030 by alerting on unhealthy worker and/or failed n8n workflow attention with understandable secret-safe payloads and clear failure/blocked communication.
- Prefer extending the existing evaluate/emit contract and ledger; add only a narrow evidence-ingest boundary where the worker cannot observe n8n failures otherwise.
- Preserve ADR-0001: n8n orchestrates over HTTP only; the worker owns evaluation (and optional emission) via HTTP.
- Keep evaluate-only free of campaign/run/calendar/editorial lifecycle mutation; emit remain fail-closed and ledger-isolated.
- Preserve API-key auth, deterministic ordering, and secret-safe payloads.

## Non-goals

- Re-accepting US-028 or US-029, or closing BL-011 from proposal/code alone.
- BL-015 supervision UI / console.
- Slack/email/SMS SDKs as first-class worker integrations (generic webhook + n8n mapping remains the MVP channel).
- Deploy, push, live mutation, or production webhook enablement as part of this change.
- Broad paging platforms or multi-channel fan-out beyond the existing generic webhook model.
- Changing `GET /flow-a/operational-status` request/response shape beyond purpose/scope clarification.
- Treating process-down / unreachable worker as a worker-emitted alert (n8n health-check failure remains outside this contract).
- Deploy-revision / `BUILD_REVISION` mismatch alerts (not currently part of `/health` evaluate evidence; not invented here).
- Calling ComfyUI, DeepSeek, LinkedIn, OAuth, Git, or live-site APIs during evaluation.

## Acceptance Criteria Coverage

- **Alert on unhealthy worker or failed n8n workflow:** evaluate/emit `unhealthy_worker` from health-equivalent folder readiness evidence; evaluate/emit `failed_n8n_workflow` from authenticated, worker-persisted orchestration-failure reports.
- **Visible and understandable:** structured alert type, severity, fingerprint, safe identifiers/codes/reasons, and short summaries without secrets or content bodies.
- **Failures or blocked states clearly communicated:** explicit alert types, severities, and emission status (`not_requested` / `disabled` / `misconfigured` / emitted / already emitted / failed).
- **Existing completed work not duplicated or unintentionally changed:** reuse evaluate/emit/ledger; preserve US-028/US-029 types and counts; do not rework or re-accept those stories; do not close BL-011 from this change alone.

No US-030 acceptance criteria are intentionally excluded. BL-011 closure and operator acceptance of US-028/US-029/US-030 remain later acceptance gates.

## Capabilities

### New Capabilities

- None. US-030 extends the existing operational-alerts capability rather than introducing a sibling alerts surface.

### Modified Capabilities

- `flow-a-operational-alerts`: Add US-030 alert types (`unhealthy_worker`, `failed_n8n_workflow`), derivation rules, authenticated orchestration-failure report/ingest contract for n8n-failure evidence, updated summary counts (eight types total), and scope/verification language. Preserve the authenticated evaluate endpoint, fail-closed webhook emission, ledger isolation, and all US-028/US-029 alert behaviors.
- `flow-a-operational-status`: Clarify purpose/out-of-scope language so BL-011 US-028/US-029/**US-030** alerting is owned by `flow-a-operational-alerts` while the existing read-only status contract, classifications, and zero-mutation guarantees remain unchanged. No change to `GET /flow-a/operational-status` request/response requirements beyond that scope clarification.

## Impact

- **API:** same authenticated `POST /flow-a/operational-alerts/evaluate` contract; response `alerts[]` / `summary.counts` gain US-030 types. Add a narrow authenticated report endpoint (or equivalent ingest under the operational-alerts capability) for n8n orchestration-failure evidence. Existing operational-status and `/health` routes remain observation foundations; `/health` response shape is not required to change for MVP.
- **Worker:** extend `flow_a_operational_alerts` derivation for health-equivalent unreadiness and persisted orchestration-failure evidence; reuse existing config, webhook adapter, and emission ledger.
- **Persistence:** continue using `metadata/operational-alerts/emissions.json` for emit dedupe; add confined orchestration-failure evidence under `metadata/operational-alerts/` (separate from campaign/run lifecycle docs). Evaluate-only still does not mutate campaign/run/calendar/editorial lifecycle.
- **n8n:** may schedule evaluate over HTTP and optionally POST orchestration-failure reports from Error Trigger / catch paths; no Execute Command; no requirement to ship or activate a production n8n workflow in this change.
- **Tests and docs:** behavioral tests for both US-030 types, regression that US-028/US-029 types still work, fail-closed emission, safe payloads, and zero lifecycle mutation; CURRENT-STATE / operator docs / product progress updated only to demonstrated level after implementation.
- **Out of scope systems:** no Slack/email SDK; no BL-015 UI; no deploy/live validation; no US-028/US-029 re-acceptance; no BL-011 closure from proposal/code alone.
