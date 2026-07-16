# Proposal: store-linkedin-publication-evidence-us-019

## Why

BL-007 story 2 (US-019 — "store the external publication identifier") requires that every successful real LinkedIn publish leaves **complete, consistent evidence** (external identifier + UTC timestamp), that failures after a real API attempt are recorded with a **stable, operator-readable taxonomy**, and that re-runs over already-published variants **observably avoid duplicate posts**. The US-018 slice (validated 2026-07-16, URN `urn:li:share:7483618197204770818`) already stores `linkedin_post_urn`, `published_at`, and `linkedin_publication` failure context — but the canonical spec leaves the evidence contract ambiguous ("`linkedin_post_urn` or `linkedin_post_id`", no required-vs-optional field rule, no normative failure-context shape, no explicit US-019 idempotency-evidence scenarios under the combined auto-queue path). US-019 closes that gap by formalizing the contract so acceptance can be demonstrated and future changes (US-020, BL-008) cannot silently erode the evidence.

## Goals

- Define the **minimum complete publication evidence** per variant after a real successful publish: mandatory fields are `linkedin_post_urn`, `published_at` UTC, and the safe `linkedin_publication` subset including `http_status`; the only optional field is `linkedin_post_id`. `http_status` is **mandatory inside `linkedin_publication` in both success and failure after a real attempt** — numeric when an HTTP response was received, `null` when none was (transport-level failure).
- Make that evidence observable in the `POST /publish-linkedin-due-variants` HTTP response (per-variant results), including under `auto_queue_pending=true`: when a variant results `published` or already-published within an auto-queue scan (including the cross-campaign scan without `campaign_id`), its `auto_queue_results` entry MUST include `linkedin_post_urn` and `published_at`. This only adds optional fields to the US-018 response shape — no breaking change.
- Formalize the **failure taxonomy** in `linkedin_publication` after a real API attempt (`last_error_code`, `last_failed_at`, `retryable`, `http_status`) and the normative distinction between conditions that mark `publish_state=failed` (real API failure / content rejection `linkedin_publish_content_invalid`) and conditions that never do (enablement off, OAuth reauthorization required, member URN missing, token missing).
- Specify US-019 **idempotency evidence**: re-run over a `published` variant preserves URN and `published_at` with no new LinkedIn API call, with stable operator-visible signals (`linkedin_publish_already_published`, `linkedin_publish_auto_queue_skipped_state`).
- Draw the normative **US-019 ↔ BL-008 boundary** in design and specs: evidence completeness + observable idempotency here; recoverable/non-recoverable classification, retry limits, token renewal, and duplicate-after-timeout handling are BL-008.

## Non-Goals

- US-020 (audience cadence/sequence) and closing BL-007.
- BL-008 retry/recovery rules: no retry policy, no `retryable` interpretation rules, no token-renewal behavior, no timeout-duplicate mitigation, no attempt-history preservation model. In particular, the behavior of stored evidence after a manual re-queue of a `failed` variant (preservation, clearing, or attempt history) is explicitly out of scope of US-019 and is a BL-008 normative decision.
- No changes to the per-variant `publish_state` state machine, no renamed fields, no new endpoints, and no changes to the scheduling model or US-017 supervision endpoints. The synced US-018 auto-queue contract is not broken or reshaped — the only touch is the additive optional evidence fields on `auto_queue_results` entries described below.
- No n8n workflow activation, enablement-flag changes, deployment, or operational validation (separate gated steps).

## What Changes

- **Spec formalization (primary):** MODIFY requirements in canonical capability `linkedin-publication-integration` to (a) replace the ambiguous "`linkedin_post_urn` or `linkedin_post_id`" rule with a mandatory/optional evidence field contract, (b) make the failure-context shape and the failed-vs-not-failed condition taxonomy normative, (c) add US-019 idempotency-evidence scenarios covering repeat runs (direct and via `auto_queue_pending`), (d) require `linkedin_post_urn`/`published_at` in `auto_queue_results` entries for published and already-published outcomes, and (e) state the BL-008 exclusion boundary in the spec text.
- **Tests:** add behavioral tests in `tests/test_linkedin_publication.py` asserting evidence completeness after mocked real publish, failure-context shape after mocked API failure (including transport error with null `http_status` and content rejection `linkedin_publish_content_invalid` distinct from generic `linkedin_publish_api_error`), non-failure blocked conditions leaving `publish_state` untouched, preserved URN/`published_at` with zero API calls on re-run, and `linkedin_post_urn`/`published_at` present in `auto_queue_results` entries for published and already-published outcomes.
- **Docs:** update operator documentation to describe the evidence fields and failure taxonomy; update `docs/CURRENT-STATE.md` and product tracking only per demonstrated outcomes.
- **Code (small, additive):** add `linkedin_post_urn` and `published_at` as optional fields (default `None`) to `LinkedInAutoQueueVariantResult` in `linkedin_publication_flow.py`, populated when the publish phase confirms a published or already-published outcome for that variant. This is the only functional code change; it is additive to the synced US-018 auto-queue contract (adds fields only, no rename, no shape break). The evidence-write and failure-context behavior itself requires no code change (design D4).

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `linkedin-publication-integration`:
  - "Per-variant publication metadata fields" — mandatory vs optional evidence fields after real successful publish; normative failure-context shape; explicit no-secrets/no-body-text reaffirmation.
  - "Publish due variants service" — normative failed-vs-not-failed condition taxonomy after a real attempt (delta clarifies, does not contradict, existing scenarios).
  - "HTTP endpoint POST /publish-linkedin-due-variants" — per-variant response evidence fields (`linkedin_post_urn`, `published_at`) required for published and already-published outcomes, including inside `auto_queue_results` under `auto_queue_pending` (cross-campaign scan included).
  - "Auto-queue outcome visibility" — `auto_queue_results` entries for published / already-published variants MUST carry `linkedin_post_urn` and `published_at` (additive fields on the US-018 result shape).
  - "Idempotent published variant on repeat publish-due" — extended with US-019 evidence-preservation scenarios and the explicit BL-008 boundary statement.
  - "Test coverage" — new US-019 evidence/taxonomy/idempotency test bullets.

## Backlog traceability

- **Backlog item:** BL-007 — Implement Scheduled LinkedIn Publication Execution (P2). Remains **open** after this change.
- **User story:** US-019 (story 2 of 3). Acceptance criteria addressed: store the external publication identifier; record failures clearly; avoid retries that could create duplicates; outcome visible/understandable; failures/blocked states clearly communicated; existing completed work not duplicated or changed.
- **Intentionally excluded:** US-018 (already validated — not re-specified), US-020 (cadence/sequence), US-021/US-022 (BL-008 retry/recovery, token renewal, timeout duplicates, retry limits, attempt-history preservation).
- Story/checklist updates occur only after demonstrated outcomes, never at proposal time.

## Impact

- `openspec/changes/store-linkedin-publication-evidence-us-019/specs/linkedin-publication-integration/spec.md` (delta), then sync to `openspec/specs/linkedin-publication-integration/spec.md`.
- `tests/test_linkedin_publication.py` — additive tests only; no weakened assertions.
- `docs/deployment/linkedin-publication-prerequisites.md` (or the operator publication runbook) — evidence/taxonomy documentation.
- `docs/CURRENT-STATE.md` — status update after verification.
- `src/silverman_blog_linkedin/linkedin_publication_flow.py` — **small additive change**: optional `linkedin_post_urn` / `published_at` fields on `LinkedInAutoQueueVariantResult`, populated for published / already-published outcomes under `auto_queue_pending`. `linkedin_client.py` — no expected change; touched only if a spec↔behavior gap is proven by tests.
- ADR-0001 unaffected (worker HTTP only; no n8n Execute Command). Fail-closed enablement guard and dry-run defaults unchanged.
