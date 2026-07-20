## ADDED Requirements

### Requirement: Promote handoff from approved decision

Capability `flow-b-blog-draft-approval` SHALL treat successful approve as a decision-only handoff to capability `flow-b-blog-draft-promotion` (US-081). Approve responses MUST continue to communicate that Flow A eligibility requires promote (`promoted: false` / `promotion_pending: true` until promote succeeds). Silverman Authority Manager MAY expose a promote control for approved drafts that calls the US-081 promote endpoint; that control is owned by promotion behavior and MUST NOT change approve/reject decision-only semantics.

#### Scenario: Approve still leaves promotion pending

- **WHEN** an authenticated client approves a pending draft after US-081 lands
- **THEN** durable sidecar metadata records approved status
- **AND** the `.md` / `.png` / sidecar remain under `blog-posts/pending-approval/` until promote
- **AND** the approve response indicates promotion is still pending

#### Scenario: Authority Manager can surface promote after approve

- **WHEN** an authenticated operator has an approved-not-promoted draft in Authority Manager
- **THEN** the console MAY offer promote via the US-081 authenticated promote action
- **AND** approve/reject presentation from US-080 remains available for non-promoted drafts

## MODIFIED Requirements

### Requirement: US-080 scope excludes promote, spill, trigger, and CMS

This capability MUST NOT implement promote/move to `blog-posts/ready/` inside the approve action, MUST NOT implement spill algorithm A inside approve/reject, and MUST NOT implement gap trigger orchestration (US-082). Promote/move and spill algorithm A are owned by capability `flow-b-blog-draft-promotion` (US-081). This capability MUST NOT introduce a revision-history CMS or mandatory edit-apply loop. It MUST NOT change the HTTP contracts of `flow-b-blog-draft-generation` (`POST /flow-b/generate-blog-drafts`), `flow-b-topic-discovery`, `flow-b-calendar-gap-detect`, or `flow-b-gap-operator-settings` except by reading/updating pending-approval artifacts produced by draft generation. Approve MUST remain decision-only (`promoted: false` / `promotion_pending: true`).

#### Scenario: Approve does not promote

- **WHEN** approve completes successfully
- **THEN** `blog-posts/ready/` gains no new files from the approve action
- **AND** promotion remains a separate authenticated promote action (US-081)

#### Scenario: No trigger required for US-080 completion

- **WHEN** this capability's requirements are evaluated
- **THEN** gap trigger endpoints are not required for US-080 completion
- **AND** spill algorithm A is not implemented by approve/reject

#### Scenario: Generation contract unchanged

- **WHEN** this capability is implemented
- **THEN** `POST /flow-b/generate-blog-drafts` remains the generation-only write path into `pending-approval/`
