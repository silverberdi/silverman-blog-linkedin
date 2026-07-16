# Design: implement-scheduled-linkedin-publication-execution-us-018

## Context

Flow A leaves every scheduled variant at `publish_state` `pending` with a per-variant `scheduled_at_utc` (canonical spec `linkedin-distribution-scheduling-model`). Real publication is a two-step operator path per canonical spec `linkedin-publication-integration`:

1. `POST /queue-linkedin-publication` — per campaign+variant, `pending` → `queued`, sets `publish_after_utc` (default safety delay 120 min).
2. `POST /publish-linkedin-due-variants` — publishes `queued` variants when `publish_after_utc <= now` or `publish_now=true`.

US-017 (BL-006) added `operator_supervision` metadata: cancel sets `auto_queue_eligible=false` permanently; defer reschedules `scheduled_at_utc` and sets `auto_queue_eligible=false` until the new time is due (runtime evaluation — no persisted flip back required); edit sets it `true`. The supervision mechanics doc defines the BL-007 eligibility contract this change implements.

Uncommitted construction WIP (see `docs/product/bl-007-auto-queue-pending-handoff.md`) adds `auto_queue_pending` to publish-due plus operator scripts and a manual inactive n8n workflow. This change formalizes that contract; apply will absorb/rewrite the WIP, not merge it blindly.

Constraints: ADR-0001 (n8n → worker HTTP only), US-011 fail-closed enablement guard (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`), dry-run defaults on all publication endpoints, no variant body text in metadata/responses, and no automatic background triggers introduced by an OpenSpec apply.

## Goals / Non-Goals

**Goals:**

- One worker call that identifies due `pending` variants, queues only eligible ones, and publishes via the existing publish-due path — opt-in, default off.
- Deterministic, spec-backed eligibility rules honoring US-017 supervision metadata.
- Bounded cross-campaign scan with an operator-readable outcome summary.
- Once-only publication preserved under the combined path.
- Absorb WIP scripts and inactive n8n workflow under the approved contract.

**Non-Goals:**

- US-019 (URN/failure evidence polish), US-020 (normative cross-audience cadence/sequence), BL-008 retry rules, BL-015 console.
- Auto re-queue of `failed` variants (manual re-queue via the queue endpoint remains the only `failed` path).
- Activating any n8n workflow, changing enablement flags, or unattended production scheduling.
- New endpoints — the change extends `POST /publish-linkedin-due-variants` only.

## Decisions

### D1 — Opt-in `auto_queue_pending` on publish-due (not two-step-only, not a new endpoint)

Add optional `auto_queue_pending: bool = false` to `POST /publish-linkedin-due-variants`.

- **Why over two-step-only n8n composition:** the queue endpoint requires explicit `campaign_id` + `variant` per call; n8n composing "discover pending across campaigns → N queue calls → publish-due" would move due/eligibility discovery logic into workflow JSON, which is harder to test, spec, and keep consistent with supervision exclusions. The worker already owns eligibility validation; discovery belongs beside it (ADR-0001 spirit: worker owns validation and lifecycle, n8n only orchestrates HTTP).
- **Why over a new endpoint:** the combined operation is publish-due with a pre-phase; a separate route would duplicate auth/response plumbing and create two overlapping contracts for the same state machine.
- **Fail-safe default:** `auto_queue_pending=false` preserves the canonical two-step behavior exactly; the canonical separate endpoints remain unchanged and remain the manual/granular path.

### D2 — "Due" definition and interaction with safety delay / `publish_now`

A `pending` variant is **due for auto-queue** when `scheduled_at_utc <= now_utc` (worker UTC clock at request evaluation).

- Missing or unparsable `scheduled_at_utc` ⇒ not due; skipped with a stable reason (never an exception path that aborts the scan).
- `publish_now=true` on the request is an explicit operator override that also bypasses the `scheduled_at_utc` gate for auto-queue target selection (matching WIP script semantics: default is send-now operator override; `--respect-schedule` sets `publish_now=false`). Supervision exclusions in D3 still apply — `publish_now` never overrides operator cancel/defer eligibility.
- Queue phase applies the existing safety-delay rules unchanged: `publish_after_utc = now + safety_delay` from `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES` (no request-level `safety_delay_minutes` on publish-due — that field stays exclusive to the canonical queue endpoint to keep the WIP contract shape). Publish phase then applies existing due semantics (`publish_after_utc <= now` unless `publish_now`). Consequence: with a nonzero safety delay and `publish_now=false`, an auto-queued variant is queued in this call and published by a later call — that is correct two-gate behavior, not a defect, and MUST be visible in the response summary.

### D3 — Eligibility exclusions (implements the US-017 documented contract)

Normative eligibility rule for auto-queue:

```text
eligible iff:
  publish_state == "pending"                       # never queued/published/failed/cancelled
  AND campaign is flow_a in distribution_scheduled # existing queue eligibility, re-enforced by queue service
  AND (
       # strategy-default variants (no operator defer/cancel block):
       operator_supervision.auto_queue_eligible is not false   # absent ⇒ eligible (US-015 default)
       AND due per D2 (scheduled_at_utc <= now_utc OR publish_now)
    OR
       # deferred variants — runtime re-evaluation; publish_now does NOT bypass the deferred time:
       operator_supervision.last_action == "defer"
       AND scheduled_at_utc <= now_utc
  )
```

- **`publish_state` gate:** auto-queue does **not** touch `queued`, `published`, `failed`, or `cancelled`. Although manual queue accepts `failed` re-queue today, automatic re-queue of `failed` is excluded (BL-008 territory; avoids duplicate-risk retries without retry rules). Cancel is excluded twice: by `publish_state` `cancelled` and by its permanent `auto_queue_eligible=false`.
- **Defer runtime re-evaluation:** US-017 persists `auto_queue_eligible=false` on defer with no flip back. Per the supervision mechanics contract, BL-007 evaluates at runtime: a `pending` variant whose `last_action` is `defer` becomes eligible again once its deferred `scheduled_at_utc` is due — the persisted `false` from defer does not permanently exclude it. While the deferred schedule is not yet due, the variant is skipped.
- **`publish_now` interaction:** `publish_now` bypasses only the D2 schedule gate for strategy-default variants. It never overrides supervision: a cancelled variant, or a deferred variant whose new schedule is not yet due, is not auto-queued even with `publish_now=true` (defer means "not before the new time" regardless of override).

Excluded variants are reported as skipped with stable reason codes (new warning-level codes, e.g. `linkedin_publish_auto_queue_skipped_not_due`, `linkedin_publish_auto_queue_skipped_supervision`); they never change state and never fail the overall request by themselves.

### D4 — Bounded cross-campaign scan

When `campaign_id` is omitted and `auto_queue_pending=true`, the worker scans `metadata/campaigns/*.json` (existing `_list_campaign_ids` enumeration — same bound already used by publish-due for queued targets), filtering to `flow` `flow_a` and state `distribution_scheduled`. No recursion, no other directories, no pagination (campaign count is small and local; the scan is a directory listing plus JSON reads). `variant` filter requires `campaign_id` (HTTP 422 otherwise, consistent with script validation). Response includes per-variant entries for both phases so the operator can see exactly what was queued, published, and skipped and why.

### D5 — Idempotency / once-only publication

- Already-`queued` variants are not re-queued (no duplicate `publication_queued_at` rewrite, no `publish_after_utc` reset); they flow to the publish phase as today.
- Already-`published` variants keep the existing idempotent no-API-call behavior with preserved URN.
- The queue phase reuses the existing queue service logic (same validation, metadata writes, artifact hash checks) — no parallel implementation.
- Real API calls still require `dry_run=false` **and** `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` **and** token-provider credentials; enablement-off fails closed with `linkedin_publish_not_enabled` without marking variants `failed`.
- `dry_run=true` (default) reports planned queue+publish outcomes with zero mutation and zero LinkedIn/OAuth calls.

### D6 — Scope slice boundary (US-018 vs US-019/US-020)

US-018 delivers identify-due + queue-eligible + publish-once. Existing publish-due already stores `linkedin_post_urn`/failure context; US-019 will assess evidence/failure-taxonomy polish on top without contract conflict. Ordering within one auto-queue pass processes variants deterministically (per campaign, in stored `variants[]` order → schedule order from the `flow_a_staggered` strategy), but **no normative cross-audience cadence/sequence requirement is added** — that is US-020. The delta specs are written so US-020 can add ordering requirements without modifying US-018 requirements.

### D7 — Tooling and n8n absorption

- `deploy/server/run-publish-pending-linkedin-variants.sh`: dry-run default; `--real` requires enablement in the server `.env` (preflight); `--respect-schedule` maps to `publish_now=false`; optional `--campaign-id` / `--variant`. Never prints secrets.
- `deploy/server/finish-pending-linkedin-publication.sh`: Mac-side scp+run convenience wrapper; no direct worker/module invocation.
- `n8n/workflows/silverman-blog-linkedin-publish-pending.json`: manual-trigger workflow calling health + publish-due with `auto_queue_pending=true` over HTTP; repo export MUST remain `"active": false`. Import and any activation are separate gated operational decisions (import ≠ unattended).

## Risks / Trade-offs

- [Combined call queues and publishes in one request — larger blast radius than two-step] → default `dry_run=true`, default `auto_queue_pending=false`, enablement fail-closed, per-variant summary before real windows; canonical two-step path untouched for granular control.
- [`publish_now=true` with auto-queue bypasses both schedule and safety delay] → documented as explicit operator override; script defaults keep dry-run; supervision exclusions still enforced; tests assert cancel/defer are never overridden.
- [Cross-campaign scan may touch legacy campaigns with stale metadata] → scan filters to `flow_a` + `distribution_scheduled`; unreadable/ineligible campaigns produce skip reasons, not failures; campaign/variant filters available for controlled windows.
- [Server image may already run construction WIP that differs from the approved contract] → apply rewrites WIP to spec; deploy is a separate approved step; `BUILD_REVISION` check confirms deployed version before validation evidence is collected.
- [Deferred variant becomes due again and publishes without a persisted `auto_queue_eligible=true` flip] → this is the documented US-017 runtime-evaluation contract (defer means "not until new time"), asserted by tests; operators who want permanent stop must cancel.

## Migration Plan

1. Implement worker + tests (implementation commit after `/opsx-verify`, with explicit user commit approval).
2. Sync delta specs to `openspec/specs/` (separate commit), then archive (separate commit).
3. Push/deploy/import/validation are separate, explicitly approved operational steps: rebuild Docker image on `192.168.0.194`, confirm `BUILD_REVISION`, dry-run smoke via the operator script, then a controlled real window (enable flag, publish, verify once-only + URN evidence, restore flag per policy). None of this is implied by the implementation commit.
4. Rollback: revert the implementation commit; default-off flag means no behavioral change for existing callers even before rollback.

## Open Questions

- None blocking. Cadence/sequence normalization (US-020) and failure-evidence polish (US-019) intentionally deferred.
