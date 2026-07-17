# linkedin-retry-recovery-classification

## ADDED Requirements

### Requirement: Scope, inputs, and boundaries

This capability SHALL define the normative classification of LinkedIn publication outcomes and the safe recovery path per class for the `silverman-blog-linkedin` worker (BL-008 / US-021).

Classification MUST be a deterministic function of evidence already defined by `linkedin-publication-integration` (US-019): the stable error code (`last_error_code` for stored failure evidence; response `errors[]` codes for blocked outcomes) and `http_status` (numeric, or `null` for transport-level failure). The `retryable` boolean remains descriptive evidence and MUST NOT be the sole classification key.

This capability MUST NOT introduce new endpoints, request fields, environment variables, `publish_state` values, or evidence fields, and MUST NOT modify the US-018/US-019/US-020 contracts in `linkedin-publication-integration` — including the no-automatic-retry requirement, the blocked-vs-failed taxonomy, idempotent already-published handling, and the publish-time sequence and cadence guard.

Retry limits, attempt counting, automated retry execution, and evidence preservation across manual re-queue are US-022 concerns and are out of scope.

Manual re-queue via `POST /queue-linkedin-publication` remains the only retry path for `failed` variants.

#### Scenario: Classification derives only from existing evidence

- **WHEN** an operator or future tooling classifies a `failed` variant
- **THEN** the class is determined from the stored `last_error_code` and `http_status` without requiring any new metadata field

#### Scenario: No publication execution behavior changes

- **WHEN** this capability is applied
- **THEN** queue, publish-due, and cancel behavior, stable codes, and evidence shapes remain exactly as defined by `linkedin-publication-integration`, and no automatic retry path exists

### Requirement: Recovery classification of failure outcomes

Every `failed` publication outcome MUST belong to exactly one of these classes:

- **Recoverable (transient)** — `last_error_code` `linkedin_publish_api_error` with numeric `http_status` `429` or `>= 500`. LinkedIn returned an error response, so no post was created; manual re-queue after a waiting period is safe without a verification step.
- **Recoverable after remediation** — `last_error_code` `linkedin_publish_token_invalid` or `linkedin_publish_token_expired` (remediation: token renewal per the token-renewal requirement), or `linkedin_publish_insufficient_permission` (remediation: LinkedIn app scope/product correction followed by reauthorization). Manual re-queue before the remediation completes is not a valid recovery step.
- **Non-recoverable as-is** — `last_error_code` `linkedin_publish_content_invalid` (HTTP `400`/`422`). Re-queueing the unchanged variant is expected to fail again and MUST NOT be presented to the operator as a recovery path. No supported worker path currently exists to correct the content of a `failed` variant; this limitation MUST be documented rather than worked around, and its resolution is deferred to US-022.
- **Uncertain (duplicate risk)** — `last_error_code` `linkedin_publish_api_error` with `http_status` `null` (transport failure or timeout: the post may exist on LinkedIn) or with `http_status` `201` (success response without a usable post identifier: the post very likely exists). Recovery MUST follow the duplicate-prevention requirement before any re-queue.

The classification MUST be documented as a complete table covering all stable failure codes; a failure outcome whose code/status combination is absent from the table MUST be treated as uncertain (fail-safe toward duplicate prevention).

#### Scenario: Transient platform error classified recoverable

- **WHEN** a variant is `failed` with `last_error_code` `linkedin_publish_api_error` and `http_status` `503`
- **THEN** the documented class is recoverable (transient) and the recovery path is manual re-queue via `POST /queue-linkedin-publication` after waiting, with no LinkedIn verification step required

#### Scenario: Token failure classified recoverable after remediation

- **WHEN** a variant is `failed` with `last_error_code` `linkedin_publish_token_invalid` or `linkedin_publish_token_expired`
- **THEN** the documented class is recoverable after remediation and the documented recovery path requires token renewal before manual re-queue

#### Scenario: Content rejection classified non-recoverable as-is

- **WHEN** a variant is `failed` with `last_error_code` `linkedin_publish_content_invalid`
- **THEN** the documented class is non-recoverable as-is, re-queue of the unchanged variant is not presented as recovery, and the missing content-correction path for `failed` variants is documented as a deferred US-022 concern

#### Scenario: Transport failure classified uncertain

- **WHEN** a variant is `failed` with `last_error_code` `linkedin_publish_api_error` and `http_status` `null`
- **THEN** the documented class is uncertain (duplicate risk) and the duplicate-prevention verification procedure applies before any re-queue

#### Scenario: Success without identifier classified uncertain

- **WHEN** a variant is `failed` with `last_error_code` `linkedin_publish_api_error` and `http_status` `201`
- **THEN** the documented class is uncertain (duplicate risk) with the post presumed likely to exist, and the duplicate-prevention verification procedure applies before any re-queue

#### Scenario: Unlisted combination fails safe to uncertain

- **WHEN** a `failed` variant carries a code/status combination not present in the classification table
- **THEN** the operator guidance treats it as uncertain (duplicate risk), requiring verification before re-queue

### Requirement: Blocked outcomes are a separate non-failure class

Blocked outcomes MUST be classified and communicated as **blocked**, distinct from every failure class: publication not enabled (`linkedin_publish_not_enabled`), OAuth reauthorization required or token provider `action_required` (`linkedin_oauth_reauthorization_required` and related), missing token (`linkedin_publish_token_missing`), missing member URN (`linkedin_publish_member_urn_missing`), publish-time guard blocks (`linkedin_publish_blocked_sequence`, `linkedin_publish_blocked_cadence`, `linkedin_publish_blocked_evidence_invalid`), auto-queue skips (`linkedin_publish_auto_queue_skipped_*`), and dry-run outcomes.

Blocked outcomes MUST NOT be described to operators as failures requiring re-queue: the variant's `publish_state` is unchanged (per `linkedin-publication-integration`), no LinkedIn post was attempted, and recovery is resolving the named condition (enable the flag within an approved window, reauthorize, wait out the guard, or complete OAuth setup) and re-running publish-due.

`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` remains fail-closed: this capability MUST NOT define any recovery step that bypasses or weakens the enablement guard.

#### Scenario: Enablement-off communicated as blocked, not failed

- **WHEN** a real publish-due request is rejected with `linkedin_publish_not_enabled`
- **THEN** operator documentation classifies the outcome as blocked, states that no variant became `failed` and no re-queue is needed, and directs recovery through an approved enablement window

#### Scenario: OAuth action-required communicated as blocked with renewal recovery

- **WHEN** publish-due reports `linkedin_oauth_reauthorization_required`
- **THEN** the documented class is blocked, the variant remains `queued`, and the documented recovery is reauthorization followed by re-running publish-due — not re-queue

### Requirement: Token-renewal behavior

Token renewal MUST follow the existing `linkedin-oauth-token-lifecycle` mechanics as the only token recovery paths: automatic refresh-before-publish inside the token provider (skew-based, before a real attempt) and operator browser reauthorization when the provider reports `action_required`.

The worker MUST NOT attempt token refresh or reauthorization as a reaction to a failed publish attempt within the same request; the exactly-one-LinkedIn-API-call-per-variant-per-request contract of `linkedin-publication-integration` is preserved.

For failures classified recoverable after remediation with token codes (`linkedin_publish_token_invalid`, `linkedin_publish_token_expired`), the documented recovery path MUST require confirming token validity (via `GET /linkedin/oauth/status` or documented equivalent) before manual re-queue, so a re-queued variant does not consume a real attempt against a known-bad token.

Token values, refresh tokens, and client secrets MUST NOT appear in any classification documentation, response, or evidence.

#### Scenario: No renewal-and-retry inside a failed request

- **WHEN** a real publish attempt fails with an authentication error from the LinkedIn API
- **THEN** the variant becomes `failed` with the stored evidence, and the worker does not refresh the token and retry within that request

#### Scenario: Token renewal precedes re-queue for token-class failures

- **WHEN** an operator recovers a variant `failed` with `linkedin_publish_token_expired`
- **THEN** the documented procedure verifies OAuth status shows a valid token (renewing or reauthorizing if needed) before calling `POST /queue-linkedin-publication`

### Requirement: Duplicate prevention after timeouts and uncertain outcomes

For a `failed` variant in the uncertain class, the operator MUST verify whether the post exists on LinkedIn (profile feed or activity, matched against the variant and the `last_failed_at` window) before any manual re-queue.

- If the post **exists**, re-queue is forbidden. Recovery MUST be manual evidence repair in `metadata/campaigns/<campaign-id>.json`: set the variant to `publish_state` `published` with the real `linkedin_post_urn` and the UTC ISO8601 `published_at` of the actual publication (cross-checked against LinkedIn), following the same deliberate manual-repair pattern documented for invalid `published_at` evidence under US-020. The worker MUST NOT guess or auto-repair such evidence.
- If the post **does not exist**, manual re-queue via `POST /queue-linkedin-publication` is the documented safe path, after which normal queue → publish-due rules (including the US-020 guard) apply.

The documentation MUST state why blind re-queue of an uncertain outcome is dangerous: a duplicate would not be caught by existing safeguards, because idempotent already-published protection and the cadence guard both key on stored `published_at`/URN evidence that an uncertain outcome never wrote.

This procedure is operator-executed; no automatic LinkedIn read/query integration is introduced.

#### Scenario: Uncertain outcome with existing post repaired, not re-queued

- **WHEN** an operator verifies that a post for a variant `failed` with `http_status` `null` actually exists on LinkedIn
- **THEN** the documented recovery is manual metadata repair to `published` with the real URN and `published_at`, and re-queue is explicitly forbidden for that variant

#### Scenario: Uncertain outcome with confirmed absence re-queued safely

- **WHEN** an operator confirms no matching post exists on LinkedIn for an uncertain-class `failed` variant
- **THEN** the documented recovery is manual re-queue via `POST /queue-linkedin-publication`, and subsequent publication follows the unchanged queue and publish-due contracts

#### Scenario: Repaired evidence re-enters existing safeguards

- **WHEN** an uncertain-class variant is repaired to `published` with a valid `published_at`
- **THEN** the US-020 cadence rule and sequence release apply to that campaign using the repaired evidence, with no spec change to the guard

### Requirement: Operator-visible classification and recovery documentation

Operator documentation MUST present, in the canonical LinkedIn publication operator documentation set:

- the complete classification table (class per stable failure code and `http_status` combination, including the `null` and `201` uncertain cases);
- the recovery path per class, each expressed over existing operations only (`POST /queue-linkedin-publication`, publish-due re-run, OAuth status/reauthorization, manual evidence repair);
- the blocked-vs-failed distinction with the blocked codes listed and the statement that blocked outcomes never change `publish_state`;
- the uncertain-outcome verification procedure as a mandatory pre-re-queue step;
- the explicit boundary statements: no automatic retry exists (retry limits are US-022), and failure-evidence behavior across manual re-queue is a US-022 decision — including the current implementation behavior that re-queueing a `failed` variant clears the stored `linkedin_publication` failure context, which MUST be recorded as a known divergence for US-022 rather than silently relied upon or changed.

Documentation MUST NOT include secret values or variant body text, and MUST use qualified status language (policy defined ≠ operationally validated).

#### Scenario: Operator finds the classification table and recovery paths

- **WHEN** an operator consults the LinkedIn publication documentation after a variant fails
- **THEN** they find the class for the stored `last_error_code`/`http_status`, the corresponding recovery path, and the mandatory verification step for uncertain outcomes

#### Scenario: Evidence-clearing divergence recorded for US-022

- **WHEN** the policy documentation describes manual re-queue of a `failed` variant
- **THEN** it states that current behavior clears stored failure evidence at re-queue time and that preservation or attempt history is an open US-022 decision
