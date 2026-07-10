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

### Requirement: ComfyUI blog image generation before validation

When a Flow A post lacks full-validation canonical image prerequisites and ComfyUI image generation is enabled, the system SHALL attempt editorial image remediation during the staged publish sequence defined by `worker-blog-publishing-endpoint`.

`<active_source_folder>` MUST be derived from `source_relative_path` as `blog-posts/ready` or `blog-posts/queued`. Unsupported source folders MUST be rejected.

Full-validation canonical image prerequisites are satisfied when front matter `image` equals `/assets/images/<public_slug>.png` and companion PNG `<active_source_folder>/<source_slug>.png` exists.

`publish_blog_post()` MUST orchestrate the following strict order for posts that require image remediation or full validation:

1. **Pre-generation validation** — deterministic editorial requirements per `ready-post-editorial-validation`; MUST NOT block solely on missing/empty generatable `image` or a generatable missing companion PNG when automatic generation is eligible.
2. **Editorial image remediation** — ComfyUI generation, active-folder sibling adoption, or active-folder sibling backfill from a readable public asset per `comfyui-blog-image-generation`; patch canonical frontmatter when authorized; no public repo write.
3. **Authorized hash reconciliation** — when frontmatter is patched, update active `source_content_sha256` per `flow-a-lifecycle`.
4. **Full validation** — `validate_ready_post()` requires canonical `image` and companion PNG `<active_source_folder>/<source_slug>.png`.
5. **Public asset handoff** — per `blog-image-public-asset-handoff`; runs only after full validation succeeds.
6. **Blog publication** — existing bridge semantics.

Editorial remediation SHALL be attempted only when **either**:

- YAML front matter omits `image` or `image` is empty/whitespace-only, OR
- front matter `image` equals `/assets/images/<public_slug>.png` and companion PNG `<active_source_folder>/<source_slug>.png` is missing and active-folder backfill/adoption rules do not yet satisfy the local pair

When front matter `image` is present and points to any non-canonical path, the system MUST NOT invoke ComfyUI generation; the post MUST remain unchanged and existing validation or operator remediation MUST handle the mismatch.

Direct `publish_blog_post` calls with sources under `blog-posts/ready/` MUST remain a supported compatibility path: the same staged sequence applies with `<active_source_folder>` = `blog-posts/ready` without requiring queue acceptance.

Generated images MUST target 1200×900 (4:3) by default to match the public blog template at [silverman.pro](https://silverman.pro), which reuses front matter `image` for post hero, list cards, tag cards, and sidebar thumbnails with `aspect-ratio: 1.3333333333` and `object-fit: cover`.

When generation is enabled and required but fails, Flow A blog publication MUST NOT proceed.

When generation is disabled, missing image prerequisites MUST continue to fail full validation per `ready-post-editorial-validation` without automatic remediation.

#### Scenario: Generation enabled remediates missing image before full validation

- **WHEN** a post under `blog-posts/queued/<source_slug>.md` lacks `image` front matter, ComfyUI generation is enabled, and generation succeeds during editorial remediation
- **THEN** the post receives companion PNG at `blog-posts/queued/<source_slug>.png` and canonical `image` front matter before full validation runs and may proceed to blog publish if full validation passes

#### Scenario: Generation enabled remediates missing active-folder companion PNG with canonical image path

- **WHEN** a post has `image: /assets/images/<public_slug>.png` but companion PNG `<active_source_folder>/<source_slug>.png` is missing, ComfyUI generation is enabled, and generation succeeds
- **THEN** the post receives the companion PNG beside the active Markdown before full validation runs and may proceed to blog publish if full validation passes

#### Scenario: Legacy direct ready publish uses ready active folder

- **WHEN** `publish_blog_post` is invoked directly with `blog-posts/ready/<source_slug>.md`, absent `image`, no companion PNG, and ComfyUI generation is enabled
- **THEN** the same staged sequence runs with `<active_source_folder>` = `blog-posts/ready`, editorial remediation writes `blog-posts/ready/<source_slug>.png`, and publish may proceed without queue acceptance

#### Scenario: Non-canonical image path blocks auto-generation

- **WHEN** a post has front matter `image` pointing to a non-canonical path (for example `/assets/images/wrong-slug.png`)
- **THEN** ComfyUI generation MUST NOT run, the post MUST remain unchanged, and validation or operator remediation MUST handle the mismatch

#### Scenario: Generation failure blocks Flow A publish

- **WHEN** a post lacks full-validation canonical image prerequisites, ComfyUI generation is enabled, and generation fails during editorial remediation
- **THEN** Flow A blog publication does not proceed and structured errors reference blog image generation failure

#### Scenario: Generation disabled preserves full validation gate

- **WHEN** a post lacks full-validation canonical image prerequisites and ComfyUI generation is disabled
- **THEN** full validation fails with existing missing-image errors and publish does not proceed

### Requirement: Automated ready-post editorial validation

Before Flow A blog publication, the system SHALL validate each candidate blog post pair (`<source_slug>.md` and `<source_slug>.png`) beside the active source folder (`blog-posts/ready/` or `blog-posts/queued/` derived from `source_relative_path`) against editorial rules from the canonical artifact and structural requirements.

Pre-generation validation MUST run before editorial image remediation per `ready-post-editorial-validation`.

Full validation MUST run after editorial image remediation and authorized hash reconciliation when remediation applies.

When optional ComfyUI blog image generation is enabled and succeeds for a post that initially lacked full-validation canonical image prerequisites, full validation MUST run against the updated local Markdown + PNG pair after remediation completes.

Validation MUST check at minimum:

- `source_slug` and derived `public_slug` per the slug validation requirement
- readable Markdown and PNG pair exists beside the active folder
- required YAML frontmatter fields per blog rules (including parseable `date` and canonical `image: /assets/images/<public_slug>.png`)
- absence of forbidden content types defined in the editorial artifact where reliably automatable

For Flow A user-provided blog input, validation MUST block only reliably automatable structural and editorial contract violations. Anti-AI-writing rules MUST NOT be treated as perfectly detectable on user-authored blog content; such rules MAY produce warnings unless a child spec explicitly marks a rule as blocking.

Anti-AI-writing rules MUST be applied strongly to generated LinkedIn derivative content and future Flow B generated content.

Validation MUST return structured JSON with `status` (`completed` or `failed`), `errors[]`, optional `warnings[]`, and `campaign_id` when created.

#### Scenario: Valid active-folder post pair passes full validation

- **WHEN** a post pair under `blog-posts/queued/` meets slug, file, frontmatter, and editorial rules after remediation
- **THEN** full validation returns `status` `completed` and the post is eligible for Flow A blog publish

#### Scenario: Missing PNG fails full validation when generation disabled or failed

- **WHEN** `<active_source_folder>/<source_slug>.md` exists but `<active_source_folder>/<source_slug>.png` does not and ComfyUI generation is disabled or editorial remediation did not run successfully
- **THEN** full validation returns `status` `failed` with a clear error and does not publish

#### Scenario: Post passes full validation after successful remediation

- **WHEN** a post initially lacked full-validation canonical image prerequisites, editorial remediation succeeded writing PNG and/or front matter, and all other editorial rules pass
- **THEN** full validation returns `status` `completed` and the post is eligible for Flow A blog publish

#### Scenario: Forbidden content type fails validation

- **WHEN** post content or metadata matches a forbidden content type defined in the editorial artifact (for example pure news commentary)
- **THEN** validation returns `status` `failed` with reason referencing the violated rule
