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

**Validated:** 2026-07-15 — [us-011 LinkedIn publication-guard validation](../operations/us-011-linkedin-publication-guard-validation-2026-07-15.md). Baseline `true` → temporary `false` → fail-closed `linkedin_publish_not_enabled` → restore `true`. Flow A has no LinkedIn API nodes/paths. Not permanent LinkedIn-off; BL-005 remains open.

## BL-005 — Run a Fully Unattended Flow A Test

**Priority:** P1

**Business context:** Demonstrate that a new approved blog post can move through Flow A without technical intervention.

### US-012 — Run a Fully Unattended Flow A Test: Story 1

**Description**

As a content operator, I want to accept a new markdown post from the ready folder, so that a new post completes the full unattended flow a path with traceable evidence.

**Acceptance criteria**

- [ ] Accept a new Markdown post from the ready folder.
- [ ] Generate and validate the image.
- [ ] Publish the blog post to the live site.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-013 — Run a Fully Unattended Flow A Test: Story 2

**Description**

As a content operator, I want to generate linkedin variants, so that a new post completes the full unattended flow a path with traceable evidence.

**Acceptance criteria**

- [ ] Generate LinkedIn variants.
- [ ] Schedule distribution.
- [ ] Complete the source lifecycle.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-014 — Run a Fully Unattended Flow A Test: Story 3

**Description**

As a content operator, I want to complete campaign and calendar records, so that a new post completes the full unattended flow a path with traceable evidence.

**Acceptance criteria**

- [ ] Complete campaign and calendar records.
- [ ] Require no technical intervention during execution.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-006 — Define the LinkedIn Variant Review Process

**Priority:** P2

**Business context:** Establish a clear business process for reviewing, approving, rejecting, or retaining generated LinkedIn variants.

### US-015 — Define the LinkedIn Variant Review Process: Story 1

**Description**

As a content operator, I want to define whether all variants may eventually be published, so that each linkedin variant has a clear review decision and publication purpose.

**Acceptance criteria**

- [ ] Define whether all variants may eventually be published.
- [ ] Define when review is mandatory.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-016 — Define the LinkedIn Variant Review Process: Story 2

**Description**

As a content operator, I want to establish quality and differentiation criteria, so that each linkedin variant has a clear review decision and publication purpose.

**Acceptance criteria**

- [ ] Establish quality and differentiation criteria.
- [ ] Associate each variant with an audience and objective.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-017 — Define the LinkedIn Variant Review Process: Story 3

**Description**

As a content operator, I want to support correction or rejection before queueing, so that each linkedin variant has a clear review decision and publication purpose.

**Acceptance criteria**

- [ ] Support correction or rejection before queueing.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-007 — Implement Scheduled LinkedIn Publication Execution

**Priority:** P2

**Business context:** Publish due LinkedIn variants automatically according to the approved editorial schedule.

**Implementation handoff:** Construction WIP for opt-in `auto_queue_pending` on `POST /publish-linkedin-due-variants` exists locally (not on `main`, not OpenSpec-approved). Absorb under this backlog item — see [bl-007-auto-queue-pending-handoff.md](bl-007-auto-queue-pending-handoff.md). Do not mark US-018–US-020 complete from that WIP alone.

### US-018 — Implement Scheduled LinkedIn Publication Execution: Story 1

**Description**

As a content operator, I want to identify due variants, so that due variants are published once, in order, with complete publication evidence.

**Acceptance criteria**

- [ ] Identify due variants.
- [ ] Move only eligible variants to queued state.
- [ ] Publish each variant once.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-019 — Implement Scheduled LinkedIn Publication Execution: Story 2

**Description**

As a content operator, I want to store the external publication identifier, so that due variants are published once, in order, with complete publication evidence.

**Acceptance criteria**

- [ ] Store the external publication identifier.
- [ ] Record failures clearly.
- [ ] Avoid retries that could create duplicates.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-020 — Implement Scheduled LinkedIn Publication Execution: Story 3

**Description**

As a content operator, I want to respect audience cadence and sequence, so that due variants are published once, in order, with complete publication evidence.

**Acceptance criteria**

- [ ] Respect audience cadence and sequence.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-008 — Define LinkedIn Retry and Recovery Rules

**Priority:** P2

**Business context:** Create safe business rules for handling LinkedIn publication failures and uncertain outcomes.

### US-021 — Define LinkedIn Retry and Recovery Rules: Story 1

**Description**

As a content operator, I want to classify recoverable and non-recoverable errors, so that linkedin failures can be recovered without losing traceability or duplicating content.

**Acceptance criteria**

- [ ] Classify recoverable and non-recoverable errors.
- [ ] Define token-renewal behavior.
- [ ] Prevent duplicate posts after timeouts.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-022 — Define LinkedIn Retry and Recovery Rules: Story 2

**Description**

As a content operator, I want to set retry limits, so that linkedin failures can be recovered without losing traceability or duplicating content.

**Acceptance criteria**

- [ ] Set retry limits.
- [ ] Preserve operational evidence.
- [ ] Support safe manual intervention.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-009 — Validate LinkedIn Article Preview Rendering

**Priority:** P2

**Business context:** Confirm that LinkedIn renders the expected title, description, image, and link preview.

### US-023 — Validate LinkedIn Article Preview Rendering: Story 1

**Description**

As a content operator, I want to verify title and description, so that published linkedin posts display the intended article preview.

**Acceptance criteria**

- [ ] Verify title and description.
- [ ] Verify image availability.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-024 — Validate LinkedIn Article Preview Rendering: Story 2

**Description**

As a content operator, I want to confirm preview behavior on linkedin, so that published linkedin posts display the intended article preview.

**Acceptance criteria**

- [ ] Confirm preview behavior on LinkedIn.
- [ ] Identify cache or metadata issues.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-025 — Validate LinkedIn Article Preview Rendering: Story 3

**Description**

As a content operator, I want to define a fallback when the preview is incorrect, so that published linkedin posts display the intended article preview.

**Acceptance criteria**

- [ ] Define a fallback when the preview is incorrect.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

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

## BL-015 — Define Flow B

**Priority:** P4

**Business context:** Define the complete business process for system-generated content that requires human review.

### US-038 — Define Flow B: Story 1

**Description**

As a content reviewer, I want to define idea sources, so that flow b has an approved business process and clear human approval boundaries.

**Acceptance criteria**

- [ ] Define idea sources.
- [ ] Define draft generation.
- [ ] Define review, revision, approval, and rejection.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-039 — Define Flow B: Story 2

**Description**

As a content reviewer, I want to define publication eligibility, so that flow b has an approved business process and clear human approval boundaries.

**Acceptance criteria**

- [ ] Define publication eligibility.
- [ ] Define calendar integration.
- [ ] Prevent automatic publication without approval.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-016 — Generate Blog Drafts for Flow B

**Priority:** P4

**Business context:** Create high-quality blog drafts from approved ideas while preserving Silverio's voice and editorial standards.

### US-040 — Generate Blog Drafts for Flow B: Story 1

**Description**

As a content reviewer, I want to generate complete blog drafts, so that the system produces review-ready flow b blog drafts.

**Acceptance criteria**

- [ ] Generate complete blog drafts.
- [ ] Follow the editorial canon.
- [ ] Include required metadata and structure.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-041 — Generate Blog Drafts for Flow B: Story 2

**Description**

As a content reviewer, I want to create or request an image, so that the system produces review-ready flow b blog drafts.

**Acceptance criteria**

- [ ] Create or request an image.
- [ ] Save the result for review.
- [ ] Prevent automatic publication.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-017 — Implement Flow B Review and Approval

**Priority:** P4

**Business context:** Support human review and approval of system-generated content.

### US-042 — Implement Flow B Review and Approval: Story 1

**Description**

As a content reviewer, I want to present drafts for review, so that flow b content cannot proceed to publication without recorded approval.

**Acceptance criteria**

- [ ] Present drafts for review.
- [ ] Capture feedback.
- [ ] Apply revisions.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-043 — Implement Flow B Review and Approval: Story 2

**Description**

As a content reviewer, I want to approve or reject content, so that flow b content cannot proceed to publication without recorded approval.

**Acceptance criteria**

- [ ] Approve or reject content.
- [ ] Keep revision history.
- [ ] Promote approved content to publication eligibility.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-018 — Integrate Flow B with the Editorial Calendar

**Priority:** P4

**Business context:** Plan Flow B content alongside approved Flow A content.

### US-044 — Integrate Flow B with the Editorial Calendar: Story 1

**Description**

As a content reviewer, I want to schedule topics, so that flow b content is visible and manageable in the editorial calendar.

**Acceptance criteria**

- [ ] Schedule topics.
- [ ] Assign target dates.
- [ ] Avoid thematic duplication.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-045 — Integrate Flow B with the Editorial Calendar: Story 2

**Description**

As a content reviewer, I want to balance audiences, so that flow b content is visible and manageable in the editorial calendar.

**Acceptance criteria**

- [ ] Balance audiences.
- [ ] Coordinate blog and LinkedIn timing.
- [ ] Keep approval mandatory before publication.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-019 — Create the Editorial Content Backlog

**Priority:** P5

**Business context:** Maintain a prioritized business backlog of future content topics.

### US-046 — Create the Editorial Content Backlog: Story 1

**Description**

As a editorial manager, I want to capture topic, audience, objective, format, priority, status, and target date, so that the content pipeline has a clear, prioritized source of future topics.

**Acceptance criteria**

- [ ] Capture topic, audience, objective, format, priority, status, and target date.
- [ ] Link blog topics to potential LinkedIn derivatives.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-047 — Create the Editorial Content Backlog: Story 2

**Description**

As a editorial manager, I want to identify dependencies, so that the content pipeline has a clear, prioritized source of future topics.

**Acceptance criteria**

- [ ] Identify dependencies.
- [ ] Support prioritization and reprioritization.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-020 — Define Editorial Calendar and Publishing Cadence

**Priority:** P5

**Business context:** Establish a sustainable publishing rhythm for the blog and LinkedIn.

### US-048 — Define Editorial Calendar and Publishing Cadence: Story 1

**Description**

As a editorial manager, I want to define blog frequency, so that publications follow an approved cadence that avoids saturation and redundancy.

**Acceptance criteria**

- [ ] Define blog frequency.
- [ ] Define LinkedIn frequency.
- [ ] Define spacing between variants.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-049 — Define Editorial Calendar and Publishing Cadence: Story 2

**Description**

As a editorial manager, I want to define publishing windows, so that publications follow an approved cadence that avoids saturation and redundancy.

**Acceptance criteria**

- [ ] Define publishing windows.
- [ ] Balance audience segments.
- [ ] Define rescheduling rules.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-021 — Define Business and Content Metrics

**Priority:** P5

**Business context:** Measure whether the content program supports Silverio's professional goals.

### US-050 — Define Business and Content Metrics: Story 1

**Description**

As a business owner, I want to define blog traffic metrics, so that the content program has measurable business and editorial outcomes.

**Acceptance criteria**

- [ ] Define blog traffic metrics.
- [ ] Define LinkedIn reach and engagement metrics.
- [ ] Track profile visits and audience growth.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-051 — Define Business and Content Metrics: Story 2

**Description**

As a business owner, I want to track recruiter and executive conversations, so that the content program has measurable business and editorial outcomes.

**Acceptance criteria**

- [ ] Track recruiter and executive conversations.
- [ ] Track job and consulting opportunities.
- [ ] Identify high-performing topics and formats.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-022 — Use Performance Feedback to Improve Future Content

**Priority:** P5

**Business context:** Turn performance data into better editorial decisions.

### US-052 — Use Performance Feedback to Improve Future Content: Story 1

**Description**

As a business owner, I want to collect metrics consistently, so that future editorial decisions are informed by evidence rather than intuition alone.

**Acceptance criteria**

- [ ] Collect metrics consistently.
- [ ] Compare themes and variants.
- [ ] Identify effective formats.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-053 — Use Performance Feedback to Improve Future Content: Story 2

**Description**

As a business owner, I want to feed insights into future planning, so that future editorial decisions are informed by evidence rather than intuition alone.

**Acceptance criteria**

- [ ] Feed insights into future planning.
- [ ] Reduce repetition of low-performing content.
- [ ] Keep human oversight over strategic changes.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-023 — Rotate and Review Operational Secrets

**Priority:** P6

**Business context:** Ensure operational credentials remain secure and appropriately managed.

### US-054 — Rotate and Review Operational Secrets: Story 1

**Description**

As a system owner, I want to rotate keys that may have been exposed during testing, so that operational secrets are current, protected, and auditable.

**Acceptance criteria**

- [ ] Rotate keys that may have been exposed during testing.
- [ ] Verify secure storage.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-055 — Rotate and Review Operational Secrets: Story 2

**Description**

As a system owner, I want to review permissions, so that operational secrets are current, protected, and auditable.

**Acceptance criteria**

- [ ] Review permissions.
- [ ] Confirm secrets are absent from Git, logs, and workflow exports.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-056 — Rotate and Review Operational Secrets: Story 3

**Description**

As a system owner, I want to define ownership and rotation cadence, so that operational secrets are current, protected, and auditable.

**Acceptance criteria**

- [ ] Define ownership and rotation cadence.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-024 — Formalize LinkedIn Token Management

**Priority:** P6

**Business context:** Define the full lifecycle of LinkedIn authentication tokens.

### US-057 — Formalize LinkedIn Token Management: Story 1

**Description**

As a content operator, I want to store tokens securely, so that linkedin token management is secure, predictable, and recoverable.

**Acceptance criteria**

- [ ] Store tokens securely.
- [ ] Handle renewal and expiration.
- [ ] Support revocation.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-058 — Formalize LinkedIn Token Management: Story 2

**Description**

As a content operator, I want to detect invalid tokens, so that linkedin token management is secure, predictable, and recoverable.

**Acceptance criteria**

- [ ] Detect invalid tokens.
- [ ] Separate development and production credentials.
- [ ] Document recovery.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-025 — Review Service Permissions and Exposure

**Priority:** P6

**Business context:** Reduce the attack surface of the worker, n8n, ComfyUI, Docker, shared filesystem, and public checkout.

### US-059 — Review Service Permissions and Exposure: Story 1

**Description**

As a system owner, I want to apply least privilege, so that services and files are exposed only as required for operation.

**Acceptance criteria**

- [ ] Apply least privilege.
- [ ] Review open ports.
- [ ] Review authentication.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-060 — Review Service Permissions and Exposure: Story 2

**Description**

As a system owner, I want to review allowed paths, so that services and files are exposed only as required for operation.

**Acceptance criteria**

- [ ] Review allowed paths.
- [ ] Separate secrets.
- [ ] Document accepted exposure.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-026 — Correct Stale Flow A Readiness Defaults

**Priority:** P7

**Business context:** Remove obsolete revision assumptions from readiness validation.

### US-061 — Correct Stale Flow A Readiness Defaults: Story 1

**Description**

As a content operator, I want to identify stale expected revisions, so that flow a readiness checks remain accurate as the repository evolves.

**Acceptance criteria**

- [x] Identify stale expected revisions.
- [x] Replace brittle commit assumptions.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

### US-062 — Correct Stale Flow A Readiness Defaults: Story 2

**Description**

As a content operator, I want to avoid false failures, so that flow a readiness checks remain accurate as the repository evolves.

**Acceptance criteria**

- [x] Avoid false failures.
- [x] Preserve valid readiness checks.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

### US-063 — Correct Stale Flow A Readiness Defaults: Story 3

**Description**

As a content operator, I want to document the new baseline, so that flow a readiness checks remain accurate as the repository evolves.

**Acceptance criteria**

- [x] Document the new baseline.
- [x] The outcome is visible and understandable to the intended user.
- [x] Failures or blocked states are clearly communicated.
- [x] Existing completed work is not duplicated or unintentionally changed.

## BL-027 — Establish a Warning and Test Quality Baseline

**Priority:** P7

**Business context:** Create a known baseline for test-suite warnings and code-quality signals.

### US-064 — Establish a Warning and Test Quality Baseline: Story 1

**Description**

As a content operator, I want to run the full suite, so that the team can identify whether a change introduces new quality problems.

**Acceptance criteria**

- [ ] Run the full suite.
- [ ] Inventory warnings.
- [ ] Correct root causes where possible.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-065 — Establish a Warning and Test Quality Baseline: Story 2

**Description**

As a content operator, I want to separate inherited warnings from new warnings, so that the team can identify whether a change introduces new quality problems.

**Acceptance criteria**

- [ ] Separate inherited warnings from new warnings.
- [ ] Document the baseline.
- [ ] Maintain zero new warnings.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-028 — Establish Continuous Integration

**Priority:** P7

**Business context:** Run repository validation automatically on proposed changes.

### US-066 — Establish Continuous Integration: Story 1

**Description**

As a content operator, I want to run tests, so that invalid changes are detected before they reach the main branch.

**Acceptance criteria**

- [ ] Run tests.
- [ ] Validate specifications.
- [ ] Validate YAML and JSON.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-067 — Establish Continuous Integration: Story 2

**Description**

As a content operator, I want to check whitespace and repository consistency, so that invalid changes are detected before they reach the main branch.

**Acceptance criteria**

- [ ] Check whitespace and repository consistency.
- [ ] Scan for secrets.
- [ ] Block invalid changes.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

## BL-029 — Maintain Current Project and Runtime Context

**Priority:** P7

**Business context:** Keep business, technical, and operational documentation aligned with reality.

### US-068 — Maintain Current Project and Runtime Context: Story 1

**Description**

As a content operator, I want to update current-state documentation when capabilities change, so that project context remains accurate, current, and trustworthy.

**Acceptance criteria**

- [ ] Update current-state documentation when capabilities change.
- [ ] Update runtime state after deployment or live validation.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-069 — Maintain Current Project and Runtime Context: Story 2

**Description**

As a content operator, I want to detect contradictions, so that project context remains accurate, current, and trustworthy.

**Acceptance criteria**

- [ ] Detect contradictions.
- [ ] Prevent historical documents from being treated as current.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.

### US-070 — Maintain Current Project and Runtime Context: Story 3

**Description**

As a content operator, I want to keep cursor and repository guidance aligned, so that project context remains accurate, current, and trustworthy.

**Acceptance criteria**

- [ ] Keep Cursor and repository guidance aligned.
- [ ] The outcome is visible and understandable to the intended user.
- [ ] Failures or blocked states are clearly communicated.
- [ ] Existing completed work is not duplicated or unintentionally changed.
