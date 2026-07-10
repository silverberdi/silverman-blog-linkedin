## ADDED Requirements

### Requirement: Markdown-only Flow A image generation path

Flow A MUST support the canonical Markdown-only execution path:

calendar-selected Markdown in `blog-posts/ready/` (no companion PNG; `image` absent, empty, or canonical)
→ queue acceptance to `blog-posts/queued/`
→ execution claim
→ pre-generation validation that does not block solely on missing/empty generatable `image` or generatable missing PNG
→ editorial image remediation beside active queued source (ComfyUI when eligible; public-asset backfill when applicable; no public write)
→ authorized source-hash reconciliation when frontmatter is patched
→ full editorial validation including canonical `image` and local companion PNG
→ public asset handoff
→ blog publication
→ LinkedIn package generation
→ LinkedIn scheduling
→ lifecycle completion moving queued Markdown and generated PNG to `blog-posts/processed/`

Operators MUST NOT be required to manually provide a PNG for normal Flow A execution when frontmatter `image` is absent, empty, or canonical and ComfyUI generation is enabled.

Direct `publish_blog_post` calls with sources under `blog-posts/ready/` MUST remain valid without queue acceptance, including legacy behavior that generates and patches missing frontmatter `image`.

#### Scenario: Markdown-only post with absent image completes Flow A without manual PNG

- **WHEN** an approved Markdown-only post with absent frontmatter `image` is processed through the editorial calendar connector with ComfyUI enabled
- **THEN** editorial remediation patches `image`, ComfyUI generates the companion PNG, full validation and handoff succeed, publish and downstream steps succeed, and both Markdown and PNG end in `blog-posts/processed/`

#### Scenario: Legacy direct ready publish still works with missing image

- **WHEN** `publish_blog_post` is invoked directly with `blog-posts/ready/<slug>.md`, absent `image`, and no companion PNG
- **THEN** editorial remediation patches frontmatter, image generation and publish proceed without requiring queue acceptance

## MODIFIED Requirements

### Requirement: Flow A content policy

The system SHALL treat Flow A as the automatic publishing path for user-provided blog posts placed in `blog-posts/ready/` by the author.

Flow A content SHALL be considered pre-approved for blog publication and LinkedIn derivative generation only after automated full editorial validation passes (after editorial image remediation when generation or backfill applies).

Flow A MUST NOT require human review or approval after validation passes.

Flow A MUST NOT require operators to supply companion PNG files when automatic ComfyUI generation is enabled and frontmatter `image` is absent, empty, or canonical.

Flow B (system-generated ideas, blog drafts, or LinkedIn drafts) SHALL require human review and approval before publication and MUST NOT enter Flow A automatic publish paths.

Every campaign and derivative record MUST include a `flow` field with value `flow_a` or `flow_b`.

#### Scenario: Flow A proceeds without human approval after full validation

- **WHEN** a user-provided blog post passes full automated Flow A validation (including generated, adopted, or backfilled PNG when required)
- **THEN** the system MAY proceed to automatic blog publish and LinkedIn derivative generation without a human approval step

#### Scenario: Flow B blocked from Flow A automatic path

- **WHEN** content is marked or detected as Flow B (system-generated, not user-provided ready input)
- **THEN** the system MUST NOT automatically publish the blog or schedule LinkedIn posts on the Flow A path

#### Scenario: Full validation failure blocks automatic path

- **WHEN** automated Flow A full validation fails for a ready or queued blog post after editorial remediation
- **THEN** the system MUST NOT hand off public assets, publish the blog, or generate Flow A LinkedIn derivatives

#### Scenario: Generation failure blocks automatic path without masking as missing ready image

- **WHEN** ComfyUI generation fails for an eligible Markdown-only post
- **THEN** the system MUST NOT publish and MUST surface a specific `blog_image_generation_*` error, not solely `ready_post_image_missing` from a premature validation gate

#### Scenario: Generation disabled requires strict image validation

- **WHEN** automatic image generation is disabled and a queued source has absent `image` or missing companion PNG
- **THEN** full validation fails and the automatic publish path does not proceed
