# flow-b-blog-draft-promotion

## Purpose

US-081: Authenticated promote of approved Flow B pending-approval packages to blog-posts/ready/, Authority Manager promote affordance, Flow A path reuse after promotion, and spill algorithm A scheduling under US-040K max 2.

## Requirements

### Requirement: Authenticated promote of approved pending-approval drafts

The worker SHALL expose an authenticated HTTP promote action (for example `POST /flow-b/pending-approval-drafts/{draft_id}/promote`) that promotes an already-approved Flow B blog draft from `blog-posts/pending-approval/` to `blog-posts/ready/`. Unauthenticated requests MUST be rejected. Orchestration remains **n8n → worker HTTP only** (ADR-0001); this capability MUST NOT introduce n8n Execute Command usage. Promote MUST require sidecar `status` `approved` with durable approval metadata (`approved_at_utc`, draft id/slug, and `approved_by` when recorded). Promote MUST NOT succeed for unapproved or rejected drafts.

#### Scenario: Unauthenticated promote is rejected

- **WHEN** a client calls the promote endpoint without valid worker authentication
- **THEN** the request is rejected and no files are moved into `blog-posts/ready/`

#### Scenario: Promote requires prior approve decision

- **WHEN** an authenticated client promotes a draft whose sidecar status is still `pending_approval`
- **THEN** the worker fails closed with a clear operator-visible error
- **AND** no files are written under `blog-posts/ready/` from this attempt

#### Scenario: Rejected draft cannot be promoted

- **WHEN** an authenticated client promotes a draft whose sidecar status is `rejected`
- **THEN** the worker fails closed with a clear operator-visible error
- **AND** no files are written under `blog-posts/ready/`

### Requirement: Promote moves Markdown image pair and metadata to ready

On successful promote, the worker MUST move the draft Markdown file, sibling PNG, and Flow B sidecar (`.flow-b.json`) from `blog-posts/pending-approval/` into `blog-posts/ready/`, preserving the editorial basename. Path identifiers MUST be confined; path traversal MUST fail closed. Destination basename collision under `ready/` MUST fail closed without partial moves. After promote, durable sidecar metadata MUST record `status: promoted`, `promoted_at_utc`, draft id/slug, preserved `approved_at_utc` / `approved_by`, updated `ready/` relative paths, `origin: flow_b`, and when present preserved `target_week` / `empty_days[]`.

#### Scenario: Approved draft is moved to ready with promotion metadata

- **WHEN** an authenticated client promotes an approved pending-approval draft with complete `.md` + `.png` + sidecar
- **THEN** those artifacts are present under `blog-posts/ready/` and absent from `blog-posts/pending-approval/`
- **AND** the sidecar records promoted status with who/when/draft id (and preserved approval fields)

#### Scenario: Incomplete pair fails closed

- **WHEN** an authenticated client promotes an approved draft missing its sibling PNG
- **THEN** the worker fails closed with a clear operator-visible error
- **AND** no partial promote leaves Markdown alone under `ready/`

#### Scenario: Ready basename collision fails closed

- **WHEN** promote would overwrite an existing `blog-posts/ready/<slug>.md` (or sibling PNG)
- **THEN** the worker fails closed without moving the pending-approval artifacts

### Requirement: Promote does not auto-run Flow A or LinkedIn publish

Promote MUST NOT invoke Flow A publish/package/schedule, GitHub Pages git publication, or LinkedIn API publish. Promote establishes Flow A eligibility only. Optional `dry_run` MUST validate and return would-be ready paths without durable filesystem moves or sidecar mutation.

#### Scenario: Successful promote does not publish

- **WHEN** promote completes successfully
- **THEN** Flow A publish/package/schedule and LinkedIn API publication are not invoked
- **AND** the response indicates Flow A eligibility via `ready/` without claiming blog or LinkedIn published

#### Scenario: Dry-run promote does not move files

- **WHEN** an authenticated client calls promote with `dry_run=true` for an eligible approved draft
- **THEN** the response describes the would-be promote outcome
- **AND** artifacts remain under `blog-posts/pending-approval/`

### Requirement: After promotion Flow A path is reused without second LinkedIn gate

After a draft is promoted into `blog-posts/ready/`, blog publish, LinkedIn package generation, distribution scheduling, and optional LinkedIn supervision MUST reuse existing Flow A behavior and endpoints. This capability MUST NOT introduce a second mandatory LinkedIn approval queue for Flow B–origin content. Campaigns created from promoted sources MUST use Flow A lifecycle (`flow` `flow_a`) while retaining Flow B provenance metadata for spill scheduling.

#### Scenario: Promoted draft is Flow A eligible without mandatory LinkedIn review queue

- **WHEN** a draft has been successfully promoted to `blog-posts/ready/`
- **THEN** subsequent publish/package/schedule MAY proceed via Flow A worker endpoints
- **AND** no additional mandatory LinkedIn approval queue is required solely because the blog originated in Flow B

### Requirement: Spill algorithm A for Flow B origin LinkedIn scheduling

When scheduling LinkedIn variants for a Flow B–origin promoted blog (provenance with usable `target_week` and/or `empty_days[]`), the worker MUST apply spill algorithm A under US-040K local-day density max 2 (operator settings `density_max_per_local_day` default 2, never exceeding max 2): (1) fill target-week gap days chronological with remaining capacity; (2) then other days in the target week with remaining capacity; (3) then forward day-by-day after the week with remaining capacity. Scheduling MUST remain on the Flow A schedule service (strategy such as `flow_b_spill_a`); MUST NOT call LinkedIn API publish; MUST fail closed rather than exceed density max 2. When Flow B gap provenance is absent, default Flow A stagger scheduling MUST remain available.

#### Scenario: Spill A fills gap days first under max 2

- **WHEN** distribution scheduling runs for a Flow B–origin campaign with `empty_days[]` in the target week and density capacity available
- **THEN** variants are placed first onto those gap days in chronological order without exceeding max 2 per local day

#### Scenario: Spill A continues within week then forward

- **WHEN** gap days are full or exhausted and additional variants remain
- **THEN** placement continues to other days in the target week with remaining capacity
- **AND** then forward day-by-day after the week under max 2

#### Scenario: Non–Flow-B campaigns keep default stagger

- **WHEN** distribution scheduling runs for a campaign without Flow B gap provenance and strategy is default
- **THEN** existing Flow A staggered scheduling behavior is used
- **AND** spill algorithm A is not required

### Requirement: Silverman Authority Manager promote affordance

Silverman Authority Manager (existing console surface) SHALL expose a promote action for drafts in approved-not-promoted state that calls the authenticated promote endpoint, and SHALL communicate promoted, approved-but-not-promoted, rejected/blocked, and failure states clearly. The UI MUST NOT replace or remove US-080 approve/reject presentation, and MUST NOT add a revision-history CMS or mandatory edit-apply loop.

#### Scenario: Operator can promote an approved draft from Authority Manager

- **WHEN** an authenticated operator views an approved-not-promoted Flow B draft in Authority Manager and chooses promote
- **THEN** the console invokes the authenticated promote endpoint
- **AND** the resulting promoted / Flow A–eligible state is visible

#### Scenario: Failures are communicated in the UI

- **WHEN** promote fails (not approved, collision, incomplete pair, auth, or filesystem error)
- **THEN** the console communicates the failure clearly
- **AND** the UI does not imply the draft was published to the blog or LinkedIn

### Requirement: Idempotent promote and fail-closed errors

Re-promote of an already-promoted draft whose artifacts already exist under `ready/` with matching provenance MUST return success without duplicate side effects. Missing draft, path traversal, conflicting status, and filesystem errors MUST fail closed with structured operator-visible errors and MUST NOT be reported as successful promotion.

#### Scenario: Idempotent re-promote

- **WHEN** an authenticated client promotes a draft that is already `promoted` with matching files under `ready/`
- **THEN** the response indicates success without creating duplicate ready artifacts

#### Scenario: Missing draft fails closed

- **WHEN** an authenticated client promotes a `draft_id` that does not exist under `pending-approval/` (and is not an idempotent already-promoted case)
- **THEN** the worker returns a structured operator-visible error
- **AND** the response is not a successful promote

### Requirement: US-081 scope excludes gap trigger auto-publish and CMS

This capability MUST NOT implement gap trigger orchestration (US-082), auto-publish blog/LinkedIn without Flow A guards, revision-history CMS, or multi-round feedback. It MUST NOT change US-080 approve/reject decision-only semantics (approve still MUST NOT promote). It MUST NOT close BL-018 or mark US-081 Story accepted without operator walkthrough. Marking CURRENT-STATE as implemented is allowed when automated evidence exists.

#### Scenario: No gap trigger required for US-081 completion

- **WHEN** this capability's requirements are evaluated
- **THEN** gap trigger endpoints and unattended weekly draft spam protection are not required for US-081 completion

#### Scenario: Approve remains decision-only

- **WHEN** US-080 approve is invoked after this capability lands
- **THEN** approve still MUST NOT move drafts to `blog-posts/ready/`
- **AND** promotion remains the promote action defined here
