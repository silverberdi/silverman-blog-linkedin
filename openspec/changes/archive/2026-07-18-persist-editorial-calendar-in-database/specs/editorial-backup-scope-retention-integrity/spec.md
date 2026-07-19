## MODIFIED Requirements

### Requirement: Editorial backup scope inventory

Editorial backup scope MUST include the following relative path classes under `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` when present:

- `blog-posts/ready/`, `blog-posts/queued/`, `blog-posts/processed/`, `blog-posts/error/`
- `linkedin-posts/review/`, `linkedin-posts/approved/`, `linkedin-posts/published/`
- `metadata/campaigns/`
- `metadata/runs/`
- `prompts/`
- binary or image assets co-located inside those included trees

Editorial filesystem backup scope MUST NOT treat `editorial-calendar/calendar.json` as the durable recovery source of truth for master calendar schedule state. The directory `editorial-calendar/` MAY be omitted from required filesystem backup inventory, or included only as optional non-authoritative legacy/export residue, without implying calendar SoT recovery from that path.

Master editorial calendar durability and restore MUST be owned by PostgreSQL backup procedures for database **`silverman_linkedin_db`** (capability `editorial-calendar-database`), not by packing `calendar.json` alone under `metadata/backups/`.

Editorial backup scope MUST exclude:

- contents of `metadata/backups/` when assembling a new package (no recursive backup-of-backups by default)
- secrets and credential material (including `.env`, API keys, LinkedIn tokens, credential files, and calendar database passwords)
- the public GitHub Pages checkout path (handoff / live site target is not a substitute for editorial source trees)
- worker source trees, Docker images, and shared-stack services (n8n, postgres data volumes, and related backup-runner scope) from the **filesystem editorial package** (postgres calendar backups remain a separate stack concern)
- transient junk files (for example `.DS_Store`, `__pycache__/`, `*.tmp`)

Ambiguous requests to treat an excluded class as in-scope MUST fail closed pending a new approved OpenSpec change.

#### Scenario: Scope includes campaign metadata and excludes calendar file as SoT

- **WHEN** an operator consults the normative backup scope
- **THEN** `metadata/campaigns/` and `metadata/runs/` are listed as included filesystem scope, and `calendar.json` is not described as the durable calendar recovery SoT

#### Scenario: Scope excludes secrets and public checkout

- **WHEN** an operator consults the normative backup exclusions
- **THEN** secrets/credential material and the public GitHub Pages checkout are listed as excluded

#### Scenario: Ambiguous scope fails closed

- **WHEN** an operator requests treating an excluded class as required backup scope without a new approved change
- **THEN** the policy and verifier treat the request as blocked or out of contract rather than silently expanding scope

#### Scenario: Calendar DB backup is documented as separate from filesystem packages

- **WHEN** an operator reads the backup policy after calendar database cutover
- **THEN** the policy states that master calendar restore depends on database/stack backup, not solely on `metadata/backups/` filesystem packages

## ADDED Requirements

### Requirement: Policy distinguishes filesystem editorial packages from calendar database backup

The operator-facing backup policy MUST state that:

- BL-014 filesystem packages protect editorial Markdown/metadata trees under the editorial base;
- master calendar schedule state is restored via the calendar database backup path;
- recovering only `metadata/backups/` packages MUST NOT be claimed sufficient to restore calendar SoT after database cutover.

#### Scenario: Operator sees dual durability paths

- **WHEN** an operator opens the editorial backup policy document
- **THEN** filesystem package scope and calendar database backup ownership are both described without equating them
