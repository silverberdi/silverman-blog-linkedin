# flow-b-blog-draft-generation

## ADDED Requirements

### Requirement: Authenticated Flow B blog draft generation endpoint

The worker SHALL expose an authenticated HTTP endpoint for Flow B blog draft generation (for example `POST /flow-b/generate-blog-drafts`). Unauthenticated requests MUST be rejected. The endpoint MUST accept one or more US-078 topic objects (`thesis`, `referent_positioning`, `rationale`, `topic_id`; optional `pillar_hints`) and MUST generate complete blog Markdown plus a hero image pair under `blog-posts/pending-approval/` using the same Markdown + image sibling pair rules as `blog-posts/ready/`. The endpoint MUST NOT write files under `blog-posts/ready/`. Orchestration remains **n8n → worker HTTP only** (ADR-0001); this capability MUST NOT introduce n8n Execute Command usage.

#### Scenario: Unauthenticated draft generation is rejected

- **WHEN** a client calls the draft generation endpoint without valid worker authentication
- **THEN** the request is rejected and no draft files are written

#### Scenario: Successful generation writes pending-approval pair

- **WHEN** an authenticated client posts valid topic object(s) and generation succeeds
- **THEN** the response status indicates drafts were generated
- **AND** each successful draft has a Markdown file and matching hero image sibling under `blog-posts/pending-approval/`
- **AND** no files are created under `blog-posts/ready/`

### Requirement: DeepSeek v1 with provider-pluggable seam

v1 blog draft text generation MUST use DeepSeek only. The implementation SHALL provide a provider-pluggable client seam so additional models can be enabled later without rewriting Flow B orchestration. Selecting an unsupported provider MUST fail closed. DeepSeek configuration MUST load from environment (existing DeepSeek settings patterns); API keys MUST NEVER appear in HTTP responses, logs, or error bodies.

#### Scenario: v1 uses DeepSeek for blog draft text

- **WHEN** an authenticated draft generation request succeeds
- **THEN** the effective text-generation provider is DeepSeek
- **AND** the response identifies the provider without exposing secrets

#### Scenario: Missing DeepSeek configuration fails closed

- **WHEN** DeepSeek settings are missing or invalid and draft generation is invoked
- **THEN** the worker returns a clear operator-visible configuration/draft error
- **AND** no draft pair is written to `blog-posts/ready/`

### Requirement: Hero image via ComfyUI blog image path

Draft generation SHALL request a hero image for each blog draft using the existing ComfyUI blog image generation path (for example `blog_image_generation` with `comfyui_client`). The implementation MUST respect ComfyUI enablement flags and MUST honor `dry_run` when specified so dry-run requests do not mutate production image files under `blog-posts/pending-approval/`.

#### Scenario: ComfyUI generates hero image for pending draft

- **WHEN** ComfyUI is enabled, `dry_run` is false, and text generation succeeds
- **THEN** a hero image sibling is created or requested for the pending-approval Markdown path
- **AND** the Markdown front matter references the sibling image per blog pair rules

#### Scenario: Dry-run skips durable image write

- **WHEN** an authenticated client invokes draft generation with `dry_run=true`
- **THEN** no durable `.md` or `.png` pair is written under `blog-posts/pending-approval/`
- **AND** the response indicates dry-run status

#### Scenario: ComfyUI disabled fails closed when image required

- **WHEN** ComfyUI is disabled by enablement flags and a non-dry-run draft is requested
- **THEN** the worker returns a clear operator-visible error for the affected draft
- **AND** the draft is not treated as a complete successful package without a hero image path

### Requirement: Editorial canon and anti-AI-writing rules at draft time

Draft generation SHALL assemble prompts from the editorial canon (including blog post rules, topic boundaries, and Flow B authority posture) and MUST apply anti-AI-writing rules at draft time for Flow B generated content. Per editorial canon, anti-AI checks for Flow B generated blogs MUST use **blocking** behavior (not warnings-only). Blocked drafts MUST NOT be reported as successful approval-ready packages.

#### Scenario: Editorial canon informs generation prompt

- **WHEN** draft generation assembles the provider prompt
- **THEN** the inputs include authority/referent positioning and editorial canon blog rules
- **AND** the prompt instructs against news-spreader and generic AI-sounding patterns

#### Scenario: Anti-AI violations block draft success

- **WHEN** generated Markdown fails anti-AI-writing heuristics defined for Flow B
- **THEN** the worker returns a structured operator-visible blocked state with violation detail
- **AND** the draft is not reported as a successful approval-ready package

### Requirement: Durable metadata linking topic and gap context

Each generated draft package MUST include durable metadata linking the source `topic_id` and, when provided, optional gap-batch context (`target_week`, `empty_days[]`). Metadata MUST be persisted alongside the draft package in a operator-inspectable form (for example a sibling JSON file under `blog-posts/pending-approval/`).

#### Scenario: Topic id is persisted with draft

- **WHEN** a draft is successfully generated from a topic with `topic_id`
- **THEN** durable metadata records that `topic_id` and discovery fields (`thesis`, `referent_positioning`, `rationale`)
- **AND** the HTTP response references the written paths

#### Scenario: Gap context is recorded when provided

- **WHEN** draft generation is invoked with `target_week` and/or `empty_days[]`
- **THEN** durable metadata records those fields for operator review
- **AND** generation does not require scanning `blog-posts/ready/` or `blog-posts/pending-approval/` inventory to succeed

### Requirement: Batch size capped by max_drafts_per_weekly_run

Draft generation MUST accept multiple topics in one request and MUST generate at most N draft packages where N is ≤ effective `max_drafts_per_weekly_run` from `load_gap_operator_settings()` (documented default **2** when settings row missing). Requested topic counts above the ceiling MUST be clamped or rejected with a clear validation error (implementation MUST document which; prefer clamp with echoed effective max).

#### Scenario: Batch respects settings ceiling

- **WHEN** effective `max_drafts_per_weekly_run` is `2` and a client posts more than 2 topics
- **THEN** the worker generates at most 2 draft packages on success

#### Scenario: Default ceiling applies when settings row missing

- **WHEN** no settings row exists and a client posts multiple topics without an explicit smaller limit
- **THEN** the effective ceiling is the documented default `2`

### Requirement: No publication or Flow A side effects

This capability MUST NOT auto-publish blog posts, invoke Flow A publish/package/schedule endpoints, create Flow A campaign lifecycle side effects, hand off to GitHub Pages git publication, or call LinkedIn API publish. Generated drafts MUST remain in `blog-posts/pending-approval/` until a separate approve/promote capability (US-080/US-081) runs. This capability MUST NOT enable LinkedIn API publication or modify `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

#### Scenario: No ready folder writes

- **WHEN** draft generation completes successfully
- **THEN** `blog-posts/ready/` gains no new files from this capability

#### Scenario: No Flow A publish invocation

- **WHEN** draft generation runs
- **THEN** Flow A publish, package, and schedule operations are not invoked

#### Scenario: No LinkedIn API publish

- **WHEN** draft generation runs successfully or unsuccessfully
- **THEN** LinkedIn API publication enablement remains governed solely by existing env guards

### Requirement: Fail closed with operator-visible errors

When draft generation cannot produce at least one valid approval-ready package for a requested topic, the worker MUST fail closed with clear operator-visible structured errors. Provider failures, anti-AI blocks, filesystem errors, and missing configuration MUST NOT be reported as successful draft generation.

#### Scenario: Provider failure fails closed

- **WHEN** the blog draft provider returns no usable Markdown content
- **THEN** the worker returns a structured operator-visible error
- **AND** the response is not a successful `drafts_generated` status for that topic

### Requirement: US-079 scope excludes approve, promote, trigger, and discovery contract changes

This capability MUST NOT implement blog approve/reject UI (US-080), promote-to-`ready/` (US-081), or gap trigger orchestration (US-082). It MUST NOT change the HTTP contracts of `flow-b-topic-discovery` (`POST /flow-b/discover-topics`), `flow-b-calendar-gap-detect` (`GET /flow-b/calendar-gaps`), or `flow-b-gap-operator-settings` (`GET`/`PUT /flow-b/gap-operator-settings`) except by consuming shared settings via `load_gap_operator_settings()`.

#### Scenario: Discover-topics contract unchanged

- **WHEN** this capability is implemented
- **THEN** `POST /flow-b/discover-topics` remains discovery-only with no draft filesystem writes

#### Scenario: No approve or trigger routes required

- **WHEN** this capability's requirements are evaluated
- **THEN** approve/promote and gap trigger endpoints are not required for US-079 completion
