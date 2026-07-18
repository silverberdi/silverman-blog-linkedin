# LinkedIn variant supervision mechanics (Flow A)

**Scope:** US-017 (BL-006 story 3) — persisted operator edit, reject/cancel, and defer mechanics during the optional supervision window while `publish_state` is `pending`.
**Status:** Mechanics defined (docs + worker routes); operationally validated only when exercised in controlled smoke — not unattended production.
**Authority:** Complements [linkedin-variant-review-policy.md](linkedin-variant-review-policy.md) (US-015), [linkedin-variant-quality-criteria.md](linkedin-variant-quality-criteria.md) (US-016), [GLOSSARY.md](../GLOSSARY.md), [user-stories.md](../product/user-stories.md) US-017, and [silverman-editorial-system.md](../../content-strategy/silverman-editorial-system.md) `#flow-a-vs-flow-b` and `#linkedin-distribution-strategy`.

## Purpose and scope

This document answers: **“How does the operator persist correction, rejection, or deferral before LinkedIn API queueing during the supervision window?”**

**In scope (US-017):**

- Worker HTTP routes for edit (`POST /correct-linkedin-variant`), defer (`POST /defer-linkedin-variant`), and extended cancel (`POST /cancel-linkedin-publication` accepts `pending` and `queued`).
- `operator_supervision` metadata contract on campaign `variants[]`.
- Blocked/invalid action table and stable error codes.
- BL-007 auto-queue eligibility exclusions consumed by the implemented US-018 worker path.

**Out of scope (explicit non-goals):**

- BL-007 US-019 publication-evidence polish and US-020 cadence/sequence. US-018 `auto_queue_pending` is implemented separately and consumes this supervision contract.
- **BL-015** — supervision console UI (US-038–US-040). US-038 Story 1 read view + US-039 Story 2 edit/defer + US-040 Story 3 cancel/blocked-state: `GET /flow-a/console/linkedin-variant-supervision` / `GET /flow-a/linkedin-variants/pending-supervision` (nullable `draft_content`, `integration_failures[]`). Console exercises existing US-017 `POST /correct-linkedin-variant`, `POST /defer-linkedin-variant`, and `POST /cancel-linkedin-publication` (does not rewrite these contracts).
- Flow B mandatory review implementation.
- New `publish_state` values (`deferred`, `rejected`) — supervision uses parallel `operator_supervision` metadata.
- US-016 criteria as automatic queue gates.
- `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` changes — supervision is pre-API and does not require enablement.

## Relationship to US-015 optional supervision

US-015 defines **strategy-driven publication** (scheduled variants expected to publish unless operator override) and the **optional supervision window** while `pending` before API queue/send. Supervision is **not** mandatory approval.

US-017 provides **persistence mechanics** for operator overrides during that window:

| Operator intent | Route | `publish_state` after success |
|-----------------|-------|-------------------------------|
| Edit draft | `POST /correct-linkedin-variant` | `pending` (unchanged) |
| Defer/reschedule | `POST /defer-linkedin-variant` | `pending` (unchanged) |
| Reject/cancel | `POST /cancel-linkedin-publication` | `cancelled` |

Absent `operator_supervision` on a `pending` variant means strategy-driven default (eligible per BL-007 rules when due).

## Relationship to US-016 criteria failure

US-016 defines quality and differentiation criteria that **guide** operator judgment during optional supervision. Criteria failure is editorial guidance — **not** a new `publish_state` and **not** a mandatory gate.

When the operator acts on criteria failure, they **SHOULD** use US-017 routes and MAY record `reason` values such as `criteria_failure` in `operator_supervision` history. Absence of a recorded criteria pass does **not** block strategy-driven publication.

## Correction (edit) mechanics

**When:** `publish_state` is `pending` only.

**Route:** `POST /correct-linkedin-variant` with `campaign_id`, `variant`, `draft_content`, optional `reason`, optional `idempotency_key`, `dry_run` (default `true`).

**Mutations:**

1. Atomically writes `linkedin-posts/generated/<campaign_id>/<variant_id>.md`.
2. Updates `derivative_content_sha256` to match new content.
3. Appends `operator_supervision.edit_history[]` with previous and new content hashes.
4. Sets `operator_supervision.last_action` `edit`, `phase` `pre_queue`, `auto_queue_eligible` `true` (correction does not block strategy).

**Dry-run:** Validates eligibility and content change without filesystem or metadata mutation.

## Rejection and cancel: pre-queue vs post-queue

**Route:** `POST /cancel-linkedin-publication` — extended to accept `pending` **and** `queued`.

| Starting `publish_state` | Terminal state | `operator_supervision.cancellation.phase` | `linkedin_publication` |
|--------------------------|----------------|-------------------------------------------|----------------------|
| `pending` | `cancelled` | `pre_queue` | Not set |
| `queued` | `cancelled` | `post_queue` | Preserves existing `cancelled_at` alongside `operator_supervision` |

Cancel sets `operator_supervision.auto_queue_eligible` to `false`.

Cancel does **not** call LinkedIn API. Cancel from `published` fails with `linkedin_publish_cancel_not_allowed`.

## Defer/delay mechanics

**When:** `publish_state` is `pending` only.

**Route:** `POST /defer-linkedin-variant` with `campaign_id`, `variant`, `new_scheduled_at_utc` (strictly in the future), optional `reason`, optional `idempotency_key`, `dry_run` (default `true`).

**Mutations:**

1. Updates variant `scheduled_at_utc` to `new_scheduled_at_utc`.
2. Appends `operator_supervision.deferral_history[]` with previous and new schedule.
3. Sets `operator_supervision.last_action` `defer`, `phase` `pre_queue`, `auto_queue_eligible` `false`.

`publish_state` remains `pending`.

**Calendar follow-up:** Defer does **not** automatically update the editorial calendar. Operators SHOULD reconcile calendar entries manually or via future BL-015 console (follow-up operador/BL-015).

**Campaign aggregate `linkedin_distribution`:** Defer updates per-variant `scheduled_at_utc` only. Campaign-level `linkedin_distribution.scheduled_at_utc` (if present) may become stale until a future reconciliation change — operators should treat variant-level schedule as authoritative for due-time.

## `operator_supervision` metadata contract

Each `variants[]` entry MAY include:

```json
"operator_supervision": {
  "last_action": "edit|defer|cancel",
  "last_action_at_utc": "ISO8601",
  "phase": "pre_queue|post_queue",
  "actor": "operator",
  "reason": "optional string",
  "auto_queue_eligible": true,
  "edit_history": [
    {
      "edited_at_utc": "ISO8601",
      "previous_content_sha256": "hex",
      "new_content_sha256": "hex",
      "reason": "criteria_failure|operator_choice|optional"
    }
  ],
  "deferral_history": [
    {
      "deferred_at_utc": "ISO8601",
      "previous_scheduled_at_utc": "ISO8601",
      "new_scheduled_at_utc": "ISO8601",
      "reason": "optional"
    }
  ],
  "cancellation": {
    "cancelled_at_utc": "ISO8601",
    "phase": "pre_queue|post_queue",
    "reason": "optional"
  },
  "idempotency_proofs": {
    "<idempotency_key>": {
      "action": "edit|defer|cancel",
      "payload_fingerprint": "hex",
      "completed_at_utc": "ISO8601"
    }
  }
}
```

Absent `operator_supervision` ⇒ strategy-driven default for `pending` variants.

## Blocked and invalid actions

| Condition | Error code | `publish_state` unchanged |
|-----------|------------|---------------------------|
| Variant not `pending` for edit/defer | `linkedin_supervision_variant_not_pending` | Yes |
| Variant `published` for cancel | `linkedin_publish_cancel_not_allowed` | Yes |
| Variant `failed` / `cancelled` / other for supervision | `linkedin_supervision_action_not_allowed` | Yes |
| `new_scheduled_at_utc` not strictly in future (defer) | `linkedin_supervision_defer_time_invalid` | Yes |
| Empty or unchanged draft content (edit) | `linkedin_supervision_edit_unchanged` | Yes |
| Same `idempotency_key`, different payload | `linkedin_supervision_idempotency_conflict` | Yes |
| Campaign not `distribution_scheduled` (Flow A) | existing eligibility errors | Yes |
| Artifact missing or hash mismatch | existing schedule/queue errors | Yes |

Supervision endpoints do **not** require `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` (pre-API actions).

## BL-007 auto-queue eligibility (implemented by US-018)

US-018 auto-queue treats a variant as **not eligible** when any of:

- `publish_state` is not `pending` (`failed` is never automatically re-queued; the manual queue endpoint remains available).
- `publish_state` is `cancelled`.
- `operator_supervision.auto_queue_eligible` is `false`, except for the due-time defer rule below.
- `scheduled_at_utc` is after current UTC (`now`).

A variant is **eligible** when `publish_state` is `pending`, not cancelled, `auto_queue_eligible` is not `false`, and `scheduled_at_utc <= now_utc`.

**After defer:** `auto_queue_eligible` remains persisted as `false`. US-018 evaluates `last_action == "defer"` at runtime: once the deferred `scheduled_at_utc <= now`, the variant may be auto-queued without a persisted flip back to `true`. `publish_now` never bypasses a future deferred time. Operators who want a permanent stop must cancel.

**After edit:** `auto_queue_eligible` is set `true` — correction does not block strategy-driven queueing when due.

**After cancel:** `auto_queue_eligible` is `false` permanently for that variant.

Implementation does not imply deploy, workflow activation, or operational validation.

Reference: [bl-007-auto-queue-pending-handoff.md](../product/bl-007-auto-queue-pending-handoff.md).

## Preserved behavior (no duplication)

US-017 does **not** change:

- US-015 policy substance or US-016 criteria substance (cross-links only).
- Flow A ready-path completion, package, or schedule behavior.
- US-011 publication-guard semantics (`distribution_scheduled` ≠ LinkedIn API published; enablement fail-closed on real publish only).
- Post-queue cancel semantics for `queued` → `cancelled` (extended with `operator_supervision`, not replaced).
- ADR-0001 (n8n → worker HTTP only).

## Related documents

- [linkedin-variant-review-policy.md](linkedin-variant-review-policy.md) — US-015 publication and supervision policy
- [linkedin-variant-quality-criteria.md](linkedin-variant-quality-criteria.md) — US-016 quality and differentiation criteria
- [GLOSSARY.md](../GLOSSARY.md) — operator supervision override, `auto_queue_eligible`, supervision window
- [user-stories.md](../product/user-stories.md) — US-017 acceptance criteria
- [silverman-editorial-system.md](../../content-strategy/silverman-editorial-system.md) — `#flow-a-vs-flow-b`, `#linkedin-distribution-strategy`
- [bl-007-auto-queue-pending-handoff.md](../product/bl-007-auto-queue-pending-handoff.md) — construction WIP absorption record
- [backlog.md](../product/backlog.md) — BL-015 supervision console (US-038–US-040)
