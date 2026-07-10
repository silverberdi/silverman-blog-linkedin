## ADDED Requirements

### Requirement: Active companion path for handoff

Callers of public blog image handoff MUST pass the actual active companion image path derived from `source_relative_path`, whether under `blog-posts/ready/` or `blog-posts/queued/`.

Handoff MUST support copying or reusing validated images from both `blog-posts/ready/<source_slug>.png` and `blog-posts/queued/<source_slug>.png` into public repo `assets/images/<public_slug>.png`.

Public handoff MUST run only after full editorial validation succeeds for the active local Markdown + companion PNG pair.

Campaign metadata MUST record for queued-generated images:

- generation status and provenance (`comfyui_generated`, `adopted_existing`, or `reused_public`);
- editorial image-relative path (queued or ready);
- public repository image-relative path;
- public image URL or equivalent existing fields;
- public asset handoff status.

#### Scenario: Handoff from queued-generated PNG after full validation

- **WHEN** editorial remediation generated `blog-posts/queued/01-example.png`, full validation succeeded, and handoff runs with configured public repo path
- **THEN** `assets/images/<public_slug>.png` exists in the public checkout and campaign metadata records queued editorial path and handoff success

#### Scenario: Handoff from ready sibling unchanged

- **WHEN** `handoff_public_blog_image` adopts `blog-posts/ready/01-example.png` into public assets after full validation
- **THEN** existing ready-path handoff behavior is preserved

### Requirement: Active-folder sibling backfill before full validation

When a readable public asset exists at `assets/images/<public_slug>.png` and the active-folder sibling PNG `<active_source_folder>/<source_slug>.png` is missing, the worker MUST attempt active-folder sibling backfill by copying from the public asset during editorial remediation solely so full validation can operate on the local pair.

The worker MUST NOT overwrite an existing active-folder sibling PNG during backfill.

When backfill succeeds, the worker MUST record `active_sibling_backfill_status` `copied` (or equivalent) in `blog_image_generation` metadata.

When backfill fails, publish MUST NOT bypass full validation merely because the public asset exists. The worker MUST return an explicit failure classified as `retryable` or `repair_required` according to cause.

Full validation MUST NOT be skipped when the public asset exists but the active-folder sibling is missing and backfill did not succeed.

#### Scenario: Public asset reuse backfills queued sibling and passes full validation without ComfyUI

- **WHEN** public asset exists, front matter `image` is canonical or absent, `blog-posts/queued/<source_slug>.png` is missing, backfill copy succeeds, and ComfyUI generation is enabled
- **THEN** the worker creates the queued sibling from the public asset without calling ComfyUI, full validation succeeds on the local pair, and handoff may reuse the existing public asset

#### Scenario: Public asset reuse with failed queued-sibling backfill does not publish

- **WHEN** public asset exists and is readable, active-folder sibling is missing, backfill fails (for example unwritable `blog-posts/queued/`), and full validation requires the local companion PNG
- **THEN** the worker does not call ComfyUI, does not call full validation success path, does not hand off or publish, and returns an explicit failure with `retryable` or `repair_required` classification per cause

#### Scenario: Active-folder backfill must not overwrite existing file

- **WHEN** public asset exists and `blog-posts/queued/<source_slug>.png` already exists
- **THEN** the worker does not overwrite the existing sibling PNG and records backfill status `not_needed` or equivalent

## MODIFIED Requirements

### Requirement: Public blog image handoff entry point

The worker SHALL provide public blog image handoff behavior (for example `handoff_public_blog_image` or an internal helper called only after full validation) that copies or reuses images at `assets/images/<public_slug>.png` inside the configured public GitHub Pages repository checkout (`SILVERMAN_GITHUB_PAGES_REPO_PATH`).

The handoff helper MUST accept an explicit editorial companion image path and MUST NOT assume `blog-posts/ready/` when the active source is queued.

Handoff MUST NOT run inside editorial remediation or before `validate_ready_post()` succeeds in `publish_blog_post`.

On retry of `publish_blog_post` for the same source post, the worker MUST NOT invoke ComfyUI when a reusable image already exists at the public asset path and/or a valid editorial sibling PNG can be adopted into public assets after full validation.

When a readable public asset already exists, handoff MAY record reuse without overwriting the public file.

#### Scenario: Handoff failure after successful full validation blocks publish

- **WHEN** companion PNG exists at `blog-posts/queued/01-example.png`, full validation succeeded, but public asset copy fails
- **THEN** handoff returns failure with `blog_image_public_asset_handoff_failed`, preserves the generated queued PNG, does not write public post files, and does not mask the error as `ready_post_image_missing`

#### Scenario: Full validation failure prevents handoff invocation

- **WHEN** `validate_ready_post` fails after editorial remediation for a queued source
- **THEN** handoff is not invoked and no public asset file is created or modified

## REMOVED Requirements

### Requirement: Ready sibling backfill from public asset for compatibility

**Reason**: Superseded by active-folder sibling backfill before full validation. Publish MUST NOT continue without the local companion when full validation requires it.

**Migration**: Replace ready-only optional backfill semantics with active-folder backfill required for validation; failed backfill blocks publish explicitly.

### Requirement: Public asset exists with missing ready sibling backfill fails but publish proceeds

**Reason**: Inconsistent with staged ordering and full validation on the active local pair.

**Migration**: Classify failed active-folder backfill as explicit `retryable` or `repair_required` failure; do not allow publish without local companion when validation requires it.
