## ADDED Requirements

### Requirement: Operator-visible editorial backup policy artifact

The system SHALL provide an operator-facing policy document at `docs/operations/editorial-backup-scope-retention-integrity.md` that defines editorial-state backup scope, retention, and integrity verification for BL-014 / US-036.

The policy MUST:

- state included and excluded path classes under the editorial base path;
- define retention for packages under `metadata/backups/`;
- describe how operators run integrity verification and interpret `pass` / `fail` / `blocked`;
- communicate failures and blocked states with stable reason language;
- state that restoration testing and the recovery procedure belong to US-037;
- forbid embedding secrets, tokens, content bodies, or absolute secret-bearing paths in integrity reports or examples.

#### Scenario: Operator locates backup policy

- **WHEN** an operator opens `docs/operations/editorial-backup-scope-retention-integrity.md`
- **THEN** the document defines backup scope, retention, and integrity verification in language understandable to a system operator

#### Scenario: Policy separates US-036 from US-037

- **WHEN** an operator reads the policy boundary section
- **THEN** the document states that restore drills and the recovery procedure are US-037 and are not required for US-036 acceptance

### Requirement: Editorial backup scope inventory

Editorial backup scope MUST include the following relative path classes under `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` when present:

- `blog-posts/ready/`, `blog-posts/queued/`, `blog-posts/processed/`, `blog-posts/error/`
- `linkedin-posts/review/`, `linkedin-posts/approved/`, `linkedin-posts/published/`
- `metadata/campaigns/`
- `metadata/runs/`
- `editorial-calendar/` (including `calendar.json` when present)
- `prompts/`
- binary or image assets co-located inside those included trees

Editorial backup scope MUST exclude:

- contents of `metadata/backups/` when assembling a new package (no recursive backup-of-backups by default)
- secrets and credential material (including `.env`, API keys, LinkedIn tokens, and credential files)
- the public GitHub Pages checkout path (handoff / live site target is not a substitute for editorial source trees)
- worker source trees, Docker images, and shared-stack services (n8n, postgres, and related backup-runner scope)
- transient junk files (for example `.DS_Store`, `__pycache__/`, `*.tmp`)

Ambiguous requests to treat an excluded class as in-scope MUST fail closed pending a new approved OpenSpec change.

#### Scenario: Scope includes campaign and calendar state

- **WHEN** an operator consults the normative backup scope
- **THEN** `metadata/campaigns/`, `metadata/runs/`, and `editorial-calendar/` are listed as included

#### Scenario: Scope excludes secrets and public checkout

- **WHEN** an operator consults the normative backup exclusions
- **THEN** secrets/credential material and the public GitHub Pages checkout are listed as excluded

#### Scenario: Ambiguous scope fails closed

- **WHEN** an operator requests treating an excluded class as required backup scope without a new approved change
- **THEN** the policy and verifier treat the request as blocked or out of contract rather than silently expanding scope

### Requirement: Backup package root and layout

Editorial backup packages MUST be stored under `{editorial_base}/metadata/backups/<backup_id>/`.

Each package MUST include:

- `manifest.json` with schema version, `backup_id`, UTC created timestamp, scope declaration, retention metadata fields as applicable, and a per-file index of relative paths with sha256 digests and sizes;
- a `content/` tree (or equivalent archive layout documented in the policy) holding mirrored relative paths from the included scope.

Manifest path entries MUST be relative, MUST NOT contain `..` segments, and MUST NOT be absolute filesystem paths.

#### Scenario: Package lives under metadata/backups

- **WHEN** a valid editorial backup package exists
- **THEN** it is located at `metadata/backups/<backup_id>/` with `manifest.json` present

#### Scenario: Manifest rejects path traversal

- **WHEN** integrity verification reads a manifest entry containing `..` or an absolute path
- **THEN** verification reports `fail` with a stable path-safety reason code and does not follow the unsafe path

### Requirement: Backup retention policy

The system SHALL define retention for packages under `metadata/backups/` as retaining the **7 most recent** integrity-eligible packages by default.

Retention prune operations MUST:

- only delete or remove package directories under `metadata/backups/`;
- MUST NOT modify `blog-posts/`, `linkedin-posts/`, `metadata/campaigns/`, `metadata/runs/`, `editorial-calendar/`, or `prompts/`;
- MUST NOT auto-delete packages whose latest integrity status is `fail` or `blocked` (failed packages remain until explicit operator removal).

#### Scenario: Retention prune stays inside backups root

- **WHEN** retention prune runs against an editorial base path
- **THEN** no files outside `metadata/backups/` are deleted or modified

#### Scenario: Failed packages are retained

- **WHEN** a package has integrity status `fail` or `blocked`
- **THEN** routine retention prune does not auto-delete that package

### Requirement: Automated backup integrity verification

The system SHALL provide automated integrity verification for an editorial backup package that returns a structured result with:

- `status` of exactly one of `pass`, `fail`, or `blocked`;
- stable `reason_codes` (array; empty on clean `pass`);
- summary counts safe for operators (for example files checked, mismatches);
- paths reported relative to the package or editorial base only.

Verification MUST:

- mark `blocked` when the package or manifest is missing, unreadable, or schema-ambiguous so verification cannot complete;
- mark `fail` when the package is readable but violates the integrity contract (hash/size mismatch, missing required scope class representation, path traversal, or excluded content present);
- confirm each manifest file entry exists under the package content root and matches declared sha256 and size;
- confirm required scope path classes are represented or explicitly recorded empty;
- refuse to restore or mutate source editorial trees;
- omit secret values, token material, and file content bodies from the result.

#### Scenario: Passing package

- **WHEN** integrity verification runs on a fixture package whose files match the manifest and scope contract
- **THEN** the result `status` is `pass` with empty `reason_codes`

#### Scenario: Hash mismatch fails

- **WHEN** a manifest entry’s content bytes do not match the declared sha256
- **THEN** the result `status` is `fail` with a stable hash-mismatch reason code

#### Scenario: Missing package is blocked

- **WHEN** integrity verification is requested for a non-existent `backup_id` under `metadata/backups/`
- **THEN** the result `status` is `blocked` with a stable missing-package reason code

#### Scenario: Integrity report is secret-safe

- **WHEN** integrity verification produces a result for any package
- **THEN** the result does not include API keys, tokens, `.env` values, or file content bodies

#### Scenario: Verification does not restore

- **WHEN** integrity verification completes with any status
- **THEN** source editorial trees outside the inspected backup package are not written, moved, or restored by the verifier

### Requirement: Optional copy-out package build without source mutation

IF a package builder is provided in this change, it MUST copy included scope into `metadata/backups/<backup_id>/` only, MUST write `manifest.json`, MUST NOT modify source editorial trees as part of build, and MUST exclude excluded classes.

Absence of a builder MUST NOT block integrity verification of fixture packages.

#### Scenario: Builder writes only under metadata/backups

- **WHEN** an optional package builder creates a backup from an editorial fixture tree
- **THEN** new files appear under `metadata/backups/<backup_id>/` and source included trees remain byte-unchanged aside from unrelated concurrent activity outside the builder

### Requirement: US-036 does not claim restore completion

US-036 deliverables MUST NOT mark BL-014 complete, MUST NOT mark US-037 acceptance criteria satisfied, and MUST NOT perform live restore drills that mutate production editorial state.

Product progress updates after implementation MUST leave US-036 / BL-014 open until later operator acceptance of demonstrated criteria.

#### Scenario: Story boundary preserved

- **WHEN** US-036 scope, retention, and integrity artifacts are delivered
- **THEN** restoration testing and recovery procedure documentation remain deferred to US-037 and product checkboxes for US-036 acceptance stay open until operator acceptance
