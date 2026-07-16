## Context

US-015 (`docs/operations/linkedin-variant-review-policy.md`) established Flow A **strategy-driven publication** and the **optional supervision window** while `publish_state` is `pending`. US-016 (`docs/operations/linkedin-variant-quality-criteria.md`) defined quality/differentiation criteria that guide operator action on **criteria failure** — but persistence mechanics were explicitly deferred to US-017.

**Current implementation gap:**

- `cancel_linkedin_publication()` accepts only `queued` → `cancelled`; rejects `pending` with `linkedin_publish_variant_not_queued`.
- No worker route to atomically edit `linkedin-posts/generated/<campaign>/<variant>.md` and update `derivative_content_sha256`.
- No worker route to defer/reschedule `scheduled_at_utc` with audit history.
- Campaign `variants[]` has no `operator_supervision` contract for BL-015 console or BL-007 eligibility.

**Constraints:** ADR-0001 (n8n → worker HTTP only); US-011 publication guard unchanged; no BL-007 WIP merge; no mandatory approval gate; smallest coherent diff.

## Goals / Non-Goals

**Goals:**

- Persist operator edit, reject/cancel, and defer actions during the `pending` supervision window.
- Expose three worker HTTP surfaces: extend cancel + two new routes (correct, defer).
- Record auditable `operator_supervision` metadata on `variants[]`.
- Document BL-007 auto-queue eligibility exclusions (metadata + docs only).
- Provide operator mechanics doc cross-linked from US-015, US-016, GLOSSARY, and user-stories.

**Non-Goals:**

- BL-007 `auto_queue_pending`, publish-pending n8n, deploy scripts.
- BL-015 supervision console (US-038–US-040).
- Flow B mandatory review implementation.
- New `publish_state` values (`deferred`, `rejected`).
- US-016 criteria as automatic queue gates.
- US-011 / enablement changes.
- Rewriting US-015 policy or US-016 criteria substance.

## Decisions

| ID | Question | Decision | Rationale | Rejected alternative |
|----|----------|----------|-----------|---------------------|
| **D1** | New `publish_state` vs parallel metadata? | **Parallel `operator_supervision` object on `variants[]`** — do **not** add `deferred` or `rejected` to `publish_state`. Defer keeps `publish_state` `pending`. Cancel-from-pending sets `publish_state` `cancelled` (same terminal value as post-queue cancel). | Preserves `linkedin-publication-integration` state machine; BL-007 and operators already understand `pending`/`cancelled`. Supervision intent captured in `operator_supervision` without enum churn. | New `publish_state` values — breaks existing specs/tests and conflates editorial defer with technical queue state. |
| **D2** | Edit: filesystem only vs atomic endpoint? | **`POST /correct-linkedin-variant`** atomically writes draft artifact + updates `derivative_content_sha256` + appends `operator_supervision.edit_history[]`. | Single transactional boundary; hash stays consistent for future queue verification; BL-015 console can call one route. | Filesystem-only manual edit — no traceability, hash drift, BL-007 risk. |
| **D3** | Cancel/reject from `pending`: same `cancelled` or distinct value? | **Same `publish_state` `cancelled`** with `operator_supervision.last_action` `cancel` and `operator_supervision.phase` `pre_queue` (post-queue cancel records `phase` `post_queue`). | One terminal state for “will not publish”; phase distinguishes audit context. | Distinct `rejected` state — unnecessary enum; duplicates `cancelled` semantics. |
| **D4** | Defer: mutate `scheduled_at_utc` vs flag only? | **Mutate `scheduled_at_utc`** on `variants[]` + append `operator_supervision.deferral_history[]` + set `operator_supervision.auto_queue_eligible` `false` until `new_scheduled_at_utc <= now_utc`. `publish_state` remains `pending`. | BL-007 can use due-time logic; calendar reflects new schedule; history preserves original timing. | Flag-only `operator_deferred` without schedule change — calendar/BL-007 cannot determine due window. |
| **D5** | BL-007 eligibility exclusions | Variant is **not** auto-queue eligible when any of: `publish_state` ∉ `{pending}` (after failed re-queue rules), `publish_state` `cancelled`, `operator_supervision.auto_queue_eligible` is `false`, or `scheduled_at_utc` > `now_utc`. **Eligible** when `pending`, not cancelled, `auto_queue_eligible` not `false`, and due per schedule. Edit correction sets `auto_queue_eligible` `true` (correction does not block strategy). | Documented contract for BL-007 handoff; no BL-007 code in this change. | Criteria-failure flag blocking queue — contradicts US-015/US-016 (not mandatory gate). |
| **D6** | Idempotency and dry-run | All supervision endpoints default `dry_run: true`. **Idempotency keys** optional per request (`idempotency_key`); replay with same key + same payload returns `completed` without duplicate history entries. Mismatched payload with same key returns validation error. | Matches existing publication endpoint patterns; safe operator rehearsal. | No idempotency — duplicate defer/edit records on retry. |
| **D7** | Extend cancel vs new pre-queue route | **Extend `POST /cancel-linkedin-publication`** to accept `pending` **and** `queued`. Post-queue behavior unchanged. New routes only for edit and defer (distinct payloads). | Cancel semantics unified; one escape hatch name operators learn. | Separate `/reject-linkedin-variant` — route proliferation for same terminal state. |

### `operator_supervision` metadata shape (normative)

Each `variants[]` entry MAY gain:

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
  }
}
```

- Absent `operator_supervision` on a `pending` variant ⇒ strategy-driven default (eligible per D5 when due).
- `criteria_failure` MAY appear in `reason` when operator acts per US-016 guidance — **not** a separate gate field.

### HTTP surface summary

| Route | Action | Valid `publish_state` | Mutations |
|-------|--------|----------------------|-----------|
| `POST /correct-linkedin-variant` | Edit draft | `pending` only | Artifact file, `derivative_content_sha256`, `edit_history` |
| `POST /defer-linkedin-variant` | Defer/reschedule | `pending` only | `scheduled_at_utc`, `deferral_history`, `auto_queue_eligible` |
| `POST /cancel-linkedin-publication` (extended) | Cancel/reject | `pending` or `queued` | `publish_state` → `cancelled`, `cancellation` audit |

### Module layout

- New `linkedin_supervision_flow.py` for `correct_linkedin_variant()` and `defer_linkedin_variant()`.
- Extend `cancel_linkedin_publication()` in `linkedin_publication_flow.py` for `pending` acceptance + `operator_supervision` writes.
- Register routes in `main.py` with API key auth and Pydantic request models.

### Blocked / invalid actions

| Condition | Error code (stable) | `publish_state` unchanged |
|-----------|---------------------|---------------------------|
| Variant not `pending` for edit/defer | `linkedin_supervision_variant_not_pending` | Yes |
| Variant `published` for cancel | `linkedin_publish_cancel_not_allowed` | Yes |
| Variant `failed`/`publishing` for supervision | `linkedin_supervision_action_not_allowed` | Yes |
| `new_scheduled_at_utc` not in future (defer) | `linkedin_supervision_defer_time_invalid` | Yes |
| Empty or unchanged draft content (edit) | `linkedin_supervision_edit_unchanged` | Yes |
| Campaign not `distribution_scheduled` | existing eligibility errors | Yes |
| Hash/artifact path mismatch | existing schedule/queue errors | Yes |

Publication enablement off does **not** block supervision endpoints (supervision is pre-API).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operators confuse `cancelled` pre-queue vs post-queue | `operator_supervision.phase` + mechanics doc table; HTTP response includes `phase` |
| Manual filesystem edit bypasses worker | Mechanics doc states worker routes are canonical; hash mismatch blocks future queue |
| Defer without BL-007 leaves variant `pending` indefinitely | Documented: defer only changes schedule; BL-007 or manual queue still required |
| Extending cancel breaks post-queue tests | Preserve `queued` path verbatim; add `pending` branch with separate audit fields |
| BL-007 WIP conflicts | Explicit non-touch task; no `auto_queue_pending` or publish-due changes |

## Migration Plan

1. Apply docs, delta specs, worker routes, and tests.
2. Existing campaigns without `operator_supervision` remain valid (`pending` = strategy default).
3. Deploy worker; no n8n or enablement changes required for supervision itself.
4. Update CURRENT-STATE / product progress after AC walkthrough; close BL-006 when US-017 demonstrated.

## Open Questions

1. **`linkedin_distribution` aggregate reschedule** — defer updates per-variant `scheduled_at_utc` only; campaign-level `linkedin_distribution.scheduled_at_utc` (if present) updated only when all variants share anchor — document in mechanics; minimal sync if distribution model requires it.
2. **Actor identity** — v1 `actor: "operator"` static string; future BL-015 may add operator id from request header.
3. **Calendar connector refresh** — defer MAY require calendar reconciliation follow-up; out of scope unless calendar spec mandates sync (document as operator follow-up).
