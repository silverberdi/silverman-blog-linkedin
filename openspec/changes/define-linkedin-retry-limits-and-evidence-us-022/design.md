## Context

US-021 defines a deterministic recovery class from the latest US-019 `linkedin_publication.last_error_code` and `http_status`, but deliberately leaves retry limits and evidence behavior to US-022. The current queue service accepts both `pending` and `failed` variants and unconditionally removes `linkedin_publication` on a real queue, so a manual retry destroys the evidence needed to explain the previous outcome. It also allows unlimited failed-state re-queues.

Existing recovery mechanics are incomplete: `POST /correct-linkedin-variant` accepts only `pending`, while `POST /cancel-linkedin-publication` accepts only `pending` or `queued`. Consequently, `linkedin_publish_content_invalid` is a dead end and an exhausted failed variant cannot be deliberately retired using the existing `cancelled` state.

This is a **hybrid code-and-docs change**. Policy alone cannot meet “set retry limits” or “preserve operational evidence” because the existing worker contradicts those outcomes. The implementation remains inside the existing HTTP worker boundary; ADR-0001 prohibits n8n Execute Command, and no n8n activation or deployment is included.

Stakeholders are the content operator performing recovery and maintainers auditing campaign metadata. Constraints include the US-021 classification, US-019 evidence fields, the US-020 sequence/cadence guard, no automatic retry, no new `publish_state`, fail-closed `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, dry-run defaults, and no secrets, variant body text, or raw LinkedIn responses in evidence.

## Goals / Non-Goals

**Goals:**

- Enforce two manual retries after the initial real API attempt for each variant.
- Preserve every real-attempt outcome and every recovery decision in append-only metadata.
- Make re-queue eligibility depend on the existing US-021 class and explicit evidence of required operator action.
- Support safe correction of content-rejected failed variants and cancellation of failed/exhausted variants through existing endpoints.
- Keep pending queue callers and completed US-018/US-019/US-020 behavior compatible.
- Surface stable reasons and attempt/retry counters in dry-run and real responses.

**Non-Goals:**

- Automatic, scheduled, or background retries.
- A campaign-wide shared retry pool, a new endpoint, a new environment variable, or a new publication state.
- Automated LinkedIn lookup for uncertain outcomes or automated evidence repair when a post exists.
- Token refresh as a reaction within the failed request.
- BL-009 preview validation, BL-012 general campaign recovery, BL-015 UI/console work, n8n activation, deployment, or live validation.

## Decisions

### 1. Limit each variant to three real attempts: one initial attempt plus two manual retries

A real attempt is counted only when the worker calls the LinkedIn publication API. Queue operations, blocked outcomes before that call, OAuth/configuration failures, guard blocks, dry-runs, corrections, cancellations, and manual evidence repair do not increment the count.

There is no independent campaign-wide quota. For a campaign with `N` variants, the maximum is therefore `3N` real attempts, but each variant owns its allowance. This avoids one failing audience variant consuming another's recovery path while still producing a finite campaign bound.

The queue service blocks a failed variant when its real-attempt count is already three, using `linkedin_publish_retry_limit_exhausted`. The publish result that records the third failure reports zero retries remaining, so exhaustion is visible immediately rather than only on a later queue call.

**Alternative considered:** one retry, or a shared campaign quota. One retry is too brittle for separate transient and post-remediation failures; a shared quota couples otherwise independent variants. More than two retries encourages repeated action without diagnosis.

### 2. Keep manual re-queue as the only retry mechanism

`POST /queue-linkedin-publication` remains the sole transition from `failed` back to `queued`. Publish-due and `auto_queue_pending` continue to exclude failed variants. No loop, delayed job, scheduler, or same-request retry is introduced.

**Alternative considered:** automatic retry for 429/5xx. This would modify the canonical no-automatic-retry requirement and blur US-021's operator boundary. It also creates timing and duplicate-control complexity without being required by US-022.

### 3. Add append-only attempt and recovery histories without replacing US-019 latest evidence

Each variant gains two additive metadata collections:

- `linkedin_publication_attempts`: one immutable safe snapshot per real LinkedIn API call. Entries use consecutive `attempt_number`, common `attempted_at`, `outcome` (`published` or `failed`), and `derivative_content_sha256`. A failed entry reuses `last_error_code`, `last_failed_at`, `retryable`, and `http_status`; a successful entry reuses `provider`, `post_urn`, `published_at`, and `http_status`.
- `linkedin_recovery_history`: immutable operator recovery events with consecutive `event_number`, `action`, `recorded_at`, source `attempt_number`, US-021 `classification`, and only action-specific safe details such as confirmation value, previous/new content hashes, or cancellation reason.

The existing `linkedin_publication` object remains the latest outcome for compatibility. Re-queue no longer removes it. A later real attempt replaces that latest object as today while history retains prior outcomes.

For a legacy `failed` variant with no attempt history, the first mutating recovery action synthesizes attempt 1 from its current US-019 evidence and current `derivative_content_sha256` before any correction or re-queue. Missing or invalid mandatory legacy evidence fails closed with `linkedin_publish_recovery_evidence_invalid`; the worker does not invent classification inputs or counts. This lazy migration avoids a bulk metadata rewrite.

Writes use the existing atomic campaign metadata writer. Dry-runs calculate and return the planned counters/actions but write neither history.

**Alternative considered:** retain only the latest failure object or snapshot it only at re-queue. Latest-only still loses older attempts; re-queue-only misses a terminal failure that is never re-queued. Recording at every real outcome gives complete evidence.

### 4. Add one constrained queue confirmation field for failed-state recovery

The existing queue request gains optional `recovery_confirmation` with only:

- `remediation_completed` for US-021 “recoverable after remediation”; and
- `linkedin_post_absence_verified` for US-021 “uncertain”.

Pending queue requests reject the field as inapplicable. Transient failures require no confirmation. An uncertain failure cannot be queued without `linkedin_post_absence_verified`; if the post exists, the unchanged US-021 manual repair-to-`published` procedure applies and queue remains forbidden. Token/permission failures require `remediation_completed`, which is an operator attestation after the documented OAuth status/scope procedure, not a secret or an attempt to perform renewal inside queue.

Every successful failed-state re-queue appends a `manual_requeue` recovery event containing the class and applicable confirmation. The response adds `publication_attempt_count`, `manual_retries_used`, `manual_retries_remaining`, and `recovery_classification`.

**Alternative considered:** separate booleans per class or a new recovery endpoint. A constrained enum avoids contradictory booleans and keeps recovery on the canonical queue path with one additive field.

### 5. Extend correction only for failed content rejection, while keeping the variant failed

`POST /correct-linkedin-variant` continues to support all existing `pending` behavior. It additionally accepts `failed` only when the latest US-021 class is `non-recoverable as-is` with `last_error_code=linkedin_publish_content_invalid`.

The operation atomically updates the artifact and hash, preserves `publish_state=failed`, preserves latest failure and attempt history, and appends both the existing supervision edit evidence and a `content_corrected` recovery event. That event binds `source_attempt_number`, `previous_content_sha256`, and `new_content_sha256`.

Re-queue of a content-invalid failed variant is allowed only when the latest matching correction event refers to the latest failed attempt and its `new_content_sha256` equals the current verified artifact hash. No confirmation enum is needed because the worker has mechanical correction evidence. Unchanged content remains blocked with `linkedin_publish_content_correction_required`.

**Alternative considered:** correction transitions failed to pending. Keeping it failed prevents auto-queue eligibility and makes explicit manual re-queue the authorization boundary, preserving US-021 and US-018 behavior.

### 6. Extend cancellation to failed variants, including exhausted variants

The existing cancel service accepts `failed -> cancelled`, does not call LinkedIn, preserves all publication/attempt evidence, and appends a `recovery_cancelled` event. Existing pending/queued cancellation behavior remains unchanged. This gives the operator a deliberate terminal action without expanding the state vocabulary.

**Alternative considered:** leave failed variants indefinitely or add `abandoned`. Existing `cancelled` already means the operator removed the variant from the publication plan and releases the US-020 sequence, so a new state is unnecessary.

### 7. Consume the US-021 classifier through one shared internal helper

Implementation introduces one internal deterministic helper over `last_error_code` and `http_status`, returning the five existing outcomes: recoverable transient, recoverable after remediation, non-recoverable as-is, uncertain, or blocked where applicable. Queue and failed correction consume it; they do not create a second classification table.

The canonical `linkedin-retry-recovery-classification` spec and operator policy remain the authority. Unlisted combinations fail safe to uncertain. `retryable` remains descriptive only.

### 8. Stable communication and API compatibility

New stable errors are:

- `linkedin_publish_retry_limit_exhausted`
- `linkedin_publish_recovery_confirmation_required`
- `linkedin_publish_recovery_confirmation_invalid`
- `linkedin_publish_content_correction_required`
- `linkedin_publish_recovery_evidence_invalid`

Attempt/retry counters and recovery class are additive nullable fields on queue and per-variant publish results, and on failed-state correction/cancel results where useful. Existing fields and status semantics are retained. Request models remain `extra="forbid"`, all endpoints retain API-key authentication and `dry_run: true` defaults, and no response exposes content or credentials.

### 9. Verification scope

Tests will cover:

- attempt append on success, API failure, transport failure, and success-without-URN;
- two retries allowed and third re-queue blocked, with only real API calls counted;
- no campaign-shared quota and no automatic retry;
- legacy failed evidence normalization and invalid-evidence fail-closed behavior;
- evidence retained byte-for-byte across re-queue and all attempts retained after later failure/success;
- each US-021 class's queue confirmation behavior, including the unlisted→uncertain fallback;
- failed content correction, unchanged-content rejection, explicit subsequent re-queue, and no auto-queue;
- failed/exhausted cancellation preserving evidence;
- dry-run zero mutation, API auth/422 validation, no body text/secrets, and stable response counters;
- unchanged US-018/US-019/US-020 behavior via the existing test suite.

Documentation verification maps these mechanics to all six US-022 acceptance criteria. Implementation does not by itself mark US-022 accepted or BL-008 closed.

## Risks / Trade-offs

- **[Metadata arrays grow over time]** → The hard three-attempt bound limits attempt history; recovery events are similarly bounded by allowed actions and remain small per variant.
- **[Legacy evidence lacks an explicit attempted content hash]** → Lazy normalization captures the verified current hash before the first mutation; invalid or missing US-019 evidence fails closed and requires deliberate manual repair.
- **[Operator confirmation can be inaccurate]** → Use explicit class-specific values, persist the attestation, document the required external check, and never automate uncertain re-queue. The worker cannot independently query LinkedIn in this scope.
- **[Retaining latest failure evidence while state is queued may surprise existing readers]** → Document it as “latest attempt evidence,” expose counters/class in responses, and preserve existing key names rather than relocating them.
- **[Extending correction/cancel state eligibility could affect BL-007 assumptions]** → Changes are additive and limited to `failed`; pending/queued paths and all existing assertions remain intact. Failed correction never makes a variant auto-queueable.
- **[Partial artifact/metadata write during correction]** → Reuse the existing atomic artifact write and campaign metadata patterns; tests cover failure behavior and hash consistency.

## Migration Plan

1. Add the shared classifier, bounded-counter helpers, result fields, and safe history append/legacy-normalization logic.
2. Update real publication outcomes to append attempt evidence before writing campaign metadata.
3. Update failed-state queue validation, confirmation persistence, retry-limit enforcement, and stop deleting `linkedin_publication`.
4. Extend failed content correction and failed cancellation through existing services and routes.
5. Add focused tests, then run the complete existing LinkedIn publication/supervision suites and full pytest because executable code changes.
6. Update operator policy, prerequisites, CURRENT-STATE, and product traceability with qualified “implemented/tested” language only.
7. No deployment or live migration occurs in this change. Existing campaign files migrate lazily on their first failed-state recovery action.

Rollback reverts worker code and docs. Metadata arrays already written are additive and safe for the previous worker to ignore; they MUST NOT be deleted during rollback. A previous worker would again clear latest evidence on re-queue, so operators must not perform failed-state recovery while rolled back.

## Open Questions

None. Operational acceptance and whether the demonstrated US-022 outcome is sufficient to accept US-021 and close BL-008 remain post-implementation review decisions, not design assumptions.
