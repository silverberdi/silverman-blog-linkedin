## ADDED Requirements

### Requirement: Authenticated Flow B topic discovery endpoint

The worker SHALL expose an authenticated HTTP endpoint for Flow B AI topic discovery (for example `POST /flow-b/discover-topics`). Unauthenticated requests MUST be rejected. Successful responses MUST return structured JSON topic choices suitable for later attachment to draft packages (US-079). The endpoint MUST NOT write files under `blog-posts/ready/` or `blog-posts/pending-approval/`. Orchestration remains **n8n → worker HTTP only** (ADR-0001); this capability MUST NOT introduce n8n Execute Command usage.

#### Scenario: Unauthenticated discovery is rejected

- **WHEN** a client calls the discovery endpoint without valid worker authentication
- **THEN** the request is rejected and no topic choices are returned

#### Scenario: Successful discovery returns attachable topic payloads

- **WHEN** an authenticated client requests discovery and the provider returns valid objective-aligned topics
- **THEN** the response status indicates topics were discovered
- **AND** each topic includes a thesis, referent positioning explanation, and brief rationale
- **AND** no files are created under `blog-posts/ready/` or `blog-posts/pending-approval/`

### Requirement: Authority-constrained discovery posture

Discovery SHALL constrain the AI brief to the career/authority objective (senior leadership / architecture / transformation / AI; referent positioning). Discovery MUST NOT optimize for “X vs Y”, “what’s new”, or headline rebroadcast as the discovery objective. RSS/news APIs MUST NOT be the primary discovery driver in v1.

#### Scenario: Authority objective is encoded in discovery inputs

- **WHEN** discovery assembles the provider prompt
- **THEN** the inputs include authority/referent positioning and editorial canon topic spaces
- **AND** the prompt instructs against news-spreader objectives (“X vs Y”, “what’s new”, headline rebroadcast)

#### Scenario: News-chase-only output fails closed

- **WHEN** the provider returns only candidates that fail objective-alignment checks
- **THEN** the worker returns a clear operator-visible discovery failure
- **AND** it does not invent filler topics to satisfy the requested count

### Requirement: DeepSeek v1 with provider-pluggable seam

v1 discovery calls MUST use DeepSeek only. The implementation SHALL provide a provider-pluggable client seam so additional models can be enabled later without rewriting Flow B orchestration. Selecting an unsupported provider MUST fail closed. DeepSeek configuration MUST load from environment (existing DeepSeek settings patterns); API keys MUST NEVER appear in HTTP responses, logs, or error bodies.

#### Scenario: v1 uses DeepSeek

- **WHEN** an authenticated discovery request succeeds
- **THEN** the effective provider used for the discovery call is DeepSeek
- **AND** the response identifies the provider without exposing secrets

#### Scenario: Missing DeepSeek configuration fails closed

- **WHEN** DeepSeek settings are missing or invalid and discovery is invoked
- **THEN** the worker returns a clear operator-visible configuration/discovery error
- **AND** no draft filesystem writes occur

### Requirement: Discovery inputs and BL-020 independence

Discovery inputs v1 MUST include: authority brief, editorial canon topic spaces, and soft anti-dup signals against recent published blogs. Discovery MAY include optional durable primary material for thesis formation when present. Discovery MUST NOT require a hand-curated BL-020 topic backlog to run. Soft anti-dup is preferential, not a hard thematic engine.

#### Scenario: Discovery runs without BL-020 backlog

- **WHEN** no hand-curated BL-020 backlog is present and an authenticated client requests discovery
- **THEN** discovery still proceeds using authority brief, canon topic spaces, and soft anti-dup inputs

#### Scenario: Soft anti-dup uses recent published blogs read-only

- **WHEN** recent published blog titles/themes are available under the editorial layout
- **THEN** discovery includes them as soft anti-dup context
- **AND** those source files are not moved or rewritten by discovery

### Requirement: Optional gap-batch context

When invoked with optional gap-batch context (for future US-082), the discovery endpoint MUST accept target ISO week and `empty_days[]` as informational fields. Those fields MUST NOT invent or require a filesystem inventory of `blog-posts/ready/` or `blog-posts/pending-approval/` as a discovery prerequisite. When provided, the response SHOULD echo the gap context for operator visibility.

#### Scenario: Gap context is informational only

- **WHEN** an authenticated client posts discovery with `target_week` and `empty_days`
- **THEN** discovery may include that context in the provider brief as scheduling hints
- **AND** discovery does not require scanning `ready/` or `pending-approval/` inventory to succeed

#### Scenario: Discovery works without gap context

- **WHEN** an authenticated client requests discovery without gap-batch fields
- **THEN** discovery still proceeds and returns topics or a fail-closed error based on discovery outcomes alone

### Requirement: Batch size capped by max_drafts_per_weekly_run

Discovery MUST produce at most N distinct topic choices in one batch where N is ≤ effective `max_drafts_per_weekly_run` from `load_gap_operator_settings()` (documented default **2** when settings row missing). Requested counts above the ceiling MUST be clamped. Topics in a successful batch MUST be distinct theses.

#### Scenario: Batch respects settings ceiling

- **WHEN** effective `max_drafts_per_weekly_run` is `2` and a client requests more than 2 topics
- **THEN** the worker returns at most 2 distinct topic choices on success

#### Scenario: Default ceiling applies when settings row missing

- **WHEN** no settings row exists and discovery runs without an explicit smaller count
- **THEN** the effective ceiling is the documented default `2`

### Requirement: Fail closed with operator-visible errors

When discovery cannot produce at least one objective-aligned topic, the worker MUST fail closed with a clear operator-visible structured error. Partial provider failures, empty responses, and alignment rejections MUST NOT be reported as successful topic discovery. Discovery MUST NOT enable LinkedIn API publication or modify `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

#### Scenario: Empty provider response fails closed

- **WHEN** the discovery provider returns no usable topic content
- **THEN** the worker returns a structured operator-visible error
- **AND** the response is not a successful `topics_discovered` status

#### Scenario: Discovery does not enable LinkedIn publish

- **WHEN** an authenticated client runs discovery successfully or unsuccessfully
- **THEN** LinkedIn API publication enablement remains governed solely by existing env guards

### Requirement: US-078 scope excludes draft, approve, and trigger

This capability MUST NOT implement blog draft generation into `pending-approval/` (US-079), approve/reject UI or promote-to-`ready/` (US-080/US-081), or gap trigger orchestration (US-082). Gap detect (`flow-b-calendar-gap-detect`) and settings persist/UI (`flow-b-gap-operator-settings`) contracts MUST remain unchanged except that discovery consumes `max_drafts_per_weekly_run` via `load_gap_operator_settings()`.

#### Scenario: No draft folder writes from discovery

- **WHEN** discovery completes successfully
- **THEN** `blog-posts/pending-approval/` and `blog-posts/ready/` gain no new draft files from this capability

#### Scenario: No trigger or approve routes required

- **WHEN** this capability’s requirements are evaluated
- **THEN** gap trigger and blog approve/promote endpoints are not required for US-078 completion
