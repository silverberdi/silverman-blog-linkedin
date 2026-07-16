# linkedin-variant-review-process

## Purpose

Operator-visible policy and criteria for Flow A LinkedIn variant publication expectations — strategy-driven publish default (all scheduled variants unless operator overrides), optional supervision window while `pending`, quality and differentiation criteria (US-016), when review is mandatory (Flow B only), blocked/deferred states, and how the policy informs BL-007 eligibility without implementing auto-queue or worker publication behavior (US-015 / BL-006 story 1; US-016 / BL-006 story 2).

## Requirements

### Requirement: Operator-visible LinkedIn variant review policy artifact

The repository MUST provide an operator-facing policy document at `docs/operations/linkedin-variant-review-policy.md` that defines the Flow A LinkedIn variant publication and supervision policy for US-015 (BL-006 story 1).

The policy artifact MUST be understandable to the content operator without requiring worker source code or n8n workflow inspection.

The policy artifact MUST cross-link at least: `docs/GLOSSARY.md` LinkedIn publication states, `docs/product/user-stories.md` US-015, and `content-strategy/silverman-editorial-system.md` `#flow-a-vs-flow-b`.

#### Scenario: Policy artifact exists for operators

- **WHEN** an operator opens `docs/operations/linkedin-variant-review-policy.md`
- **THEN** the document states it is the Flow A LinkedIn variant policy covering strategy-driven publication expectations and the optional pre-send supervision window

#### Scenario: Policy is findable from product story

- **WHEN** an operator reads US-015 in `docs/product/user-stories.md` after this capability is implemented
- **THEN** US-015 points to `docs/operations/linkedin-variant-review-policy.md` as the demonstrated policy outcome (or CURRENT-STATE does equivalent linking)

### Requirement: Strategy-driven publication default for Flow A

The policy MUST define that Flow A LinkedIn variants scheduled by distribution strategy are **expected to publish** at their scheduled times unless the operator explicitly overrides (cancel, defer/delay, or edit — mechanics deferred to US-017).

The default MUST NOT be selective publication where only a subset is expected to publish without operator override.

The policy MUST state that the blog source is pre-reviewed (user-provided `ready` content) and that LinkedIn derivatives are generated and scheduled per `#linkedin-distribution-strategy` (audience, spacing, `scheduled_at_utc`).

The policy MUST state that `publish_state` `pending` after distribution scheduling means the variant is scheduled and in the pre-send supervision window; it is not yet sent to the LinkedIn API queue until queue authorization occurs under existing publication integration.

The policy MUST NOT redefine worker `publish_state` enum values (`pending`, `queued`, `publishing`, `published`, `failed`, `cancelled`).

#### Scenario: Operator learns scheduled variants are expected to publish

- **WHEN** an operator reads the strategy-driven publication section
- **THEN** the section states that all variants scheduled by Flow A distribution strategy are expected to publish unless the operator explicitly cancels or defers them

#### Scenario: Pending is supervision window before API queue

- **WHEN** an operator reads the policy’s relationship to `publish_state`
- **THEN** the document states that `pending` after Flow A schedule is the pre-send supervision window and is not the same as LinkedIn API published

### Requirement: Mandatory review defined for Flow A vs Flow B

The policy MUST define when human review is mandatory:

- **Flow A:** Human review is **not mandatory** after blog validation for blog publish, LinkedIn package generation, distribution scheduling, campaign lifecycle completion (`distribution_scheduled` / `flow_a_complete`), calendar reconciliation, or LinkedIn API queue/publish. The operator MAY supervise variants during the `pending` supervision window (edit, delay, cancel) but absence of supervision does not block publication per strategy.
- **Flow B:** Human review **is mandatory** before any publication. Flow B implementation is deferred; the policy MUST encode this distinction now.

The policy MUST state that LinkedIn publication enablement (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`) is a separate technical guard and does not substitute for Flow B mandatory review or replace Flow A strategy-driven publication expectations.

The policy MAY reference a future operator console as the intended supervision surface; console implementation is out of scope for this capability.

#### Scenario: Flow A does not require mandatory review before LinkedIn send

- **WHEN** an operator reads the mandatory-vs-optional review section
- **THEN** the section states Flow A does not require mandatory human review before LinkedIn API queue or publish

#### Scenario: Flow A supervision window is optional

- **WHEN** an operator reads the supervision window section
- **THEN** the section states the operator MAY edit, delay, or cancel while the variant is `pending` and before API send, but non-intervention allows publication per strategy

#### Scenario: Flow B mandatory review is encoded

- **WHEN** an operator reads the mandatory-vs-optional review section
- **THEN** the section states Flow B requires mandatory human review before any publish and is deferred for implementation

#### Scenario: Enablement flag is a technical guard

- **WHEN** an operator reads the policy’s relationship to publication enablement
- **THEN** the document distinguishes the enablement flag from Flow A supervision and from Flow B mandatory review

### Requirement: Blocked and deferred states are communicated

The policy MUST include an explicit blocked/deferred-states section that communicates at least:

- Variant `pending` before `scheduled_at_utc` → scheduled; supervision window open; not yet API-queued (normal state, not a policy failure).
- Operator cancel or defer (mechanics US-017) → not eligible for strategy-driven auto-queue until policy defines recovery.
- LinkedIn publication not enabled → blocked for real API publish by existing technical guard.
- Existing publication/integration failure states (`failed`, OAuth action-required, missing URN) → follow existing publication error semantics.
- US-017 edit/cancel mechanics and supervision console → deferred; absence is not a worker defect for US-015. US-016 quality/differentiation criteria → `docs/operations/linkedin-variant-quality-criteria.md`.
- BL-007 auto-queue / scheduled publication execution → not implemented in this capability; local `auto_queue_pending` WIP remains out of scope.

#### Scenario: Pending before schedule is normal supervision state

- **WHEN** an operator reads the blocked-states section for a `pending` variant before its scheduled time
- **THEN** the section describes this as the optional supervision window, not as a mandatory-review block

#### Scenario: Deferred stories are labeled deferred

- **WHEN** an operator reads the blocked-states section
- **THEN** US-017, console UI, and BL-007 are labeled deferred or out of scope relative to this policy story; US-016 criteria are referenced at `docs/operations/linkedin-variant-quality-criteria.md`

### Requirement: Future BL-007 eligibility informed by policy (documentation only)

The policy and this capability MUST state that future BL-007 scheduled LinkedIn publication / auto-queue work SHOULD target Flow A variants that remain `pending`, are due per schedule, and have not been operator-cancelled or deferred (per US-017 when defined).

Future BL-007 MUST NOT require a mandatory Flow A human review flag introduced by this capability.

This capability MUST NOT implement auto-queue, MUST NOT modify `POST /publish-linkedin-due-variants` or `POST /queue-linkedin-publication` behavior, and MUST NOT merge or require the BL-007 construction WIP.

#### Scenario: BL-007 follows strategy not mandatory review gate

- **WHEN** an implementer reads the BL-007 interaction section
- **THEN** the text describes auto-queue eligibility as scheduled non-overridden `pending` variants and explicitly excludes a mandatory per-variant review gate from US-015

### Requirement: No duplication of completed Flow A or publication guards

Applying this capability MUST NOT change Flow A ready-path completion behavior, campaign lifecycle transitions for package/schedule, US-011 publication-guard semantics, or ADR-0001 (n8n → worker HTTP only).

This capability MUST NOT add worker HTTP endpoints or n8n LinkedIn publish workflows.

#### Scenario: No new publication endpoints required

- **WHEN** this capability is applied
- **THEN** no new worker LinkedIn publication routes are introduced and existing queue/publish/cancel contracts remain unchanged by this change

### Requirement: Glossary distinguishes supervision window from publish_state and mandatory review

`docs/GLOSSARY.md` MUST define **LinkedIn variant supervision window** (Flow A `pending` phase before API queue/send where the operator may optionally edit, delay, or cancel) as distinct from technical `publish_state` values and from **mandatory review** (required for Flow B before publish).

The glossary MUST NOT equate `distribution_scheduled` or `flow_a_complete` with LinkedIn API published.

#### Scenario: Glossary separates supervision from mandatory review

- **WHEN** an operator reads the LinkedIn publication / review terms in `docs/GLOSSARY.md`
- **THEN** supervision window, `publish_state`, mandatory review (Flow B), variant publication objective, and criteria failure are defined as distinct concepts

### Requirement: Operator-visible LinkedIn variant quality and differentiation criteria artifact

The repository MUST provide an operator-facing criteria document at `docs/operations/linkedin-variant-quality-criteria.md` that defines Flow A LinkedIn variant **quality** and **differentiation** criteria for US-016 (BL-006 story 2).

The criteria artifact MUST be understandable to the content operator without requiring worker source code or n8n workflow inspection.

The criteria artifact MUST answer: whether a variant is **good enough and distinct enough** to publish for its intended audience and objective during the optional supervision window defined by US-015.

The criteria artifact MUST cross-link at least: `docs/operations/linkedin-variant-review-policy.md` (US-015), `docs/GLOSSARY.md`, `docs/product/user-stories.md` US-016, and `content-strategy/silverman-editorial-system.md` anchors `#audience-map`, `#linkedin-derivative-package`, `#no-redundancy-rules`, `#anti-ai-writing-rules`, and `#linkedin-distribution-strategy`.

The criteria artifact MUST NOT contradict US-015 strategy-driven publication defaults or convert Flow A into mandatory per-variant approval.

#### Scenario: Criteria artifact exists for operators

- **WHEN** an operator opens `docs/operations/linkedin-variant-quality-criteria.md`
- **THEN** the document states it defines quality and differentiation criteria for Flow A LinkedIn variants during the optional supervision window

#### Scenario: Criteria is findable from product story

- **WHEN** an operator reads US-016 in `docs/product/user-stories.md` after this capability is implemented
- **THEN** US-016 points to `docs/operations/linkedin-variant-quality-criteria.md` as the demonstrated criteria outcome (or CURRENT-STATE does equivalent linking)

### Requirement: Default variant audience and objective association

The criteria artifact MUST include a normative mapping table for default variant IDs that associates each variant with:

- a **primary audience lens** (from `#audience-map`),
- a **publication objective** (from `#linkedin-derivative-package` objective definitions),
- and **differentiation checks** relative to sibling variants in the same package.

The mapping MUST cover at minimum: `executive-recruiter`, `technical-architect`, `engineering-leadership`, and `short-provocative`.

Campaign `variants[]` metadata produced at package generation MUST include `audience` and `objective` for each default variant entry so the association is visible in campaign JSON without opening draft files.

#### Scenario: Operator reads variant audience and objective mapping

- **WHEN** an operator reads the default variant mapping section
- **THEN** each of the four default variant IDs lists a primary audience lens and a publication objective distinct from the other variants

#### Scenario: Campaign metadata exposes objective

- **WHEN** an operator inspects `metadata/campaigns/<campaign-id>.json` after Flow A package generation
- **THEN** each `variants[]` entry includes `audience` and `objective` fields for the generated variant

### Requirement: Quality criteria for supervision-window evaluation

The criteria artifact MUST define quality checks for Flow A LinkedIn derivatives, including at minimum:

- **Source fidelity** — facts and thesis derive from the canonical blog only; no invented metrics, companies, or URLs.
- **Voice and style fit** — senior, practical tone per `#voice-and-style`; no engagement bait, hashtags, or emoji by default.
- **Anti-AI editorial patterns** — generated derivatives follow `#anti-ai-writing-rules` **rewrite/blocking** posture (documented as criteria; not Flow A blog warning posture).
- **CTA and URL rules** — CTA placement and `source_public_url` usage per `#cta-rules` and publish-confirmed URL requirements.
- **Independent readability** — each variant stands alone without requiring the blog opening.

#### Scenario: Operator evaluates source fidelity

- **WHEN** an operator reads the quality criteria section
- **THEN** the section states variants MUST NOT invent facts not present in the source blog

#### Scenario: Anti-AI posture for derivatives is stated

- **WHEN** an operator reads the quality criteria section
- **THEN** the section states generated LinkedIn derivatives use rewrite/blocking anti-AI editorial posture, distinct from Flow A user-blog warnings

### Requirement: Differentiation criteria across package siblings

The criteria artifact MUST define differentiation requirements across variants in the same package, aligned with `#no-redundancy-rules`:

- unique opening hook (first 1–2 sentences),
- distinct primary objective angle,
- varied structure and narrative arc,
- distinct CTA phrasing (same URL allowed),
- no duplicate variant text with only audience label changed.

The criteria artifact MUST include a supervision-window checklist derived from the normative mapping and differentiation rules.

#### Scenario: Operator verifies sibling differentiation

- **WHEN** an operator supervises a multi-variant package using the differentiation section
- **THEN** the section requires unique hooks and objective angles across siblings

#### Scenario: Supervision checklist exists

- **WHEN** an operator reads the supervision-window checklist
- **THEN** a condensed pass/fail checklist is present for optional evaluation while `publish_state` is `pending`

### Requirement: Criteria failure and blocked states are communicated

The criteria artifact MUST distinguish:

- **Criteria failure** — variant does not meet quality or differentiation criteria; operator SHOULD edit, defer, or cancel during supervision (persistence deferred to US-017); this is **not** a new worker `publish_state` value in US-016.
- **Normal supervision** — `pending` before API queue per US-015; not a policy failure.
- **Technical blocks** — publication enablement off, integration `failed`, OAuth action-required — follow existing publication semantics.
- **Deferred capabilities** — US-017 override mechanics, supervision console, automated similarity checks — absence is not a worker defect for US-016.

The criteria artifact MUST NOT redefine US-015 strategy-driven publication defaults or `publish_state` enum values.

#### Scenario: Criteria failure is guidance not automatic queue block

- **WHEN** an operator reads the criteria-failure section
- **THEN** the section states criteria failure guides optional supervision actions and does not introduce a mandatory approval gate or new `publish_state` for US-016

#### Scenario: Technical blocks remain separate

- **WHEN** an operator reads the blocked-states section
- **THEN** technical publication blocks are distinguished from editorial criteria failure

### Requirement: No duplication of US-015 or publication guards (US-016)

Applying US-016 criteria capability MUST NOT change US-015 strategy-driven publication defaults, Flow A ready-path completion, campaign lifecycle transitions, US-011 publication-guard semantics, or ADR-0001 (n8n → worker HTTP only).

This capability MUST NOT add worker HTTP endpoints, n8n LinkedIn publish workflows, or BL-007 auto-queue behavior.

This capability MUST NOT modify `linkedin_publication_flow.py` queue/publish/cancel behavior.

#### Scenario: US-015 defaults preserved

- **WHEN** US-016 criteria capability is applied
- **THEN** `docs/operations/linkedin-variant-review-policy.md` strategy-driven publication and optional supervision sections remain unchanged in substance (cross-link updates only)

#### Scenario: No new publication endpoints

- **WHEN** US-016 criteria capability is applied
- **THEN** no new worker LinkedIn publication routes are introduced

### Requirement: Operator-visible LinkedIn variant supervision mechanics artifact

The repository MUST provide an operator-facing mechanics document at `docs/operations/linkedin-variant-supervision-mechanics.md` that defines Flow A LinkedIn variant **supervision override mechanics** for US-017 (BL-006 story 3).

The mechanics artifact MUST be understandable to the content operator without requiring worker source code or n8n workflow inspection.

The mechanics artifact MUST define at minimum:

- **Correction (edit)** — update draft artifact atomically via worker, invalidate/register `derivative_content_sha256`, append `operator_supervision.edit_history`.
- **Rejection/cancel from `pending`** — semantics vs post-queue `cancelled` (same `publish_state`, distinct `operator_supervision.phase`).
- **Defer/delay** — update `scheduled_at_utc`, deferral history, and `auto_queue_eligible` flag.
- Relationship to US-015 strategy-driven default and optional supervision (not mandatory approval gate).
- Relationship to US-016 criteria failure (guidance → persisted action via optional `reason`).
- Blocked vs invalid actions (`queued`, `published`, `failed`, `publishing`, wrong campaign state).
- BL-007 auto-queue eligibility exclusions (documentation only).

The mechanics artifact MUST cross-link at least: `docs/operations/linkedin-variant-review-policy.md` (US-015), `docs/operations/linkedin-variant-quality-criteria.md` (US-016), `docs/GLOSSARY.md`, `docs/product/user-stories.md` US-017, and `content-strategy/silverman-editorial-system.md` `#flow-a-vs-flow-b` and `#linkedin-distribution-strategy`.

The mechanics artifact MUST NOT contradict US-015 strategy-driven publication defaults or US-016 criteria guidance.

#### Scenario: Mechanics artifact exists for operators

- **WHEN** an operator opens `docs/operations/linkedin-variant-supervision-mechanics.md`
- **THEN** the document states it defines persisted edit, defer, and cancel mechanics during the optional `pending` supervision window

#### Scenario: Mechanics is findable from product story

- **WHEN** an operator reads US-017 in `docs/product/user-stories.md` after this capability is implemented
- **THEN** US-017 points to `docs/operations/linkedin-variant-supervision-mechanics.md` as the demonstrated mechanics outcome (or CURRENT-STATE does equivalent linking)

### Requirement: Operator supervision metadata contract on variants

Campaign `variants[]` entries MUST support an `operator_supervision` object for persisted supervision decisions.

`operator_supervision` MUST NOT introduce new `publish_state` enum values.

`operator_supervision` MUST record at minimum for each action:

- `last_action` — one of `edit`, `defer`, `cancel`
- `last_action_at_utc` — UTC ISO8601 timestamp
- `phase` — `pre_queue` when action occurs while `publish_state` is `pending`; `post_queue` when cancel occurs from `queued`
- `actor` — `operator` for v1 worker routes
- optional `reason` — free-text or documented enum values including `criteria_failure` per US-016 guidance

`operator_supervision` MUST include `auto_queue_eligible` boolean defaulting to effective `true` for `pending` variants without operator override.

Edit actions MUST append to `edit_history[]` with `previous_content_sha256`, `new_content_sha256`, and `edited_at_utc`.

Defer actions MUST append to `deferral_history[]` with `previous_scheduled_at_utc`, `new_scheduled_at_utc`, and `deferred_at_utc`.

Cancel actions MUST record `cancellation` with `cancelled_at_utc`, `phase`, and optional `reason`.

#### Scenario: Operator inspects edit audit trail

- **WHEN** an operator inspects campaign metadata after a successful correction
- **THEN** the variant entry includes `operator_supervision.edit_history` with old and new content hashes and timestamp

#### Scenario: Pre-queue cancel phase is recorded

- **WHEN** an operator cancels a `pending` variant via worker
- **THEN** `publish_state` is `cancelled` and `operator_supervision.cancellation.phase` is `pre_queue`

### Requirement: Supervision blocked and invalid states are communicated

The mechanics artifact and worker responses MUST communicate blocked and invalid supervision actions, including at minimum:

- Edit/defer only allowed while `publish_state` is `pending`.
- Cancel allowed while `publish_state` is `pending` or `queued`; not allowed when `published`.
- Supervision endpoints do not require LinkedIn publication enablement (pre-API actions).
- Technical publication blocks (enablement off, OAuth, `failed`) remain separate from supervision mechanics.
- US-016 criteria failure guides operator action but does not auto-block supervision endpoints.

#### Scenario: Edit rejected when not pending

- **WHEN** an operator attempts correction for a `queued` variant
- **THEN** the worker fails with stable code `linkedin_supervision_variant_not_pending` and does not mutate artifact or metadata

#### Scenario: Criteria failure reason is optional metadata

- **WHEN** an operator corrects a variant after US-016 criteria failure
- **THEN** the operator MAY supply `reason` `criteria_failure` in the request and it is persisted in `operator_supervision` without changing `publish_state` to a new criteria-failure state

### Requirement: BL-007 auto-queue eligibility informed by supervision metadata (documentation only)

The mechanics artifact and this capability MUST document that future BL-007 auto-queue MUST NOT queue variants when any of the following apply:

- `publish_state` is not `pending` (except documented re-queue from `failed` per publication integration)
- `publish_state` is `cancelled`
- `operator_supervision.auto_queue_eligible` is `false`
- `scheduled_at_utc` is in the future relative to evaluation time

Future BL-007 MUST treat corrected `pending` variants with `auto_queue_eligible` not `false` as eligible when due per schedule.

This capability MUST NOT implement `auto_queue_pending`, MUST NOT modify `POST /publish-linkedin-due-variants` queue behavior, and MUST NOT merge BL-007 construction WIP.

#### Scenario: Cancelled variant excluded from auto-queue documentation

- **WHEN** an implementer reads the BL-007 eligibility section in the mechanics artifact
- **THEN** the text states `cancelled` variants and `auto_queue_eligible` `false` variants are excluded from auto-queue

### Requirement: Glossary distinguishes supervision overrides from publish_state and mandatory review

`docs/GLOSSARY.md` MUST define terms for **operator supervision override** (persisted edit/defer/cancel during the supervision window) and **`auto_queue_eligible`** (metadata flag for BL-007 eligibility) as distinct from technical `publish_state` and mandatory Flow B review.

#### Scenario: Glossary links supervision override to mechanics doc

- **WHEN** an operator reads supervision override terms in `docs/GLOSSARY.md`
- **THEN** the entry cross-links `docs/operations/linkedin-variant-supervision-mechanics.md`

### Requirement: No duplication of US-015, US-016, or publication guards (US-017)

Applying US-017 supervision mechanics MUST NOT change US-015 strategy-driven publication defaults, US-016 criteria substance, Flow A ready-path completion, US-011 publication-guard semantics, or ADR-0001 (n8n → worker HTTP only).

US-017 MUST NOT convert supervision into a mandatory approval gate.

US-017 MUST NOT implement BL-007 auto-queue or BL-015 console UI.

#### Scenario: US-015 optional supervision preserved

- **WHEN** US-017 capability is applied
- **THEN** `docs/operations/linkedin-variant-review-policy.md` strategy-driven and optional supervision sections remain unchanged in substance (cross-link updates only)

#### Scenario: No BL-007 implementation

- **WHEN** US-017 capability is applied
- **THEN** `POST /publish-linkedin-due-variants` behavior is unchanged and BL-007 WIP paths are not required
