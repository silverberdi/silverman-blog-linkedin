## Why

BL-011 / US-028 requires operators to receive timely, actionable alerts when Flow A items move to error, image generation fails, or blog publication fails. US-026 and US-027 already consolidate those failure signals in read-only `GET /flow-a/operational-status`, but observation alone does not notify the operator when attention is required.

## What Changes

- Add a small, explicit Flow A operational-alert capability that derives alert candidates from the same confined, validated operational-status evidence (campaign/run failure and blocked signals, dependency buckets `comfyui` / `github_pages_checkout` / related safe codes) rather than ad-hoc raw-file rescans.
- Expose an n8n-callable, API-key-protected worker HTTP contract that evaluates US-028 alert conditions and returns structured, secret-safe alert payloads operators (and n8n) can understand.
- Provide an optional fail-closed outbound webhook emission path so the worker can deliver those payloads when explicitly enabled; when disabled, evaluation remains available without external notification side effects.
- Define minimal idempotent “already alerted” persistence only as needed to prevent duplicate emissions for the same alert fingerprint; keep editorial/campaign/run lifecycle state immutable during evaluation.
- Update CURRENT-STATE and product progress only to the demonstrated implementation level; do not mark US-028 accepted or BL-011 closed from proposal or code alone.

## Goals

- Satisfy US-028 by alerting on items moved to error, image-generation failure, and blog publication failure.
- Make alert outcomes visible, understandable, and clearly labeled for the intended operator/n8n consumer.
- Reuse US-026/US-027 validated classifications and dependency buckets; do not invent a parallel failure ontology.
- Preserve ADR-0001: n8n orchestrates over HTTP only; the worker owns evaluation (and optional emission) via HTTP — never n8n Execute Command.
- Keep evaluation free of unintended lifecycle mutation; gate emission behind fail-closed enablement.

## Non-goals

- US-029: partial calendar execution, LinkedIn token/publication failure, or stale-campaign alerts.
- US-030: unhealthy worker or failed n8n workflow alerts.
- BL-015 supervision UI / console.
- Closing BL-010 or claiming US-026/US-027 business acceptance.
- Deploy, push, live mutation, or assuming Slack/email/UI as the MVP channel without an explicit design choice.
- Replacing or duplicating `GET /flow-a/operational-status`; alerts build on it, they do not fork a second observability surface.
- Broad notification platforms, paging systems, or multi-channel fan-out beyond the chosen MVP emission contract.

## Acceptance Criteria Coverage

- **Alert on items moved to error:** emit/evaluate alerts when operational evidence shows an item in the editorial `error` location / failed campaign classification tied to that error move.
- **Alert on image-generation failure:** emit/evaluate alerts from validated ComfyUI / `blog_image_generation_*` dependency evidence (`comfyui` bucket).
- **Alert on blog publication failure:** emit/evaluate alerts from validated blog publish / git publication / checkout failure evidence (`github_pages_checkout` bucket for publication-failure codes).
- **Visible and understandable / clear failures:** structured alert type, reason codes, safe artifact identifiers, and human-readable summaries without secrets or content bodies.
- **No duplication or unintended change:** reuse existing status classifications; do not rewrite completed US-026/US-027 behavior; evaluation MUST NOT mutate campaign/run/editorial lifecycle; emission dedupe MUST be explicit and minimal.

No US-028 acceptance criteria are intentionally excluded. US-029 and US-030 criteria are intentionally excluded (separate stories).

## Capabilities

### New Capabilities

- `flow-a-operational-alerts`: US-028 alert evaluation and optional fail-closed emission contract — candidate derivation from operational-status evidence, alert types for error-folder moves / image-generation failure / blog publication failure, safe payloads, idempotent emission bookkeeping, and n8n-callable HTTP boundary.

### Modified Capabilities

- `flow-a-operational-status`: Clarify purpose/out-of-scope language so BL-011 US-028 alerting is owned by `flow-a-operational-alerts` while the existing read-only status contract, classifications, and zero-mutation guarantees remain unchanged. No change to `GET /flow-a/operational-status` request/response requirements beyond that scope clarification.

## Impact

- **API:** new authenticated worker HTTP endpoint(s) for alert evaluation and optional emission; existing operational-status route remains the observation foundation.
- **Worker:** new alert evaluation/emission module that reuses operational-status classification helpers or their shared evidence rules; optional outbound HTTP webhook adapter behind a fail-closed enablement flag.
- **Persistence:** only if emission is enabled — minimal idempotent alert-fingerprint store under an approved metadata path; evaluation-only mode stays non-mutating for editorial/campaign/run lifecycle artifacts.
- **n8n:** may schedule/call the worker over HTTP and own downstream channel mapping; no Execute Command; no requirement to ship a production n8n workflow in this change.
- **Tests and docs:** behavioral tests for candidate derivation, enablement fail-closed behavior, safe payloads, idempotency, and zero lifecycle mutation; CURRENT-STATE / operator docs / product progress updated only to demonstrated level after implementation.
- **Out of scope systems:** no Slack/email SDK assumption in MVP beyond a generic webhook (or evaluate-only + n8n delivery); no BL-015 UI; no deploy/live validation as part of this change.
