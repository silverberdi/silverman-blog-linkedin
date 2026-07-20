## MODIFIED Requirements

### Requirement: Pre-publish fallback decision procedure

For a fallback-triggering outcome on a campaign whose affected variants are not `published`, the documented policy SHALL define exactly four supported actions, each with its mechanism and safety consequences:

1. **Accept and proceed** — no endpoint call; the decision and rationale are recorded. The policy MUST state that the v1 text post carries the blog URL in commentary regardless of card rendering.
2. **Delay publication** — `POST /defer-linkedin-variant` for **`pending` or `queued`** variants (US-084) with a future UTC time, followed by repeating the US-024 confirmation before publication. The policy MUST state that deferring an earlier-sequence variant blocks its followers at publish time under the US-020 sequence rule, that LinkedIn's cache duration is not officially documented and no specific TTL is normative, and that deferring a `queued` variant **keeps** `publish_state` `queued` (does not return to `pending`) while updating `scheduled_at_utc` so due evaluation waits for the new time. Cancellation remains the withdraw path (US-085 / existing cancel endpoint); postpone is not cancel.
3. **Correct inputs and repeat US-023/US-024** — applicable only when inputs are wrong; blog-post and public-checkout corrections follow ADR-0002 (blog post is canonical) and any Git commit/push to the live site follows the existing guarded or manual publication paths with operator approval.
4. **Withdraw the variant** — `POST /cancel-linkedin-publication`. The policy MUST state that cancellation releases the US-020 sequence for followers, sets `operator_supervision.auto_queue_eligible` to `false`, preserves evidence, and is irreversible through existing endpoints except the approved reopen path where product already allows it.

The policy MUST direct that endpoint-backed actions are executed dry-run first and then real, per the existing endpoint defaults, and MUST direct preview fallback decisions into the `pending` supervision window before queueing wherever possible.

#### Scenario: Delay uses the existing defer mechanics for pending

- **WHEN** the operator chooses to delay a `pending` variant as preview fallback
- **THEN** the policy directs `POST /defer-linkedin-variant` with a future UTC time (dry-run first), notes the follower-blocking consequence under US-020, and requires a repeated US-024 confirmation before publication proceeds

#### Scenario: Delay uses defer for queued without un-queue

- **WHEN** the fallback-affected variant is already `queued` and the operator chooses delay
- **THEN** the policy directs `POST /defer-linkedin-variant` with a future UTC time (dry-run first), states that `publish_state` remains `queued`, and does not invent an un-queue-to-pending path; cancellation remains the withdraw alternative

#### Scenario: Accept records a decision without side effects

- **WHEN** the operator accepts publication despite a wrong or missing card
- **THEN** no worker endpoint is called, no campaign metadata changes, and the decision is captured in a fallback evidence record

### Requirement: Supported, approval-gated, and forbidden actions

The documented policy SHALL classify every fallback action into exactly one of three classes and present the classification as a single reference table:

**Supported (operator decision, no additional approval):** accept and proceed / accept and record; delay via `POST /defer-linkedin-variant` for **`pending` or `queued`** variants (US-084); correct inputs and repeat US-023/US-024 (the input-remediation loop itself; any live-site Git push within it keeps its existing approval requirement); withdraw via `POST /cancel-linkedin-publication`; US-023 re-verification runs; repeated US-024 confirmations.

**Approval-gated (explicit prior operator/owner approval recorded in the evidence record):** manual removal of the operator's own published LinkedIn post via the LinkedIn UI, when leaving the defective post visible is judged worse than removing it. The approval record MUST precede the removal; the variant MUST remain `published` with all evidence intact; the removal MUST be captured in the fallback evidence record including the fact that the stored URN now references a removed post; the US-020 cadence anchored to the stored `published_at` remains in force.

**Forbidden:** delete-then-re-post as a fallback procedure (re-publishing an already-published variant's content through endpoints, metadata edits, or a new variant/campaign created for that purpose); cache-busting query parameters or any divergence of the shared URL from the canonical recorded `public_url`; publishing additional LinkedIn posts to test or force a preview refresh; editing campaign metadata to record fallback outcomes or to reset publication state; LinkedIn UI scraping or automation; reliance on undocumented LinkedIn API or cache behavior; any automatic or scheduled execution of fallback actions.

The policy MUST record the safety rationale for the delete/re-post prohibition (duplicate-content risk outside every existing safeguard, uncertain-outcome window without US-021 evidence machinery, evidence integrity) and MUST name the two deferred future-change candidates with their preconditions: an explicit article post format (for example `content.article`) and any worker-supported post deletion/re-publication capability — each requiring at least one operationally recorded triggering US-024 evidence record, verification against current official LinkedIn API documentation, and its own OpenSpec change with unchanged guard, dry-run, idempotency, retry-budget, and evidence contracts.

#### Scenario: Manual post removal requires recorded prior approval

- **WHEN** an operator considers removing a published post with a defective card via the LinkedIn UI
- **THEN** the policy requires explicit prior approval recorded in the fallback evidence record, keeps the variant `published` with all evidence intact, and records the removal outcome as `fallback_post_removal_approved`

#### Scenario: Delete-then-re-post is rejected as a fallback path

- **WHEN** an operator proposes deleting a published post and re-publishing its content to obtain a correct card
- **THEN** the policy classifies the action as forbidden, states the duplicate-risk and evidence-integrity rationale, and directs any future capability of this kind to a separate OpenSpec change

#### Scenario: Post-format change is deferred, not improvised

- **WHEN** a `preview_not_rendered_post_format` outcome is recorded and the operator wants article cards on future posts
- **THEN** the policy records the outcome as `fallback_format_change_deferred` when escalation is chosen, and directs a separate future OpenSpec change modifying `linkedin-publication-integration` rather than any change to current publication behavior

#### Scenario: Cache-busting and test posts remain forbidden

- **WHEN** any fallback step would alter the shared URL relative to the recorded `public_url` or publish an additional LinkedIn post to force a preview refresh
- **THEN** the policy forbids the step

#### Scenario: Supported delay includes queued defer

- **WHEN** an operator chooses delay for a `queued` fallback-affected variant
- **THEN** the supported-actions classification includes delay via `POST /defer-linkedin-variant` without requiring return to `pending`
