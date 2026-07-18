# Silverman Blog–LinkedIn Business Backlog

This backlog describes the outstanding business and operational capabilities required to evolve the current solution. It intentionally avoids implementation design and engineering workflow details.

## Priority Overview

| Priority | Focus |
|---|---|
| P1 | Complete Flow A Operationally |
| P2 | Complete LinkedIn Automation |
| P3 | Operations, Reliability, and Recovery |
| P4 | Flow B |
| P5 | Editorial Strategy and Measurement |
| P6 | Security and Administration |
| P7 | Technical Debt and Maintenance |

## P1 — Complete Flow A Operationally

### BL-001 — Automate Live Blog Publication

**Business need:** Eliminate the manual Git commit and push step required after the worker writes the blog post and image to the public repository checkout.

**Expected outcomes:**

- Validate the generated blog post and image before publication.
- Create a controlled commit in the public blog repository.
- Push the approved commit to the remote repository.
- Confirm that the content becomes available on the live site.
- Prevent duplicate commits and duplicate publication attempts.
- Handle remote divergence and publication conflicts safely.

**Completion outcome:** Flow A can move a validated post from the public checkout to the live site without manual Git intervention.

### BL-002 — Validate the First Real LinkedIn Publication

**Business need:** Prove that the implemented LinkedIn integration can publish one real post safely and capture the resulting publication identifier.

**Expected outcomes:**

- Validate OAuth credentials and the member identity.
- Select one approved LinkedIn variant.
- Move the variant through pending, queued, publishing, and published states.
- Store the LinkedIn post URN.
- Confirm the post is visible on LinkedIn.
- Prevent duplicate publication.
- Restore publication safeguards after the controlled test.

**Completion outcome:** One LinkedIn variant is published successfully, traceably, and without duplicate side effects.

### BL-003 — Correct LinkedIn Status Summary in the Editorial Calendar

**Business need:** Remove incomplete calendar summaries caused by mismatched LinkedIn package and distribution status fields.

**Expected outcomes:**

- Show the actual package-generation status.
- Show the actual distribution-scheduling status.
- Keep completed campaign facts immutable.
- Preserve reconciliation idempotency.
- Avoid changing unrelated campaign or calendar data.

**Completion outcome:** The calendar accurately reflects package and scheduling status for completed campaigns.

### BL-004 — Activate Flow A Orchestration in n8n

**Business need:** Move Flow A from manually triggered orchestration to a controlled, scheduled n8n workflow.

**Expected outcomes:**

- Identify the canonical Flow A workflow.
- Confirm correct import and configuration.
- Define execution frequency.
- Activate the workflow.
- Prevent duplicate or concurrent processing.
- Validate restart and recovery behavior.
- Keep LinkedIn publication disabled until separately approved.

**Completion outcome:** Flow A runs on schedule through n8n without duplicate processing or unintended publication.

**Status:** Closed 2026-07-15 after US-009, US-010, and US-011 demonstrated. LinkedIn API publication remains independently gated (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`); US-011 restored the operator baseline `true` after a controlled fail-closed window — not a permanent LinkedIn-off policy. BL-005 closed separately 2026-07-16. Evidence: [us-011 validation](../operations/us-011-linkedin-publication-guard-validation-2026-07-15.md).

### BL-005 — Run a Fully Unattended Flow A Test

**Business need:** Demonstrate that a new approved blog post can move through Flow A without technical intervention.

**Status:** Closed 2026-07-16 after US-012, US-013, and US-014 demonstrated (Manual Post A + Schedule Post B on remediated ready-path). LinkedIn API publication remains out of scope (variants `pending`). BL-006 / BL-007 remain open. Evidence: [bl-005 validation](../operations/bl-005-unattended-flow-a-validation-2026-07-15.md).

**Expected outcomes:**

- Accept a new Markdown post from the ready folder.
- Generate and validate the image.
- Publish the blog post to the live site.
- Generate LinkedIn variants.
- Schedule distribution.
- Complete the source lifecycle.
- Complete campaign and calendar records.
- Require no technical intervention during execution.

**Completion outcome:** A new post completes the full unattended Flow A path with traceable evidence.


## P2 — Complete LinkedIn Automation

### BL-006 — Define the LinkedIn Variant Review Process

**Status:** Closed 2026-07-16 after US-015, US-016, and US-017 demonstrated (policy + criteria + supervision mechanics). Evidence: [linkedin-variant-review-policy.md](../operations/linkedin-variant-review-policy.md), [linkedin-variant-quality-criteria.md](../operations/linkedin-variant-quality-criteria.md), [linkedin-variant-supervision-mechanics.md](../operations/linkedin-variant-supervision-mechanics.md).

**Business need:** Establish a clear business process for reviewing, approving, rejecting, or retaining generated LinkedIn variants.

**Expected outcomes:**

- Define whether all variants may eventually be published.
- Define when review is mandatory.
- Establish quality and differentiation criteria.
- Associate each variant with an audience and objective.
- Support correction or rejection before queueing.

**Completion outcome:** Each LinkedIn variant has a clear review decision and publication purpose.

### BL-007 — Implement Scheduled LinkedIn Publication Execution

**Business need:** Publish due LinkedIn variants automatically according to the approved editorial schedule.

**Expected outcomes:**

- Identify due variants.
- Move only eligible variants to queued state.
- Publish each variant once.
- Store the external publication identifier.
- Record failures clearly.
- Avoid retries that could create duplicates.
- Respect audience cadence and sequence.

**Completion outcome:** Due variants are published once, in order, with complete publication evidence.

**Status:** Closed 2026-07-17 after US-018, US-019, and US-020 operational validation on `192.168.0.194` (`BUILD_REVISION=3c4d9f5`). Evidence: [us-018 validation](../operations/us-018-scheduled-linkedin-publication-validation-2026-07-16.md), [us-019/us-020 validation](../operations/us-019-us-020-linkedin-publication-validation-2026-07-17.md). Not unattended: n8n publish-pending export remains `active: false`. Handoff record: [bl-007-auto-queue-pending-handoff.md](bl-007-auto-queue-pending-handoff.md).

### BL-008 — Define LinkedIn Retry and Recovery Rules

**Business need:** Create safe business rules for handling LinkedIn publication failures and uncertain outcomes.

**Expected outcomes:**

- Classify recoverable and non-recoverable errors.
- Define token-renewal behavior.
- Prevent duplicate posts after timeouts.
- Set retry limits.
- Preserve operational evidence.
- Support safe manual intervention.

**Completion outcome:** LinkedIn failures can be recovered without losing traceability or duplicating content.

**Status:** Closed 2026-07-17 after US-021 (policy, 2026-07-16) and US-022 (mechanics) acceptance. Primary recovery chain operationally validated on `192.168.0.194` (`BUILD_REVISION=d15d85b`): controlled transport failure on a real due variant classified `uncertain`, blind/wrong-class re-queues rejected, operator-attested re-queue, successful retry `urn:li:share:7483974070842241024` with the failed attempt preserved in append-only history, idempotent replay. Correction, failed-cancellation, exhaustion, and legacy normalization paths validated at unit-test scope only. Evidence: [us-021/us-022 validation](../operations/us-021-us-022-linkedin-retry-recovery-validation-2026-07-17.md).

### BL-009 — Validate LinkedIn Article Preview Rendering

**Business need:** Confirm that LinkedIn renders the expected title, description, image, and link preview.

**Expected outcomes:**

- Verify title and description.
- Verify image availability.
- Confirm preview behavior on LinkedIn.
- Identify cache or metadata issues.
- Define a fallback when the preview is incorrect.

**Completion outcome:** Published LinkedIn posts display the intended article preview.

**Status:** Closed 2026-07-17 after US-023, US-024, and US-025 operational demonstration and acceptance. Inputs LinkedIn scrapes are verified correct (`POST /validate-linkedin-article-preview`, live OG remediation `silverberdi.github.io` `e4d10de`); rendering behavior observed on a real post (`preview_not_rendered_post_format` — the v1 text post renders no article card); fallback reaction executed per policy (`fallback_accept_rendering`, `fallback_format_change_deferred`). An explicit article post format (`content.article`) remains a named deferred future-change candidate requiring its own OpenSpec change. Evidence: [us-023](../operations/us-023-linkedin-preview-input-validation-2026-07-17.md), [us-024 blocked](../operations/us-024-preview-confirmation-blocked-2026-07-17.md), [us-024 post-publish](../operations/us-024-preview-confirmation-keep-contracts-boring-2026-07-17.md), [us-025 decision](../operations/us-025-preview-fallback-decision-keep-contracts-boring-2026-07-17.md).


## P3 — Operations, Reliability, and Recovery

### BL-010 — Add Operational Observability

**Business need:** Provide a consolidated view of Flow A execution health and campaign status.

**Expected outcomes:**

- Identify successful and failed executions.
- Identify blocked or stale campaigns.
- Show delayed calendar items.
- Capture stage duration.
- Surface failures by external dependency.
- Allow status review without opening multiple raw files.

**Completion outcome:** Operators can understand system health and campaign progress from one clear operational view.

**Status:** Closed 2026-07-17 after US-026 and US-027 acceptance on `192.168.0.194` (`BUILD_REVISION=b67c538`): controlled live smoke of `GET /flow-a/operational-status` (deterministic, auth 401, invalid `now_utc` 422, zero mutation). Evidence: [flow-a-operational-status.md](../operations/flow-a-operational-status.md).

### BL-011 — Add Operational Alerts

**Business need:** Notify the operator when the system requires attention.

**Expected outcomes:**

- Alert on items moved to error.
- Alert on image-generation failure.
- Alert on blog publication failure.
- Alert on partial calendar execution.
- Alert on LinkedIn token or publication failure.
- Alert on stale campaigns.
- Alert on unhealthy worker or failed n8n workflow.

**Completion outcome:** Important failures and blocked states generate timely, actionable alerts.

**Status:** Closed 2026-07-17 after US-028, US-029, and US-030 acceptance on `192.168.0.194` (`BUILD_REVISION=b67c538`): controlled live smoke for evaluate/report/fail-closed emit plus fixture coverage for all eight alert types. Follow-up enabled 2026-07-17: production webhook emit + n8n Error Trigger → report + daily evaluate/emit schedule. Evidence: [flow-a-operational-alerts.md](../operations/flow-a-operational-alerts.md).

### BL-012 — Consolidate Recovery for Incomplete Campaigns

**Business need:** Provide a consistent recovery model for campaigns that stop before completion.

**Expected outcomes:**

- Identify the last valid stage.
- Resume without repeating successful work.
- Repair inconsistent metadata.
- Classify recovery actions.
- Preserve attempt history.
- Support safe cancellation when recovery is not appropriate.

**Completion outcome:** Incomplete campaigns can be resumed or repaired safely and predictably.

**Status:** Closed 2026-07-18 after US-031 + US-032 acceptance against automated fixture evidence; worker recovery endpoints deployed on `192.168.0.194` (`BUILD_REVISION=018aa36`). Evidence: [bl-012 acceptance](../operations/bl-012-incomplete-campaign-recovery-acceptance-2026-07-18.md), [flow-a-incomplete-campaign-recovery.md](../operations/flow-a-incomplete-campaign-recovery.md).

### BL-013 — Validate Concurrency and Duplicate Execution Protection

**Business need:** Ensure that simultaneous or repeated triggers cannot process the same content twice.

**Expected outcomes:**

- Prevent duplicate post processing.
- Prevent duplicate image generation.
- Prevent duplicate blog publication.
- Prevent duplicate scheduling.
- Prevent duplicate LinkedIn publication.
- Recover abandoned processing claims.
- Validate behavior during restarts.

**Completion outcome:** Concurrent triggers do not create duplicate artifacts or external publications.

**Status:** Closed 2026-07-18 after US-033 + US-034 + US-035 acceptance against automated fixture evidence (not deployed / not operationally validated on the live worker). Evidence: [us-033](../operations/flow-a-concurrency-duplicate-execution-protection-us-033.md), [us-034](../operations/flow-a-concurrency-duplicate-execution-protection-us-034.md), [us-035](../operations/flow-a-concurrency-duplicate-execution-protection-us-035.md).

### BL-014 — Establish Backup and Restore for Editorial State

**Business need:** Protect the files and metadata required to recover the editorial system.

**Expected outcomes:**

- Define backup scope.
- Define retention.
- Verify backup integrity.
- Test restoration.
- Document the recovery procedure.
- Protect calendar, campaigns, runs, posts, images, and LinkedIn artifacts.

**Completion outcome:** Editorial state can be restored from a verified backup.

**Status:** Closed 2026-07-18 after US-036 + US-037 acceptance against automated fixture evidence and operator policy/recovery artifacts (not a live production restore execution on the editorial mount). Evidence: [bl-014 acceptance](../operations/bl-014-editorial-backup-restore-acceptance-2026-07-18.md), [US-036 policy](../operations/editorial-backup-scope-retention-integrity.md), [US-037 recovery](../operations/editorial-backup-restore-recovery.md).

### BL-015 — Implement Flow A LinkedIn Variant Supervision Console

**Business need:** Provide an operator-facing console to supervise Flow A LinkedIn variants after distribution scheduling and before LinkedIn API publication.

**Expected outcomes:**

- Present pending variants in a campaign or calendar view.
- Show campaign, variant, audience, schedule, and publication state.
- Allow operators to edit variant content before queue authorization.
- Allow operators to defer, reschedule, or cancel variants before queue.
- Persist operator changes traceably.
- Surface publication blocks and integration failures.
- Use a modern, componentized frontend stack for the console without rewriting backend workflows.
- Preserve the existing list-oriented supervision view and make it coexist with the month calendar view.
- Provide a dark, mobile-friendly month calendar view for upcoming publications.
- Allow future publication schedule changes directly from the calendar.
- Keep the console ready for future public URL operation with Google authentication.
- Use worker HTTP capabilities without bypassing publication guards.

**Completion outcome:** Operators can supervise Flow A LinkedIn variants and upcoming editorial publication timing from one usable dark console, switching between list and month calendar views during the optional pre-send window, without opening multiple raw files.


## P4 — Flow B

### BL-016 — Define Flow B

**Business need:** Define the complete business process for system-generated content that requires human review.

**Expected outcomes:**

- Define idea sources.
- Define draft generation.
- Define review, revision, approval, and rejection.
- Define publication eligibility.
- Define calendar integration.
- Prevent automatic publication without approval.

**Completion outcome:** Flow B has an approved business process and clear human approval boundaries.

### BL-017 — Generate Blog Drafts for Flow B

**Business need:** Create high-quality blog drafts from approved ideas while preserving Silverio's voice and editorial standards.

**Expected outcomes:**

- Generate complete blog drafts.
- Follow the editorial canon.
- Include required metadata and structure.
- Create or request an image.
- Save the result for review.
- Prevent automatic publication.

**Completion outcome:** The system produces review-ready Flow B blog drafts.

### BL-018 — Implement Flow B Review and Approval

**Business need:** Support human review and approval of system-generated content.

**Expected outcomes:**

- Present drafts for review.
- Capture feedback.
- Apply revisions.
- Approve or reject content.
- Keep revision history.
- Promote approved content to publication eligibility.

**Completion outcome:** Flow B content cannot proceed to publication without recorded approval.

### BL-019 — Integrate Flow B with the Editorial Calendar

**Business need:** Plan Flow B content alongside approved Flow A content.

**Expected outcomes:**

- Schedule topics.
- Assign target dates.
- Avoid thematic duplication.
- Balance audiences.
- Coordinate blog and LinkedIn timing.
- Keep approval mandatory before publication.

**Completion outcome:** Flow B content is visible and manageable in the editorial calendar.


## P5 — Editorial Strategy and Measurement

### BL-020 — Create the Editorial Content Backlog

**Business need:** Maintain a prioritized business backlog of future content topics.

**Expected outcomes:**

- Capture topic, audience, objective, format, priority, status, and target date.
- Link blog topics to potential LinkedIn derivatives.
- Identify dependencies.
- Support prioritization and reprioritization.

**Completion outcome:** The content pipeline has a clear, prioritized source of future topics.

### BL-021 — Define Editorial Calendar and Publishing Cadence

**Business need:** Establish a sustainable publishing rhythm for the blog and LinkedIn.

**Expected outcomes:**

- Define blog frequency.
- Define LinkedIn frequency.
- Define spacing between variants.
- Define publishing windows.
- Balance audience segments.
- Define rescheduling rules.

**Completion outcome:** Publications follow an approved cadence that avoids saturation and redundancy.

### BL-022 — Define Business and Content Metrics

**Business need:** Measure whether the content program supports Silverio's professional goals.

**Expected outcomes:**

- Define blog traffic metrics.
- Define LinkedIn reach and engagement metrics.
- Track profile visits and audience growth.
- Track recruiter and executive conversations.
- Track job and consulting opportunities.
- Identify high-performing topics and formats.

**Completion outcome:** The content program has measurable business and editorial outcomes.

### BL-023 — Use Performance Feedback to Improve Future Content

**Business need:** Turn performance data into better editorial decisions.

**Expected outcomes:**

- Collect metrics consistently.
- Compare themes and variants.
- Identify effective formats.
- Feed insights into future planning.
- Reduce repetition of low-performing content.
- Keep human oversight over strategic changes.

**Completion outcome:** Future editorial decisions are informed by evidence rather than intuition alone.


## P6 — Security and Administration

### BL-024 — Rotate and Review Operational Secrets

**Business need:** Ensure operational credentials remain secure and appropriately managed.

**Expected outcomes:**

- Rotate keys that may have been exposed during testing.
- Verify secure storage.
- Review permissions.
- Confirm secrets are absent from Git, logs, and workflow exports.
- Define ownership and rotation cadence.

**Completion outcome:** Operational secrets are current, protected, and auditable.

### BL-025 — Formalize LinkedIn Token Management

**Business need:** Define the full lifecycle of LinkedIn authentication tokens.

**Expected outcomes:**

- Store tokens securely.
- Handle renewal and expiration.
- Support revocation.
- Detect invalid tokens.
- Separate development and production credentials.
- Document recovery.

**Completion outcome:** LinkedIn token management is secure, predictable, and recoverable.

### BL-026 — Review Service Permissions and Exposure

**Business need:** Reduce the attack surface of the worker, n8n, ComfyUI, Docker, shared filesystem, and public checkout.

**Expected outcomes:**

- Apply least privilege.
- Review open ports.
- Review authentication.
- Review allowed paths.
- Separate secrets.
- Document accepted exposure.

**Completion outcome:** Services and files are exposed only as required for operation.


## P7 — Technical Debt and Maintenance

### BL-027 — Correct Stale Flow A Readiness Defaults

**Business need:** Remove obsolete revision assumptions from readiness validation.

**Expected outcomes:**

- Identify stale expected revisions.
- Replace brittle commit assumptions.
- Avoid false failures.
- Preserve valid readiness checks.
- Document the new baseline.

**Completion outcome:** Flow A readiness checks remain accurate as the repository evolves.

### BL-028 — Establish a Warning and Test Quality Baseline

**Business need:** Create a known baseline for test-suite warnings and code-quality signals.

**Expected outcomes:**

- Run the full suite.
- Inventory warnings.
- Correct root causes where possible.
- Separate inherited warnings from new warnings.
- Document the baseline.
- Maintain zero new warnings.

**Completion outcome:** The team can identify whether a change introduces new quality problems.

### BL-029 — Establish Continuous Integration

**Business need:** Run repository validation automatically on proposed changes.

**Expected outcomes:**

- Run tests.
- Validate specifications.
- Validate YAML and JSON.
- Check whitespace and repository consistency.
- Scan for secrets.
- Block invalid changes.

**Completion outcome:** Invalid changes are detected before they reach the main branch.

### BL-030 — Maintain Current Project and Runtime Context

**Business need:** Keep business, technical, and operational documentation aligned with reality.

**Expected outcomes:**

- Update current-state documentation when capabilities change.
- Update runtime state after deployment or live validation.
- Detect contradictions.
- Prevent historical documents from being treated as current.
- Keep Cursor and repository guidance aligned.

**Completion outcome:** Project context remains accurate, current, and trustworthy.
