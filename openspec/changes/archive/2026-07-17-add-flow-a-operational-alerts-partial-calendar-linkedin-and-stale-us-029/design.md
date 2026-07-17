## Context

US-026 and US-027 deliver authenticated read-only `GET /flow-a/operational-status`, which already classifies delayed calendar items, campaign `stale`/`blocked` flags, LinkedIn progress failure codes, and dependency-failure bucket `linkedin`. Canonical contract: `openspec/specs/flow-a-operational-status/spec.md`. Implementation: `src/silverman_blog_linkedin/flow_a_operational_status.py`.

US-028 delivers authenticated `POST /flow-a/operational-alerts/evaluate` with optional fail-closed generic webhook emission and `metadata/operational-alerts/emissions.json` ledger for:

1. `item_moved_to_error`
2. `image_generation_failure`
3. `blog_publication_failure`

Canonical contract: `openspec/specs/flow-a-operational-alerts/spec.md`. Implementation: `src/silverman_blog_linkedin/flow_a_operational_alerts.py`.

BL-011 / US-029 needs operators to be **notified** when attention is required for:

1. partial calendar execution,
2. LinkedIn token or publication failure,
3. stale campaigns.

Observation alone does not notify. ADR-0001 requires n8n ↔ worker HTTP only. US-028 remains implemented/tested locally (business acceptance pending) and MUST NOT be reworked or re-accepted by this change. US-030 / BL-015 remain out of scope.

## Goals / Non-Goals

**Goals:**

- Derive US-029 alert candidates from existing operational-status evidence only.
- Reuse the US-028 evaluate/emit HTTP contract, fail-closed enablement, secret-safe payloads, and emission ledger.
- Keep alert payloads understandable and deterministic; extend `summary.counts` for the new types.
- Preserve campaign/run/editorial lifecycle immutability during evaluate-only (and emit ledger-only writes).
- Preserve all US-028 alert behaviors and regression coverage.

**Non-Goals:**

- US-030 unhealthy-worker / failed-n8n alert types.
- Slack, email, SMS, or UI SDKs.
- Shipping or activating a production n8n workflow.
- Changing `GET /flow-a/operational-status` response shape or classification rules.
- Deploy / live mutation / BL-011 closure / US-028 re-acceptance.
- Parallel filesystem scanners or a second alerts endpoint.

## Decisions

### 1. Extend US-028 evaluate/emit — no new route or channel

**Decision:** Keep `POST /flow-a/operational-alerts/evaluate` as the sole alerts HTTP boundary. Same request fields (`now_utc`, `emit`), same auth (`Depends(require_api_key)`), same env flags (`SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED`, `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_WEBHOOK_URL`), same ledger path, same fail-closed emission semantics.

US-029 only extends candidate derivation and summary counts. n8n continues to schedule the same endpoint over HTTP (ADR-0001).

Alternatives considered:

- Separate `/flow-a/operational-alerts/evaluate-us-029` route: rejected; duplicates auth/emission and fragments the operator contract.
- New Slack/email adapter: rejected; out of scope and already non-goal for US-028 MVP.

### 2. Derive US-029 candidates from operational-status evidence — no ad-hoc rescans

**Decision:** Call the same operational-status aggregation used by US-028 (`get_flow_a_operational_status` / shared builders) as the sole evidence source. Map US-029 alert types as follows:

| Alert type | Derivation rule |
|------------|-----------------|
| `partial_calendar_execution` | Each entry in `delayed_calendar_items` (already past-due, non-terminal calendar evidence with reason `calendar_item_past_due`). One alert per `item_id`. |
| `linkedin_token_or_publication_failure` | Union of (a) dependency-failure attributions in bucket `linkedin` for a campaign or failed run, and (b) non-empty `campaign.linkedin.failure_codes` from LinkedIn progress. One alert per `(campaign_id\|run_id)` with sorted unique codes. |
| `stale_campaign` | Flow A campaign with `stale=true`. One alert per `campaign_id`. |

Do not invent a second filesystem scanner. Do not call ComfyUI, DeepSeek, LinkedIn, OAuth, Git, or live-site APIs while evaluating. Do not rescan `editorial-calendar/calendar.json` or campaign files outside the status aggregation.

**LinkedIn code scope:** Include validated codes already attributed to the `linkedin` bucket (token/oauth and publication families such as `linkedin_oauth_*`, `linkedin_publish_*`, and other `linkedin_*` codes not claimed by `github_pages_checkout`). Do **not** raise this alert solely for LinkedIn-preview checkout codes (those remain excluded from blog publication and are not in the `linkedin` bucket). Package-generation codes that operational-status already places in `linkedin` ARE in scope because they are LinkedIn dependency failures surfaced by the same evidence channel the user required.

Alternatives considered:

- Rescan calendar.json / campaigns for “partial” heuristics: rejected; duplicates US-026 delayed/stale rules and risks drift.
- Alert only on `publish_state=failed` without dependency codes: rejected; misses token/oauth failures already bucketed under `linkedin`.
- Alert on all `blocked` campaigns as stale: rejected; blocked ≠ stale; use the existing `stale` boolean only.

### 3. Alert payload extensions (safe, understandable)

**Decision:** Reuse the US-028 `OperationalAlert` shape and extend it minimally:

- Existing fields remain required where already specified: `alert_type`, `severity`, `fingerprint`, `observed_at_utc`, `summary`, optional `campaign_id` / `run_id` / `dependency` / `error_codes`.
- Add optional `calendar_item_id` for `partial_calendar_execution` (safe identifier only; never titles that might embed operator-private free text beyond the existing status-safe `item_id`).
- For partial-calendar alerts, include stable reason code `calendar_item_past_due` in `error_codes` (matches delayed-item reason).
- For stale alerts, include sorted stale-related `health_reasons` that are already safe status strings (for example `execution_state_stale`, processing-inactivity reasons) as `error_codes` when present; otherwise use primary code `stale` in the fingerprint.
- For LinkedIn alerts, set `dependency=linkedin` and include sorted validated `error_codes`.

**Severity:**

| Alert type | Severity |
|------------|----------|
| `linkedin_token_or_publication_failure` | `error` |
| `partial_calendar_execution` | `warning` |
| `stale_campaign` | `warning` |

US-028 types remain `error`. Severity differentiation makes attention-vs-hard-failure understandable without inventing a UI.

Fingerprint format remains:

`{alert_type}:{artifact_id}:{primary_error_code}`

where `artifact_id` is `campaign_id` or `run_id` or, for calendar-only items, `calendar_item_id`.

`summary.counts` MUST include integer counts for all six types (three US-028 + three US-029). Ordering of `alerts[]` remains deterministic: `alert_type` ascending, then `fingerprint` ascending.

### 4. Preserve emission ledger and lifecycle non-mutation

**Decision:** No new ledger path. New fingerprints participate in the same once-per-fingerprint emit rules. Evaluate-only still writes nothing. Emit still writes only `metadata/operational-alerts/emissions.json` after HTTP 2xx. No mutation of campaigns, runs, calendar, editorial folders, or LinkedIn artifacts.

### 5. Preserve operational-status as observation-only

**Decision:** Do not add alert fields to `GET /flow-a/operational-status`. Update that capability’s purpose/scope requirements so BL-011 US-028 **and** US-029 alerting are owned by `flow-a-operational-alerts`, while status remains free of notification side effects. Shared derivation code remains an implementation detail.

### 6. Documentation and progress discipline

Update `docs/CURRENT-STATE.md`, the existing operator note under `docs/operations/flow-a-operational-alerts.md`, and product progress only to the demonstrated level after implementation. Do not mark US-029 accepted, do not re-accept US-028, and do not close BL-011 from proposal/code alone. Do not implement US-030.

## Risks / Trade-offs

- **[Risk] Double-counting LinkedIn signals** (dependency bucket + `failure_codes`) → Mitigation: merge codes into one alert per artifact fingerprint before sorting.
- **[Risk] Calendar alert storms for many delayed items** → Mitigation: one alert per `item_id`; ledger prevents re-emit; evaluate remains available without emit.
- **[Risk] Stale + LinkedIn failure on same campaign produces multiple alerts** → Mitigation: intentional — different attention classes; fingerprints differ by `alert_type`.
- **[Risk] Regressing US-028 derivation** → Mitigation: keep US-028 mapping functions intact; add US-029 derivations beside them; regression tests for all six types.
- **[Risk] Operators expect Slack** → Mitigation: unchanged generic webhook + n8n mapping; document in operator notes.
- **[Trade-off] `warning` vs `error` severity** → Acceptable clarity gain; webhook consumers must not assume all alerts are `error`.
- **[Trade-off] Once-per-fingerprint means cleared-then-recurring conditions need a new fingerprint or future reset** → Same as US-028; acceptable for US-029 MVP; US-030+ may add reopen rules later.

## Migration Plan

1. Implement US-029 derivation + summary count updates with tests (emit default false) — safe to deploy with alerts disabled.
2. Confirm US-028 regression suite still passes.
3. Document new alert types in operator docs; leave enablement false until operator approval.
4. Optional controlled emission validation remains an explicit later ops step (not part of default change completion).
5. Rollback: disable enablement flag; evaluate remains available; ledger isolation means campaigns are untouched.

## Open Questions

None blocking proposal approval. Apply-time may decide whether calendar `title` is ever echoed in `summary` text; prefer **omit title** and use only `calendar_item_id` + reason so free-text calendar titles cannot surprise operators or leak unintended content.
