## Context

US-026 and US-027 deliver authenticated read-only `GET /flow-a/operational-status`, which already classifies failed/blocked campaigns (including `source_file_status.location=error`), aggregates dependency failures into `comfyui` / `deepseek` / `linkedin` / `github_pages_checkout` / `unclassified`, and guarantees zero mutation of editorial lifecycle artifacts. Canonical contract: `openspec/specs/flow-a-operational-status/spec.md`. Implementation: `src/silverman_blog_linkedin/flow_a_operational_status.py`.

BL-011 / US-028 needs operators to be **notified** when attention is required for:

1. items moved to error,
2. image-generation failure,
3. blog publication failure.

Observation alone does not notify. ADR-0001 requires n8n ↔ worker HTTP only (no Execute Command). US-026/US-027 business acceptance remains pending and is not reopened. US-029 / US-030 / BL-015 remain out of scope.

## Goals / Non-Goals

**Goals:**

- Derive US-028 alert candidates from existing operational-status classifications and dependency buckets.
- Expose an n8n-callable authenticated worker HTTP contract for evaluation (and optional emission).
- Choose an explicit MVP notification channel with fail-closed enablement.
- Keep alert payloads secret-safe, deterministic, and understandable.
- Persist only minimal idempotent “already alerted” state when emission is enabled.
- Preserve campaign/run/editorial lifecycle immutability during evaluate-only calls.

**Non-Goals:**

- US-029 / US-030 alert types.
- Slack, email, SMS, or UI SDKs as first-class worker integrations.
- Shipping or activating a production n8n workflow as part of this change.
- Changing `GET /flow-a/operational-status` response shape or classification rules.
- Deploy / live mutation / BL-010 closure.

## Decisions

### 1. MVP channel: evaluate endpoint + optional generic webhook (not Slack/email/UI)

**Decision:** MVP notification channel is:

1. **Primary (always available when authenticated):** `POST /flow-a/operational-alerts/evaluate` returns structured alert candidates derived from current operational evidence. n8n (or an operator) schedules this over HTTP and owns any downstream Slack/email/UI mapping.
2. **Optional emission:** when fail-closed enablement is on and a webhook URL is configured, the same request may ask the worker to `POST` a secret-safe alert payload to that generic HTTP webhook. The worker does **not** embed Slack/email/UI clients.

Chosen MVP = **generic outbound webhook adapter + n8n-callable evaluate contract**. Slack/email/UI are deliberately **not** assumed; operators map the webhook (or the evaluate JSON) to their channel outside this change.

Alternatives considered:

- Worker posts directly to Slack/email: rejected for MVP; adds provider secrets and SDKs without product requirement.
- n8n-only polling of `GET /flow-a/operational-status` with no alert contract: rejected; leaves alert typing, dedupe, and emission semantics undefined and duplicates operator logic.
- Background in-process monitor/timer in the worker: rejected; scheduling belongs to n8n under ADR-0001.

### 2. Single evaluate endpoint with explicit emit mode; fail-closed enablement

**Decision:**

- Route: authenticated `POST /flow-a/operational-alerts/evaluate` via `Depends(require_api_key)`.
- Request JSON (small, explicit):
  - optional `now_utc` (same canonical form as operational-status; invalid → 422),
  - optional `emit` boolean (default `false`).
- When `emit=false` (default): evaluate only — no webhook call; no alert-ledger write; no lifecycle mutation.
- When `emit=true`:
  - If `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED` is not truthy **or** webhook URL is unset/invalid → fail closed: return structured JSON indicating emission skipped/disabled (HTTP 200 with clear `emission.status`, or 503 if the product prefers hard failure — prefer **200 with `emission.status=disabled|misconfigured`** so n8n can distinguish “no candidates” from “alerts off” without treating config as a pipeline crash). Do not call webhook. Do not write ledger.
  - If enabled and configured → emit only new fingerprints; update ledger after successful webhook acceptance.

Env (names final in implementation, documented in ops docs):

| Variable | Role |
|----------|------|
| `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED` | Fail-closed master switch (default off / false) |
| `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_WEBHOOK_URL` | Generic HTTPS webhook target; required for emit |

Webhook URL MUST NOT appear in HTTP responses. Secrets MUST NOT appear in alert payloads or logs.

Alternatives considered:

- Separate GET evaluate + POST emit routes: workable but more surface; one POST with `emit` keeps the contract small.
- Always emit when enabled without request flag: rejected; removes dry evaluate for tests and n8n preview.

### 3. Derive candidates from operational-status evidence — no ad-hoc rescans

**Decision:** Reuse the operational-status aggregation result (shared service function or internal call to the same builders) as the sole evidence source. Map US-028 alert types as follows:

| Alert type | Derivation rule |
|------------|-----------------|
| `item_moved_to_error` | Flow A campaign with `failed=true` and evidence that `source_file_status.location` is `error` (or equivalent health reason already produced by operational-status for error-folder campaigns). One alert per such `campaign_id`. |
| `image_generation_failure` | Any artifact attribution in dependency bucket `comfyui` (codes `comfyui_*` / `blog_image_generation_*`). One alert per `(artifact_id, alert_type)` fingerprint using campaign_id or run_id. |
| `blog_publication_failure` | Dependency bucket `github_pages_checkout` attributions whose validated codes match publication-failure families `blog_publish_*` or `blog_git_publication_*` (exclude preview-only checkout codes such as `linkedin_preview_validation_checkout_*` and `linkedin_article_preview_public_repo_not_configured` so US-028 stays on blog publication failure, not LinkedIn preview). |

Do not invent a second filesystem scanner. Do not call ComfyUI, DeepSeek, LinkedIn, Git, or live-site APIs while evaluating.

Alternatives considered:

- Rescan `blog-posts/error/` directly: rejected; bypasses validated campaign linkage and duplicates queue lifecycle rules.
- Alert on all `github_pages_checkout` codes including LinkedIn preview: rejected; expands beyond US-028 “blog publication failure”.

### 4. Alert payload shape (safe, understandable)

Each candidate MUST include:

- `alert_type` (one of the three US-028 types),
- `severity` (`error` for all three in MVP),
- `fingerprint` (stable idempotency key),
- `observed_at_utc`,
- safe identifiers (`campaign_id` and/or `run_id` when known),
- sorted validated `error_codes` when applicable,
- `dependency` when derived from a bucket (`comfyui` or `github_pages_checkout`),
- short `summary` string built only from safe fields (type + ids + codes) — no Markdown bodies, tokens, or base paths.

Response MUST include `status` (`ok`/`partial` mirrored from underlying evidence issues where relevant), `observed_at_utc`, `alerts[]`, `summary.counts` by alert type, `data_issues` when evaluation evidence is partial, and `emission` object describing whether emit was requested and what happened.

Ordering of `alerts[]` MUST be deterministic: `alert_type` ascending, then fingerprint ascending.

### 5. Minimal idempotent emission ledger (explicit persistence)

**Decision:** When `emit=true` and emission is enabled/configured, persist fingerprints under:

`metadata/operational-alerts/emissions.json`

(confined under the editorial base; create directory as needed). Schema (minimal):

- `version`
- `entries`: map fingerprint → `{ "alert_type", "first_emitted_at_utc", "last_emitted_at_utc", "campaign_id?", "run_id?" }`

Rules:

- Emit webhook only when fingerprint is absent from the ledger **or** (future US-029+) explicitly reopened — MVP: emit once per fingerprint while the condition remains; do not re-spam on every n8n poll.
- Write ledger **after** successful webhook HTTP success (2xx). Failed webhook MUST NOT mark fingerprint emitted.
- Evaluate-only (`emit=false`) MUST NOT read-require or write the ledger (may skip ledger I/O entirely).
- Ledger writes MUST NOT touch `metadata/campaigns/`, `metadata/runs/`, editorial folders, calendar, or LinkedIn artifacts.
- Atomic replace for the ledger file.

Fingerprint format (normative intent):  
`{alert_type}:{campaign_id|run_id}:{primary_error_code|none}`  
normalized and stable.

Alternatives considered:

- Stateless always-notify: rejected; not actionable (alert storms).
- Embed “alerted” flags on campaign JSON: rejected; mutates lifecycle documents and couples alerts to campaign schema.
- n8n-only dedupe: acceptable for evaluate-only deployments, but worker emission still needs a ledger when the worker owns webhook POST.

### 6. Preserve operational-status as observation-only; alerts are a sibling capability

**Decision:** Do not add alert fields to `GET /flow-a/operational-status`. Update that capability’s purpose/scope requirements so BL-011 US-028 is owned by `flow-a-operational-alerts`, while status remains free of notification side effects. Shared derivation code is an implementation detail; the HTTP contracts stay separate.

### 7. Documentation and progress discipline

Update `docs/CURRENT-STATE.md`, a short operator note under `docs/operations/`, and product progress only to the demonstrated level after implementation. Do not mark US-028 accepted or BL-011 closed from proposal/code alone. Do not close BL-010.

## Risks / Trade-offs

- **[Risk] Alert storms if fingerprints are too coarse/fine** → Mitigation: fingerprint includes type + artifact + primary code; one emission per fingerprint; tests for repeated evaluate+emit.
- **[Risk] Webhook delivers but ledger write fails → duplicate next time** → Mitigation: prefer write-after-success; document rare duplicate as acceptable vs lost alert; keep ledger atomic.
- **[Risk] Coupling to operational-status internals** → Mitigation: call shared aggregation API; regression-test US-026/US-027 zero mutation and classifications unchanged.
- **[Risk] Operators expect Slack** → Mitigation: design explicitly chooses generic webhook + n8n mapping; document in operator docs.
- **[Risk] Emission disabled in prod → silent non-delivery** → Mitigation: evaluate always returns candidates; emission status explicitly reports disabled/misconfigured; fail closed without pretending success of delivery.
- **[Trade-off] Once-per-fingerprint means cleared-then-recurring failures need a new fingerprint or future reset** → Acceptable for US-028 MVP; US-029+ may add reopen/stale rules later.

## Migration Plan

1. Implement evaluate path with tests (emit default false) — safe to deploy with alerts disabled.
2. Document env flags; leave `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED` false until operator approval.
3. Optional: configure webhook URL and enable emission in a controlled validation window (requires explicit user approval for live/server changes — not part of this change’s default completion).
4. Rollback: set enablement false; evaluate remains available; delete or ignore ledger if needed (does not affect campaigns).

## Open Questions

None blocking proposal approval. Implementation may choose HTTP 200+`emission.status` vs 503 for misconfigured emit; prefer 200+explicit status as decided above unless apply-time review finds n8n error-handling needs 503.
