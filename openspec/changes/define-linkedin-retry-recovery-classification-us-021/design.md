# Design: define-linkedin-retry-recovery-classification-us-021

## Context

BL-007 (closed) delivered publication execution with a deliberate boundary: US-019 records failure evidence (`last_error_code`, `last_failed_at`, `retryable`, `http_status`) as descriptive data, `linkedin-publication-integration` forbids automatic retry, and both specs name BL-008 as the owner of interpretation. The worker today:

- maps LinkedIn HTTP outcomes to stable codes in `linkedin_client._map_http_status` (401 → `linkedin_publish_token_invalid`, 403 → `linkedin_publish_insufficient_permission`, 400/422 → `linkedin_publish_content_invalid`, 429/5xx → `linkedin_publish_api_error` with `retryable: true`, transport failure → `linkedin_publish_api_error` with `http_status: null`, 201 without a post URN → `linkedin_publish_api_error` with `http_status: 201`);
- keeps blocked conditions (`linkedin_publish_not_enabled`, OAuth `action_required`, missing token/URN, guard blocks) out of `failed` entirely;
- accepts `failed` alongside `pending` in `QUEUE_ELIGIBLE_PUBLISH_STATES`, so `POST /queue-linkedin-publication` is already the manual re-queue path;
- clears the stored `linkedin_publication` failure context when re-queueing (evidence behavior US-019 explicitly left undecided).

US-021 must classify these outcomes and define safe recovery without adding retry execution (US-022 owns retry limits) and without regressing the US-018/US-019/US-020 contracts.

Stakeholders: content operator (sole consumer of the policy), future US-022 implementation (consumes the classification).

## Goals / Non-Goals

**Goals**

- Deterministic classification of every publication outcome into recoverable / non-recoverable / uncertain (failure classes) plus blocked (non-failure class), computed only from existing evidence fields and stable codes.
- Normative token-renewal behavior tied to the existing `linkedin-oauth-token-lifecycle` mechanics.
- Normative duplicate-prevention procedure for uncertain outcomes before any manual re-queue.
- Operator-visible documentation of classes, recovery paths, and blocked-vs-failed communication.

**Non-Goals**

- No automatic retry, retry limits, attempt counters, or background recovery (US-022).
- No change to `publish_state` vocabulary, evidence field names/types, endpoints, request fields, env vars, or worker code.
- No decision on evidence preservation across manual re-queue (documented divergence handed to US-022).
- No n8n activation, deployment, or live publication.

## Decisions

### D1 — Policy as canonical spec + operator docs, zero code

The classification is normative documentation: a new canonical capability spec plus operator-facing docs. No worker change computes or stores a classification value.

*Rationale:* every input the policy needs is already emitted and stored (stable codes, `http_status` incl. `null` semantics, `retryable`). Persisting a derived `recovery_class` would duplicate information, touch the US-019 evidence shape the guardrails freeze, and prejudge US-022's implementation. *Alternative considered:* add a `recovery_class` field to failure evidence and HTTP results — rejected as spec-vocabulary reshaping without a driving requirement; US-022 can introduce it if retry limits need machine-readable state.

### D2 — Four classes keyed on `last_error_code` + `http_status`, not on `retryable` alone

| Class | Outcomes | Recovery path |
|---|---|---|
| **Recoverable** | `linkedin_publish_api_error` with numeric `http_status` 429 or ≥ 500 (transient platform errors; LinkedIn returned an error response, so no post was created) | Wait, then manual re-queue via `POST /queue-linkedin-publication`; no verification step required |
| **Recoverable after remediation** | `linkedin_publish_token_invalid`, `linkedin_publish_token_expired` (token renewal required); `linkedin_publish_insufficient_permission` (LinkedIn app scope/product remediation + reauthorization required) | Complete the named remediation first; only then is manual re-queue meaningful |
| **Non-recoverable as-is** | `linkedin_publish_content_invalid` (400/422 — same content will be rejected again) | Re-queue without content change is unsafe/pointless; content remediation for a `failed` variant has no supported worker path today (documented limitation, candidate US-022 concern) |
| **Uncertain (duplicate risk)** | `linkedin_publish_api_error` with `http_status: null` (transport failure/timeout — post may exist) and with `http_status: 201` (success response without usable URN — post very likely exists) | Mandatory operator verification on LinkedIn before any re-queue (D4) |

*Rationale:* `retryable` alone cannot drive the policy — it is `true` for both the safe transient class and the duplicate-risk uncertain class. The code+status pair is already stored, stable, and unambiguous. *Alternative:* classify on `retryable` — rejected, conflates duplicate-risk timeouts with safe 429/5xx retries, which is exactly the duplicate hazard US-021 must prevent.

Blocked outcomes (`linkedin_publish_not_enabled`, `linkedin_oauth_reauthorization_required` and related `action_required`, `linkedin_publish_token_missing`, `linkedin_publish_member_urn_missing`, guard reasons `linkedin_publish_blocked_*`, dry-run) form a separate **blocked** communication class: not failures, no `publish_state` change, no re-queue involved; recovery is resolving the named condition and re-running publish-due. This restates the US-019 blocked-vs-failed taxonomy without modifying it.

### D3 — Token renewal is a precondition, never a reaction

Token-renewal behavior is defined entirely by existing `linkedin-oauth-token-lifecycle` mechanics: refresh-before-publish inside the token provider (skew-based) and browser reauthorization when the provider reports `action_required`. Two normative statements are added on top: (a) the worker MUST NOT attempt token renewal as a reaction to a failed publish attempt within the same request (preserves single-API-call US-019 contract); (b) for token-class failures, renewal MUST precede manual re-queue — re-queueing with a known-bad token is a wasted real attempt that writes new failure evidence. *Alternative:* renew-and-retry inside the publish request on 401 — rejected: it is automatic retry execution (US-022 territory) and violates the exactly-one-API-call contract.

### D4 — Duplicate prevention for uncertain outcomes = verify, then repair or re-queue

For an uncertain-class `failed` variant the operator MUST, before re-queue: check the LinkedIn profile/activity for a post matching the variant within the attempt window (`last_failed_at`).

- **Post exists:** the publication actually succeeded; recovery is manual evidence repair in `metadata/campaigns/<campaign-id>.json` — set `publish_state` `published` with the real URN and UTC `published_at` (same deliberate manual-repair pattern US-020 documents for invalid `published_at`). Re-queue is forbidden: it would create a duplicate post, and the US-020 cadence guard cannot catch it because no `published_at` evidence exists yet.
- **Post absent:** manual re-queue is safe; normal queue → publish-due flow resumes.

*Rationale:* the worker cannot resolve uncertainty itself without a LinkedIn read API (not in scope, would need new integration surface). Operator verification is the smallest safe mechanism and matches the existing manual-repair precedent. *Alternative:* query LinkedIn for recent posts before re-queue — rejected: new API surface, new scopes, out of documentation/policy scope.

### D5 — Surface, don't fix, the evidence-clearing divergence

`queue_linkedin_publication` pops `linkedin_publication` when re-queueing a `failed` variant, so classification evidence is lost at re-queue time. US-019 explicitly declared this neither authorized nor prohibited. This change records the behavior as a documented divergence feeding the US-022 "preserve operational evidence" criterion; it does not change the queue service. *Alternative:* preserve evidence now — rejected: code change beyond documentation/policy scope and pre-empts US-022's attempt-history design.

## Risks / Trade-offs

- [Policy without enforcement: an operator can still blind-re-queue an uncertain variant] → The procedure is normative in canonical spec and stated at the exact operator touchpoint (`linkedin-publication-prerequisites.md` re-queue section); US-022 may add mechanical guards (e.g., confirmation flag) on top of this classification.
- [Classification table drifts from `_map_http_status` if codes change later] → The spec keys classes on stable codes already frozen by `linkedin-publication-integration`; any future code change requires an OpenSpec change that must reconcile both capabilities.
- [`content_invalid` recovery dead-end (no correction path for `failed` variants)] → Documented explicitly as a limitation with the safe interim answer (do not re-queue unchanged content); scoped as a US-022 candidate, not silently invented here.
- [Evidence cleared on re-queue weakens post-hoc traceability] → Divergence recorded in CURRENT-STATE and handed to US-022 rather than hidden.

## Migration Plan

Documentation/spec-only: no deploy, no env change, no data migration. Rollout order: delta spec + policy doc land together; `docs/CURRENT-STATE.md` gains the policy-defined entry (mirroring the US-015/US-016 "policy defined" pattern); progress tracking updated only for criteria actually demonstrated. Rollback = revert the docs/spec commit; no runtime state involved.

## Open Questions

- None blocking. Two questions are explicitly parked for US-022: (1) preserve or snapshot failure evidence across manual re-queue; (2) whether a supported content-correction path for `failed` variants (or a `failed` → cancel path) is needed to make `linkedin_publish_content_invalid` recoverable.
