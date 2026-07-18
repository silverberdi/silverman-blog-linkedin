# editorial-backup-restore-recovery

## Purpose

Operator-visible contracts for editorial-state **restoration testing** and **recovery procedure** (BL-014 / US-037): restore drills against verified packages under `metadata/backups/`, protected US-036 scope classes, dry-run / fixture-first defaults, fail-closed live mutation, secret-safe `pass` / `fail` / `blocked` reporting, and an explicit boundary that US-036 remains definition/verify only.

## Requirements

### Requirement: Operator-visible editorial recovery procedure artifact

The system SHALL provide an operator-facing recovery procedure document at `docs/operations/editorial-backup-restore-recovery.md` that defines how to test restoration and how to recover editorial state from a verified backup for BL-014 / US-037.

The recovery procedure MUST:

- state that US-036 integrity verification (`pass`) is a prerequisite for restore mutation;
- describe fixture / dry-run restore drills before any live production mutation;
- document fail-closed gates for live restore (explicit operator confirmation);
- list protected path classes matching US-036 included scope (calendar, campaigns, runs, blog posts, LinkedIn artifacts, prompts, co-located images/binaries);
- state exclusions (secrets, public GitHub Pages checkout as SoT, shared-stack services, recursive backup packages as source content);
- describe how operators interpret restore `pass` / `fail` / `blocked` outcomes with stable reason language;
- forbid embedding secrets, tokens, content bodies, or absolute secret-bearing paths in restore reports or examples;
- state that Git push, Pages deploy, and LinkedIn API publication are not part of editorial restore;
- state that this document alone does not accept US-037 or close BL-014.

#### Scenario: Operator locates recovery procedure

- **WHEN** an operator opens `docs/operations/editorial-backup-restore-recovery.md`
- **THEN** the document defines restoration testing and recovery steps in language understandable to a system operator

#### Scenario: Procedure separates US-036 verify from US-037 restore

- **WHEN** an operator reads the prerequisite section
- **THEN** the document states that integrity verification remains US-036 and restore drills / recovery procedure are US-037

#### Scenario: Live restore is fail-closed in the procedure

- **WHEN** an operator reads the live restore section
- **THEN** the document requires explicit confirmation and prefers fixture or dry-run drills before mutating production editorial trees

### Requirement: Restoration drills against verified backup packages

The system SHALL provide automated restoration drill capability that:

- reads an editorial backup package under `{editorial_base}/metadata/backups/<backup_id>/`;
- requires US-036 integrity verification status `pass` before writing restored files;
- supports dry-run (no writes) and restore-to-explicit-target (fixture/staging) modes;
- refuses live production overwrite by default unless an explicit live-confirmation mechanism is supplied;
- returns a structured result with `status` of exactly one of `pass`, `fail`, or `blocked`, stable `reason_codes`, and secret-safe summaries.

Restoration drills MUST NOT use n8n Execute Command (ADR-0001) and MUST NOT introduce a new primary FastAPI restore route in this capability’s default delivery.

#### Scenario: Fixture restore drill passes

- **WHEN** a restore drill runs against a fixture package with integrity `pass` into an empty explicit target tree
- **THEN** the result `status` is `pass` and protected scope classes present in the package appear under the target

#### Scenario: Integrity fail blocks restore

- **WHEN** restore is requested for a package whose integrity status is not `pass`
- **THEN** the restore result `status` is `blocked` with a stable integrity-prerequisite reason code and no target editorial files are written

#### Scenario: Dry-run does not mutate

- **WHEN** a dry-run restore is requested for a pass-integrity package
- **THEN** the result communicates planned coverage without writing files into the target tree

#### Scenario: Live restore without confirmation is blocked

- **WHEN** a live restore into a production editorial base is requested without explicit live confirmation
- **THEN** the result `status` is `blocked` with a stable confirmation-required reason code and no production files are written

### Requirement: Protected editorial classes on restore

Restore and restore drills MUST protect and, when present in the pass-integrity package, restore the following relative path classes under the restore target base:

- `blog-posts/ready/`, `blog-posts/queued/`, `blog-posts/processed/`, `blog-posts/error/`
- `linkedin-posts/review/`, `linkedin-posts/approved/`, `linkedin-posts/published/`
- `metadata/campaigns/`
- `metadata/runs/`
- `editorial-calendar/` (including `calendar.json` when present)
- `prompts/`
- binary or image assets co-located inside those included trees

Restore MUST NOT:

- restore secrets or credential material (including `.env`, API keys, LinkedIn tokens, and credential files) into the target;
- use the public GitHub Pages checkout as the restore source of truth;
- write package contents from `metadata/backups/` into restored editorial source trees as if they were editorial content;
- mutate backup packages under `metadata/backups/` as part of restore.

#### Scenario: Campaigns and calendar are restored in a drill

- **WHEN** a pass-integrity fixture package includes `metadata/campaigns/` and `editorial-calendar/` content and a restore drill targets an explicit fixture base
- **THEN** those classes are present under the target after a `pass` result

#### Scenario: LinkedIn artifacts and images are restored in a drill

- **WHEN** a pass-integrity fixture package includes LinkedIn post files and co-located image binaries under included trees
- **THEN** a successful restore drill materializes those artifacts under the corresponding target paths

#### Scenario: Secrets are refused

- **WHEN** restore encounters a secret-like relative path in package content despite prior checks
- **THEN** the restore result is `fail` or `blocked` with a stable secret-refusal reason code and the secret path is not written to the target

#### Scenario: Public checkout is not restore SoT

- **WHEN** an operator consults the normative restore exclusions
- **THEN** the public GitHub Pages checkout is listed as not the editorial restore source of truth

### Requirement: Secret-safe restore outcome reporting

Restore results and documentation examples MUST:

- omit API keys, tokens, `.env` values, and file content bodies;
- prefer paths relative to the editorial base, backup package root, or restore target root;
- include `status`, `reason_codes` (empty on clean `pass`), and summary counts safe for operators.

#### Scenario: Restore report is secret-safe

- **WHEN** restore produces a result for any package or mode
- **THEN** the result does not include API keys, tokens, `.env` values, or file content bodies

### Requirement: Clear failure and blocked communication

Restore status meanings MUST be:

- `pass` — dry-run validated or restore/drill completed with post-checks OK for covered protected classes;
- `fail` — operation detected a restore contract violation after starting (for example postcheck hash mismatch or excluded content write attempt);
- `blocked` — prerequisite or policy gate prevented restore (integrity not pass, missing package, live confirmation required, unsafe target).

Operators MUST be able to distinguish blocked prerequisites from restore failures via stable reason codes.

#### Scenario: Missing package is blocked

- **WHEN** restore is requested for a non-existent `backup_id` under `metadata/backups/`
- **THEN** the result `status` is `blocked` with a stable missing-package reason code

#### Scenario: Postcheck mismatch fails

- **WHEN** a restore drill writes files that do not match the package manifest digests on postcheck
- **THEN** the result `status` is `fail` with a stable postcheck reason code

### Requirement: US-037 does not claim BL-014 closed or reopen US-036

US-037 deliverables MUST NOT mark BL-014 complete, MUST NOT mark US-037 Story accepted from documentation alone, MUST NOT reopen or alter US-036 scope/retention/integrity contracts except additive restore references, and MUST NOT reopen BL-013 concurrency contracts.

Product progress updates after implementation MUST leave US-037 Story accepted and BL-014 closed unchecked until later operator acceptance of demonstrated criteria.

#### Scenario: Story and backlog boundary preserved

- **WHEN** US-037 restore drills and recovery procedure artifacts are delivered
- **THEN** US-036 integrity contracts remain authoritative for verify, and product checkboxes for US-037 acceptance and BL-014 closed stay open until operator acceptance

#### Scenario: No primary HTTP restore surface required

- **WHEN** US-037 restore capability is delivered in its default form
- **THEN** restoration is available via library and CLI without a new primary FastAPI restore route
