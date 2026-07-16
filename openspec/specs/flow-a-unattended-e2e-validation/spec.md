# flow-a-unattended-e2e-validation

## Purpose

Operator and system requirements for proving fully unattended Flow A with real ready content — Manual and Schedule Trigger evidence windows, ready-gate prerequisites, live blog side effects, package/schedule/lifecycle/calendar completion, PASS/PENDING/FAIL ops reporting, and BL-005 closure without claiming LinkedIn API publication or BL-007 (US-012–US-014).

## Requirements

### Requirement: Dual-trigger unattended Flow A evidence with serialized ready

Unattended Flow A validation for BL-005 SHALL demonstrate two separate executions against real ready Markdown: one via Manual Trigger and one via Schedule Trigger. The operator MUST serialize `blog-posts/ready/` so that each execution sees exactly one intended candidate (ready count 1 for the target post).

#### Scenario: Manual run with single ready post

- **WHEN** only the Manual-designated post is present under `blog-posts/ready/` and Manual Trigger executes `silvermanFlowAPublish01`
- **THEN** Flow A processes that post through publish → package → schedule → lifecycle without requiring mid-run technical intervention

#### Scenario: Schedule run with single ready post

- **WHEN** only the Schedule-designated post is present under `blog-posts/ready/` after the Manual campaign completed and Schedule Trigger fires
- **THEN** Flow A processes that post through the same HTTP path without mid-run technical intervention

#### Scenario: Both posts in ready for Manual is invalid dual-evidence

- **WHEN** both BL-005 posts are left in ready during a Manual run
- **THEN** that run MUST NOT be treated as successful dual Manual+Schedule evidence for BL-005

### Requirement: Ready-gate prerequisites before unattended triggers

Before Manual or Schedule evidence runs, posts MUST pass Flow A ready-post editorial validation prerequisites (required front matter fields and image remediation eligibility when ComfyUI is enabled). Non-content junk files (for example AppleDouble `._*`) MUST be removed from ready.

#### Scenario: Incomplete front matter blocks evidence start

- **WHEN** a candidate lacks required front matter fields (`layout`, `date`, `categories`, `tags`, `description`, `image`, and other required fields)
- **THEN** operators remediate before claiming unattended success and evidence records remediation

#### Scenario: AppleDouble files removed

- **WHEN** ready contains `._*` companion files alongside Markdown posts
- **THEN** those files are removed before trigger so they are not treated as candidates

### Requirement: Full-path outcomes for each unattended run

Each successful unattended run SHALL demonstrate: ready acceptance, image generation or validation as required, blog publication including live-site confirmation when enabled/opted in, LinkedIn package generation, distribution scheduling, source lifecycle completion, and campaign records. Calendar records MUST be completed or reconciled when the editorial calendar is configured.

LinkedIn API publication endpoints MUST NOT be invoked by Flow A during BL-005 evidence.

#### Scenario: Manual campaign reaches distribution and lifecycle completion

- **WHEN** the Manual unattended run succeeds
- **THEN** campaign metadata shows package and distribution scheduling and source is not left stuck in ready

#### Scenario: Schedule campaign reaches distribution and lifecycle completion

- **WHEN** the Schedule unattended run succeeds
- **THEN** campaign metadata shows package and distribution scheduling and source is not left stuck in ready

#### Scenario: Flow A does not call LinkedIn publication APIs

- **WHEN** either BL-005 evidence run completes
- **THEN** worker LinkedIn publication endpoints are not invoked by the Flow A workflow and no new LinkedIn API post is created for this test

### Requirement: Operator-visible pass fail pending for unattended E2E

BL-005 verification MUST emit human-readable overall status with distinct modes and remediation for Manual and Schedule sections.

Supported overall states MUST include at minimum: `PASS`, `PENDING`, and `FAIL`.

Failure/pending modes MUST distinguish at minimum:

- Ready serialization violated (`FAIL`)
- Ready-gate validation failure (`FAIL`)
- Manual or Schedule run hard failure (`FAIL`)
- Schedule evidence not yet collected after Post B placement (`PENDING`)
- Calendar expectations unmet when calendar is configured (`FAIL` or `PENDING` with remediation)
- Secrets printed (`FAIL`)

Evidence MUST be written under `docs/operations/` (for example `bl-005-unattended-flow-a-validation-YYYY-MM-DD.md`).

#### Scenario: Pass when Manual and Schedule both succeed

- **WHEN** Manual and Schedule evidence sections both succeed with full-path outcomes
- **THEN** verification reports overall `PASS` and product progress may close BL-005

#### Scenario: Pending while waiting for Schedule

- **WHEN** Manual succeeded and Post B is staged but Schedule has not fired yet
- **THEN** verification reports `PENDING` for the Schedule section with remediation to wait for `0 9 * * *` UTC

### Requirement: BL-005 closure without claiming LinkedIn API or BL-007

Successful BL-005 validation SHALL allow closing backlog item BL-005 (US-012, US-013, US-014). It MUST NOT mark BL-006 or BL-007 complete and MUST NOT claim LinkedIn API publication as part of unattended Flow A.

Product progress and CURRENT-STATE updates MUST occur only after demonstrated evidence.

#### Scenario: BL-005 closable after dual evidence

- **WHEN** US-012, US-013, and US-014 acceptance criteria are demonstrated across the Manual and Schedule evidence
- **THEN** product progress may close BL-005

#### Scenario: BL-007 remains open

- **WHEN** BL-005 validation passes
- **THEN** scheduled LinkedIn API publication (BL-007) remains incomplete
