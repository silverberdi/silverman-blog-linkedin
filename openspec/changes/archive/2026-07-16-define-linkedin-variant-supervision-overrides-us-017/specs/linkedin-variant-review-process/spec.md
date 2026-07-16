## ADDED Requirements

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
