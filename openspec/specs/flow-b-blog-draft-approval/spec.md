# flow-b-blog-draft-approval

## Purpose

Authenticated Flow B blog draft approve/reject presentation (US-080): list/detail/image of `blog-posts/pending-approval/` packages via worker HTTP; Silverman Authority Manager UI for review; approve records durable decision without promoting to `ready/`; reject remains non-publishable; no revision CMS / multi-round feedback / mandatory edit-apply; no Flow A / LinkedIn publish side effects. Promote + spill A (US-081) and gap trigger (US-082) remain separate capabilities.

## Requirements

### Requirement: Authenticated list and detail of pending-approval drafts

The worker SHALL expose authenticated HTTP endpoints to list and retrieve Flow B blog drafts from `blog-posts/pending-approval/` (for example `GET /flow-b/pending-approval-drafts` and `GET /flow-b/pending-approval-drafts/{draft_id}`). Unauthenticated requests MUST be rejected. List and detail responses MUST include fields needed for operator presentation: title/topic, discovery summary (`topic_id`, `thesis`, `referent_positioning`, `rationale`), draft status, relative paths, and when present gap context (`target_week`, `empty_days[]`). Detail MUST include the Markdown body. Path identifiers MUST be confined to `blog-posts/pending-approval/`; path traversal MUST fail closed. Orchestration remains **n8n → worker HTTP only** (ADR-0001); this capability MUST NOT introduce n8n Execute Command usage.

#### Scenario: Unauthenticated list is rejected

- **WHEN** a client calls the pending-approval drafts list endpoint without valid worker authentication
- **THEN** the request is rejected and no draft metadata is returned as a successful list

#### Scenario: List presents pending drafts with discovery and gap fields

- **WHEN** an authenticated client lists pending-approval drafts and one or more packages exist with sidecars
- **THEN** each listed item includes title/topic, discovery summary fields, status, and relative paths
- **AND** when the sidecar contains `target_week` and/or `empty_days[]`, those fields are included

#### Scenario: Detail returns body for operator review

- **WHEN** an authenticated client requests detail for an existing pending-approval `draft_id`
- **THEN** the response includes the Markdown body and presentation fields for that draft
- **AND** the draft remains under `blog-posts/pending-approval/`

#### Scenario: Path traversal is rejected

- **WHEN** an authenticated client supplies a `draft_id` that would escape `blog-posts/pending-approval/`
- **THEN** the worker fails closed with a clear operator-visible error
- **AND** no files outside the pending-approval tree are read as draft content

### Requirement: Authenticated hero image for console presentation

The worker SHALL expose an authenticated HTTP route that returns the hero image bytes for a pending-approval draft (for example `GET /flow-b/pending-approval-drafts/{draft_id}/image`), confined to the matching PNG under `blog-posts/pending-approval/`. Unauthenticated image requests MUST be rejected. The route MUST NOT expose arbitrary filesystem paths.

#### Scenario: Authenticated image is returned for a pending draft

- **WHEN** an authenticated client requests the image for a draft that has a sibling PNG under `blog-posts/pending-approval/`
- **THEN** the worker returns the image content for console display

#### Scenario: Unauthenticated image request is rejected

- **WHEN** a client requests a pending-approval draft image without valid worker authentication
- **THEN** the request is rejected and image bytes are not returned as a successful response

### Requirement: Approve records decision without promoting to ready

The worker SHALL expose an authenticated approve action (for example `POST /flow-b/pending-approval-drafts/{draft_id}/approve`) that records the operator approve decision in durable sidecar metadata for the draft. Approve MUST NOT move or copy the Markdown/image/sidecar pair into `blog-posts/ready/`. Approve MUST NOT invoke Flow A publish/package/schedule, GitHub Pages publication, or LinkedIn API publish. The response MUST communicate that promotion to Flow A eligibility remains a separate step (US-081) — for example via `promoted: false` / `promotion_pending: true`.

#### Scenario: Approve updates sidecar and leaves files in pending-approval

- **WHEN** an authenticated client approves an existing pending draft
- **THEN** durable sidecar metadata records an approved decision (including a UTC timestamp)
- **AND** the `.md` / `.png` / sidecar remain under `blog-posts/pending-approval/`
- **AND** `blog-posts/ready/` gains no files from this action

#### Scenario: Approve response communicates promotion still pending

- **WHEN** approve succeeds
- **THEN** the response indicates the draft is approved but not promoted to `ready/`
- **AND** the response does not claim Flow A publish eligibility is complete

### Requirement: Reject marks draft non-publishable

The worker SHALL expose an authenticated reject action (for example `POST /flow-b/pending-approval-drafts/{draft_id}/reject`) that records a rejected/blocked state in durable sidecar metadata. Rejected drafts MUST remain non-publishable: the action MUST NOT promote, move, or copy the pair into `blog-posts/ready/`. The rejected/blocked state MUST be clearly communicable via HTTP response and list/detail status fields. An optional single free-text rejection reason MAY be accepted; the capability MUST NOT require a structured multi-round feedback or revision-history workflow.

#### Scenario: Reject updates status and does not promote

- **WHEN** an authenticated client rejects an existing pending draft
- **THEN** durable sidecar metadata records rejected status with a UTC timestamp
- **AND** no files are written under `blog-posts/ready/` from this action

#### Scenario: Rejected drafts are clearly identifiable

- **WHEN** an authenticated client lists or retrieves a rejected draft (via status filter or detail)
- **THEN** the response status clearly indicates rejected/blocked
- **AND** the draft is not presented as approve-pending by default list behavior

### Requirement: Silverman Authority Manager presents approve or reject

Silverman Authority Manager (the existing operator console surface, not a separate Flow B-only application) SHALL present pending drafts from `blog-posts/pending-approval/` with title/topic, body, image, discovery summary, and gap week / empty-days when present, and SHALL expose approve and reject actions that call the authenticated worker endpoints. The UI MUST communicate rejected/blocked and failure states clearly. The UI MUST NOT require a revision-history CMS, structured multi-round feedback capture, or a mandatory in-app edit-apply loop (offline file edits remain out of band).

#### Scenario: Operator can review a pending draft in Authority Manager

- **WHEN** an authenticated operator opens the Flow B pending-drafts presentation in Silverman Authority Manager and pending packages exist
- **THEN** the console shows title/topic, body, image, and discovery summary for a selectable draft
- **AND** gap week / empty-days are shown when present on that draft

#### Scenario: Operator can approve or reject from Authority Manager

- **WHEN** an authenticated operator chooses approve or reject for a pending draft
- **THEN** the console invokes the corresponding authenticated worker action
- **AND** the resulting approved or rejected state is visible to the operator

#### Scenario: Rejected or failed states are communicated in the UI

- **WHEN** a draft is rejected or an approve/reject/list call fails
- **THEN** the console communicates the rejected/blocked or failure state clearly
- **AND** the UI does not imply the draft was promoted to `ready/` or published

### Requirement: No publication or Flow A side effects

This capability MUST NOT auto-publish blog posts, invoke Flow A publish/package/schedule, create Flow A campaign lifecycle side effects, hand off to GitHub Pages git publication, call LinkedIn API publish, or modify `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. Approve and reject MUST NOT promote drafts to `blog-posts/ready/` (promotion remains US-081).

#### Scenario: No ready folder writes on approve or reject

- **WHEN** approve or reject completes successfully
- **THEN** `blog-posts/ready/` gains no new files from this capability

#### Scenario: No Flow A or LinkedIn publish invocation

- **WHEN** list, detail, approve, or reject runs
- **THEN** Flow A publish/package/schedule and LinkedIn API publication are not invoked

### Requirement: Fail closed with operator-visible errors

When a draft cannot be listed, read, approved, or rejected (missing draft, invalid id, conflicting status, filesystem errors), the worker MUST fail closed with clear operator-visible structured errors. Failures MUST NOT be reported as successful approve, successful reject, or successful promotion.

#### Scenario: Missing draft fails closed

- **WHEN** an authenticated client approves or rejects a `draft_id` that does not exist under `blog-posts/pending-approval/`
- **THEN** the worker returns a structured operator-visible error
- **AND** the response is not a successful approve or reject

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
