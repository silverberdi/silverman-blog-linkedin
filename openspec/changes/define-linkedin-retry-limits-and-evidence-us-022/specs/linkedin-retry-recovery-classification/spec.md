## MODIFIED Requirements

### Requirement: Scope, inputs, and boundaries

This capability SHALL define the normative classification of LinkedIn publication outcomes and the safe recovery path per class for the `silverman-blog-linkedin` worker (BL-008 / US-021), plus the bounded retry, evidence-preservation, and safe manual-intervention policy for BL-008 / US-022.

Classification MUST remain a deterministic function of evidence already defined by `linkedin-publication-integration` (US-019): the stable error code (`last_error_code` for stored failure evidence; response `errors[]` codes for blocked outcomes) and `http_status` (numeric, or `null` for transport-level failure). The `retryable` boolean remains descriptive evidence and MUST NOT be the sole classification key.

US-022 MUST consume the US-021 classes unchanged and MUST NOT introduce automatic retry, background retry, a new endpoint, a new environment variable, or a new `publish_state`. It MAY add the minimum request and evidence fields needed to enforce manual recovery safely. It MUST preserve the US-018/US-019/US-020 contracts in `linkedin-publication-integration`, including blocked-vs-failed taxonomy, idempotent already-published handling, the publish-time sequence/cadence guard, and the fail-closed `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` guard.

Manual re-queue via `POST /queue-linkedin-publication` MUST remain the only retry path for `failed` variants.

#### Scenario: Recovery continues to use US-021 classification

- **WHEN** a failed variant is evaluated for US-022 recovery
- **THEN** its class is determined from stored `last_error_code` and `http_status` under the existing US-021 table, including the unlisted-combination fail-safe to uncertain

#### Scenario: No automatic publication behavior is introduced

- **WHEN** this capability is applied
- **THEN** no failed variant is retried within the same request, by a background job, or by auto-queue, and only an explicit queue request can authorize another attempt

### Requirement: Operator-visible classification and recovery documentation

Operator documentation MUST present, in the canonical LinkedIn publication operator documentation set:

- the complete US-021 classification table (class per stable failure code and `http_status` combination, including the `null` and `201` uncertain cases);
- the recovery path per class, including required confirmation and correction mechanics under US-022;
- the blocked-vs-failed distinction with the blocked codes listed and the statement that blocked outcomes never change `publish_state` or consume an attempt;
- the uncertain-outcome verification procedure as a mandatory pre-re-queue step;
- the explicit no-automatic-retry boundary;
- the limit of two manual retries after the initial real attempt, the exact counting rules, the per-variant and derived campaign bounds, and the exhaustion outcome;
- the append-only attempt/recovery evidence contract and legacy failed-evidence normalization rule;
- the supported failed-content correction and failed-state cancellation procedures;
- the meaning of every confirmation value and stable recovery error.

Documentation MUST NOT include secret values or variant body text, and MUST use qualified status language that distinguishes proposed, implemented, tested, deployed, and operationally validated states.

#### Scenario: Operator can determine the next safe action

- **WHEN** an operator consults the LinkedIn publication documentation after a variant fails
- **THEN** they can find its US-021 class, attempts and retries remaining, required confirmation or correction, exhaustion behavior, and the evidence that will be retained

## ADDED Requirements

### Requirement: Per-variant retry budget and counting

Each LinkedIn variant MUST permit at most two manual retries after its initial real LinkedIn API attempt, for at most three real attempts total.

Only a call to the LinkedIn publication API counts as a real attempt. Queue operations, dry-runs, blocked outcomes where no LinkedIn call occurs, OAuth/configuration failures before the call, sequence/cadence/evidence guard blocks, content correction, cancellation, and manual evidence repair MUST NOT consume the retry budget.

The retry budget MUST be per variant. There MUST NOT be a separate shared campaign quota: for a campaign with `N` variants, the derived maximum is `3N` real attempts, and one variant MUST NOT consume another variant's allowance.

After three recorded attempts, manual re-queue MUST fail with `linkedin_publish_retry_limit_exhausted`, leave metadata and `publish_state` unchanged, and communicate zero retries remaining. The third failed publication result MUST itself communicate exhaustion.

#### Scenario: Two manual retries are allowed

- **WHEN** a variant has one initial failed real attempt and then fails after its first manually authorized retry
- **THEN** one further manual re-queue is allowed and the operator sees two retries used or available according to the response counters

#### Scenario: Third re-queue is blocked

- **WHEN** a failed variant already has three real attempts
- **THEN** queue fails with `linkedin_publish_retry_limit_exhausted`, reports zero retries remaining, writes no metadata, and makes no LinkedIn call

#### Scenario: Blocked request consumes no attempt

- **WHEN** publish-due is blocked before the LinkedIn API call by enablement, OAuth, sequence, cadence, invalid evidence, timing, or dry-run
- **THEN** the publication attempt count and retries remaining are unchanged

#### Scenario: Variants do not share a retry pool

- **WHEN** one campaign variant exhausts all three real attempts and another variant has made only its initial attempt
- **THEN** the second variant retains both of its manual retries

### Requirement: Append-only publication attempt evidence

Every real LinkedIn API call MUST append exactly one immutable entry to the variant's `linkedin_publication_attempts` array. Entries MUST have consecutive positive `attempt_number`, UTC `attempted_at`, `outcome` (`failed` or `published`), and the attempted `derivative_content_sha256`.

A failed attempt entry MUST reuse the US-019 fields `last_error_code`, `last_failed_at`, `retryable`, and nullable `http_status`. A successful attempt entry MUST reuse `provider`, `post_urn`, `published_at`, and numeric `http_status`. Entries MUST NOT contain secrets, variant body text, or raw LinkedIn response bodies.

The existing `linkedin_publication` object MUST remain the latest-outcome evidence contract. Re-queue MUST NOT remove it. A later outcome MAY replace the latest object only after its predecessor is retained in attempt history.

For a legacy `failed` variant without attempt history, the first mutating failed-state recovery action MUST normalize the current US-019 failure object into attempt 1, using `last_failed_at` as `attempted_at` and the current verified `derivative_content_sha256`, before any correction or re-queue mutation. If mandatory evidence is absent or invalid, recovery MUST fail closed with `linkedin_publish_recovery_evidence_invalid` without inventing evidence.

#### Scenario: Failure then success retains both attempts

- **WHEN** an initial real attempt fails, the operator safely re-queues, and the second real attempt succeeds
- **THEN** attempt history contains immutable failed attempt 1 and published attempt 2 while `linkedin_publication` contains the latest success evidence

#### Scenario: Re-queue preserves latest failure context

- **WHEN** a failed variant is re-queued in real mode
- **THEN** its `linkedin_publication.last_error_code`, `http_status`, `last_failed_at`, and `retryable` remain available and the corresponding attempt-history entry is unchanged

#### Scenario: Legacy failure normalizes before correction

- **WHEN** a legacy failed content-invalid variant has valid US-019 evidence but no attempt history and an operator performs a real correction
- **THEN** the worker first records the original failure and original content hash as attempt 1, then records the correction without changing that attempt

#### Scenario: Invalid legacy evidence fails closed

- **WHEN** a legacy failed variant lacks a mandatory US-019 field needed to classify or count it
- **THEN** failed-state recovery returns `linkedin_publish_recovery_evidence_invalid` and changes neither artifact nor metadata

### Requirement: Append-only recovery action evidence

Every successful mutating action on a `failed` variant MUST append an immutable event to `linkedin_recovery_history` with consecutive positive `event_number`, UTC `recorded_at`, `action`, source `attempt_number`, and the US-021 `classification`.

A manual re-queue event MUST record any required `recovery_confirmation`. A failed-content correction event MUST record previous and new content hashes. A failed-state cancellation event MUST record its reason when supplied. Recovery history MUST NOT contain secrets, variant body text, or raw LinkedIn responses.

Dry-run MUST return planned action and counters without appending history.

#### Scenario: Uncertain re-queue records verification attestation

- **WHEN** an uncertain outcome is re-queued with `linkedin_post_absence_verified`
- **THEN** recovery history records a `manual_requeue` event tied to the failed attempt, classed uncertain, with that confirmation value

#### Scenario: Dry-run records no recovery event

- **WHEN** any failed-state queue, correction, or cancellation is run with `dry_run: true`
- **THEN** no recovery-history event is written and no existing event is changed

### Requirement: Class-specific manual re-queue authorization

Failed-state queue MUST enforce the existing US-021 class:

- recoverable transient outcomes require no confirmation;
- recoverable-after-remediation outcomes require `recovery_confirmation=remediation_completed`;
- uncertain outcomes require `recovery_confirmation=linkedin_post_absence_verified`;
- non-recoverable-as-is content outcomes require mechanically recorded correction after the latest failed attempt and MUST NOT accept unchanged content.

`recovery_confirmation` MUST be rejected for a normal `pending` queue request and when its value does not match the failed variant's class. Missing required confirmation MUST return `linkedin_publish_recovery_confirmation_required`; mismatched or inapplicable confirmation MUST return `linkedin_publish_recovery_confirmation_invalid`; missing content correction MUST return `linkedin_publish_content_correction_required`.

If an uncertain post is found on LinkedIn, re-queue MUST remain forbidden and the US-021 manual evidence repair to `published` with real URN and `published_at` MUST remain the recovery path.

#### Scenario: Transient failure needs no confirmation

- **WHEN** a failed variant is classified recoverable transient and is below its retry limit
- **THEN** manual queue may proceed without `recovery_confirmation`

#### Scenario: Token remediation requires confirmation

- **WHEN** a failed variant is classified recoverable after remediation
- **THEN** queue is blocked until the operator supplies `recovery_confirmation=remediation_completed` after completing the documented remediation

#### Scenario: Uncertain absence requires confirmation

- **WHEN** a failed variant is classified uncertain and the operator has verified no matching LinkedIn post exists
- **THEN** queue requires `recovery_confirmation=linkedin_post_absence_verified` and persists that attestation

#### Scenario: Unchanged rejected content remains blocked

- **WHEN** a content-invalid failed variant has no correction event tied to its latest failed attempt
- **THEN** queue fails with `linkedin_publish_content_correction_required` and leaves the variant failed

### Requirement: Safe correction and cancellation of failed variants

The existing correction operation MUST accept a failed variant only when its latest evidence class is non-recoverable as-is and `last_error_code` is `linkedin_publish_content_invalid`. It MUST atomically update the artifact and `derivative_content_sha256`, retain `publish_state=failed`, retain all publication evidence, and record a `content_corrected` recovery event tied to the latest failed attempt. It MUST NOT queue, auto-queue, or publish the corrected variant.

The existing cancel operation MUST accept `failed -> cancelled`, including after retry exhaustion. It MUST preserve publication and recovery evidence, record a `recovery_cancelled` event, make no LinkedIn call, and use the existing `cancelled` state so the US-020 sequence remains released.

#### Scenario: Content-invalid failure is corrected but not queued

- **WHEN** an operator performs a real correction with changed content on a failed `linkedin_publish_content_invalid` variant
- **THEN** the artifact/hash and audit evidence are updated, `publish_state` remains `failed`, and a separate explicit queue request is still required

#### Scenario: Other failed class cannot use failed-content correction

- **WHEN** correction is requested for a failed transient, remediation, or uncertain outcome
- **THEN** correction fails with a stable supervision action error and changes neither artifact nor metadata

#### Scenario: Exhausted failed variant can be cancelled

- **WHEN** an operator cancels a failed variant with zero retries remaining
- **THEN** it moves to existing state `cancelled`, retains every attempt and recovery event, and no LinkedIn call occurs

### Requirement: US-022 acceptance traceability and completion boundary

Implementation and documentation MUST map evidence to every US-022 acceptance criterion: retry limits, preserved operational evidence, safe manual intervention, understandable outcomes, clear failures/blocks, and no duplication or unintended changes to completed work.

US-022 and BL-008 MUST remain open until the intended-user outcome is demonstrated and reviewed. Code completion, tests, or policy publication alone MUST NOT be represented as operational validation, story acceptance, or BL-008 closure.

#### Scenario: Implementation does not prematurely close BL-008

- **WHEN** worker code, tests, and documentation are complete but no acceptance review has approved the business outcome
- **THEN** progress documentation keeps US-022 unaccepted and BL-008 open with qualified implemented/tested status
