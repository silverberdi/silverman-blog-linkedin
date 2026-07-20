# linkedin-article-preview-fallback Specification

## Purpose

Normative operator fallback policy for BL-009 / US-025: decision procedure, action classification, outcome vocabulary, evidence records, and blocked states for reacting to an incorrect or missing LinkedIn article preview. Procedure/policy capability only: no worker code or new LinkedIn API usage. Consumes `linkedin-article-preview-verification` (US-023) and `linkedin-article-preview-rendering-confirmation` (US-024) unchanged.

## Requirements

### Requirement: Scope, actors, and boundaries

This capability SHALL define the normative operator fallback policy for BL-009 / US-025: the decision procedure, action classification, outcome vocabulary, evidence records, and blocked states for reacting to an incorrect or missing LinkedIn article preview detected for a Flow A campaign.

The policy MUST be executable by a human operator using existing worker HTTP endpoints (`POST /validate-linkedin-article-preview`, `POST /defer-linkedin-variant`, `POST /cancel-linkedin-publication`, `POST /correct-linkedin-variant`) and the documented US-024 confirmation procedure. It MUST NOT require worker code changes, new worker endpoints, new request or response fields, new environment variables, new `publish_state` values, n8n workflow changes, or deploy script changes.

The policy MUST NOT introduce LinkedIn API usage beyond capabilities that already exist (`linkedin-publication-integration`), MUST NOT automate or scrape LinkedIn's UI, MUST NOT rely on undocumented LinkedIn API or cache behavior, and MUST NOT require storing LinkedIn session data or credentials in the repository.

The policy MUST consume `linkedin-article-preview-verification` (US-023) as the sole source of input-correctness truth and `linkedin-article-preview-rendering-confirmation` (US-024) as the sole source of rendering observations. It MUST NOT redefine, duplicate, or manually re-derive any US-023 input check or US-024 observation step.

#### Scenario: No new automation surface

- **WHEN** this capability is applied
- **THEN** no worker endpoint, request field, environment variable, `publish_state` value, n8n workflow, or deploy script is added or changed, and no new LinkedIn API usage is introduced

#### Scenario: Input truth and rendering observation are not re-derived

- **WHEN** a fallback decision needs to know whether preview inputs are correct or how LinkedIn rendered the preview
- **THEN** the policy references the US-023 verification result and the recorded US-024 evidence record respectively, and defines no competing check or observation of its own

### Requirement: Fallback triggers are recorded US-024 outcomes

The documented policy SHALL define that a fallback decision is triggered only by a recorded US-024 evidence record with one of these outcomes:

1. `preview_stale_cache` where the US-024 safe re-scrape procedure has been completed (inputs re-confirmed via US-023, Post Inspector re-inspection performed, propagation lag allowed) and the intended card is still not shown — a pre-publish trigger.
2. `preview_not_rendered_post_format` — a post-publish trigger recorded on a real published v1 text post.
3. A post-publish observation that an already-published post retains a stale or incorrect card (recorded under `preview_stale_cache` with the US-024 statement that a re-scrape affects new posts only) — a post-publish trigger.

The policy MUST state that `preview_inputs_incorrect` is not a fallback trigger: its remediation is the existing US-023 code-driven input correction followed by US-023 re-verification and US-024 re-confirmation, and the fallback policy references that loop without adding to it. `preview_confirmed` requires no fallback, and `confirmation_blocked` routes to the US-024 blocked-state table.

The policy MUST forbid initiating fallback actions from operator impressions, screenshots, or any observation not recorded through the US-024 procedure.

#### Scenario: Persistent stale cache triggers pre-publish fallback

- **WHEN** a campaign has a recorded `preview_stale_cache` outcome and the US-024 safe re-scrape cycle has been completed without producing the intended card
- **THEN** the policy directs the operator to a pre-publish fallback decision for the campaign's unpublished variants

#### Scenario: Inputs-incorrect routes to US-023 remediation, not fallback

- **WHEN** the latest US-024 evidence record for a campaign is `preview_inputs_incorrect`
- **THEN** the policy directs remediation per the reported `linkedin_preview_validation_*` codes followed by US-023 re-verification and US-024 re-confirmation, and no fallback action is selected

#### Scenario: Unrecorded observation does not trigger fallback

- **WHEN** an operator believes a preview looks wrong but no US-024 evidence record with a triggering outcome exists
- **THEN** the policy requires completing the US-024 confirmation procedure first and records any premature fallback attempt as blocked

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

### Requirement: Post-publish recovery decision procedure

For a published post showing a stale, incorrect, or missing article card, the documented policy SHALL define **accept and record** as the default supported action: the post remains, campaign evidence (`linkedin_post_urn`, `published_at`, `linkedin_publication`, attempt and recovery history) is untouched, and the rendering defect is captured in a fallback evidence record.

The policy MUST state that a Post Inspector re-scrape never updates an already-published post and MUST NOT present re-scrape as a post-publish remedy.

The policy MUST forbid editing or removing stored publication evidence to enable re-publication of a `published` variant, and MUST state the reason: already-published idempotency and the US-020 cadence guard key on that stored evidence, so evidence mutation would disable the exact safeguards that prevent duplicate posts, and would violate the US-022 append-only evidence contract.

The only non-default post-publish action SHALL be the approval-gated manual post removal defined in the action classification requirement; even when executed, the affected variant MUST remain `published` with all evidence intact.

#### Scenario: Published post with stale card defaults to accept and record

- **WHEN** a post-publish US-024 observation shows a published post retaining an incorrect card and the operator applies the default action
- **THEN** the outcome is recorded as `fallback_accept_rendering` with the defect described, and campaign metadata is byte-identical to its pre-decision state

#### Scenario: Evidence mutation for re-publication is forbidden

- **WHEN** any procedure step would edit or remove `linkedin_post_urn`, `published_at`, `linkedin_publication`, attempt history, or recovery history to make a `published` variant publishable again
- **THEN** the policy forbids the step and directs the operator to the supported post-publish actions instead

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

### Requirement: Duplicate prevention and safeguard preservation

The documented policy MUST preserve every existing publication safeguard unchanged and MUST state how each interacts with fallback actions:

- Re-publication of a `published` variant remains impossible through existing endpoints (`POST /queue-linkedin-publication` accepts `pending` or eligible `failed` variants only; publish-due is idempotent for `published` variants), and the policy MUST NOT define any path around this.
- Fallback actions consume no US-022 retry budget (no fallback action is a real LinkedIn API call), and the policy MUST NOT use `failed`-state recovery confirmations (`recovery_confirmation`) for preview issues — a wrong preview never makes a variant `failed`.
- Defer and cancel interactions with the US-020 sequence and cadence rules MUST be stated per action (defer blocks followers; cancel releases the sequence; cadence remains anchored to stored `published_at`, including after an approved manual post removal).
- Scheduling metadata contracts (`linkedin-distribution-scheduling-model`), including schedule idempotency proofs and single-variant defer semantics, remain unchanged.
- The `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` guard remains fail-closed; no fallback step may bypass or weaken it.

#### Scenario: Fallback consumes no retry budget

- **WHEN** an operator executes any supported or approval-gated fallback action for a campaign
- **THEN** no variant's `publication_attempt_count`, `manual_retries_used`, or `manual_retries_remaining` changes, and no real LinkedIn API call is made by the fallback procedure

#### Scenario: Recovery confirmations are not repurposed for preview issues

- **WHEN** a fallback decision concerns a variant whose `publish_state` is not `failed`
- **THEN** the policy directs no use of `recovery_confirmation` values, and the US-021/US-022 recovery paths remain reserved for publication failures

#### Scenario: Cadence stays anchored after approved post removal

- **WHEN** an approval-gated manual post removal is executed for a published variant
- **THEN** the variant's stored `published_at` continues to drive the US-020 cadence rule and the sequence remains released, with no metadata change

### Requirement: Fallback outcome vocabulary and evidence record

The documented policy SHALL define a fixed fallback outcome vocabulary — `fallback_accept_rendering`, `fallback_delay_publication`, `fallback_correct_inputs_reverify`, `fallback_cancel_variant`, `fallback_post_removal_approved`, `fallback_format_change_deferred`, `fallback_blocked` — as documented checklist labels (no worker codes are introduced), used exactly and exclusively for recording fallback decisions.

Each fallback decision SHALL be recorded using an evidence template that captures at minimum: campaign id; affected variant(s) with `publish_state` at decision time; the referenced US-024 evidence record (outcome label and UTC timestamp); the referenced US-023 verification run; the chosen action with its classification (supported or approval-gated) and, for approval-gated actions, the recorded prior approval; the worker endpoint calls made (dry-run and real) with key response fields; the resulting variant `publish_state`; the outcome label; and the operator and UTC timestamp of the decision.

Evidence records MUST NOT contain LinkedIn session data, credentials, secrets, variant body text, or image bytes. Campaign metadata files MUST NOT be edited to record fallback outcomes under this capability.

#### Scenario: Fallback decision recorded with fixed label and evidence

- **WHEN** an operator completes a fallback decision for a campaign
- **THEN** the evidence record contains the campaign id, affected variants and states, the US-024 and US-023 references, the chosen action and classification, one outcome label from the fixed vocabulary, and the operator and UTC timestamp

#### Scenario: Campaign metadata untouched by fallback recording

- **WHEN** a fallback outcome is recorded
- **THEN** `metadata/campaigns/<campaign-id>.json` is not modified by the recording procedure

### Requirement: Blocked states and operator communication

The documented policy SHALL enumerate blocked conditions with the named next action for each, including at minimum: no US-024 evidence record with a fallback-triggering outcome exists for the campaign; the US-024 safe re-scrape cycle has not been completed for a stale-cache trigger; prior approval is absent for an approval-gated action; a required input correction depends on a live-site Git commit/push that has not been approved; and the chosen action is invalid for the affected variant's `publish_state` (for example defer on a `queued` variant).

Blocked fallback attempts MUST be recorded with the `fallback_blocked` label and the specific blocking condition, MUST NOT be recorded as failures of preview inputs, of LinkedIn rendering, or of the fallback policy, and MUST never result in guessing or improvising an action.

#### Scenario: Missing US-024 record blocks fallback

- **WHEN** a fallback action is attempted for a campaign without a recorded triggering US-024 outcome
- **THEN** the attempt is recorded as `fallback_blocked` with the named condition and the next action is to complete the US-024 confirmation procedure

#### Scenario: Ungranted approval blocks a gated action

- **WHEN** an approval-gated action is attempted without recorded prior approval
- **THEN** the attempt is recorded as `fallback_blocked` and the post remains untouched

### Requirement: Existing capabilities unchanged

This capability MUST NOT modify the behavior, requirements, or implementation of `linkedin-article-preview-verification` (US-023), `linkedin-article-preview-rendering-confirmation` (US-024), `linkedin-article-preview-image-support`, `linkedin-derivative-package-generation`, `linkedin-distribution-scheduling-model`, `linkedin-publication-integration` (including US-018/US-019/US-020 contracts and the `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` guard), or `linkedin-retry-recovery-classification` (US-021/US-022).

Documentation recording this capability MUST use qualified status language: policy defined ≠ deployed ≠ operationally validated ≠ story accepted; US-025 acceptance requires an operator-demonstrated fallback decision with a completed evidence record on a real campaign, and BL-009 remains open until US-023, US-024, and US-025 business outcomes are demonstrated and accepted.

#### Scenario: No source, test, or workflow changes

- **WHEN** this change is applied
- **THEN** there are no changes under `src/`, `tests/`, `n8n/`, or `deploy/`, and all existing endpoint contracts are unchanged

#### Scenario: Qualified status language in documentation

- **WHEN** project documentation records this capability
- **THEN** it states the fallback policy is defined but not operationally validated, US-025 is not accepted, and BL-009 is not closed
