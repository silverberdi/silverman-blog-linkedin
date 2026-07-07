# flow-a-automatic-publishing

## Purpose

End-to-end automatic publishing for user-provided blog posts (Flow A): automated editorial validation, idempotent blog publication to GitHub Pages, publish-confirmed public URL, LinkedIn derivative package generation, distribution scheduling per digital strategy (variants staggered, not simultaneous), lifecycle metadata, duplicate prevention, and visible error handling—without human approval after validation passes. **Flow A Core** (this umbrella's closure scope) stops at generated LinkedIn artifacts, scheduled distribution metadata with `publish_state: pending`, and campaign state `distribution_scheduled`. Flow A *policy* allows automatic LinkedIn publication after validation and scheduling; runtime LinkedIn API integration is deferred to a **separate follow-up change** `linkedin-publication-integration` (slice 8). Flow B (system-generated content requiring review) is reserved and MUST NOT use Flow A automatic paths.

## ADDED Requirements

### Requirement: Flow A content policy

The system SHALL treat Flow A as the automatic publishing path for user-provided blog posts placed in `blog-posts/ready/` by the author.

Flow A content SHALL be considered pre-approved for blog publication and LinkedIn derivative generation only after automated editorial validation passes.

Flow A MUST NOT require human review or approval after validation passes.

Flow B (system-generated ideas, blog drafts, or LinkedIn drafts) SHALL require human review and approval before publication and MUST NOT enter Flow A automatic publish paths.

Every campaign and derivative record MUST include a `flow` field with value `flow_a` or `flow_b`.

#### Scenario: Flow A proceeds without human approval after validation

- **WHEN** a user-provided blog post in `blog-posts/ready/` passes automated Flow A validation
- **THEN** the system MAY proceed to automatic blog publish and LinkedIn derivative generation without a human approval step

#### Scenario: Flow B blocked from Flow A automatic path

- **WHEN** content is marked or detected as Flow B (system-generated, not user-provided ready input)
- **THEN** the system MUST NOT automatically publish the blog or schedule LinkedIn posts on the Flow A path

#### Scenario: Validation failure blocks automatic path

- **WHEN** automated Flow A validation fails for a ready blog post
- **THEN** the system MUST NOT publish the blog or generate Flow A LinkedIn derivatives

### Requirement: Canonical editorial artifact

The repository SHALL define a canonical editorial artifact at `content-strategy/silverman-editorial-system.md`.

The artifact MUST be readable by worker validation logic and LLM prompt assembly.

The artifact MUST define operational rules (not decorative prose only) for:

- brand positioning
- target audiences
- content pillars and topics
- goals
- writing style
- anti-AI-writing rules
- blog rules
- LinkedIn derivative rules
- CTA rules
- no-redundancy rules
- LinkedIn cadence and distribution strategy
- automatic vs approval-required policy (Flow A vs Flow B)

Worker validation and generation logic MUST reference applicable sections from this artifact when enforcing Flow A rules.

#### Scenario: Editorial artifact path is canonical

- **WHEN** Flow A validation or generation runs
- **THEN** the system loads rules from `content-strategy/silverman-editorial-system.md` or reports a structured error if the file is missing or unreadable

#### Scenario: Artifact includes Flow A vs Flow B policy

- **WHEN** an operator reviews `content-strategy/silverman-editorial-system.md`
- **THEN** the document explicitly states that Flow A is automatic after validation and Flow B requires human approval

### Requirement: Flow A lifecycle states

The system SHALL track each Flow A blog post through a documented lifecycle with at minimum these states:

`ready`, `validation_failed`, `validated`, `blog_publish_pending`, `blog_published`, `derivatives_pending`, `derivatives_generated`, `distribution_scheduled`, `distribution_complete`, `flow_a_complete`, `error`.

Lifecycle state MUST be persisted in campaign metadata under `metadata/campaigns/`.

State transitions MUST be recorded with timestamps and machine-readable reasons on failure.

#### Scenario: Successful Flow A lifecycle progression

- **WHEN** a valid ready post completes validation, blog publish, derivative package generation, and distribution scheduling
- **THEN** campaign metadata reflects progression through `validated` → `blog_published` → `derivatives_generated` → `distribution_scheduled` → `flow_a_complete`

#### Scenario: Validation failure state

- **WHEN** automated validation fails
- **THEN** campaign metadata records state `validation_failed` with non-empty error reasons and the source is moved to `blog-posts/error/` or marked as error according to the lifecycle child spec

#### Scenario: Error state on unrecoverable failure

- **WHEN** blog publish or derivative generation fails with no successful retry path in the same run
- **THEN** campaign metadata records state `error` with visible error context suitable for n8n branching

### Requirement: Source slug and public slug validation

Flow A validation SHALL distinguish `source_slug` (ready-file basename without `.md`, MAY include ordering prefix such as `01-`) from `public_slug` (published slug after stripping leading numeric prefix matching `^\d+-`).

Validation MUST verify:

- `source_slug` is safe as an input filename (lowercase alphanumeric segments separated by hyphens; no path separators or `..`)
- derived `public_slug` matches `^[a-z0-9]+(?:-[a-z0-9]+)*$`

Prefix stripping rules MUST align with `openspec/specs/github-pages-blog-publishing/spec.md`.

Canonical example:

- Source file: `blog-posts/ready/01-why-i-did-not-start-with-the-database.md`
- `source_slug`: `01-why-i-did-not-start-with-the-database`
- `public_slug`: `why-i-did-not-start-with-the-database`
- Public URL: `https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/`

#### Scenario: Numeric prefix stripped for public slug

- **WHEN** validation runs for `blog-posts/ready/01-why-i-did-not-start-with-the-database.md`
- **THEN** `source_slug` is `01-why-i-did-not-start-with-the-database`, derived `public_slug` is `why-i-did-not-start-with-the-database`, and both pass safety checks

#### Scenario: Invalid derived public slug fails validation

- **WHEN** stripping the ordering prefix yields a slug that does not match `^[a-z0-9]+(?:-[a-z0-9]+)*$`
- **THEN** validation returns `status` `failed` with a clear error referencing `public_slug`

### Requirement: Automated ready-post editorial validation

Before Flow A blog publication, the system SHALL validate each candidate blog post pair (`<source-slug>.md` and `<source-slug>.png`) in `blog-posts/ready/` against editorial rules from the canonical artifact and structural requirements.

Validation MUST check at minimum:

- `source_slug` and derived `public_slug` per the slug validation requirement
- readable Markdown and PNG pair exists
- required YAML frontmatter fields per blog rules (including parseable `date`)
- absence of forbidden content types defined in the editorial artifact where reliably automatable

For Flow A user-provided blog input, validation MUST block only reliably automatable structural and editorial contract violations. Anti-AI-writing rules MUST NOT be treated as perfectly detectable on user-authored blog content; such rules MAY produce warnings unless a child spec explicitly marks a rule as blocking.

Anti-AI-writing rules MUST be applied strongly to generated LinkedIn derivative content and future Flow B generated content.

Validation MUST return structured JSON with `status` (`completed` or `failed`), `errors[]`, optional `warnings[]`, and `campaign_id` when created.

#### Scenario: Valid ready post passes validation

- **WHEN** a ready post pair meets slug, file, frontmatter, and editorial rules
- **THEN** validation returns `status` `completed` and the post is eligible for Flow A blog publish

#### Scenario: Missing PNG fails validation

- **WHEN** `blog-posts/ready/<source-slug>.md` exists but the matching `.png` does not
- **THEN** validation returns `status` `failed` with a clear error and does not publish

#### Scenario: Forbidden content type fails validation

- **WHEN** post content or metadata matches a forbidden content type defined in the editorial artifact (for example pure news commentary)
- **THEN** validation returns `status` `failed` with reason referencing the violated rule

### Requirement: Automatic idempotent blog publication

After Flow A validation passes, the system SHALL publish the blog post to the public GitHub Pages repository checkout using the existing publishing bridge semantics (Jekyll `_posts/`, `assets/images/`, frontmatter normalization, non-overwrite).

Publication MUST be idempotent: if the target `_posts/YYYY-MM-DD-<public-slug>.md` and `assets/images/<public-slug>.png` already exist for the same publication intent, the system MUST NOT overwrite and MUST return a structured `already_published` (or equivalent) outcome.

Publication MUST be invocable over HTTP from n8n via the worker (not n8n Execute Command or direct filesystem access).

Source files in `blog-posts/ready/` MUST remain unchanged by the publish step (consistent with existing CLI bridge).

#### Scenario: First-time publish writes assets

- **WHEN** validation passed and public blog targets do not exist
- **THEN** the worker writes `_posts/YYYY-MM-DD-<public-slug>.md` and `assets/images/<public-slug>.png` and returns `status` `completed`

#### Scenario: Repeat publish is idempotent

- **WHEN** the same post is published again with unchanged slug and publication date and targets already exist
- **THEN** the worker returns `already_published` without overwriting files

#### Scenario: n8n invokes publish via HTTP only

- **WHEN** n8n orchestrates Flow A blog publish
- **THEN** the call is made through an HTTP Request node to the worker and not through Execute Command or filesystem nodes

### Requirement: Publish-confirmed public URL

After successful blog publication, the system SHALL record a publish-confirmed `source_public_url` in campaign metadata.

The confirmed URL MUST follow `https://silverman.pro/YYYY/MM/DD/<public-slug>/` (or configured `site_base_url`) using the actual publication date and public slug from the publish result.

A merely derived URL from frontmatter and filename BEFORE publish MUST NOT be stored or passed to LinkedIn generation as publish-confirmed.

LinkedIn derivative generation for Flow A MUST use publish-confirmed `source_public_url` for CTA behavior when the blog is live.

#### Scenario: Confirmed URL after publish

- **WHEN** blog publish completes successfully for source slug `01-why-i-did-not-start-with-the-database` with publication date `2026-07-06` and public slug `why-i-did-not-start-with-the-database`
- **THEN** metadata records `source_public_url` `https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/`

#### Scenario: Derivative generation blocked without confirmed URL

- **WHEN** blog publish has not completed and no publish-confirmed URL exists
- **THEN** Flow A LinkedIn package generation MUST NOT include a live-blog CTA claiming a publish-confirmed URL

### Requirement: LinkedIn derivative package

For each Flow A blog post with publish-confirmed URL, the system SHALL generate a LinkedIn derivative package: one or more LinkedIn posts linked to the source blog via `campaign_id`.

Each package MUST record:

- `campaign_id`
- `source_slug`
- `source_content_sha256`
- `source_public_url` (publish-confirmed)
- `flow` = `flow_a`
- `variants[]` with per-variant `variant`, `audience`, `objective`, `cta_mode`, and `draft_relative_path`

Variants MUST be faithful to the canonical blog post (ADR-0002).

The system MUST generate at least three variants over the package lifetime unless the editorial artifact specifies a narrower set: executive/recruiter, technical leadership, and short provocative.

Package generation MUST be idempotent per `source_content_sha256` + `variant` + `flow_a`.

#### Scenario: Package links multiple variants to one blog

- **WHEN** package generation completes for a Flow A campaign
- **THEN** metadata lists multiple `variants` entries sharing the same `campaign_id` and `source_public_url`

#### Scenario: Variant fidelity to blog

- **WHEN** a LinkedIn variant is generated
- **THEN** claims and examples in the draft trace to the source blog content and do not introduce unsupported facts

#### Scenario: Idempotent variant regeneration

- **WHEN** package generation is re-run for the same `source_content_sha256` and `variant` without content change
- **THEN** the system returns the existing draft path or skips re-generation without creating duplicate draft files

### Requirement: LinkedIn distribution strategy and scheduling

The system SHALL apply a digital distribution strategy to each derivative package so that variants are NOT all published at the same time and are NOT implied to publish immediately upon generation.

Flow A policy allows automatic LinkedIn publication after validation and scheduling. The roadmap first implements package generation and scheduling metadata; actual LinkedIn API publication remains deferred to `linkedin-publication-integration` until credentials, API surface, and rate-limit constraints are known. Until then, `publish_state` MUST be `pending` for scheduled variants.

Strategy dimensions MUST include at minimum:

- cadence (minimum spacing between scheduled variants)
- audience (per variant)
- objective (per scheduled post)
- variant selection and ordering
- CTA behavior (aligned with publish-confirmed URL rules)
- non-redundancy (no duplicate hooks or overlapping thesis across scheduled variants)
- scheduling window (preferred timing from editorial artifact)

Scheduling metadata MUST be persisted per variant with `schedule_at` (or equivalent) and `publish_state` (`pending`, `published`, `skipped`, `failed`).

The system MUST act as an expert digital strategist by encoding strategy rules in the editorial artifact and applying them programmatically in the scheduling model child change.

#### Scenario: Variants scheduled on different dates

- **WHEN** a package has three variants and cadence requires minimum 3-day spacing
- **THEN** scheduled `schedule_at` values are at least 3 days apart unless the editorial artifact explicitly allows same-day exceptions

#### Scenario: Non-redundant variant angles

- **WHEN** multiple variants are scheduled for one blog post
- **THEN** each variant uses a distinct primary hook and objective per no-redundancy rules

#### Scenario: CTA uses confirmed URL only

- **WHEN** a variant is scheduled and `cta_mode` requires blog link
- **THEN** the CTA uses the publish-confirmed `source_public_url` from campaign metadata

#### Scenario: Scheduling without immediate API publish

- **WHEN** package generation and scheduling complete before `linkedin-publication-integration` is implemented
- **THEN** each variant has `schedule_at` per strategy and `publish_state` `pending`; no variant is published to LinkedIn API immediately solely because it was generated

### Requirement: Anti-AI-writing rule application by content source

The editorial artifact MUST define anti-AI-writing rules.

For Flow A user-provided blog input, automated validation MUST block only reliably automatable structural and editorial contract violations. Anti-AI-writing checks on user blog content MAY produce `warnings[]` unless a child spec explicitly marks a rule as blocking.

Anti-AI-writing rules MUST be applied strongly when generating LinkedIn derivative content and when generating Flow B content in the future.

The system MUST NOT claim or imply perfect detection of AI-authored writing in user-provided blog posts.

#### Scenario: User blog validation may warn on anti-AI heuristics

- **WHEN** Flow A validation detects a heuristic anti-AI-writing signal on user-provided blog content and no child spec marks that rule as blocking
- **THEN** validation MAY return `warnings[]` while still returning `status` `completed` if no blocking violations exist

#### Scenario: LinkedIn generation enforces anti-AI rules

- **WHEN** the system generates a Flow A LinkedIn derivative variant
- **THEN** generation prompts and post-checks apply anti-AI-writing rules from the editorial artifact strongly

### Requirement: Flow A metadata traceability without content bloat

Campaign and run metadata MUST support end-to-end traceability for Flow A without storing full `markdown_content` or full generated draft bodies in metadata files.

Metadata MUST record at minimum:

- `campaign_id`, `flow`, lifecycle `state`
- `source_slug`, `public_slug`, `source_relative_path`, `source_content_sha256`
- `publication_date`, `source_public_url` (when confirmed)
- per-variant: `variant`, `draft_relative_path`, `schedule_at`, `publish_state`
- timestamps and structured `errors[]` on failure

Metadata MUST NOT include `markdown_content` or `generated_draft_content` fields.

#### Scenario: Metadata traces blog to variants without body content

- **WHEN** an operator inspects `metadata/campaigns/<campaign-id>.json` after a successful run
- **THEN** they can identify source post, confirmed URL, and all variant draft paths without full post or draft text in the file

#### Scenario: Run metadata links to campaign

- **WHEN** a Flow A orchestration run completes
- **THEN** `metadata/runs/` contains a record referencing `campaign_id` and high-level outcome status

### Requirement: Duplicate prevention across Flow A pipeline

The system MUST prevent duplicate blog publication, duplicate LinkedIn drafts for the same blog/variant, and duplicate LinkedIn publication for the same campaign/variant/schedule slot.

Re-triggering the Flow A orchestration MUST be safe and MUST return structured skip or already-complete responses rather than creating duplicates.

#### Scenario: Re-run after flow_a_complete

- **WHEN** n8n re-triggers Flow A for a campaign already in `flow_a_complete`
- **THEN** worker responses indicate no duplicate publish or duplicate scheduled posts were created

#### Scenario: Duplicate variant draft prevented

- **WHEN** generation is requested for an existing `source_content_sha256` + `variant` + `flow_a` with unchanged content
- **THEN** no second draft file is written for that variant key

### Requirement: Flow A error visibility

Failures at validation, blog publish, URL confirmation, derivative generation, scheduling, or publication MUST produce visible, structured errors in worker JSON responses and campaign metadata.

n8n MUST be able to branch on `status` `failed` at each step without parsing log files.

Errors MUST NOT expose secrets (API keys, tokens).

#### Scenario: Publish failure visible to n8n

- **WHEN** blog publish fails (for example target exists conflict or missing checkout)
- **THEN** the worker returns `status` `failed` with non-empty `errors[]` and n8n can surface the failure in execution output

#### Scenario: No secrets in error responses

- **WHEN** any Flow A step returns an error
- **THEN** the response does not contain worker API keys, LinkedIn tokens, or other secrets

### Requirement: HTTP-only n8n orchestration for Flow A

Flow A orchestration MUST use n8n HTTP Request nodes (and standard control nodes) exclusively to call worker endpoints.

n8n MUST NOT use Execute Command, SSH, Read/Write Binary File, direct filesystem access, direct LLM provider calls, or direct LinkedIn/GitHub publish nodes for Flow A.

The worker MUST remain the sole filesystem and LLM boundary.

Exported n8n workflow JSON for Flow A MUST keep `"active": false` unless a later change explicitly documents activation for scheduled production runs.

#### Scenario: Flow A worker boundary preserved

- **WHEN** the Flow A n8n workflow export is inspected
- **THEN** all filesystem and LLM operations are delegated to worker HTTP endpoints

#### Scenario: Exported Flow A workflow inactive by default

- **WHEN** the Flow A workflow JSON is stored in the repository
- **THEN** top-level `"active"` is `false`

### Requirement: Flow A success criteria

Flow A SHALL be considered complete for a blog post when all of the following have occurred:

1. User placed a valid blog post pair in `blog-posts/ready/`
2. Automated validation passed
3. Blog published idempotently to GitHub Pages checkout
4. Publish-confirmed public URL recorded
5. LinkedIn derivative package generated with one or more variants
6. Variants scheduled per distribution strategy (not simultaneous by default; `publish_state` `pending` until API integration)
7. Metadata recorded without full content bodies
8. Source is moved or marked processed according to the lifecycle child spec when lifecycle closes
9. Re-run does not create duplicate publications
10. Errors at any step are visible in metadata and orchestration output

Flow A policy allows automatic LinkedIn API publication after validation and scheduling. Until `linkedin-publication-integration` is implemented, success includes scheduling metadata and draft artifacts with `publish_state` `pending`.

#### Scenario: End-to-end Flow A happy path

- **WHEN** a valid user-provided post is processed through the full Flow A pipeline
- **THEN** the blog is live at the confirmed URL, derivative package exists, variants are scheduled per strategy, metadata is complete, and no duplicate artifacts were created

#### Scenario: Partial LinkedIn API deferral

- **WHEN** `linkedin-publication-integration` is not yet implemented
- **THEN** Flow A success still includes validated publish, confirmed URL, generated package, and scheduling metadata with `publish_state` `pending` for API publish

### Requirement: Flow A umbrella child changes

Implementation of Flow A MUST be decomposed into separate OpenSpec child changes referencing this umbrella, in preferred dependency order:

1. `editorial-canon-and-linkedin-distribution-strategy`
2. `flow-a-lifecycle-and-duplicate-prevention`
3. `ready-post-editorial-validation`
4. `worker-blog-publishing-endpoint`
5. `linkedin-derivative-package-generation`
6. `linkedin-distribution-scheduling-model`
7. `n8n-flow-a-blog-publish-orchestration`
8. `linkedin-publication-integration` (deferred)

Lifecycle and idempotency (2) is a foundational dependency for later slices. Validation (3) may be developed closely with lifecycle (2).

This umbrella change MUST remain an **active** organizing roadmap while child changes are proposed, applied, and archived. It MUST NOT be archived immediately after stakeholder approval of planning artifacts. Archive after Flow A Core child changes and operational verification are completed/validated (slices 1–7 + OV archived). Slice 8 (`linkedin-publication-integration`) is **not** required for umbrella archive — defer to a follow-up change.

This umbrella change MUST NOT itself implement worker code, n8n workflow JSON, or the editorial artifact file content.

#### Scenario: Child change cites umbrella

- **WHEN** a child change proposal is created for Flow A slice work
- **THEN** it references `flow-a-automatic-blog-linkedin-publishing-roadmap` for policy and lifecycle context

#### Scenario: Umbrella remains active during child implementation

- **WHEN** Flow A child changes are being proposed, applied, or archived
- **THEN** `flow-a-automatic-blog-linkedin-publishing-roadmap` remains an active OpenSpec change and is not archived solely because planning artifacts received stakeholder approval

#### Scenario: Umbrella archived after Flow A Core completion

- **WHEN** all Flow A Core child changes (slices 1–7 + operational verification) are completed, archived, and server-validated
- **THEN** the umbrella MAY be archived via `/opsx-archive flow-a-automatic-blog-linkedin-publishing-roadmap` without implementing slice 8

#### Scenario: Umbrella does not modify runtime

- **WHEN** only this umbrella change is applied
- **THEN** no worker endpoints, n8n workflow JSON, or `content-strategy/silverman-editorial-system.md` file are added or modified

### Requirement: Flow A Core complete boundary

Flow A Core SHALL be considered complete when child OpenSpec changes 1–7 and operational verification (`flow-a-deployment-readiness-and-smoke-test`) are implemented, archived, and server-validated.

Flow A Core deliverables MUST include:

- editorial canon artifact and spec
- lifecycle metadata and duplicate prevention
- ready-post validation
- GitHub Pages blog publishing via worker HTTP endpoint
- LinkedIn derivative package generation
- LinkedIn distribution scheduling with `publish_state: pending`
- n8n Flow A orchestration workflow (`"active": false`)
- deployment readiness and smoke verification scripts

Flow A Core MUST NOT include LinkedIn API publication, n8n workflow activation, cron triggers, or webhook triggers.

The terminal campaign state for Flow A Core success is `distribution_scheduled` with `linkedin_distribution` metadata present and all scheduled variants having `publish_state: pending`.

#### Scenario: Flow A Core stops before LinkedIn API

- **WHEN** a blog post completes the full Flow A Core pipeline successfully
- **THEN** LinkedIn derivative drafts exist under `linkedin-posts/generated/`, scheduling metadata is persisted, each variant has `publish_state: pending`, and no LinkedIn API publish call occurs

#### Scenario: Worker smoke confirms Flow A Core

- **WHEN** `run-flow-a-worker-smoke.sh` reports `OVERALL: PASS` on the Ubuntu server
- **THEN** publish, package, and schedule steps returned `status: completed` and final campaign state is `distribution_scheduled`

#### Scenario: Evidence collector confirms distribution evidence

- **WHEN** `collect-flow-a-smoke-evidence.sh` reports `OVERALL: PASS`
- **THEN** campaign metadata shows blog publish, linkedin package, and linkedin distribution present

### Requirement: LinkedIn publication deferred to follow-up change

`linkedin-publication-integration` (slice 8) MUST NOT be implemented as part of umbrella closure.

When LinkedIn API integration constraints (credentials, API surface, rate limits) are documented, operators SHALL propose a **new separate OpenSpec change** for slice 8 after this umbrella is archived.

Until slice 8 is implemented, Flow A success criteria are satisfied by scheduling metadata and generated draft artifacts with `publish_state: pending`.

#### Scenario: Slice 8 is out of umbrella scope

- **WHEN** an operator reviews umbrella closure tasks
- **THEN** slice 8 tasks remain unchecked and explicitly marked deferred to a follow-up change

#### Scenario: Umbrella ready to archive without slice 8

- **WHEN** all Flow A Core child changes and operational verification are archived and server-validated
- **THEN** the umbrella MAY be archived without implementing `linkedin-publication-integration`

### Requirement: Umbrella closure guardrails

Umbrella closure MUST NOT activate the n8n Flow A workflow, add cron or webhook triggers, or implement LinkedIn API endpoints.

The n8n workflow export MUST remain `"active": false` after umbrella closure.

#### Scenario: No n8n activation on closure

- **WHEN** the umbrella is closed as Flow A Core Complete
- **THEN** `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` retains `"active": false`

