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

**Status:** Policy defined (docs + canonical spec, 2026-07-16) — policy defined ≠ operationally validated; story not accepted as complete; BL-008 remains open until US-022.

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

**Status:** Implemented + unit-tested (2026-07-16) — not deployed, not operationally validated; story **not accepted**; BL-008 remains open pending post-implementation review.

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

**Status:** Operationally validated (2026-07-17) on `192.168.0.194` (`BUILD_REVISION=d15d85b`) — story acceptance pending operator confirmation; BL-009 remains open (US-024/US-025 pending).

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

**Status:** Procedure defined (2026-07-17) — not operationally validated; story **not accepted**; BL-009 remains open. No worker code: US-024 is an operator procedure + evidence-capture story (docs + canonical procedure-spec only). Acceptance requires operator demonstration of the procedure on a real campaign, which depends on the pending US-023 deploy + operational validation on `192.168.0.194` (archived US-023 task 6.2, still pending).

**Description**

As a content operator, I want to confirm preview behavior on linkedin, so that published linkedin posts display the intended article preview.

**Operator procedure:** [linkedin-preview-rendering-confirmation.md](../operations/linkedin-preview-rendering-confirmation.md)

**Acceptance criteria** (mapped at procedure-defined scope only; none operationally demonstrated)

- [ ] Confirm preview behavior on LinkedIn. — Mechanism: two documented observation points — pre-publish LinkedIn Post Inspector inspection of the campaign's `public_url` and post-publish observation of the real post via stored `linkedin_post_urn` — compared against recorded `linkedin_package.article_preview` metadata (procedure §"Observation points"; spec requirement "Rendering confirmation procedure").
- [ ] Identify cache or metadata issues. — Mechanism: decision matrix keyed on the US-023 input verification result × observed LinkedIn rendering, distinguishing `preview_stale_cache` (inputs pass, card wrong — safe Post Inspector re-scrape, new posts only) from `preview_inputs_incorrect` (US-023 failed — remediate per `linkedin_preview_validation_*` codes) in every case (procedure §"Decision matrix" and §"Safe re-scrape procedure"; spec requirements "Cache vs input decision matrix" and "Safe re-scrape procedure").
- [ ] The outcome is visible and understandable to the intended user. — Mechanism: fixed documented outcome vocabulary (`preview_confirmed`, `preview_stale_cache`, `preview_inputs_incorrect`, `preview_not_rendered_post_format`, `confirmation_blocked`) plus a per-confirmation evidence-record template (campaign id, `public_url`, US-023 run reference, observations with UTC timestamps, outcome label, operator); no worker codes — labels are documented checklist values (procedure §"Evidence record template"; spec requirement "Outcome vocabulary and evidence record").
- [ ] Failures or blocked states are clearly communicated. — Mechanism: decision matrix routes US-023 `failed` to `preview_inputs_incorrect` (remediate per `linkedin_preview_validation_*` codes; no LinkedIn observation); blocked-state table covers only true blocked conditions (US-023 not run / not trusted, site not live, Post Inspector unavailable, no published variant for post-publish observation) recorded as `confirmation_blocked`, never as input or rendering failures (procedure §"Decision matrix" and §"Blocked states"; spec requirements "Cache vs input decision matrix" and "Blocked states and operator communication").
- [ ] Existing completed work is not duplicated or unintentionally changed. — Mechanism: zero changes under `src/`, `tests/`, `n8n/`, `deploy/`; US-023 endpoint consumed as the sole input-truth source (no input check re-defined); package generation, publication, variant states, scheduling, and US-022 semantics untouched; no new env vars, no LinkedIn API usage (spec requirements "Scope, actors, and boundaries" and "Existing capabilities unchanged").

**Defined:** 2026-07-17 — procedure + canonical procedure-spec only; procedure defined does not mean operationally validated or accepted. Criteria checkboxes remain unchecked until the operator demonstrates the procedure end-to-end on a real campaign (passing US-023 real run, Post Inspector confirmation, decision-matrix classification, completed evidence record). US-025 (fallback when the preview is incorrect) remains a separate open story; `preview_not_rendered_post_format` is recorded as an observation only.

### US-025 — Validate LinkedIn Article Preview Rendering: Story 3

**Status:** Policy defined (2026-07-17) — not operationally validated; story **not accepted**; BL-009 remains open. No worker code: US-025 is an operator fallback-policy story (docs + canonical procedure-spec only). Acceptance requires operator demonstration of a fallback decision with a completed evidence record on a real campaign, which depends on the pending US-023 deploy + operational validation on `192.168.0.194` and a US-024 confirmation producing a fallback-triggering outcome.

**Description**

As a content operator, I want to define a fallback when the preview is incorrect, so that published linkedin posts display the intended article preview.

**Operator policy:** [linkedin-preview-fallback-policy.md](../operations/linkedin-preview-fallback-policy.md)

**Acceptance criteria** (mapped at policy-definition scope only; none operationally demonstrated)

- [ ] Define a fallback when the preview is incorrect. — Mechanism: normative fallback decision policy triggered only by recorded US-024 outcomes (`preview_stale_cache` after a completed safe re-scrape cycle; `preview_not_rendered_post_format`; published post retaining a stale/incorrect card), split into a pre-publish procedure (accept / delay via `POST /defer-linkedin-variant` / correct inputs and repeat US-023/US-024 / cancel via `POST /cancel-linkedin-publication`) and a post-publish recovery procedure (accept-and-record default; approval-gated manual post removal; evidence mutation forbidden), all over existing guarded endpoints (policy §"Fallback triggers", §"Pre-publish fallback decision procedure", §"Post-publish recovery decision procedure"; spec requirements "Fallback triggers are recorded US-024 outcomes", "Pre-publish fallback decision procedure", "Post-publish recovery decision procedure").
- [ ] The outcome is visible and understandable to the intended user. — Mechanism: single supported / approval-gated / forbidden classification table with safety rationale (including the delete/re-post analysis and two named deferred future-change candidates with preconditions), fixed fallback outcome vocabulary (`fallback_accept_rendering`, `fallback_delay_publication`, `fallback_correct_inputs_reverify`, `fallback_cancel_variant`, `fallback_post_removal_approved`, `fallback_format_change_deferred`, `fallback_blocked`), and a per-decision evidence-record template; no worker codes — labels are documented checklist values (policy §"Action classification" and §"Fallback outcome vocabulary"; spec requirements "Supported, approval-gated, and forbidden actions" and "Fallback outcome vocabulary and evidence record").
- [ ] Failures or blocked states are clearly communicated. — Mechanism: blocked-state table with named conditions and next actions (no triggering US-024 record; re-scrape cycle incomplete; approval absent for a gated action; unapproved required live-site Git push; action invalid for the variant's `publish_state`), recorded as `fallback_blocked` — never as failures of inputs, rendering, or the policy, and never resolved by guessing (policy §"Blocked states"; spec requirement "Blocked states and operator communication").
- [ ] Existing completed work is not duplicated or unintentionally changed. — Mechanism: zero changes under `src/`, `tests/`, `n8n/`, `deploy/`; US-023 consumed as the sole input-truth source and US-024 as the sole rendering-observation source (no check or observation re-defined); no retry-budget consumption, no `recovery_confirmation` repurposing, US-020 sequence/cadence and scheduling idempotency untouched, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` fail-closed; no MODIFIED requirements on US-018–US-024 capabilities (policy §"Purpose and boundaries" and §"Duplicate prevention and safeguard preservation"; spec requirements "Scope, actors, and boundaries", "Duplicate prevention and safeguard preservation", "Existing capabilities unchanged").

**Defined:** 2026-07-17 — policy + canonical procedure-spec only; policy defined does not mean operationally validated or accepted. Criteria checkboxes remain unchecked until the operator demonstrates a fallback decision end-to-end on a real campaign (recorded triggering US-024 outcome, decision per the policy, completed fallback evidence record with a fixed outcome label). BL-009 remains open until US-023, US-024, and US-025 business outcomes are all demonstrated and accepted.

## BL-010 — Add Operational Observability

**Priority:** P3

**Business context:** Provide a consolidated view of Flow A execution health and campaign status.

### US-026 — Add Operational Observability: Story 1

**Description**

As a system operator, I want to identify successful and failed executions, so that operators can understand system health and campaign progress from one clear operational view.

**Acceptance criteria**

- [ ] Identify successful and failed executions.
- [ ] Identify blocked or stale campaigns.
- [ ] Show delayed calendar items.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-027 — Add Operational Observability: Story 2

**Description**

As a system operator, I want to capture stage duration, so that operators can understand system health and campaign progress from one clear operational view.

**Acceptance criteria**

- [ ] Capture stage duration.
- [ ] Surface failures by external dependency.
- [ ] Allow status review without opening multiple raw files.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-011 — Add Operational Alerts

**Priority:** P3

**Business context:** Notify the operator when the system requires attention.

### US-028 — Add Operational Alerts: Story 1

**Description**

As a system operator, I want to alert on items moved to error, so that important failures and blocked states generate timely, actionable alerts.

**Acceptance criteria**

- [ ] Alert on items moved to error.
- [ ] Alert on image-generation failure.
- [ ] Alert on blog publication failure.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-029 — Add Operational Alerts: Story 2

**Description**

As a system operator, I want to alert on partial calendar execution, so that important failures and blocked states generate timely, actionable alerts.

**Acceptance criteria**

- [ ] Alert on partial calendar execution.
- [ ] Alert on LinkedIn token or publication failure.
- [ ] Alert on stale campaigns.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-030 — Add Operational Alerts: Story 3

**Description**

As a system operator, I want to alert on unhealthy worker or failed n8n workflow, so that important failures and blocked states generate timely, actionable alerts.

**Acceptance criteria**

- [ ] Alert on unhealthy worker or failed n8n workflow.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-012 — Consolidate Recovery for Incomplete Campaigns

**Priority:** P3

**Business context:** Provide a consistent recovery model for campaigns that stop before completion.

### US-031 — Consolidate Recovery for Incomplete Campaigns: Story 1

**Description**

As a system operator, I want to identify the last valid stage, so that incomplete campaigns can be resumed or repaired safely and predictably.

**Acceptance criteria**

- [ ] Identify the last valid stage.
- [ ] Resume without repeating successful work.
- [ ] Repair inconsistent metadata.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-032 — Consolidate Recovery for Incomplete Campaigns: Story 2

**Description**

As a system operator, I want to classify recovery actions, so that incomplete campaigns can be resumed or repaired safely and predictably.

**Acceptance criteria**

- [ ] Classify recovery actions.
- [ ] Preserve attempt history.
- [ ] Support safe cancellation when recovery is not appropriate.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-013 — Validate Concurrency and Duplicate Execution Protection

**Priority:** P3

**Business context:** Ensure that simultaneous or repeated triggers cannot process the same content twice.

### US-033 — Validate Concurrency and Duplicate Execution Protection: Story 1

**Description**

As a system operator, I want to prevent duplicate post processing, so that concurrent triggers do not create duplicate artifacts or external publications.

**Acceptance criteria**

- [ ] Prevent duplicate post processing.
- [ ] Prevent duplicate image generation.
- [ ] Prevent duplicate blog publication.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-034 — Validate Concurrency and Duplicate Execution Protection: Story 2

**Description**

As a system operator, I want to prevent duplicate scheduling, so that concurrent triggers do not create duplicate artifacts or external publications.

**Acceptance criteria**

- [ ] Prevent duplicate scheduling.
- [ ] Prevent duplicate LinkedIn publication.
- [ ] Recover abandoned processing claims.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-035 — Validate Concurrency and Duplicate Execution Protection: Story 3

**Description**

As a system operator, I want to validate behavior during restarts, so that concurrent triggers do not create duplicate artifacts or external publications.

**Acceptance criteria**

- [ ] Validate behavior during restarts.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-014 — Establish Backup and Restore for Editorial State

**Priority:** P3

**Business context:** Protect the files and metadata required to recover the editorial system.

### US-036 — Establish Backup and Restore for Editorial State: Story 1

**Description**

As a system operator, I want to define backup scope, so that editorial state can be restored from a verified backup.

**Acceptance criteria**

- [ ] Define backup scope.
- [ ] Define retention.
- [ ] Verify backup integrity.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-037 — Establish Backup and Restore for Editorial State: Story 2

**Description**

As a system operator, I want to test restoration, so that editorial state can be restored from a verified backup.

**Acceptance criteria**

- [ ] Test restoration.
- [ ] Document the recovery procedure.
- [ ] Protect calendar, campaigns, runs, posts, images, and LinkedIn artifacts.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-015 — Implement Flow A LinkedIn Variant Supervision Console

**Priority:** P3

**Business context:** Provide an operator-facing console to supervise Flow A LinkedIn variants after distribution scheduling and before LinkedIn API publication, per [linkedin-variant-review-policy.md](../operations/linkedin-variant-review-policy.md).

**Prerequisites:** BL-006 US-015 (policy defined). US-017 SHOULD supply persisted edit/cancel/defer mechanics before console actions constrain BL-007 eligibility.

### US-038 — Implement Flow A LinkedIn Variant Supervision Console: Story 1

**Description**

As a content operator, I want to see Flow A LinkedIn variants on a calendar or campaign view while they are pending, so that I can supervise scheduled publication without inspecting raw files.

**Acceptance criteria**

- [ ] Present `pending` variants with campaign id, variant id, audience, `scheduled_at_utc`, and `publish_state`.
- [ ] Align the view with the editorial calendar where applicable.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-039 — Implement Flow A LinkedIn Variant Supervision Console: Story 2

**Description**

As a content operator, I want to edit variant text and adjust scheduled timing before queue, so that I can correct derivatives during the optional supervision window.

**Acceptance criteria**

- [ ] Edit variant content before queue authorization.
- [ ] Defer or reschedule relative to distribution strategy rules.
- [ ] Persist operator changes traceably (aligned with US-017 when implemented).
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-040 — Implement Flow A LinkedIn Variant Supervision Console: Story 3

**Description**

As a content operator, I want to cancel or defer variants and see why publication is blocked, so that operator overrides constrain future BL-007 auto-queue eligibility.

**Acceptance criteria**

- [ ] Cancel or defer variants before queue per the LinkedIn variant review policy.
- [ ] Surface blocked states (publication enablement, integration failures, deferred capabilities).
- [ ] Invoke worker capabilities over HTTP only (ADR-0001); do not bypass publication guards.
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
