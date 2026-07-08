## ADDED Requirements

### Requirement: ComfyUI blog image generation before validation

When a Flow A ready post lacks canonical image prerequisites and ComfyUI image generation is enabled, the system SHALL attempt blog image generation before automated editorial validation.

Canonical image prerequisites are satisfied when front matter `image` equals `/assets/images/<public_slug>.png` and companion PNG `blog-posts/ready/<source_slug>.png` exists.

Generation SHALL be attempted only when:

- YAML front matter omits `image` or `image` is empty/whitespace-only, OR
- front matter `image` equals `/assets/images/<public_slug>.png` and companion PNG `blog-posts/ready/<source_slug>.png` is missing

When front matter `image` is present and points to any non-canonical path, the system MUST NOT invoke ComfyUI generation; the post MUST remain unchanged and existing validation or operator remediation MUST handle the mismatch.

Generated images MUST target 1200×900 (4:3) by default to match the public blog template at [silverman.pro](https://silverman.pro), which reuses front matter `image` for post hero, list cards, tag cards, and sidebar thumbnails with `aspect-ratio: 1.3333333333` and `object-fit: cover`.

When generation is enabled and required but fails, Flow A blog publication MUST NOT proceed.

When generation is disabled, missing image prerequisites MUST continue to fail validation per `ready-post-editorial-validation` without automatic remediation.

#### Scenario: Generation enabled remediates missing image before validation

- **WHEN** a ready post lacks `image` front matter, ComfyUI generation is enabled, and generation succeeds
- **THEN** the post receives companion PNG and canonical `image` front matter before validation runs and may proceed to blog publish if validation passes

#### Scenario: Generation enabled remediates missing companion PNG with canonical image path

- **WHEN** a ready post has `image: /assets/images/<public_slug>.png` but companion PNG `blog-posts/ready/<source_slug>.png` is missing, ComfyUI generation is enabled, and generation succeeds
- **THEN** the post receives the companion PNG before validation runs and may proceed to blog publish if validation passes

#### Scenario: Non-canonical image path blocks auto-generation

- **WHEN** a ready post has front matter `image` pointing to a non-canonical path (for example `/assets/images/wrong-slug.png`)
- **THEN** ComfyUI generation MUST NOT run, the post MUST remain unchanged, and validation or operator remediation MUST handle the mismatch

#### Scenario: Generation failure blocks Flow A publish

- **WHEN** a ready post lacks canonical image prerequisites, ComfyUI generation is enabled, and generation fails
- **THEN** Flow A blog publication does not proceed and structured errors reference blog image generation failure

#### Scenario: Generation disabled preserves validation gate

- **WHEN** a ready post lacks canonical image prerequisites and ComfyUI generation is disabled
- **THEN** automated validation fails with existing missing-image errors and publish does not proceed

## MODIFIED Requirements

### Requirement: Automated ready-post editorial validation

Before Flow A blog publication, the system SHALL validate each candidate blog post pair (`<source-slug>.md` and `<source-slug>.png`) in `blog-posts/ready/` against editorial rules from the canonical artifact and structural requirements.

When optional ComfyUI blog image generation is enabled and succeeds for a post that initially lacked canonical image prerequisites, validation MUST run against the updated source pair after generation completes.

Validation MUST check at minimum:

- `source_slug` and derived `public_slug` per the slug validation requirement
- readable Markdown and PNG pair exists
- required YAML frontmatter fields per blog rules (including parseable `date` and canonical `image: /assets/images/<public_slug>.png`)
- absence of forbidden content types defined in the editorial artifact where reliably automatable

For Flow A user-provided blog input, validation MUST block only reliably automatable structural and editorial contract violations. Anti-AI-writing rules MUST NOT be treated as perfectly detectable on user-authored blog content; such rules MAY produce warnings unless a child spec explicitly marks a rule as blocking.

Anti-AI-writing rules MUST be applied strongly to generated LinkedIn derivative content and future Flow B generated content.

Validation MUST return structured JSON with `status` (`completed` or `failed`), `errors[]`, optional `warnings[]`, and `campaign_id` when created.

#### Scenario: Valid ready post passes validation

- **WHEN** a ready post pair meets slug, file, frontmatter, and editorial rules
- **THEN** validation returns `status` `completed` and the post is eligible for Flow A blog publish

#### Scenario: Missing PNG fails validation when generation disabled or failed

- **WHEN** `blog-posts/ready/<source-slug>.md` exists but the matching `.png` does not and ComfyUI generation is disabled or did not run successfully
- **THEN** validation returns `status` `failed` with a clear error and does not publish

#### Scenario: Post passes validation after successful generation

- **WHEN** a post initially lacked canonical image prerequisites, ComfyUI generation succeeded writing PNG and/or front matter, and all other editorial rules pass
- **THEN** validation returns `status` `completed` and the post is eligible for Flow A blog publish

#### Scenario: Forbidden content type fails validation

- **WHEN** post content or metadata matches a forbidden content type defined in the editorial artifact (for example pure news commentary)
- **THEN** validation returns `status` `failed` with reason referencing the violated rule
