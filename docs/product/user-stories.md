# User Stories by Backlog Item

Each backlog item is decomposed into business-focused user stories. Stories describe user or operator outcomes, not implementation design.

## BL-001 — Automate Live Blog Publication

**Priority:** P1

**Business context:** Eliminate the manual Git commit and push step required after the worker writes the blog post and image to the public repository checkout.

### US-001 — Automate Live Blog Publication: Story 1

**Description**

As a content operator, I want to validate the generated blog post and image before publication, so that flow a can move a validated post from the public checkout to the live site without manual git intervention.

**Acceptance criteria**

- [x] Validate the generated blog post and image before publication.
- [x] Create a controlled commit in the public blog repository.
- [x] Push the approved commit to the remote repository.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

### US-002 — Automate Live Blog Publication: Story 2

**Description**

As a content operator, I want to confirm that the content becomes available on the live site, so that flow a can move a validated post from the public checkout to the live site without manual git intervention.

**Acceptance criteria**

- [x] Confirm that the content becomes available on the live site.
- [x] Prevent duplicate commits and duplicate publication attempts.
- [x] Handle remote divergence and publication conflicts safely.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

## BL-002 — Validate the First Real LinkedIn Publication

**Priority:** P1

**Business context:** Prove that the implemented LinkedIn integration can publish one real post safely and capture the resulting publication identifier.

### US-003 — Validate the First Real LinkedIn Publication: Story 1

**Description**

As a content operator, I want to validate oauth credentials and the member identity, so that one linkedin variant is published successfully, traceably, and without duplicate side effects.

**Acceptance criteria**

- [x] Validate OAuth credentials and the member identity.
- [x] Select one approved LinkedIn variant.
- [x] Move the variant through pending, queued, publishing, and published states.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-11 — [phase3-us003 report](../operations/phase3-us003-linkedin-publication-validation-2026-07-11.md) (`executive-recruiter` on bounded-context campaign).

### US-004 — Validate the First Real LinkedIn Publication: Story 2

**Description**

As a content operator, I want to store the linkedin post urn, so that one linkedin variant is published successfully, traceably, and without duplicate side effects.

**Acceptance criteria**

- [x] Store the LinkedIn post URN.
- [x] Confirm the post is visible on LinkedIn.
- [x] Prevent duplicate publication.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-11 — URN stored; operator confirmed visibility; idempotent rerun passed. Article image preview not validated (BL-009).

### US-005 — Validate the First Real LinkedIn Publication: Story 3

**Description**

As a content operator, I want to restore publication safeguards after the controlled test, so that one linkedin variant is published successfully, traceably, and without duplicate side effects.

**Acceptance criteria**

- [x] Restore publication safeguards after the controlled test.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-11 — `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` restored in `.env` and worker after validation window.

## BL-003 — Correct LinkedIn Status Summary in the Editorial Calendar

**Priority:** P1

**Business context:** Remove incomplete calendar summaries caused by mismatched LinkedIn package and distribution status fields.

### US-006 — Correct LinkedIn Status Summary in the Editorial Calendar: Story 1

**Description**

As a content operator, I want to show the actual package-generation status, so that the calendar accurately reflects package and scheduling status for completed campaigns.

**Acceptance criteria**

- [x] Show the actual package-generation status.
- [x] Show the actual distribution-scheduling status.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-15 — unit tests plus operational smoke on `192.168.0.194`: reconcile-close of `2026-07-10-a-bounded-context-is-not-a-folder` persisted `linkedin_package_status=completed` and `linkedin_distribution_status=completed` from `package_status: generated` / `distribution_id`; remaining legacy null rows operator-patched once. Deploy `BUILD_REVISION=1784088086`.

### US-007 — Correct LinkedIn Status Summary in the Editorial Calendar: Story 2

**Description**

As a content operator, I want to keep completed campaign facts immutable, so that the calendar accurately reflects package and scheduling status for completed campaigns.

**Acceptance criteria**

- [x] Keep completed campaign facts immutable.
- [x] Preserve reconciliation idempotency.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-15 — unit tests for conflict/idempotency/repair; operational reconcile-close closed scheduled item to completed without republish/package/schedule/lifecycle side effects (`execution_status=reconciled`, `calendar_update_status=reconciled`).

### US-008 — Correct LinkedIn Status Summary in the Editorial Calendar: Story 3

**Description**

As a content operator, I want to avoid changing unrelated campaign or calendar data, so that the calendar accurately reflects package and scheduling status for completed campaigns.

**Acceptance criteria**

- [x] Avoid changing unrelated campaign or calendar data.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-15 — unit tests preserve notes/unrelated fields; operational smoke preserved item notes on reconcile-close and touched only LinkedIn summary fields (plus required completion canonical fields) without Flow A republish/package/schedule/lifecycle.

## BL-004 — Activate Flow A Orchestration in n8n

**Priority:** P1

**Business context:** Move Flow A from manually triggered orchestration to a controlled, scheduled n8n workflow.

### US-009 — Activate Flow A Orchestration in n8n: Story 1

**Description**

As a content operator, I want to identify the canonical flow a workflow, so that flow a runs on schedule through n8n without duplicate processing or unintended publication.

**Acceptance criteria**

- [x] Identify the canonical Flow A workflow.
- [x] Confirm correct import and configuration.
- [x] Define execution frequency.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-15 — [us-009 validation report](../operations/us-009-canonical-flow-a-n8n-identity-validation-2026-07-15.md). Workflow inactive; proposed schedule 09:00 UTC docs-only. LinkedIn flag temporarily `false` for verify, then restored `true` per operator.

### US-010 — Activate Flow A Orchestration in n8n: Story 2

**Description**

As a content operator, I want to activate the workflow, so that flow a runs on schedule through n8n without duplicate processing or unintended publication.

**Acceptance criteria**

- [x] Activate the workflow.
- [x] Prevent duplicate or concurrent processing.
- [x] Validate restart and recovery behavior.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-15 — [us-010 activation validation](../operations/us-010-flow-a-n8n-activation-validation-2026-07-15.md). Server `active: true`, Schedule `0 9 * * *` UTC, single-flight skip + TTL recovery with empty ready. Repo export remains `active: false`. Not BL-005.

### US-011 — Activate Flow A Orchestration in n8n: Story 3

**Description**

As a content operator, I want to keep linkedin publication disabled until separately approved, so that flow a runs on schedule through n8n without duplicate processing or unintended publication.

**Acceptance criteria**

- [x] Keep LinkedIn publication disabled until separately approved.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-15 — [us-011 LinkedIn publication-guard validation](../operations/us-011-linkedin-publication-guard-validation-2026-07-15.md). Baseline `true` → temporary `false` → fail-closed `linkedin_publish_not_enabled` → restore `true`. Flow A has no LinkedIn API nodes/paths. Not permanent LinkedIn-off. At US-011 close, BL-005 was still open (closed separately 2026-07-16).

## BL-005 — Run a Fully Unattended Flow A Test

**Priority:** P1

**Business context:** Demonstrate that a new approved blog post can move through Flow A without technical intervention.

### US-012 — Run a Fully Unattended Flow A Test: Story 1

**Description**

As a content operator, I want to accept a new markdown post from the ready folder, so that a new post completes the full unattended flow a path with traceable evidence.

**Acceptance criteria**

- [x] Accept a new Markdown post from the ready folder.
- [x] Generate and validate the image.
- [x] Publish the blog post to the live site.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-15/16 — Manual Post A + Schedule Post B. Evidence: [bl-005 validation](../operations/bl-005-unattended-flow-a-validation-2026-07-15.md). Not LinkedIn API publish.

### US-013 — Run a Fully Unattended Flow A Test: Story 2

**Description**

As a content operator, I want to generate linkedin variants, so that a new post completes the full unattended flow a path with traceable evidence.

**Acceptance criteria**

- [x] Generate LinkedIn variants.
- [x] Schedule distribution.
- [x] Complete the source lifecycle.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-15/16 — both campaigns `flow_a_complete` with package + staggered schedule + processed sources. Evidence: [bl-005 validation](../operations/bl-005-unattended-flow-a-validation-2026-07-15.md).

### US-014 — Run a Fully Unattended Flow A Test: Story 3

**Description**

As a content operator, I want to complete campaign and calendar records, so that a new post completes the full unattended flow a path with traceable evidence.

**Acceptance criteria**

- [x] Complete campaign and calendar records.
- [x] Require no technical intervention during execution.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-15/16 — campaign + calendar completed for both posts; Schedule fire unattended (no mid-run intervention); post-Pages-lag resume between executions only (same US-002 pattern as Post A). Evidence: [bl-005 validation](../operations/bl-005-unattended-flow-a-validation-2026-07-15.md). BL-006 closed; BL-007 closed 2026-07-17.

## BL-006 — Define the LinkedIn Variant Review Process

**Priority:** P2

**Business context:** Establish a clear business process for reviewing, approving, rejecting, or retaining generated LinkedIn variants.

### US-015 — Define the LinkedIn Variant Review Process: Story 1

**Description**

As a content operator, I want to define whether all variants may eventually be published, so that each linkedin variant has a clear review decision and publication purpose.

**Policy artifact:** [linkedin-variant-review-policy.md](../operations/linkedin-variant-review-policy.md)

**Acceptance criteria**

- [x] Define whether all variants may eventually be published.
- [x] Define when review is mandatory.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-16 — US-015 policy defined (docs/spec); BL-006 remains open until US-016 and US-017.

### US-016 — Define the LinkedIn Variant Review Process: Story 2

**Description**

As a content operator, I want to establish quality and differentiation criteria, so that each linkedin variant has a clear review decision and publication purpose.

**Policy artifact:** [linkedin-variant-review-policy.md](../operations/linkedin-variant-review-policy.md)

**Criteria artifact:** [linkedin-variant-quality-criteria.md](../operations/linkedin-variant-quality-criteria.md)

**Acceptance criteria**

- [x] Establish quality and differentiation criteria.
- [x] Associate each variant with an audience and objective.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-16 — US-016 criteria defined (docs/spec + campaign `variants[]` `objective` metadata); BL-006 remains open until US-017.

### US-017 — Define the LinkedIn Variant Review Process: Story 3

**Description**

As a content operator, I want to support correction or rejection before queueing, so that each linkedin variant has a clear review decision and publication purpose.

**Mechanics artifact:** [linkedin-variant-supervision-mechanics.md](../operations/linkedin-variant-supervision-mechanics.md)

**Acceptance criteria**

- [x] Support correction or rejection before queueing.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-16 — US-017 supervision mechanics implemented (worker routes + docs + tests); BL-006 closed when combined with US-015 and US-016.

## BL-007 — Implement Scheduled LinkedIn Publication Execution

**Priority:** P2

**Business context:** Publish due LinkedIn variants automatically according to the approved editorial schedule.

**Implementation handoff:** Construction WIP for opt-in `auto_queue_pending` on `POST /publish-linkedin-due-variants` exists locally (not on `main`, not OpenSpec-approved). Absorb under this backlog item — see [bl-007-auto-queue-pending-handoff.md](bl-007-auto-queue-pending-handoff.md). Do not mark US-018–US-020 complete from that WIP alone.

### US-018 — Implement Scheduled LinkedIn Publication Execution: Story 1

**Description**

As a content operator, I want to identify due variants, so that due variants are published once, in order, with complete publication evidence.

**Acceptance criteria**

- [x] Identify due variants.
- [x] Move only eligible variants to queued state.
- [x] Publish each variant once.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

**Validated:** 2026-07-16 — deploy `BUILD_REVISION=c7bce02` on `192.168.0.194`; dry-run smoke with zero campaign mutation; controlled real window published `engineering-leadership` of `flow-a-2026-07-06-why-i-did-not-start-with-the-database` once (URN `urn:li:share:7483618197204770818`), repeat run idempotent. Evidence: [us-018 validation](../operations/us-018-scheduled-linkedin-publication-validation-2026-07-16.md).

### US-019 — Implement Scheduled LinkedIn Publication Execution: Story 2

**Status:** Accepted (operationally validated 2026-07-17).

**Description**

As a content operator, I want to store the external publication identifier, so that due variants are published once, in order, with complete publication evidence.

**Acceptance criteria**

- [x] Store the external publication identifier. — Unit/integration: `test_us019_complete_evidence_after_real_publish_success`, `test_us019_response_carries_evidence_for_published_and_already_published`, `test_us019_auto_queue_results_carry_evidence_including_cross_campaign_scan`; operator contract in [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md#publication-evidence-and-failure-taxonomy-us-019). Operational: real publish wrote URN `urn:li:share:7483704861348519936` with `linkedin_publication.http_status=201`.
- [x] Record failures clearly. — Demonstrated: `test_us019_failure_context_shape_api_and_transport_errors`, `test_us019_content_rejection_uses_dedicated_stable_code`, `test_us019_success_without_post_identifier_treated_as_failure`.
- [x] Avoid retries that could create duplicates. — Unit: `test_us019_idempotency_preserves_evidence_across_rerun_modes`, `test_us019_no_automatic_retry_after_failed_real_attempt`. Operational: replay warned `linkedin_publish_already_published` with identical URN/`published_at`.
- [x] The outcome is visible and understandable to the intended user. — Response `results[]` / `auto_queue_results[]` carry `linkedin_post_urn` / `published_at`; dry-run published skips surfaced preserved evidence.
- [x] Failures or blocked states are clearly communicated. — Unit failure/blocked tests; operational cadence/sequence blocks left `publish_state` non-`published` with null URN.
- [x] Existing completed work is not duplicated or unintentionally changed. — Existing US-018 auto-queue path preserved; enablement baseline unchanged.

**Validated:** 2026-07-17 — deploy `BUILD_REVISION=3c4d9f5` on `192.168.0.194`; controlled real publish of `executive-recruiter` on `flow-a-2026-07-10-deferring-is-not-avoiding-it-can-be-architecture` with complete success evidence; replay idempotent. Evidence: [us-019/us-020 validation](../operations/us-019-us-020-linkedin-publication-validation-2026-07-17.md).

### US-020 — Implement Scheduled LinkedIn Publication Execution: Story 3

**Status:** Accepted (operationally validated 2026-07-17). **BL-007 closed.**

**Description**

As a content operator, I want to respect audience cadence and sequence, so that due variants are published once, in order, with complete publication evidence.

**Acceptance criteria**

- [x] Respect audience cadence and sequence. — Unit suite (`test_us020_*`); operator contract in [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md#publish-time-sequence-and-cadence-guard-us-020). Operational: dry-run + real `linkedin_publish_blocked_cadence`; real `linkedin_publish_auto_queue_skipped_sequence`; post-publish cadence after sequence release.
- [x] The outcome is visible and understandable to the intended user. — Distinct stable reasons in dry-run and real responses; blocking vs releasing table in docs.
- [x] Failures or blocked states are clearly communicated. — Unit: failed/cancelled release, evidence fail-closed, cross-campaign independence. Operational: cadence/sequence blocks without LinkedIn calls and without falsely marking `published`.
- [x] Existing completed work is not duplicated or unintentionally changed. — US-018/US-019 paths preserved; dry-run zero campaign mutation (`dbb07a527033e277…`).

**Validated:** 2026-07-17 — same deploy/window as US-019. Evidence: [us-019/us-020 validation](../operations/us-019-us-020-linkedin-publication-validation-2026-07-17.md).

## BL-008 — Define LinkedIn Retry and Recovery Rules

**Priority:** P2

**Business context:** Create safe business rules for handling LinkedIn publication failures and uncertain outcomes.

### US-021 — Define LinkedIn Retry and Recovery Rules: Story 1

**Status:** Accepted (policy defined 2026-07-16; uncertain-class classification and duplicate-prevention procedure operationally exercised 2026-07-17; operator-accepted 2026-07-17). Evidence: [us-021/us-022 validation](../operations/us-021-us-022-linkedin-retry-recovery-validation-2026-07-17.md).

**Description**

As a content operator, I want to classify recoverable and non-recoverable errors, so that linkedin failures can be recovered without losing traceability or duplicating content.

**Policy artifact:** [linkedin-retry-recovery-classification.md](../operations/linkedin-retry-recovery-classification.md)

**Acceptance criteria**

- [x] Classify recoverable and non-recoverable errors. — Spec requirement "Recovery classification of failure outcomes" (`linkedin-retry-recovery-classification`); classification table keyed on `last_error_code` + `http_status` (incl. `null` and `201`; unlisted combinations fail safe to uncertain) in [linkedin-retry-recovery-classification.md](../operations/linkedin-retry-recovery-classification.md) and summarized in [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md#retry-and-recovery-classification-us-021).
- [x] Define token-renewal behavior. — Spec requirement "Token-renewal behavior": existing OAuth refresh/reauthorization mechanics as only token recovery paths; never a reaction within a failed request; renewal precedes manual re-queue for token-class failures.
- [x] Prevent duplicate posts after timeouts. — Spec requirement "Duplicate prevention after timeouts and uncertain outcomes": mandatory operator verification on LinkedIn before re-queue of uncertain outcomes; post exists → manual evidence repair to `published` (re-queue forbidden); post absent → manual re-queue safe. Defined policy only — no automatic mechanism added.
- [x] The outcome is visible and understandable to the intended user. — Spec requirement "Operator-visible classification and recovery documentation": policy document plus classification summary and verification step at the manual re-queue touchpoint in the prerequisites doc.
- [x] Failures or blocked states are clearly communicated. — Spec requirement "Blocked outcomes are a separate non-failure class": blocked codes listed with no-`publish_state`-change statement and per-condition recovery, distinct from the four failure classes.
- [x] Existing completed work is not duplicated or unintentionally changed. — No modified capabilities; zero changes under `src/`, `tests/`, `n8n/`, `deploy/`; US-018/US-019/US-020 contracts referenced additively (BL-007 stays closed).

**Defined:** 2026-07-16 — US-021 policy defined (docs + canonical spec); acceptance criteria demonstrated at policy-definition scope only, not operationally validated. Known divergence recorded for US-022 (manual re-queue of a `failed` variant cleared stored `linkedin_publication` failure evidence) — resolved by the US-022 implementation: re-queue now preserves evidence.

### US-022 — Define LinkedIn Retry and Recovery Rules: Story 2

**Status:** Accepted (operationally validated 2026-07-17 on `192.168.0.194`, `BUILD_REVISION=d15d85b`; operator-accepted 2026-07-17). **BL-008 closed.** Primary recovery chain demonstrated end-to-end on a real variant (controlled transport failure → `uncertain` classification → guardrail rejections → attested re-queue → successful retry with append-only evidence → idempotent replay); correction/cancellation/exhaustion paths remain at unit-test scope. Evidence: [us-021/us-022 validation](../operations/us-021-us-022-linkedin-retry-recovery-validation-2026-07-17.md).

**Description**

As a content operator, I want to set retry limits, so that linkedin failures can be recovered without losing traceability or duplicating content.

**Policy artifact:** [linkedin-retry-recovery-classification.md](../operations/linkedin-retry-recovery-classification.md) (US-022 sections)

**Acceptance criteria** (demonstrated at implemented + unit-test scope only)

- [x] Set retry limits. — Per-variant budget of 3 real LinkedIn API attempts (initial + 2 manual retries); only real API calls count (dry-runs, queue ops, blocked outcomes, corrections, cancellations never consume); no shared campaign pool; exhausted re-queue fails with `linkedin_publish_retry_limit_exhausted`. Unit evidence: `test_us022_two_manual_retries_allowed_third_requeue_blocked`, `test_us022_blocked_dry_run_and_queue_operations_consume_no_attempts`, `test_us022_variants_do_not_share_campaign_retry_pool`, `test_us022_no_automatic_retry_and_failed_excluded_from_auto_queue`.
- [x] Preserve operational evidence. — Append-only `linkedin_publication_attempts` (one immutable entry per real API call) and `linkedin_recovery_history` (one event per mutating failed-state action); re-queue no longer clears `linkedin_publication` (US-021 divergence resolved); legacy failed variants lazily normalized, invalid evidence fails closed (`linkedin_publish_recovery_evidence_invalid`). Unit evidence: `test_us022_failure_then_success_retains_both_attempts`, `test_us022_requeue_preserves_latest_failure_context`, `test_us022_legacy_failed_variant_normalizes_on_first_requeue`, `test_us022_invalid_legacy_evidence_fails_closed`.
- [x] Support safe manual intervention. — Class-aware re-queue confirmations (`remediation_completed`, `linkedin_post_absence_verified`), content correction of failed content-invalid variants via `POST /correct-linkedin-variant` (stays `failed`, never auto-queued), `failed → cancelled` with full evidence preservation and no LinkedIn call. Unit evidence: `test_us022_class_specific_requeue_authorization`, `test_us022_correct_failed_content_invalid_keeps_failed_and_audits`, `test_us022_cancel_exhausted_failed_variant_preserves_all_evidence`, `test_cancel_failed_variant_now_supported_preserves_evidence`.
- [x] The outcome is visible and understandable to the intended user. — Additive `publication_attempt_count` / `manual_retries_used` / `manual_retries_remaining` on queue and per-variant publish results, `recovery_classification` on failed-state results; operator procedures with per-class HTTP examples in [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md#retry-recovery-classification-and-bounded-manual-retry-us-021--us-022). Unit evidence: `test_us022_queue_endpoint_exposes_counters_and_requires_auth`, `test_us022_pending_queue_reports_zero_counters_and_no_class`.
- [x] Failures or blocked states are clearly communicated. — Stable codes `linkedin_publish_retry_limit_exhausted`, `linkedin_publish_recovery_confirmation_required` / `_invalid`, `linkedin_publish_content_correction_required`, `linkedin_publish_recovery_evidence_invalid`; unknown `recovery_confirmation` values → HTTP 422; third failed publish reports zero retries remaining. Unit evidence: `test_us022_class_specific_requeue_authorization`, `test_us022_queue_endpoint_rejects_unknown_confirmation_with_422`.
- [x] Existing completed work is not duplicated or unintentionally changed. — No new endpoints/env vars/`publish_state` values; enablement guard fail-closed; US-018/US-019/US-020 suites pass unmodified except two assertions superseded by the approved failed-cancellation contract; full pytest green (1033 passed). BL-007 unchanged.

**Implemented:** 2026-07-16 — worker code + unit suites (`tests/test_linkedin_publication.py`, `tests/test_linkedin_supervision_flow.py`); acceptance demonstrated at implemented/unit-test scope only. Story acceptance and BL-008 closure require a separate business review and operational validation.

## BL-009 — Validate LinkedIn Article Preview Rendering

**Priority:** P2

**Business context:** Confirm that LinkedIn renders the expected title, description, image, and link preview.

### US-023 — Validate LinkedIn Article Preview Rendering: Story 1

**Status:** Accepted (operationally validated 2026-07-17 on `192.168.0.194`, `BUILD_REVISION=d15d85b`; operator-accepted 2026-07-17).

**Description**

As a content operator, I want to verify title and description, so that published linkedin posts display the intended article preview.

**Operator procedure:** [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md#article-preview-input-verification-us-023)

**Acceptance criteria**

- [x] Verify title and description. — Unit: `test_full_pass_all_checks`, `test_checkout_title_and_description_mismatch`, `test_og_per_field_mismatch_codes`, `test_og_whitespace_normalization_passes` (`tests/test_linkedin_preview_validation.py`). Operational: real `og_description_mismatch` detected on both 2026-07-15 campaigns, remediated (blog template commit `e4d10de`), re-verified passing against the live site.
- [x] Verify image availability. — Unit: `test_public_image_unreachable`, `test_public_image_not_image_content_type`. Operational: missing `og:image` detected on live pages (`og_tags_missing`), remediated, passing after remediation; `public_image_availability` HTTPS 2xx `image/*` confirmed.
- [x] The outcome is visible and understandable to the intended user. — Unit: `test_endpoint_dry_run_defaults_true_and_returns_structured_response`, `test_dry_run_leaves_campaign_document_byte_identical`, `test_real_run_persists_evidence_and_changes_no_other_field`. Operational: structured `status`/`checks{}`/`codes[]` responses; real runs persisted `linkedin_article_preview_validation` evidence (`validated_at` 2026-07-17T18:11Z).
- [x] Failures or blocked states are clearly communicated. — Unit: `test_unreachable_public_url_is_not_reported_as_mismatch`, `test_blocked_campaign_not_found_makes_no_http_calls`, `test_blocked_package_not_generated_makes_no_http_calls`, `test_multi_failure_single_pass_reports_all_codes`. Operational: stable codes `linkedin_preview_validation_og_tags_missing` + `linkedin_preview_validation_og_description_mismatch` reported on a real failure.
- [x] Existing completed work is not duplicated or unintentionally changed. — Unit: existing suites unmodified (full pytest 1058 passed at implementation). Operational: dry-run campaign documents byte-identical (sha256); real runs changed only the evidence block; zero LinkedIn API calls.

**Validated:** 2026-07-17 — deploy `BUILD_REVISION=d15d85b` on `192.168.0.194`; real failure detection → live-site remediation (`silverberdi.github.io` commit `e4d10de`: `og:image`, description source, canonical site url) → passing dry-run and real runs with persisted evidence on `flow-a-2026-07-15-keep-contracts-boring` and `flow-a-2026-07-15-search-is-not-one-model`. Evidence: [us-023 validation](../operations/us-023-linkedin-preview-input-validation-2026-07-17.md). Validated ≠ US-024 rendering confirmation: passing means the inputs LinkedIn scrapes are correct.

### US-024 — Validate LinkedIn Article Preview Rendering: Story 2

**Status:** Accepted (operationally demonstrated 2026-07-17 on a real campaign; operator-accepted 2026-07-17). No worker code: US-024 is an operator procedure + evidence-capture story (docs + canonical procedure-spec only).

**Description**

As a content operator, I want to confirm preview behavior on linkedin, so that published linkedin posts display the intended article preview.

**Operator procedure:** [linkedin-preview-rendering-confirmation.md](../operations/linkedin-preview-rendering-confirmation.md)

**Acceptance criteria**

- [x] Confirm preview behavior on LinkedIn. — Demonstrated 2026-07-17 via the post-publish observation point: real post `urn:li:share:7483953784612786177` (`keep-contracts-boring :: executive-recruiter`) observed against recorded `article_preview` metadata; no article card rendered. Pre-publish Post Inspector attempt honestly recorded as `confirmation_blocked` (tool unavailable — app crash across browsers). Evidence: [blocked attempt](../operations/us-024-preview-confirmation-blocked-2026-07-17.md), [post-publish confirmation](../operations/us-024-preview-confirmation-keep-contracts-boring-2026-07-17.md).
- [x] Identify cache or metadata issues. — Demonstrated via the decision matrix: US-023 `passed` (real run `2026-07-17T18:11:32Z`) × no card observed → `preview_not_rendered_post_format` (not cache, not inputs). The earlier same-day US-023 failure (`og_tags_missing`, `og_description_mismatch`) exercised the `preview_inputs_incorrect` remediation loop end-to-end before any LinkedIn observation.
- [x] The outcome is visible and understandable to the intended user. — Two completed evidence records using the fixed outcome vocabulary (`confirmation_blocked`, `preview_not_rendered_post_format`) and the per-confirmation template (campaign id, `public_url`, US-023 run reference, UTC timestamps, outcome label, operator).
- [x] Failures or blocked states are clearly communicated. — Post Inspector outage recorded as `confirmation_blocked` with the named condition and next action, never guessed as a confirmation and never recorded as an input or rendering failure.
- [x] Existing completed work is not duplicated or unintentionally changed. — Zero changes under `src/`, `tests/`, `n8n/`, `deploy/`; campaign metadata never edited by confirmation recording; publication evidence untouched.

**Demonstrated:** 2026-07-17 — procedure executed end-to-end on a real campaign with completed evidence records; the fallback reaction to `preview_not_rendered_post_format` is US-025 scope.

### US-025 — Validate LinkedIn Article Preview Rendering: Story 3

**Status:** Accepted (operationally demonstrated 2026-07-17 on a real campaign; operator-accepted 2026-07-17). **BL-009 closed.** No worker code: US-025 is an operator fallback-policy story (docs + canonical procedure-spec only). Demonstrated business outcome caveat: the v1 text post renders no article card — accepted per policy; `content.article` remains a named deferred future-change candidate.

**Description**

As a content operator, I want to define a fallback when the preview is incorrect, so that published linkedin posts display the intended article preview.

**Operator policy:** [linkedin-preview-fallback-policy.md](../operations/linkedin-preview-fallback-policy.md)

**Acceptance criteria**

- [x] Define a fallback when the preview is incorrect. — Policy defined (canonical spec `linkedin-article-preview-fallback` + [policy doc](../operations/linkedin-preview-fallback-policy.md)) and demonstrated 2026-07-17: recorded triggering US-024 outcome (`preview_not_rendered_post_format` on `keep-contracts-boring`) → post-publish default decision **accept and record** executed with zero endpoint calls → completed evidence record with fixed label `fallback_accept_rendering`; escalation recorded as `fallback_format_change_deferred` naming the `content.article` future-change preconditions. Evidence: [us-025 fallback decision](../operations/us-025-preview-fallback-decision-keep-contracts-boring-2026-07-17.md).
- [x] The outcome is visible and understandable to the intended user. — Demonstrated: completed per-decision evidence records using the fixed vocabulary and template (campaign id, variant `publish_state`, US-024/US-023 references, action + classification, endpoint calls (none), resulting state, outcome label, operator + UTC timestamp).
- [x] Failures or blocked states are clearly communicated. — The blocked-state discipline was exercised upstream in the same demonstration chain: the Post Inspector outage was recorded as `confirmation_blocked` (US-024) with named condition and next action rather than improvising a fallback without a recorded trigger.
- [x] Existing completed work is not duplicated or unintentionally changed. — Demonstrated: campaign document sha256 unchanged by the decision; `publication_attempt_count`/`manual_retries_used` unchanged (zero retry-budget consumption); no `recovery_confirmation` used; publication evidence untouched; guard/cadence/idempotency contracts unmodified.

**Demonstrated:** 2026-07-17 — fallback decision executed end-to-end on a real campaign with completed evidence records. BL-009 closure requires US-023, US-024, and US-025 to be accepted.

## BL-010 — Add Operational Observability

**Priority:** P3

**Business context:** Provide a consolidated view of Flow A execution health and campaign status.

### US-026 — Add Operational Observability: Story 1

**Status:** Accepted (operator-accepted 2026-07-17 on `192.168.0.194`,
`BUILD_REVISION=b67c538` after controlled live smoke of
`GET /flow-a/operational-status`). Evidence:
[flow-a-operational-status.md](../operations/flow-a-operational-status.md).

**Description**

As a system operator, I want to identify successful and failed executions, so that operators can understand system health and campaign progress from one clear operational view.

**Acceptance criteria**

- [x] Identify successful and failed executions. — Live smoke: 46 successful / 0 failed persisted runs in one authenticated response (`now_utc=2026-07-17T22:55:00Z`).
- [x] Identify blocked or stale campaigns. — Live smoke: 6 campaigns with `failed_campaigns=1`, `blocked_campaigns=1`, `stale_campaigns=0`, `in_progress_campaigns=1`, `successful_campaigns=4`.
- [x] Show delayed calendar items. — Live smoke: `delayed_calendar_items` present (count 0 at observation instant; field and summary exposed).
- [x] The outcome is visible and understandable to the intended user. — Demonstrated: consolidated JSON with counts, LinkedIn publish_state breakdown, and secret-safe campaign/run summaries; no raw multi-file inspection required.
- [x] Failures or blocked states are clearly communicated. — Live smoke: `status=partial` with 16 `data_issues`; failed/blocked campaign counts and `github_pages_checkout` dependency failure for an existing failed campaign.
- [x] Existing completed work is not duplicated or unintentionally changed. — Live smoke: byte-for-byte zero mutation across 128 editorial files; auth 401; invalid `now_utc` 422; deterministic repeat GET.

### US-027 — Add Operational Observability: Story 2

**Status:** Accepted (operator-accepted 2026-07-17 on `192.168.0.194`,
`BUILD_REVISION=b67c538` after controlled live smoke of
`GET /flow-a/operational-status`). Evidence:
[flow-a-operational-status.md](../operations/flow-a-operational-status.md).

**Description**

As a system operator, I want to capture stage duration, so that operators can understand system health and campaign progress from one clear operational view.

**Acceptance criteria**

- [x] Capture stage duration. — Live smoke: `summary.stage_durations` reported `campaigns_with_stage_durations=6`, `executions_with_duration=46`, `stage_intervals_reported=47`; all 6 campaigns included `stage_durations`.
- [x] Surface failures by external dependency. — Live smoke: top-level `dependency_failures` and summary buckets; `github_pages_checkout` count 1 with `blog_publish_target_exists`.
- [x] Allow status review without opening multiple raw files. — Demonstrated: single authenticated GET returns executions, campaigns, calendar delay, stage durations, and dependency buckets together.
- [x] The outcome is visible and understandable to the intended user. — Demonstrated: whole-second durations and named dependency buckets in the same response as US-026 classifications.
- [x] Failures or blocked states are clearly communicated. — Live smoke: dependency failure entry names campaign id and error codes; `data_issues` counted in summary.
- [x] Existing completed work is not duplicated or unintentionally changed. — Live smoke: zero mutation; no alert ledger write; no external integration calls as part of status.

## BL-011 — Add Operational Alerts

**Priority:** P3

**Business context:** Notify the operator when the system requires attention.

### US-028 — Add Operational Alerts: Story 1

**Status:** Accepted (operator-accepted 2026-07-17 on `192.168.0.194`, `BUILD_REVISION=b67c538` after controlled live smoke). Evidence: [flow-a-operational-alerts.md](../operations/flow-a-operational-alerts.md).

**Description**

As a system operator, I want to alert on items moved to error, so that important failures and blocked states generate timely, actionable alerts.

**Acceptance criteria**

- [x] Alert on items moved to error. — Demonstrated via controlled fixtures and live smoke: failed campaigns with `source_file_status.location=error` produce `item_moved_to_error` from `POST /flow-a/operational-alerts/evaluate` (live evaluate returned this type from existing evidence).
- [x] Alert on image-generation failure. — Demonstrated: `comfyui` / `blog_image_generation_*` dependency evidence produces `image_generation_failure` (controlled fixtures).
- [x] Alert on blog publication failure. — Demonstrated: `blog_publish_*` / `blog_git_publication_*` codes produce `blog_publication_failure`; LinkedIn-preview checkout codes are excluded (fixtures + live smoke returned this type).
- [x] The outcome is visible and understandable to the intended user. — Demonstrated: secret-safe alert objects include type, severity, fingerprint, identifiers, codes, dependency, and short summary.
- [x] Failures or blocked states are clearly communicated. — Demonstrated: evaluate responses label alert types and emission status (`not_requested` / `disabled` / `misconfigured` / emitted); evaluate-only leaves lifecycle bytes unchanged.
- [x] Existing completed work is not duplicated or unintentionally changed. — Demonstrated: derivation reuses operational-status evidence; evaluate-only and emit paths do not mutate campaign/run/editorial lifecycle.

### US-029 — Add Operational Alerts: Story 2

**Description**

As a system operator, I want to alert on partial calendar execution, so that important failures and blocked states generate timely, actionable alerts.

**Status:** Accepted (operator-accepted 2026-07-17 on `192.168.0.194`, `BUILD_REVISION=b67c538` after controlled live smoke + prior fixture demonstration). Evidence: [flow-a-operational-alerts.md](../operations/flow-a-operational-alerts.md).

**Acceptance criteria**

- [x] Alert on partial calendar execution. — Demonstrated via controlled fixtures: delayed calendar items produce `partial_calendar_execution` (severity `warning`, reason `calendar_item_past_due`, `calendar_item_id`; titles omitted) from `POST /flow-a/operational-alerts/evaluate`.
- [x] Alert on LinkedIn token or publication failure. — Demonstrated: `linkedin` dependency-bucket / LinkedIn progress `failure_codes` produce `linkedin_token_or_publication_failure` (`dependency=linkedin`, severity `error`); preview checkout codes excluded.
- [x] Alert on stale campaigns. — Demonstrated: campaigns with `stale=true` produce `stale_campaign` (severity `warning`).
- [x] The outcome is visible and understandable to the intended user. — Demonstrated: structured alert type, severity, fingerprint, safe identifiers, codes/reasons, and short summaries without secrets or content bodies; eight-type `summary.counts` on live evaluate.
- [x] Failures or blocked states are clearly communicated. — Demonstrated: severity differentiation (`warning` vs `error`); emission status remains explicit when emit is requested (`disabled` on live fail-closed smoke).
- [x] Existing completed work is not duplicated or unintentionally changed. — Demonstrated: reuses operational-status evidence and the US-028 evaluate/emit path; evaluate-only zero lifecycle mutation; US-028 types still produced on live smoke.

### US-030 — Add Operational Alerts: Story 3

**Status:** Accepted (operator-accepted 2026-07-17 on `192.168.0.194`, `BUILD_REVISION=b67c538` after controlled live smoke). **BL-011 closed 2026-07-17.** Evidence: [flow-a-operational-alerts.md](../operations/flow-a-operational-alerts.md).

**Description**

As a system operator, I want to alert on unhealthy worker or failed n8n workflow, so that important failures and blocked states generate timely, actionable alerts.

**Acceptance criteria**

- [x] Alert on unhealthy worker or failed n8n workflow. — Demonstrated: degraded folder readiness produces `unhealthy_worker` (fixtures); live report ingest produced `failed_n8n_workflow`; failed runs alone do not; healthy live folders correctly yield `unhealthy_worker=0`.
- [x] The outcome is visible and understandable to the intended user. — Demonstrated: secret-safe alert objects include type, severity, fingerprint, `workflow_id` / optional `execution_id`, sorted reason codes, and short summaries; eight-type `summary.counts`.
- [x] Failures or blocked states are clearly communicated. — Demonstrated: evaluate responses label alert types and emission status; report returns structured acknowledgment; evaluate-only leaves lifecycle bytes unchanged; live emit fail-closed → `disabled`.
- [x] Existing completed work is not duplicated or unintentionally changed. — Demonstrated: reuses evaluate/emit/ledger; US-028 types still produced on live smoke; no BL-015 UI; no parallel alerts channel.

**Follow-ups (completed 2026-07-17):** production webhook enablement (`SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED=true`, internal `http://n8n:5678/webhook/silverman-flow-a-operational-alerts`); n8n Error Trigger → `report-orchestration-failure` via `silvermanFlowAErrorReport01` as Flow A `errorWorkflow`; daily evaluate/emit schedule `silvermanFlowAAlertsEvaluate01`.

## BL-012 — Consolidate Recovery for Incomplete Campaigns

**Priority:** P3

**Business context:** Provide a consistent recovery model for campaigns that stop before completion.

### US-031 — Consolidate Recovery for Incomplete Campaigns: Story 1

**Description**

As a system operator, I want to identify the last valid stage, so that incomplete campaigns can be resumed or repaired safely and predictably.

**Status:** Implemented, automated-tested, deployed (`BUILD_REVISION=018aa36` on `192.168.0.194`), and acceptance criteria validated against fixture evidence (2026-07-18). **BL-012 closed 2026-07-18**. Evidence: [bl-012 acceptance](../operations/bl-012-incomplete-campaign-recovery-acceptance-2026-07-18.md), [flow-a-incomplete-campaign-recovery.md](../operations/flow-a-incomplete-campaign-recovery.md).

**Acceptance criteria**

- [x] Identify the last valid stage.
- [x] Resume without repeating successful work.
- [x] Repair inconsistent metadata.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

### US-032 — Consolidate Recovery for Incomplete Campaigns: Story 2

**Description**

As a system operator, I want to classify recovery actions, so that incomplete campaigns can be resumed or repaired safely and predictably.

**Status:** Implemented, automated-tested, deployed (`BUILD_REVISION=018aa36` on `192.168.0.194`), and acceptance criteria validated against fixture evidence (2026-07-18). **BL-012 closed 2026-07-18**. Evidence: [bl-012 acceptance](../operations/bl-012-incomplete-campaign-recovery-acceptance-2026-07-18.md), [flow-a-incomplete-campaign-recovery.md](../operations/flow-a-incomplete-campaign-recovery.md).

**Acceptance criteria**

- [x] Classify recovery actions.
- [x] Preserve attempt history.
- [x] Support safe cancellation when recovery is not appropriate.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

## BL-013 — Validate Concurrency and Duplicate Execution Protection

**Priority:** P3

**Business context:** Ensure that simultaneous or repeated triggers cannot process the same content twice.

### US-033 — Validate Concurrency and Duplicate Execution Protection: Story 1

**Description**

As a system operator, I want to prevent duplicate post processing, so that concurrent triggers do not create duplicate artifacts or external publications.

**Status:** Implemented, automated-tested, acceptance criteria validated against fixture evidence (2026-07-18), and **deployed** on `192.168.0.194` (`BUILD_REVISION=018aa36`). **BL-013 closed 2026-07-18**. See [flow-a-concurrency-duplicate-execution-protection-us-033.md](../operations/flow-a-concurrency-duplicate-execution-protection-us-033.md).

**Acceptance criteria**

- [x] Prevent duplicate post processing.
- [x] Prevent duplicate image generation.
- [x] Prevent duplicate blog publication.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

### US-034 — Validate Concurrency and Duplicate Execution Protection: Story 2

**Description**

As a system operator, I want to prevent duplicate scheduling, so that concurrent triggers do not create duplicate artifacts or external publications.

**Status:** Implemented, automated-tested, acceptance criteria validated against fixture evidence (2026-07-18), and **deployed** on `192.168.0.194` (`BUILD_REVISION=018aa36`). **BL-013 closed 2026-07-18**. See [flow-a-concurrency-duplicate-execution-protection-us-034.md](../operations/flow-a-concurrency-duplicate-execution-protection-us-034.md).

**Acceptance criteria**

- [x] Prevent duplicate scheduling.
- [x] Prevent duplicate LinkedIn publication.
- [x] Recover abandoned processing claims.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

### US-035 — Validate Concurrency and Duplicate Execution Protection: Story 3

**Description**

As a system operator, I want to validate behavior during restarts, so that concurrent triggers do not create duplicate artifacts or external publications.

**Status:** Implemented, automated-tested, acceptance criteria validated against restart-interruption fixture evidence (2026-07-18), and **deployed** on `192.168.0.194` (`BUILD_REVISION=018aa36`). US-033 and US-034 remain accepted. **BL-013 closed 2026-07-18**. See [flow-a-concurrency-duplicate-execution-protection-us-035.md](../operations/flow-a-concurrency-duplicate-execution-protection-us-035.md).

**Acceptance criteria**

- [x] Validate behavior during restarts.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

## BL-014 — Establish Backup and Restore for Editorial State

**Priority:** P3

**Business context:** Protect the files and metadata required to recover the editorial system.

### US-036 — Establish Backup and Restore for Editorial State: Story 1

**Description**

As a system operator, I want to define backup scope, so that editorial state can be restored from a verified backup.

**Operator policy:** [editorial-backup-scope-retention-integrity.md](../operations/editorial-backup-scope-retention-integrity.md) (scope, retention, integrity — US-036; restore is US-037).

**Status:** Implemented, automated-tested, and acceptance criteria validated against fixture evidence (2026-07-18). Not a live production restore execution. **BL-014 closed 2026-07-18**. Evidence: [bl-014 acceptance](../operations/bl-014-editorial-backup-restore-acceptance-2026-07-18.md).

**Acceptance criteria**

- [x] Define backup scope.
- [x] Define retention.
- [x] Verify backup integrity.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

### US-037 — Establish Backup and Restore for Editorial State: Story 2

**Description**

As a system operator, I want to test restoration, so that editorial state can be restored from a verified backup.

**Operator recovery procedure:** [editorial-backup-restore-recovery.md](../operations/editorial-backup-restore-recovery.md) (restore drills + recovery — US-037; integrity verify remains US-036).

**Status:** Implemented, automated-tested, and acceptance criteria validated against fixture restore drills + recovery procedure (2026-07-18). Live production restore remains operator-gated; not required for acceptance. **BL-014 closed 2026-07-18**. Evidence: [bl-014 acceptance](../operations/bl-014-editorial-backup-restore-acceptance-2026-07-18.md).

**Acceptance criteria**

- [x] Test restoration.
- [x] Document the recovery procedure.
- [x] Protect calendar, campaigns, runs, posts, images, and LinkedIn artifacts.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

## BL-015 — Implement Flow A LinkedIn Variant Supervision Console

**Priority:** P3

**Business context:** Provide an operator-facing console to supervise Flow A LinkedIn variants after distribution scheduling and before LinkedIn API publication, per [linkedin-variant-review-policy.md](../operations/linkedin-variant-review-policy.md).

**Prerequisites:** BL-006 US-015 (policy defined). US-017 SHOULD supply persisted edit/cancel/defer mechanics before console actions constrain BL-007 eligibility.

### US-038 — Implement Flow A LinkedIn Variant Supervision Console: Story 1

**Description**

As a content operator, I want to see Flow A LinkedIn variants on a calendar or campaign view while they are pending, so that I can supervise scheduled publication without inspecting raw files.

**Acceptance criteria**

- [x] Present `pending` variants with campaign id, variant id, audience, `scheduled_at_utc`, and `publish_state`. — Demonstrated by `GET /flow-a/linkedin-variants/pending-supervision` + `tests/test_linkedin_variant_pending_supervision.py`.
- [x] Align the view with the editorial calendar where applicable. — Demonstrated: calendar join fields when calendar loads; missing/invalid calendar still lists pending rows with issues.
- [x] The outcome is visible and understandable to the intended user. — Demonstrated: static console at `GET /flow-a/console/linkedin-variant-supervision` (same-origin HTML; no raw mount inspection).
- [x] Failures or blocked states are clearly communicated. — Demonstrated: `issues[]` / `status=partial` for campaign/calendar read failures; enablement-off as display-only context.
- [x] Existing completed work is not duplicated or unintentionally changed. — Demonstrated: separate read paths; no US-017 mutation UI; publication enablement guard unchanged.

### US-039 — Implement Flow A LinkedIn Variant Supervision Console: Story 2

**Description**

As a content operator, I want to edit variant text and adjust scheduled timing before queue, so that I can correct derivatives during the optional supervision window.

**Acceptance criteria**

- [x] Edit variant content before queue authorization. — Demonstrated: console Edit control calls `POST /correct-linkedin-variant` (`tests/test_linkedin_variant_pending_supervision.py`).
- [x] Defer or reschedule relative to distribution strategy rules. — Demonstrated: console Defer control calls `POST /defer-linkedin-variant` with `new_scheduled_at_utc`.
- [x] Persist operator changes traceably (aligned with US-017 when implemented). — Demonstrated: persistence via existing US-017 POSTs only; no parallel mutation SoT.
- [x] The outcome is visible and understandable to the intended user. — Demonstrated: dry-run vs real banners; list refresh after real success; `draft_content` on pending-supervision GET.
- [x] Failures or blocked states are clearly communicated. — Demonstrated: US-017 codes surfaced in console (`linkedin_supervision_variant_not_pending`, `linkedin_supervision_defer_time_invalid`, etc.).
- [x] Existing completed work is not duplicated or unintentionally changed. — Demonstrated: no cancel UI; no new mutation endpoints; secrets audit still passes; BL-007 / publication guards untouched.

### US-040 — Implement Flow A LinkedIn Variant Supervision Console: Story 3

**Description**

As a content operator, I want to cancel or defer variants and see why publication is blocked, so that operator overrides constrain future BL-007 auto-queue eligibility.

**Acceptance criteria**

- [x] Cancel or defer variants before queue per the LinkedIn variant review policy. — Demonstrated: console Cancel calls `POST /cancel-linkedin-publication`; Defer retained from US-039 (`tests/test_linkedin_variant_pending_supervision.py`).
- [x] Surface blocked states (publication enablement, integration failures, deferred capabilities). — Demonstrated: enablement display-only banner; deferred/`auto_queue_eligible`/`operator_supervision_reason` on rows; `integration_failures[]` for failed siblings.
- [x] Invoke worker capabilities over HTTP only (ADR-0001); do not bypass publication guards. — Demonstrated: browser calls existing US-017 cancel/defer/edit POSTs; GET remains non-mutating; no enablement bypass.
- [x] The outcome is visible and understandable to the intended user. — Demonstrated: dry-run vs real cancel banners; real cancel refreshes list; eligibility exclusion copy; `pending`/`cancelled`/`flow_a_complete` ≠ LinkedIn API published.
- [x] Failures or blocked states are clearly communicated. — Demonstrated: cancel codes (`linkedin_publish_cancel_not_allowed`, not-pending/action-not-allowed/idempotency, 401/422) plus retained edit/defer mapping.
- [x] Existing completed work is not duplicated or unintentionally changed. — Demonstrated: no new mutation SoT; edit/defer preserved; secrets audit still passes; BL-007 / publication guards untouched.

**US-040 variants**

These variants extend US-040 inside BL-015. They are not a new backlog item and MUST NOT be treated as Flow B implementation scope. They improve the same Flow A supervision console as a dark, mobile-friendly operational product ready for a future public URL protected by Google authentication.

**UX direction after US-040F (operator feedback 2026-07-18):** US-040A–F delivered stack, dual List+Month views, ScheduleEditor, auth readiness, polish, and a first redesign pass. Operator review rejected list-first triage and day-agenda dumps as the mental model. Subsequent variants (US-040G onward) **supersede list-as-first-class-view** for the product UX: the console MUST become **calendar-first** (Week default, Month secondary), **event-modal** driven, **local-time** oriented, with **toast** feedback, **cancelled-item** handling, and a **max 2 publications per local day** density rule. Prior List-preserving language in US-040A–F remains historical for those stories’ demonstrated scope; it MUST NOT block US-040G+ from removing the list surface.

**Shared UX Definition of Done (US-040G–US-040K — normative)**

These rules apply to every US-040G–K story. Automated tests and OpenSpec task checkboxes are **necessary but not sufficient**.

- **Product-quality bar:** The delivered UI MUST read as a modern, responsive, operational calendar product (clear hierarchy, balanced density, calm empty/loading/error states, usable on laptop and phone). Checkbox completion alone MUST NOT imply Story accepted.
- **Visual evidence:** Each story’s OpenSpec change MUST require desktop + mobile evidence (screenshots or equivalent browser-driven capture) for that story’s Visual DoD scenes — not only Vitest/component assertions.
- **Operator walkthrough gate:** **Story accepted** for US-040G–K MUST NOT be marked until the content operator completes a live walkthrough on the deployed (or explicitly agreed preview) console and confirms the UX meets the story’s intent. “Business outcome demonstrated” / implementation commit is allowed before that gate; **Acceptance criteria validated** and **Story accepted** are not.
- **Partial UX is incomplete:** If the walkthrough finds the UI still feels like a technical status page, empty/broken, or cognitively heavy, the story stays in progress — follow-up OpenSpec work, not silent AC re-interpretation.
- **BL-015 stays open** until the backlog completion outcome is operator-validated; shipping G–K code does not close BL-015 by itself.

**Additional prerequisites:** BL-021 remains the home for full editorial cadence policy; US-040K may ship an interim console/worker density cap (max 2/local day) that BL-021 MAY later supersede. Future Google authentication stays out of scope, but API boundaries MUST remain ready for it.

### US-040A — Implement Flow A LinkedIn Variant Supervision Console: Modern Frontend Stack Without Rebuild

**Description**

As a system owner, I want the supervision console to use a maintainable modern frontend stack incrementally, so that the operator experience can improve without rewriting the existing worker, n8n workflows, or publication pipeline.

**Acceptance criteria**

- [x] Define the frontend stack decision in the OpenSpec proposal before implementation; the default recommendation SHOULD be React + TypeScript + Vite, or an explicitly justified equivalent modern stack. — Demonstrated: proposal + `frontend/linkedin-variant-supervision-console/` is React + TypeScript + Vite.
- [x] Treat the stack change as a console-layer modernization only; do not rewrite the worker business logic, n8n workflows, Python utilities, file contracts, publication guards, or existing HTTP mutation semantics as part of this variant. — Demonstrated: worker change is static-asset serving only; US-017 POSTs unchanged.
- [x] Preserve the existing same-origin console route or provide a compatible replacement route so current operator access remains understandable during migration. — Demonstrated: `GET /flow-a/console/linkedin-variant-supervision` serves Vite `index.html` + same-origin `/assets/*`.
- [x] Preserve the existing list-oriented pending-variant supervision experience as a first-class view in the modernized console. — Demonstrated: `ListView` with edit/defer/cancel; calendar is scaffold-only via view switcher.
- [x] Build the UI as componentized operational screens, including list view, month calendar view, item detail, schedule editor, status summary, filters, confirmation flows, and shared API/error handling. — Demonstrated: components under `frontend/.../src/components/` + `api/` (calendar/schedule/filters are scaffolds).
- [x] Keep the browser API access centralized behind a typed client or equivalent boundary so future Google/OIDC authentication can be added without changing business components. — Demonstrated: `SupervisionApiClient` + injectable `AuthProvider` (in-memory Bearer; no browser storage).
- [x] Produce static build artifacts that can be served by the existing worker or deployment path without requiring a separate frontend server in production. — Demonstrated: build output under `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`; Docker still one worker process (`npm ci && npm run build` before image build).
- [x] Avoid introducing a backend-for-frontend, database, user-management system, or public hosting change unless a separate OpenSpec change explicitly approves it. — Demonstrated: browser → worker HTTP only; no BFF/DB/user-mgmt/public hosting.
- [x] Keep list and calendar views backed by the same worker read models or a clearly shared normalized frontend model so they cannot disagree about item identity, state, schedule, or available actions. — Demonstrated: `SupervisionItem` / `SupervisionSnapshot` shared store; calendar scaffold consumes it.
- [x] Keep dependency additions small, documented, and justified by usability, maintainability, accessibility, or calendar interaction needs. — Demonstrated: production deps are `react` + `react-dom` only; see frontend README.
- [x] Include frontend validation appropriate to the chosen stack, covering build success, key component behavior, API error mapping, desktop viewport, and mobile viewport. — Demonstrated: `npm run build`, Vitest ListView + error-mapping + viewport tests; pytest console/secrets audit updated.
- [x] The outcome is visible and understandable to the intended user. — Demonstrated: console shell copy, dry-run default, enablement display-only, qualified `pending` / `cancelled` / `flow_a_complete` language.
- [x] Failures or blocked states are clearly communicated. — Demonstrated: `ApiError` mapping for 401/422 and known US-017 codes; banners for status/actions.
- [x] Existing completed work is not duplicated or unintentionally changed. — Demonstrated: Stories 1–3 mutation SoT reused; legacy monolithic HTML removed; US-040B–US-040E / Flow B not implemented.

### US-040B — Implement Flow A LinkedIn Variant Supervision Console: List and Month Schedule Visibility

**Description**

As a content operator, I want to switch between a list view and a dark month calendar of upcoming Flow A blog posts and LinkedIn variants, so that I can inspect operational detail quickly and also understand what will be published each day from my laptop or phone.

**Acceptance criteria**

- [x] Provide two first-class views in the same console: `List` and `Month calendar`; neither view replaces, hides permanently, or weakens the other.
- [x] Preserve the list view as the detail-heavy operational view for pending variants, including campaign id, variant id, audience, `scheduled_at_utc`, publication state, draft content visibility where supported, issues, integration failures, and available actions.
- [x] Provide a clear, persistent view switcher suitable for desktop and mobile; switching views MUST NOT clear filters, selected campaign context, dry-run mode, or unsaved schedule edits without warning.
- [x] Present a month view with current month, next/previous month navigation, today marker, selected-day state, and clear empty-day states.
- [x] Show each scheduled blog post and LinkedIn variant on the correct calendar day, including title or campaign label, campaign id where available, variant id where available, audience, channel, publication state, and scheduled time.
- [x] Distinguish planned, pending, queued, published, deferred, cancelled, blocked, and failed states without implying that `pending` or `queued` content has already been published.
- [x] Make the same item recognizable across both views by preserving stable labels, ids, status colors, and detail fields.
- [x] Surface blocking issues and partial-data warnings when campaign, calendar, variant, or integration state cannot be read completely.
- [x] Provide filters or toggles for channel, campaign, publication state, blocked items, and due-soon items without hiding critical failure indicators silently.
- [x] Apply filters consistently to both list and calendar views, while making hidden critical failures discoverable through a count, warning, or reset affordance.
- [x] Display dates and times with explicit timezone handling, including the stored UTC schedule and the operator-local interpretation where useful.
- [x] Work comfortably on phone and laptop viewports: the list view SHOULD become readable stacked rows/cards on mobile, and the calendar SHOULD provide an agenda-style day expansion or equivalent mobile pattern instead of forcing horizontal table scrolling.
- [x] Use a dark visual theme with readable contrast, stable spacing, clear hierarchy, and touch targets suitable for mobile operation.
- [x] Read data through worker HTTP capabilities only; the browser MUST NOT read raw mounted files or infer state from filesystem paths.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

### US-040C — Implement Flow A LinkedIn Variant Supervision Console: Schedule Modification From Calendar

**Description**

As a content operator, I want to modify future Flow A publication timing from the calendar without losing the existing list workflow, so that I can adjust the editorial plan where I notice conflicts or better publishing windows.

**Acceptance criteria**

- [x] Allow the operator to select a future unpublished item from the month view, mobile agenda view, or list view and open the same schedule editor.
- [x] Preserve existing list-based edit, defer, reschedule, and cancel affordances where they are already supported; calendar actions MUST reuse the same business rules and worker semantics.
- [x] Support changing the scheduled date and time for future unpublished blog and LinkedIn items only; published historical items MUST be read-only.
- [x] For LinkedIn variants, reuse or extend the existing worker supervision semantics for deferring or rescheduling pending variants instead of introducing a second mutation source of truth.
- [x] For editorial calendar items, update the canonical calendar through an explicit worker API contract with validation, idempotency, and conflict protection; the browser MUST NOT write raw calendar files directly.
- [x] Validate schedule changes against approved cadence and rescheduling rules, including past dates, invalid time formats, saturation, duplicate slots, and unsupported publication states.
- [x] Make dry-run behavior visible before any real mutation and require explicit confirmation for committed schedule changes.
- [x] After a successful change, refresh the calendar and show the previous schedule, new schedule, affected item, and whether related LinkedIn variants were changed or left as separate overrides.
- [x] After a successful change, refresh the list view with the same updated schedule and state so both views remain consistent.
- [x] Persist a traceable audit record with actor/source, timestamp, previous value, new value, reason when supplied, idempotency key, and worker result.
- [x] Do not call the LinkedIn publication API or publish blog content as part of a schedule edit.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

### US-040D — Implement Flow A LinkedIn Variant Supervision Console: Public URL and Google Auth Readiness

**Description**

As a system owner, I want the Flow A supervision console architecture to be ready for a future public URL protected by Google authentication, so that later security work can add login without rewriting the calendar experience.

**Acceptance criteria**

- [x] Keep authentication and authorization concerns behind a clear frontend API client and backend middleware boundary.
- [x] Represent anonymous, authenticated, expired-session, forbidden, and service-unavailable states in the UI, even if the current local implementation uses the existing worker auth mechanism.
- [x] Avoid hardcoding API keys, tokens, operational secrets, mount paths, or local-only assumptions in frontend source, rendered HTML, logs, or browser storage.
- [x] Use same-origin calls or an explicitly documented CORS strategy that can be safely restricted when the console is exposed publicly.
- [x] Design the API request layer so a later Google/OIDC bearer token or secure session cookie can replace the current auth header without changing calendar components.
- [x] Prevent unauthenticated or read-only sessions from executing schedule mutations.
- [x] Handle mobile session expiry gracefully by preserving visible context and guiding the operator back to authentication without losing unsaved edits.
- [x] Document that public deployment and Google authentication activation are out of scope for this BL and require a separate security change before internet exposure.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

### US-040E — Implement Flow A LinkedIn Variant Supervision Console: Operational Usability and Safety

**Description**

As a content operator, I want the Flow A supervision console to make attention, risk, and next actions obvious in both list and calendar views, so that I can operate the publishing schedule confidently from anywhere.

**Status:** Implemented in console layer (US-040E polish demonstrated via Vitest + rebuilt static assets). **Not Story accepted; BL-015 remains open.** Public URL hosting and Google/OIDC IdP remain not activated.

**Acceptance criteria**

- [x] Provide at-a-glance counts for upcoming, pending, due soon, deferred, blocked, failed, and recently published items. — Demonstrated: `deriveOperationalCounts` + AppShell `StatusSummary` count strip (filter-scope; recently published uses `published` / `linkedinApiPublished` only; Vitest `us040e.polish.test.tsx`).
- [x] Prioritize actionable states visually so blocked or failed items are noticeable without overwhelming normal scheduled content. — Demonstrated: List `row-risk-blocked` / `row-risk-failed`; Month compact badges (not diagnostic walls).
- [x] Use concise operator-facing labels for technical states and preserve detailed diagnostic codes in expandable details when needed. — Demonstrated: `publicationStateLabel`; ItemDetail / failure / agenda `<details>` diagnostics.
- [x] Provide clear affordances for switching view, filtering, inspecting, rescheduling, deferring, cancelling where supported, refreshing, and dry-run/commit mode. — Demonstrated: AppShell affordance groups (`affordance-nav` / filters / content); List inspect/reschedule/cancel; shell dry-run default.
- [x] Keep the list view optimized for scanning and bulk operational triage, and keep the month calendar optimized for schedule comprehension; do not force one view to carry both jobs poorly. — Demonstrated: List retains triage actions; Month keeps day placement + compact status + agenda.
- [x] Keep destructive or irreversible actions protected by confirmation and avoid placing them next to routine navigation controls. — Demonstrated: real cancel still uses `confirmRealMutation`; cancel not in `affordance-nav` with Refresh/ViewSwitcher.
- [x] Preserve keyboard accessibility for laptop use and touch accessibility for mobile use. — Demonstrated: `:focus-visible` rings; Escape closes overlays with draft warn; `--touch-min: 44px` retained; no hover-only critical actions.
- [x] Validate visual behavior with desktop and mobile screenshots or equivalent UI checks that cover dense lists, empty lists, dense months, empty months, blocked items, long titles, switching views, and schedule editing. — Demonstrated: Vitest visual matrix in `us040e.polish.test.tsx` at 1280px and 375px.
- [x] Keep the dark theme consistent across loading, empty, error, detail, confirmation, and success states. — Demonstrated: shared dark tokens for banners/panels/count strip/diagnostics; empty zero counts not treated as failures.
- [x] Do not introduce a marketing-style landing page; the first screen MUST be the usable operational calendar experience. — Demonstrated: `App`/`AppShell` first paint is operational console shell (auth banners inside shell).
- [x] The outcome is visible and understandable to the intended user. — Demonstrated: count strip, labels, banners, qualified publication language.
- [x] Failures or blocked states are clearly communicated. — Demonstrated: actionable count chips, risk rows, expandable failure codes; mutations not shown as success on failure.
- [x] Existing completed work is not duplicated or unintentionally changed. — Demonstrated: no new mutation SoT; US-040A–D stack/views/ScheduleEditor/`canMutate` preserved; public URL/Google not activated; BL-015 left open; no Flow B.

### US-040F — Implement Flow A LinkedIn Variant Supervision Console: Modern Operational UX Redesign

**Description**

As a content operator, I want the Flow A supervision console to feel like a modern, purpose-built operational product instead of a technical status page, so that I can understand risk, review the publication plan, and take safe action from a laptop or phone with minimal cognitive load.

**Status:** Implemented in console layer (US-040F first-pass UX redesign demonstrated via Vitest + rebuilt static assets; OpenSpec change `redesign-flow-a-linkedin-variant-supervision-console-us-040f`). **Not Story accepted; BL-015 remains open.** Further operator-directed UX iteration is expected. Public URL hosting and Google/OIDC IdP remain not activated.

**UX direction**

- The console SHOULD use the available desktop width intentionally with a modern application layout, not a narrow document-like column.
- The first viewport SHOULD behave like an operations dashboard: top navigation, actionable metrics, primary view content, and a clear detail/action area.
- The UI SHOULD reduce visible explanatory prose and move technical disclaimers, endpoint names, diagnostic codes, and policy reminders into contextual help, tooltips, expandable diagnostics, or documentation links.
- The visual language SHOULD be contemporary, dark, accessible, and product-like: sans-serif typography, balanced density, clear spacing rhythm, strong hierarchy, restrained color, modern controls, and professional empty/loading/error states.
- The redesign SHOULD be mobile-first for real operation from a public URL in the future, while still taking advantage of wide laptop screens.

**Acceptance criteria**

- [x] Redesign the shell into a modern dark operational app layout that uses desktop width effectively. The page MUST NOT feel like a centered documentation page; it SHOULD provide a structured workspace with header/navigation, metric summary, primary content, and contextual detail/action area. — Demonstrated: `AppShell` app bar/session strip/filter dock + `main.console-shell` wide workspace up to 1680px.
- [x] Preserve React + TypeScript + Vite, same-origin static asset delivery, typed API client, shared normalized model, List view, Month calendar view, `ScheduleEditor`, session states, and `canMutate` gating from US-040A–US-040E. — Demonstrated: same frontend package, store/API boundaries, views, ScheduleEditor and rebuilt worker static assets.
- [x] Do not rewrite worker business logic, n8n workflows, publication guards, mutation endpoints, schedule mutation source of truth, public hosting, Google/OIDC activation, BFF/database/user-management, or Flow B as part of this UX redesign. — Demonstrated: frontend-only source changes plus static asset rebuild; no worker/n8n/API contract changes.
- [x] Replace the current text-heavy first screen with an at-a-glance command surface. Primary visible content SHOULD be actionable status, calendar/list content, and safe next actions; long explanations about endpoints, policy, and publication semantics MUST move out of the main scan path. — Demonstrated: concise shell, compact banners, shortened footer, diagnostics retained behind details.
- [x] Provide a concise top app bar suitable for future public operation: console name, current session/auth state, refresh, dry-run/commit mode, and view navigation. Session/auth controls SHOULD be visible but visually secondary to operational work. — Demonstrated: sticky `.app-bar`, `.session-strip`, view switcher, refresh and dry-run/commit mode.
- [x] Make operational metrics interactive where useful: blocked, failed, due soon, pending, upcoming, deferred, and recently published counts SHOULD support filtering or navigation to the relevant items without requiring the operator to manually configure filters. — Demonstrated: `StatusSummary` count buttons drive filters; covered by `us040f.ux-redesign.test.tsx`.
- [x] Preserve both first-class views and make their purpose immediately obvious: `List` for triage/review/action and `Calendar` for schedule comprehension. Switching views MUST preserve filters, selected context, dry-run mode, and unsaved draft protections. — Demonstrated: retained `ViewSwitcher`, `ListView`, `MonthCalendarView`, store state preservation and existing tests.
- [x] Redesign the List view for fast scanning rather than table-like technical inspection. Each item SHOULD expose title/campaign identity, channel/audience, schedule, state, risk, and primary action clearly; raw ids, source states, and diagnostic codes SHOULD be available in detail, not dominate every row. — Demonstrated: card-based `.variant-card-list`, concise row actions and detail drawer diagnostics.
- [x] On desktop, use a master-detail pattern or equivalent modern layout so selecting an item opens detail/actions in a side panel or drawer without pushing the entire list/calendar downward. — Demonstrated: `.triage-layout` + sticky `.detail-drawer` selected detail/action panel.
- [x] On mobile, avoid desktop tables and horizontal scrolling. The operator SHOULD be able to review items as cards, open detail/actions in a bottom sheet or full-screen panel, and return to the previous context without losing filters or drafts. — Demonstrated: list table hidden; card layout and drawer stack under responsive breakpoints.
- [x] Redesign the Month calendar so it communicates publication density and risk per day at a glance. Days SHOULD show compact channel/state indicators, blocked/failed emphasis, selected/today states, and overflow handling without turning cells into diagnostic walls. — Demonstrated: compact month heading, day badges, selected/today styling, blocked/failed classes retained.
- [x] On mobile calendar, provide a usable month overview plus agenda-style day detail. The selected day’s items and actions SHOULD be reachable with thumb-friendly controls. — Demonstrated: retained mobile agenda pattern and responsive calendar breakpoints.
- [x] Provide modern controls appropriate to the action: segmented control or tabs for List/Calendar, icon buttons with accessible labels for navigation/refresh where appropriate, toggles for dry-run/commit, chips for quick filters, menus for secondary actions, and confirmation dialogs/sheets for destructive actions. — Demonstrated: segmented view switcher, refresh aria label, dry-run mode toggle, metric/filter chips and confirmation flows.
- [x] Keep destructive actions visually separated from routine navigation and protected by confirmation. `Cancel` and real committed changes MUST remain impossible to trigger accidentally from the main toolbar. — Demonstrated: cancel remains row/detail destructive action with confirmation; not in app bar.
- [x] Keep blocked/failed states highly noticeable without making routine scheduled content look alarming. Visual priority SHOULD combine color, iconography or shape, label, and placement rather than relying on color alone. — Demonstrated: card borders, tinted backgrounds, status pills and calendar badges.
- [x] Use concise operator-facing language in primary chrome. Technical language such as endpoint paths, worker codes, `flow_a_complete`, raw mount/path wording, and source-state diagnostics MUST be hidden by default unless needed to understand a failure, debug issue, or confirm semantics. — Demonstrated: endpoint-heavy visible footer removed; codes retained in diagnostics/details.
- [x] Preserve qualified publication language: `pending`, `queued`, `cancelled`, campaign `flow_a_complete`, and blog handoff MUST NOT be presented as LinkedIn API published. — Demonstrated: existing label/count semantics and tests preserved.
- [x] Improve empty, loading, error, success, read-only, expired-session, unauthenticated, blocked, and confirmation states so they are visually consistent, short, actionable, and understandable on desktop and mobile. — Demonstrated: consolidated dark tokens/banners/panels; prior US-040D/E tests still pass.
- [x] Meet practical accessibility expectations for an operational web app: keyboard navigation, visible focus, semantic controls, non-hover-only actions, readable contrast, mobile touch targets, and text that does not overflow or overlap at tested viewport widths. — Demonstrated: focus styles, semantic buttons/regions, 44px touch minimum and responsive tests.
- [ ] Validate the redesign visually with desktop and mobile screenshots or equivalent browser-driven evidence, not only component assertions. Required evidence MUST cover: first screen, dense list, empty list, dense month, empty month, selected day agenda, item detail, schedule editor, destructive confirmation, blocked/failed states, long titles, read-only/session-expired state, and view switching. — Partially demonstrated: inherited US-040E viewport matrix plus new `us040f.ux-redesign.test.tsx`; browser screenshots / browser-driven capture could not be run because no in-app browser, Playwright, Puppeteer, Chromium, or Chrome CLI is available in this environment.
- [x] Include a before/after UX review note or evidence summary that explicitly explains how the redesign reduces cognitive load, improves scanability, improves mobile operation, and uses the modern frontend stack more effectively. — Demonstrated: CURRENT-STATE US-040F summary plus this checklist evidence.
- [x] The outcome is visible and understandable to the intended user. — Demonstrated: app-like shell, metric-driven focus, cards, calendar and detail drawer.
- [x] Failures or blocked states are clearly communicated. — Demonstrated: blocked/failed visual classes, banners and expandable diagnostics retained.
- [x] Existing completed work is not duplicated or unintentionally changed. — Demonstrated: no new mutation SoT; US-040A–E contracts preserved; no public URL/Google activation; no Flow B.

### US-040G — Implement Flow A LinkedIn Variant Supervision Console: Calendar-First Week and Month (Remove List)

**Description**

As a content operator, I want the supervision console to open on a clear **week** calendar with **month** as a secondary view and **no list**, so that I immediately understand what publishes when without learning a second triage surface that often looks empty or unexplained.

**Status:** Implemented in console layer (US-040G calendar-first Week + Month; List removed from operator chrome; OpenSpec change `redesign-flow-a-linkedin-variant-supervision-console-us-040g`; empty-grid follow-up `fix-us-040g-outlook-empty-calendar-grid` applied and **redeployed** — Week/Month keep day structure visible with calm empty cue; Vitest viewport matrix ~1280/~375 + live static assets `index-SFvEuRPX.js` / `index-DTJ5Tm4v.css` on `192.168.0.194:8010`). **Not Story accepted; BL-015 remains open.** Visual DoD screenshots + operator walkthrough remain gated (browser capture / walkthrough not completed). Interim event panel superseded by US-040H EventModal. UTC day-bucketing debt addressed by US-040I (console-layer; not yet Story accepted / not yet deployed). US-040J reopen and US-040K density not delivered. Filters dock removal and Cancelled metric chip are out of scope for the empty-grid fix.

**UX intent (normative)**

- The first paint MUST feel like a **calendar product**, not a status page and not an empty data table.
- Week is the **default home**: the operator should grasp “this week’s plan” in under three seconds.
- Month is for **density and horizon**, not for dumping full diagnostics into cells.
- Removing the list MUST NOT remove capability — every previous list action MUST remain reachable from the event modal (US-040H) or equivalent calendar entry points.
- Empty weeks/months MUST explain themselves (“No publications this week/month”) with a calm empty cue **while keeping the Week day columns / Month day grid visible** (Outlook-like blank days) — never a blank white/void panel or a gridless substitute panel that looks broken.
- View switching MUST be obvious: segmented control or equivalent with labels `Week` / `Month`, Week selected by default on first load and after hard refresh unless a deep-link says otherwise.

**Visual DoD / Story acceptance gate**

Required scenes (desktop + mobile): Week first paint; empty week (**day columns still visible** with empty cue); dense week; Month switch; empty month (**day grid still visible** with empty cue); dense month; Today/This-week control; proof that List chrome is gone.
**MUST NOT** mark Story accepted without operator walkthrough confirming the console feels like a modern calendar product (shared DoD above).

**Acceptance criteria**

- [x] Remove the List view from the operator-facing console chrome (no List tab, no list-first landing, no empty list as the default workspace). — Demonstrated: ViewSwitcher is Week|Month only; Vitest asserts List chrome absent.
- [x] Provide **Week** as the default first-class view and **Month** as the secondary first-class view; switching MUST preserve filters, dry-run/commit mode, and unsaved modal drafts with warning. — Demonstrated via Vitest (filters survive Week↔Month; draft-warn path preserved in store).
- [x] Week view MUST show a readable local-week grid or column layout with day headers, today emphasis, and events as scannable chips/cards (title or campaign label, channel, local time, state) — not raw ids as the primary label. — Demonstrated: day-column Week (not hour grid); local time on chips; local-day placement delivered in US-040I (console-layer).
- [x] Month view MUST remain density-oriented: compact event indicators per day, overflow handling, today/selected styling, without turning cells into diagnostic forms. — Demonstrated: agenda dump removed as primary surface; light day focus + event chips.
- [x] Navigation: previous/next week, previous/next month, and a one-click “Today / This week” affordance MUST be visible and thumb-friendly on mobile. — Demonstrated via Vitest + CSS touch targets.
- [x] When a week or month has zero items after filters, show a deliberate empty state with short copy and a path to clear filters if filters hid everything — never an unexplained blank content area. — Demonstrated via Vitest: empty cue + persistent `week-columns` / `calendar-grid` (Outlook-like); filter-zero clear path; live Visual DoD still gated pending redeploy + walkthrough.
- [x] Metric chips (if retained) MUST navigate/focus within Week/Month (e.g. jump to next blocked event week), not reopen a list. — Demonstrated: `navigateMetricFocus` stays on calendar; Vitest asserts no List.
- [x] Preserve React + TypeScript + Vite, same-origin static delivery, typed API client, shared normalized model, ScheduleEditor mutation SoT, session/`canMutate`, and worker HTTP-only access. — Demonstrated: stack unchanged; ScheduleEditor + interim path; session suites pass.
- [x] Do not activate public URL hosting, Google/OIDC, BFF/DB/user-management, LinkedIn API publish, or Flow B. — Demonstrated: out of scope; no activation.
- [ ] Capture Visual DoD evidence (desktop + mobile) for the scenes listed above; Vitest alone is insufficient for Story accepted.
- [ ] Operator walkthrough completed on deployed or agreed preview; operator confirms Week-default calendar UX meets intent before Story accepted.
- [ ] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated without restoring a list as the primary recovery UI. — Demonstrated: calendar empty/filter states + interim detail; metrics stay on Week/Month.
- [x] Existing completed work is not duplicated or unintentionally changed beyond the deliberate removal of list-first UX (US-017 mutation contracts reused). — Demonstrated: no new mutation SoT; H/I/J/K products not shipped.
### US-040H — Implement Flow A LinkedIn Variant Supervision Console: Event Modal and Toast Feedback

**Description**

As a content operator, I want to click a **specific event** and work inside a focused **modal**, with success/info feedback as brief **toasts**, so that I never face a confusing split of “day dump below + detail above” or large green banners that steal the calendar.

**Status:** Implemented and deployed to `192.168.0.194:8010` (OpenSpec change `redesign-flow-a-linkedin-variant-supervision-console-us-040h`; Vitest + rebuilt static assets; live `index-P0TKf1cr.js` / `index-BGvbD0Jm.css`; git `3aa9394`). **Not Story accepted; BL-015 remains open.** Visual DoD + operator walkthrough remain gated.

**UX intent (normative)**

- **Primary interaction:** click the **event**, not the day.
- Clicking a day MUST NOT open a full multi-event diagnostic agenda that competes with item detail. Days MAY show a light hover/focus affordance only; event chips remain the actionable targets.
- The modal is the **single focus surface** for view + edit + reschedule + cancel (where allowed): identity, local schedule, state, risk, draft/content when applicable, and safe actions.
- Success, dry-run results, and non-blocking info MUST appear as **toasts** (top-right or equivalent), auto-dismiss after a few seconds, stack sensibly, and never permanently push the calendar down.
- Persistent full-width green “everything is fine” banners MUST be removed from the primary scan path.
- Destructive confirmations remain modal/dialog — not toast-only.
- Escape / backdrop click / close control MUST dismiss the modal with draft-loss warning when unsaved edits exist.
- Mobile: modal SHOULD be a full-screen sheet or near-full sheet with large touch targets; desktop: centered or anchored modal with clear hierarchy (title → state → schedule → actions).

**Visual DoD / Story acceptance gate**

Required scenes (desktop + mobile): event open; modal hierarchy; edit/reschedule in modal; toast success + auto-dismiss; toast stack; cancel confirmation; mobile sheet; proof of no day-agenda dump; proof of no persistent green success banner on happy path.
**MUST NOT** mark Story accepted without operator walkthrough confirming modal + toast interaction feels focused and modern (shared DoD above).

**Acceptance criteria**

- [x] Clicking an event opens an event modal with view and edit affordances appropriate to state; clicking empty day space MUST NOT open the multi-item agenda dump pattern.
- [x] The modal MUST present operator-facing fields first (title/campaign, channel/audience, local datetime, publication state, risk) and bury raw ids, endpoint names, and worker codes in expandable diagnostics.
- [x] Edit content, reschedule, defer, and cancel (where supported) MUST be reachable from the modal without returning to a list.
- [x] Replace persistent success/enablement/status green banners with ephemeral toasts for non-blocking feedback; toasts MUST auto-dismiss (target ~4–6s) and be dismissible manually.
- [x] LinkedIn publish-guard / session context MAY remain as a compact chip or quiet status in the app bar — not a full-width green banner.
- [x] Dry-run vs real commit MUST remain visually obvious inside the modal and in toast copy after actions.
- [x] Keep destructive cancel behind explicit confirmation separate from toast success feedback.
- [x] Preserve keyboard access: focus trap in modal, Escape closes (with draft warn), visible focus rings, no hover-only critical actions.
- [ ] Capture Visual DoD evidence (desktop + mobile) for the scenes listed above; Vitest alone is insufficient for Story accepted.
- [ ] Operator walkthrough completed on deployed or agreed preview; operator confirms modal + toast UX meets intent before Story accepted.
- [ ] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated (error toasts or in-modal errors; not silent failure).
- [x] Existing completed work is not duplicated or unintentionally changed (reuse ScheduleEditor / US-017 semantics inside the modal shell).

### US-040I — Implement Flow A LinkedIn Variant Supervision Console: Operator-Local Time Experience

**Description**

As a content operator, I want the week/month grids, event times, and reschedule controls to work in **my local timezone**, so that I do not have to translate UTC or “another part of the world’s” calendar days while planning posts.

**Status:** Implemented and deployed to `192.168.0.194:8010` (OpenSpec change `redesign-flow-a-linkedin-variant-supervision-console-us-040i` archived; Vitest with `TZ=America/Chicago` + ~1280/~375 viewport matrix + production static rebuild; live `index-DV0R4K8U.js` / `index-BGvbD0Jm.css`; git `a1bd3cd`). **Not Story accepted; BL-015 remains open.** Visual DoD screenshots + operator walkthrough remain gated. US-040J reopen and US-040K density not delivered. US-040G/H Story accepted remain separately gated.

**UX intent (normative)**

- The operator’s mental model is **local wall time** and **local calendar days**.
- UTC MAY remain the storage and wire format, but MUST NOT be the primary visible clock for routine work.
- Week and Month day columns/cells MUST bucket events by **local calendar date**, not UTC date (avoid “event appears on the wrong day”).
- Reschedule pickers MUST default to and display local time; labels SHOULD show the timezone abbreviation (e.g. `CST`) so the operator knows which clock is in force.
- “Must be in the future” validation MUST be explained in local terms (“must be after now in your local time”) while the worker continues to enforce absolute-time safety.
- Moving an event earlier than its previous schedule MUST be allowed when the new local time is still after now (UI MUST NOT falsely imply “only later than the old schedule”).

**Visual DoD / Story acceptance gate**

Required scenes (desktop + mobile): local times on Week/Month/modal with timezone cue; near-midnight day placement; reschedule earlier-but-still-future; proof that routine UI does not force UTC thinking.
**MUST NOT** mark Story accepted without operator walkthrough confirming local-time UX feels coherent in the operator’s timezone (shared DoD above).

**Acceptance criteria**

- [x] All primary schedule displays in Week, Month, and event modal use operator-local date/time with visible timezone cue. — Demonstrated via Vitest DOM (Week/Month/EventModal local formatting + timezone cue; not Visual DoD).
- [x] Week/Month placement uses local-day bucketing; document any remaining UTC-only diagnostics as secondary. — Demonstrated: near-midnight fixture places on local day; UTC day only under EventModal diagnostics.
- [x] Schedule editor datetime controls are local-first; conversion to `*_utc` fields happens at the API boundary. — Demonstrated: picker round-trip Vitest (`new_scheduled_at_utc`).
- [x] Validation copy and client-side guards match “strictly after now” in absolute time, presented as local; earlier-than-previous-schedule moves are allowed when still future. — Demonstrated via Vitest.
- [x] Empty/error states never instruct the operator to “think in UTC” for routine edits. — Demonstrated: ScheduleEditor help + error map assertions.
- [ ] Capture Visual DoD evidence (desktop + mobile) for the scenes listed above; Vitest alone is insufficient for Story accepted.
- [ ] Operator walkthrough completed on deployed or agreed preview; operator confirms local-time UX meets intent before Story accepted.
- [x] The outcome is visible and understandable to the intended user. — Demonstrated at console-layer via Vitest; operator confirmation still gated.
- [x] Failures or blocked states are clearly communicated (`*_time_invalid` mapped to plain language). — Demonstrated: error map remapped to local-language copy.
- [x] Existing completed work is not duplicated or unintentionally changed (worker UTC contracts preserved unless a paired OpenSpec change extends them). — Demonstrated: prior Week/Month/EventModal/ScheduleEditor/session suites still pass; `*_utc` wire fields unchanged.

### US-040J — Implement Flow A LinkedIn Variant Supervision Console: Cancelled Event Handling

**Description**

As a content operator, I want cancelled calendar events to be visually honest and actionable (or clearly non-actionable), so that when I see a cancelled item on today/this week I understand **why** and what I can do next — including reopen/reschedule when product allows — instead of a mute grey chip with no path.

**Status:** Not started. **Not Story accepted; BL-015 remains open.** Requires OpenSpec for any worker reopen path; cancel remains irreversible until this story ships an approved reopen contract.

**UX intent (normative)**

- Cancelled events MUST remain visible on Week/Month with a distinct but calm treatment (not alarming like failed/blocked).
- Opening a cancelled event modal MUST answer three questions in plain language: **What is this?** **Why is it cancelled?** **What can I do now?**
- If reopen is not yet available mid-implementation, the modal MUST say so explicitly and avoid fake Edit controls.
- When reopen/reschedule is implemented, the happy path MUST feel like restoring a planned publication: confirm → choose new local time (respecting future + density rules) → toast success → event returns to an editable pending/planned state on the calendar.
- Never imply cancelled ≡ LinkedIn API published or unpublished confusion; keep qualified language.

**Visual DoD / Story acceptance gate**

Required scenes (desktop + mobile): cancelled chip on Week/Month; cancelled modal answering what/why/what next; reopen/reschedule happy path (or explicit interim read-only copy); failure toast; mobile cancelled modal.
**MUST NOT** mark Story accepted without operator walkthrough confirming cancelled items are understandable and the approved next action is obvious (shared DoD above).

**Acceptance criteria**

- [ ] Cancelled events are visible on Week/Month with clear cancelled styling and label.
- [ ] Event modal for cancelled items explains cancellation (reason/source/timestamp when available) in operator language; raw codes only in diagnostics.
- [ ] Define and implement an approved **reopen or reschedule-from-cancelled** path via worker HTTP (new or extended contract under OpenSpec) OR, if temporarily deferred inside the same change, ship an explicit read-only cancelled modal — do not leave “mystery cancelled” UX. Prefer shipping the reopen/reschedule path as the business outcome of this story.
- [ ] Reopened items MUST reappear as editable supervision targets (pending/planned as applicable) and respect dry-run/confirm, local time, and density limits (US-040I/K).
- [ ] Cancel from an active event remains destructive, confirmed, and irreversible except through the new reopen path.
- [ ] Capture Visual DoD evidence (desktop + mobile) for the scenes listed above; Vitest alone is insufficient for Story accepted.
- [ ] Operator walkthrough completed on deployed or agreed preview; operator confirms cancelled-event UX meets intent before Story accepted.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed (no silent bypass of publication guards; no n8n Execute Command).

### US-040K — Implement Flow A LinkedIn Variant Supervision Console: Max Two Publications Per Local Day

**Description**

As a content operator, I want the console and schedule rules to **cap publications at two per local calendar day**, so that I cannot accidentally look like a spammer by stacking three or more posts on the same day.

**Status:** Not started. **Not Story accepted; BL-015 remains open.** Interim product rule for BL-015; BL-021 MAY later supersede with richer cadence windows.

**UX intent (normative)**

- Density is a **first-class UX concern**: days at/over the limit MUST be visually readable on Week and Month (e.g. subtle full/warn treatment) without alarm fatigue.
- When rescheduling would create a **third** publication on a local day, the modal MUST block or require an explicit resolution path **before** commit — with plain language (“This day already has 2 publications”).
- Counting rules MUST be operator-obvious: which channels/states count (at minimum LinkedIn variants that are still part of the live plan — pending/queued/deferred/planned as defined in the OpenSpec change; cancelled and published-historical handling MUST be specified explicitly so counts do not surprise the operator).
- Prefer prevention in the picker (disable or warn on saturated days) over cryptic worker codes after submit.
- Toast/modal errors for saturation MUST be human, not only `*_saturation` codes.

**Visual DoD / Story acceptance gate**

Required scenes (desktop + mobile): local day at 2 publications (full cue); attempt to place a 3rd (plain-language block); Month density cue; existing 3+ day still visible with fix path; local-midnight boundary.
**MUST NOT** mark Story accepted without operator walkthrough confirming the density rule is obvious and prevents a spammy plan (shared DoD above).

**Acceptance criteria**

- [ ] Enforce a maximum of **2** publications per **operator-local** calendar day for items in scope of the supervision plan (exact inclusion set defined in the OpenSpec change; default intent: live planned LinkedIn — and blog if shown — excluding cancelled unless reopen restores them).
- [ ] Week/Month MUST surface day density so a day with 2 items looks “full” and a conflict attempt is understandable before commit.
- [ ] Reschedule/defer/reopen flows MUST validate the cap client-side and server-side; exceeding 2 MUST fail closed with actionable messaging.
- [ ] Existing days that already have 3+ items MUST remain visible (do not hide history) and SHOULD offer a clear path to fix density by moving events (modal actions), not silent data loss.
- [ ] Interim duplicate-slot / 72h sibling rules MAY remain until BL-021 supersedes; this story’s **2/local-day** cap is additive and MUST be documented as interim product policy.
- [ ] Do not call LinkedIn API publish as part of density enforcement.
- [ ] Capture Visual DoD evidence (desktop + mobile) for the scenes listed above; Vitest alone is insufficient for Story accepted.
- [ ] Operator walkthrough completed on deployed or agreed preview; operator confirms max-2 density UX meets intent before Story accepted.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-016 — Define Flow B

**Priority:** P4

**Business context:** Define the complete business process for system-generated content that requires human review.

### US-041 — Define Flow B: Story 1

**Description**

As a content reviewer, I want to define idea sources, so that flow b has an approved business process and clear human approval boundaries.

**Acceptance criteria**

- [ ] Define idea sources.
- [ ] Define draft generation.
- [ ] Define review, revision, approval, and rejection.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-042 — Define Flow B: Story 2

**Description**

As a content reviewer, I want to define publication eligibility, so that flow b has an approved business process and clear human approval boundaries.

**Acceptance criteria**

- [ ] Define publication eligibility.
- [ ] Define calendar integration.
- [ ] Prevent automatic publication without approval.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-017 — Generate Blog Drafts for Flow B

**Priority:** P4

**Business context:** Create high-quality blog drafts from approved ideas while preserving Silverio's voice and editorial standards.

### US-043 — Generate Blog Drafts for Flow B: Story 1

**Description**

As a content reviewer, I want to generate complete blog drafts, so that the system produces review-ready flow b blog drafts.

**Acceptance criteria**

- [ ] Generate complete blog drafts.
- [ ] Follow the editorial canon.
- [ ] Include required metadata and structure.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-044 — Generate Blog Drafts for Flow B: Story 2

**Description**

As a content reviewer, I want to create or request an image, so that the system produces review-ready flow b blog drafts.

**Acceptance criteria**

- [ ] Create or request an image.
- [ ] Save the result for review.
- [ ] Prevent automatic publication.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-018 — Implement Flow B Review and Approval

**Priority:** P4

**Business context:** Support human review and approval of system-generated content.

### US-045 — Implement Flow B Review and Approval: Story 1

**Description**

As a content reviewer, I want to present drafts for review, so that flow b content cannot proceed to publication without recorded approval.

**Acceptance criteria**

- [ ] Present drafts for review.
- [ ] Capture feedback.
- [ ] Apply revisions.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-046 — Implement Flow B Review and Approval: Story 2

**Description**

As a content reviewer, I want to approve or reject content, so that flow b content cannot proceed to publication without recorded approval.

**Acceptance criteria**

- [ ] Approve or reject content.
- [ ] Keep revision history.
- [ ] Promote approved content to publication eligibility.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-019 — Integrate Flow B with the Editorial Calendar

**Priority:** P4

**Business context:** Plan Flow B content alongside approved Flow A content.

### US-047 — Integrate Flow B with the Editorial Calendar: Story 1

**Description**

As a content reviewer, I want to schedule topics, so that flow b content is visible and manageable in the editorial calendar.

**Acceptance criteria**

- [ ] Schedule topics.
- [ ] Assign target dates.
- [ ] Avoid thematic duplication.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-048 — Integrate Flow B with the Editorial Calendar: Story 2

**Description**

As a content reviewer, I want to balance audiences, so that flow b content is visible and manageable in the editorial calendar.

**Acceptance criteria**

- [ ] Balance audiences.
- [ ] Coordinate blog and LinkedIn timing.
- [ ] Keep approval mandatory before publication.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-020 — Create the Editorial Content Backlog

**Priority:** P5

**Business context:** Maintain a prioritized business backlog of future content topics.

### US-049 — Create the Editorial Content Backlog: Story 1

**Description**

As a editorial manager, I want to capture topic, audience, objective, format, priority, status, and target date, so that the content pipeline has a clear, prioritized source of future topics.

**Acceptance criteria**

- [ ] Capture topic, audience, objective, format, priority, status, and target date.
- [ ] Link blog topics to potential LinkedIn derivatives.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-050 — Create the Editorial Content Backlog: Story 2

**Description**

As a editorial manager, I want to identify dependencies, so that the content pipeline has a clear, prioritized source of future topics.

**Acceptance criteria**

- [ ] Identify dependencies.
- [ ] Support prioritization and reprioritization.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-021 — Define Editorial Calendar and Publishing Cadence

**Priority:** P5

**Business context:** Establish a sustainable publishing rhythm for the blog and LinkedIn.

### US-051 — Define Editorial Calendar and Publishing Cadence: Story 1

**Description**

As a editorial manager, I want to define blog frequency, so that publications follow an approved cadence that avoids saturation and redundancy.

**Acceptance criteria**

- [ ] Define blog frequency.
- [ ] Define LinkedIn frequency.
- [ ] Define spacing between variants.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-052 — Define Editorial Calendar and Publishing Cadence: Story 2

**Description**

As a editorial manager, I want to define publishing windows, so that publications follow an approved cadence that avoids saturation and redundancy.

**Acceptance criteria**

- [ ] Define publishing windows.
- [ ] Balance audience segments.
- [ ] Define rescheduling rules.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-022 — Define Business and Content Metrics

**Priority:** P5

**Business context:** Measure whether the content program supports Silverio's professional goals.

### US-053 — Define Business and Content Metrics: Story 1

**Description**

As a business owner, I want to define blog traffic metrics, so that the content program has measurable business and editorial outcomes.

**Acceptance criteria**

- [ ] Define blog traffic metrics.
- [ ] Define LinkedIn reach and engagement metrics.
- [ ] Track profile visits and audience growth.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-054 — Define Business and Content Metrics: Story 2

**Description**

As a business owner, I want to track recruiter and executive conversations, so that the content program has measurable business and editorial outcomes.

**Acceptance criteria**

- [ ] Track recruiter and executive conversations.
- [ ] Track job and consulting opportunities.
- [ ] Identify high-performing topics and formats.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-023 — Use Performance Feedback to Improve Future Content

**Priority:** P5

**Business context:** Turn performance data into better editorial decisions.

### US-055 — Use Performance Feedback to Improve Future Content: Story 1

**Description**

As a business owner, I want to collect metrics consistently, so that future editorial decisions are informed by evidence rather than intuition alone.

**Acceptance criteria**

- [ ] Collect metrics consistently.
- [ ] Compare themes and variants.
- [ ] Identify effective formats.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-056 — Use Performance Feedback to Improve Future Content: Story 2

**Description**

As a business owner, I want to feed insights into future planning, so that future editorial decisions are informed by evidence rather than intuition alone.

**Acceptance criteria**

- [ ] Feed insights into future planning.
- [ ] Reduce repetition of low-performing content.
- [ ] Keep human oversight over strategic changes.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-024 — Rotate and Review Operational Secrets

**Priority:** P6

**Business context:** Ensure operational credentials remain secure and appropriately managed.

### US-057 — Rotate and Review Operational Secrets: Story 1

**Description**

As a system owner, I want to rotate keys that may have been exposed during testing, so that operational secrets are current, protected, and auditable.

**Acceptance criteria**

- [ ] Rotate keys that may have been exposed during testing.
- [ ] Verify secure storage.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-058 — Rotate and Review Operational Secrets: Story 2

**Description**

As a system owner, I want to review permissions, so that operational secrets are current, protected, and auditable.

**Acceptance criteria**

- [ ] Review permissions.
- [ ] Confirm secrets are absent from Git, logs, and workflow exports.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-059 — Rotate and Review Operational Secrets: Story 3

**Description**

As a system owner, I want to define ownership and rotation cadence, so that operational secrets are current, protected, and auditable.

**Acceptance criteria**

- [ ] Define ownership and rotation cadence.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-025 — Formalize LinkedIn Token Management

**Priority:** P6

**Business context:** Define the full lifecycle of LinkedIn authentication tokens.

### US-060 — Formalize LinkedIn Token Management: Story 1

**Description**

As a content operator, I want to store tokens securely, so that linkedin token management is secure, predictable, and recoverable.

**Acceptance criteria**

- [ ] Store tokens securely.
- [ ] Handle renewal and expiration.
- [ ] Support revocation.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-061 — Formalize LinkedIn Token Management: Story 2

**Description**

As a content operator, I want to detect invalid tokens, so that linkedin token management is secure, predictable, and recoverable.

**Acceptance criteria**

- [ ] Detect invalid tokens.
- [ ] Separate development and production credentials.
- [ ] Document recovery.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-026 — Review Service Permissions and Exposure

**Priority:** P6

**Business context:** Reduce the attack surface of the worker, n8n, ComfyUI, Docker, shared filesystem, and public checkout.

### US-062 — Review Service Permissions and Exposure: Story 1

**Description**

As a system owner, I want to apply least privilege, so that services and files are exposed only as required for operation.

**Acceptance criteria**

- [ ] Apply least privilege.
- [ ] Review open ports.
- [ ] Review authentication.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-063 — Review Service Permissions and Exposure: Story 2

**Description**

As a system owner, I want to review allowed paths, so that services and files are exposed only as required for operation.

**Acceptance criteria**

- [ ] Review allowed paths.
- [ ] Separate secrets.
- [ ] Document accepted exposure.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-027 — Correct Stale Flow A Readiness Defaults

**Priority:** P7

**Business context:** Remove obsolete revision assumptions from readiness validation.

### US-064 — Correct Stale Flow A Readiness Defaults: Story 1

**Description**

As a content operator, I want to identify stale expected revisions, so that flow a readiness checks remain accurate as the repository evolves.

**Acceptance criteria**

- [x] Identify stale expected revisions.
- [x] Replace brittle commit assumptions.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

### US-065 — Correct Stale Flow A Readiness Defaults: Story 2

**Description**

As a content operator, I want to avoid false failures, so that flow a readiness checks remain accurate as the repository evolves.

**Acceptance criteria**

- [x] Avoid false failures.
- [x] Preserve valid readiness checks.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

### US-066 — Correct Stale Flow A Readiness Defaults: Story 3

**Description**

As a content operator, I want to document the new baseline, so that flow a readiness checks remain accurate as the repository evolves.

**Acceptance criteria**

- [x] Document the new baseline.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

## BL-028 — Establish a Warning and Test Quality Baseline

**Priority:** P7

**Business context:** Create a known baseline for test-suite warnings and code-quality signals.

### US-067 — Establish a Warning and Test Quality Baseline: Story 1

**Description**

As a content operator, I want to run the full suite, so that the team can identify whether a change introduces new quality problems.

**Acceptance criteria**

- [ ] Run the full suite.
- [ ] Inventory warnings.
- [ ] Correct root causes where possible.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-068 — Establish a Warning and Test Quality Baseline: Story 2

**Description**

As a content operator, I want to separate inherited warnings from new warnings, so that the team can identify whether a change introduces new quality problems.

**Acceptance criteria**

- [ ] Separate inherited warnings from new warnings.
- [ ] Document the baseline.
- [ ] Maintain zero new warnings.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-029 — Establish Continuous Integration

**Priority:** P7

**Business context:** Run repository validation automatically on proposed changes.

### US-069 — Establish Continuous Integration: Story 1

**Description**

As a content operator, I want to run tests, so that invalid changes are detected before they reach the main branch.

**Acceptance criteria**

- [ ] Run tests.
- [ ] Validate specifications.
- [ ] Validate YAML and JSON.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-070 — Establish Continuous Integration: Story 2

**Description**

As a content operator, I want to check whitespace and repository consistency, so that invalid changes are detected before they reach the main branch.

**Acceptance criteria**

- [ ] Check whitespace and repository consistency.
- [ ] Scan for secrets.
- [ ] Block invalid changes.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-030 — Maintain Current Project and Runtime Context

**Priority:** P7

**Business context:** Keep business, technical, and operational documentation aligned with reality.

### US-071 — Maintain Current Project and Runtime Context: Story 1

**Description**

As a content operator, I want to update current-state documentation when capabilities change, so that project context remains accurate, current, and trustworthy.

**Acceptance criteria**

- [ ] Update current-state documentation when capabilities change.
- [ ] Update runtime state after deployment or live validation.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-072 — Maintain Current Project and Runtime Context: Story 2

**Description**

As a content operator, I want to detect contradictions, so that project context remains accurate, current, and trustworthy.

**Acceptance criteria**

- [ ] Detect contradictions.
- [ ] Prevent historical documents from being treated as current.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-073 — Maintain Current Project and Runtime Context: Story 3

**Description**

As a content operator, I want to keep cursor and repository guidance aligned, so that project context remains accurate, current, and trustworthy.

**Acceptance criteria**

- [ ] Keep Cursor and repository guidance aligned.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-031 — Persist Editorial Calendar in Database

**Priority:** P1

**Business context:** After the 2026-07-18 deploy wipe of `calendar.json`, master calendar schedule state must not live solely on the editorial filesystem.

### US-041 — Persist Editorial Calendar in `silverman_linkedin_db`

**Status:** Implemented and live cutover smoke on `192.168.0.194:8010` (DB `silverman_linkedin_db`; health `calendar_store_ready=true`). **Not Story accepted.** Does not restore historically wiped calendar rows.

**Description**

As a system operator, I want the master editorial calendar stored in PostgreSQL database `silverman_linkedin_db`, so that schedule state survives editorial mount wipe and code deploy sync.

**Acceptance criteria**

- [ ] Create/use PostgreSQL database named exactly `silverman_linkedin_db` (not a schema inside another app DB).
- [ ] Calendar load/save for plan, status, schedule-update, and schedule-visibility uses the database as source of truth.
- [ ] Calendar APIs fail closed when the database is unavailable (no silent `calendar.json` fallback as SoT).
- [ ] Operator-gated import from legacy `calendar.json` works when the DB is empty and refuses to clobber a non-empty DB.
- [ ] Secrets (DB URL/password) never appear in HTTP responses or logs.
- [ ] Existing completed work is not duplicated or unintentionally changed (HTTP paths stable; blog/LinkedIn Markdown remain files).
