# Proposal: define-linkedin-retry-recovery-classification-us-021

## Why

BL-008 requires safe business rules for handling LinkedIn publication failures and uncertain outcomes. US-019 deliberately recorded failure evidence (`last_error_code`, `last_failed_at`, `retryable`, `http_status`) as **descriptive only** and deferred every normative interpretation — recoverable vs non-recoverable classification, token-renewal behavior on failure, and duplicate prevention after timeouts — to BL-008. Today an operator facing a `failed` variant has evidence but no canonical rule for what is safe to do next: a transport timeout (`http_status: null`) may mean the post **already exists on LinkedIn**, and an uninformed manual re-queue would create a duplicate. US-021 closes that gap with a normative classification and recovery policy.

## Goals

- Classify every LinkedIn publication failure and blocked outcome as **recoverable**, **non-recoverable**, or **uncertain**, as a deterministic function of the existing US-019 evidence fields and stable error codes — no new metadata fields, no reshaped `publish_state` vocabulary.
- Define token-renewal behavior as the recovery path for token-related outcomes: automatic refresh-before-publish and reauthorization remain the only automatic token actions; token renewal is never triggered as a reaction to a failed attempt within the same request.
- Prevent duplicate posts after timeouts and uncertain outcomes: a normative operator verification procedure (check LinkedIn, repair evidence if the post exists, re-queue only when non-existence is confirmed) before the only retry path, manual `POST /queue-linkedin-publication`.
- Make classification and recovery guidance operator-visible in the canonical LinkedIn publication documentation, with clear separation of blocked states (never `failed`) from failure states.

## Non-goals

- **No automatic retry execution.** Retry limits, attempt counting, and any automated retry mechanics are US-022. The no-automatic-retry boundary from `linkedin-publication-integration` is preserved verbatim.
- **No evidence-preservation change on manual re-queue.** The queue service currently clears `linkedin_publication` when re-queueing a `failed` variant; whether attempt history must be preserved is the US-022 "preserve operational evidence" criterion. This change documents the current behavior and defers the normative decision (see Impact).
- **No new endpoints, request fields, `publish_state` values, environment variables, or worker code paths.** This is a documentation/policy + canonical spec change.
- **No reopening of US-018/US-019/US-020 contracts.** BL-007 is closed; references to its capabilities are additive only.
- **No n8n activation, deployment, or live LinkedIn operations.** `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` remains fail-closed and untouched.

## What Changes

- New canonical capability spec defining the recoverable / non-recoverable / uncertain classification of LinkedIn publication outcomes, keyed on the existing stable error codes and US-019 evidence shape (`last_error_code`, `retryable`, `http_status` including its `null`-on-transport-failure semantics, `last_failed_at`).
- Normative token-renewal behavior: which outcomes are recovered by OAuth refresh/reauthorization (`linkedin-oauth-token-lifecycle` mechanics unchanged), and the rule that a `failed` token outcome (`linkedin_publish_token_invalid`, `linkedin_publish_token_expired`) requires token renewal **before** manual re-queue is meaningful.
- Normative duplicate-prevention procedure for uncertain outcomes (transport failure with `http_status: null`; API success without a usable post identifier): operator MUST verify post existence on LinkedIn before re-queue; if the post exists, the recovery is manual evidence repair (US-020 repair pattern), never re-queue.
- Operator documentation: classification table, recovery path per class, and blocked-vs-failed communication guidance added to `docs/deployment/linkedin-publication-prerequisites.md` plus a dedicated policy document under `docs/operations/` (following the US-015/US-016 policy-definition pattern).

## Capabilities

### New Capabilities

- `linkedin-retry-recovery-classification`: Normative classification of LinkedIn publication outcomes (recoverable / non-recoverable / uncertain / blocked), token-renewal recovery behavior, duplicate-prevention rules after timeouts and uncertain outcomes, and operator-visible communication requirements. Consumes US-019 evidence fields read-only; changes no publication execution behavior.

### Modified Capabilities

_None._ `linkedin-publication-integration`, `linkedin-oauth-token-lifecycle`, and the US-020 guard requirements are untouched; their existing BL-008 boundary statements ("classification … are BL-008 concerns") remain accurate and are satisfied, not amended, by the new capability.

## Backlog traceability

- **Backlog item:** BL-008 — Define LinkedIn Retry and Recovery Rules (`docs/product/backlog.md`).
- **User story:** US-021 (story 1) only.
- **Acceptance criteria addressed:**
  - Classify recoverable and non-recoverable errors — classification requirements in the new capability spec.
  - Define token-renewal behavior — token-renewal recovery requirements.
  - Prevent duplicate posts after timeouts — uncertain-outcome verification procedure plus preserved no-automatic-retry and idempotency contracts.
  - The outcome is visible and understandable to the intended user — operator documentation requirements.
  - Failures or blocked states are clearly communicated — blocked-vs-failed communication requirements reusing existing stable codes.
  - Existing completed work is not duplicated or unintentionally changed — no modified capabilities; docs and spec additive only.
- **Acceptance criteria intentionally excluded:** US-022 criteria (retry limits, preserve operational evidence, safe manual intervention mechanics) are out of scope; US-021 explicitly hands the evidence-preservation-on-re-queue decision to US-022.

## Impact

- **Specs:** one new canonical capability (`openspec/specs/linkedin-retry-recovery-classification/` after sync). No deltas to existing capabilities.
- **Code:** none. The worker already provides every input the policy needs (stable codes, US-019 evidence, manual re-queue path, no-auto-retry guarantees). ADR-0001 unaffected — no orchestration change.
- **Docs:** `docs/deployment/linkedin-publication-prerequisites.md` (failure-taxonomy section extended with classification and recovery paths), new `docs/operations/linkedin-retry-recovery-classification.md` policy document, `docs/CURRENT-STATE.md` capability note, product tracking updates only when criteria are demonstrated.
- **Tests:** no executable code changes, so no new pytest modules are required; existing US-018/US-019/US-020 suites must continue to pass unmodified.
- **Known divergence surfaced (not fixed here):** `queue_linkedin_publication` clears stored `linkedin_publication` failure evidence on manual re-queue of a `failed` variant — recorded for the US-022 evidence-preservation decision.
