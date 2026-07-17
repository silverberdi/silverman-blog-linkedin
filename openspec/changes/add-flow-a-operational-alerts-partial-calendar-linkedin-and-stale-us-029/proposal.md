## Why

BL-011 / US-029 requires operators to receive timely, actionable alerts when Flow A needs attention for partial calendar execution, LinkedIn token or publication failure, and stale campaigns. US-028 already delivers authenticated evaluate/emit for error-folder, image-generation, and blog-publication failures on top of `GET /flow-a/operational-status`, but those three US-029 attention classes are still observation-only.

## What Changes

- Extend the existing `flow-a-operational-alerts` capability so `POST /flow-a/operational-alerts/evaluate` also derives US-029 alert candidates from the same confined operational-status evidence (delayed calendar items, LinkedIn dependency / progress failure codes, campaign `stale` classification) — no parallel filesystem scanner.
- Reuse the US-028 evaluate/emit contract, fail-closed webhook enablement, secret-safe payloads, and `metadata/operational-alerts/emissions.json` ledger without changing lifecycle immutability invariants.
- Preserve all US-028 alert types and behaviors; add only the three US-029 types and their summary counts.
- Clarify operational-status purpose/out-of-scope so US-029 alerting remains owned by `flow-a-operational-alerts` while the read-only status contract stays unchanged.
- Update CURRENT-STATE and product progress only to the demonstrated implementation level; do not mark US-029 accepted or BL-011 closed from proposal or code alone.

## Goals

- Satisfy US-029 by alerting on partial calendar execution, LinkedIn token or publication failure, and stale campaigns.
- Make alert outcomes visible, understandable, and clearly labeled for the intended operator/n8n consumer.
- Reuse US-026/US-027/US-028 evidence, auth, fail-closed emission, and non-mutation invariants; do not invent a parallel ontology or scanner.
- Preserve ADR-0001: n8n orchestrates over HTTP only; the worker owns evaluation (and optional emission) via HTTP.
- Keep evaluation free of unintended lifecycle mutation; gate emission behind existing fail-closed enablement.

## Non-goals

- US-030: unhealthy worker or failed n8n workflow alerts.
- Re-accepting US-028, closing BL-011, or claiming BL-010 / US-026 / US-027 business acceptance.
- BL-015 supervision UI / console.
- Slack, email, SMS, or UI SDKs as first-class worker integrations.
- Deploy, push, live mutation, or production webhook enablement as part of this change.
- Changing `GET /flow-a/operational-status` request/response shape or classification rules.
- Broad notification platforms, paging systems, or multi-channel fan-out beyond the existing generic webhook.

## Acceptance Criteria Coverage

- **Alert on partial calendar execution:** evaluate/emit alerts from operational-status `delayed_calendar_items` (past-due non-terminal calendar evidence).
- **Alert on LinkedIn token or publication failure:** evaluate/emit alerts from the `linkedin` dependency bucket and/or LinkedIn progress failure codes already surfaced by operational-status.
- **Alert on stale campaigns:** evaluate/emit alerts when operational-status classifies a campaign `stale=true`.
- **Visible and understandable / clear failures:** structured alert type, severity, fingerprint, safe identifiers, codes/reasons, and short summaries without secrets or content bodies; emission status remains explicit.
- **No duplication or unintended change:** reuse existing status classifications and the US-028 evaluate/emit path; do not rewrite completed US-026/US-027/US-028 behavior; evaluation MUST NOT mutate campaign/run/editorial lifecycle.

No US-029 acceptance criteria are intentionally excluded. US-030 criteria and BL-011 closure are intentionally excluded (separate story / later acceptance).

## Capabilities

### New Capabilities

- None. US-029 extends the existing operational-alerts capability rather than introducing a sibling surface.

### Modified Capabilities

- `flow-a-operational-alerts`: Add US-029 alert types (`partial_calendar_execution`, `linkedin_token_or_publication_failure`, `stale_campaign`), derivation rules from existing operational-status evidence, updated summary counts, and scope/verification language. Preserve the authenticated evaluate endpoint, fail-closed webhook emission, ledger isolation, and all US-028 alert behaviors.
- `flow-a-operational-status`: Clarify purpose/out-of-scope language so BL-011 US-029 alerting is owned by `flow-a-operational-alerts` while the existing read-only status contract, classifications, and zero-mutation guarantees remain unchanged. No change to `GET /flow-a/operational-status` request/response requirements beyond that scope clarification.

## Impact

- **API:** same authenticated `POST /flow-a/operational-alerts/evaluate` contract; response `alerts[]` / `summary.counts` gain US-029 types. Existing operational-status route remains the observation foundation.
- **Worker:** extend `flow_a_operational_alerts` derivation to map delayed calendar, LinkedIn failure, and stale-campaign evidence; reuse existing config, webhook adapter, and emission ledger.
- **Persistence:** no new ledger path; continue using `metadata/operational-alerts/emissions.json` with fingerprints that include the new alert types.
- **n8n:** may continue scheduling/calling the worker over HTTP; no Execute Command; no requirement to ship a production n8n workflow in this change.
- **Tests and docs:** behavioral tests for the three US-029 types, regression that US-028 types still work, fail-closed emission, safe payloads, and zero lifecycle mutation; CURRENT-STATE / operator docs / product progress updated only to demonstrated level after implementation.
- **Out of scope systems:** no Slack/email SDK; no BL-015 UI; no deploy/live validation; no US-030 types.
