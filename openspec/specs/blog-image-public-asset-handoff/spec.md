# blog-image-public-asset-handoff Specification

## Purpose
TBD - created by archiving change blog-image-public-asset-handoff. Update Purpose after archive.
## Requirements
### Requirement: Active companion path for handoff

Callers of public blog image handoff MUST pass the actual active companion image path derived from `source_relative_path`, whether under `blog-posts/ready/` or `blog-posts/queued/`.

Handoff MUST support copying or reusing validated images from both `blog-posts/ready/<source_slug>.png` and `blog-posts/queued/<source_slug>.png` into public repo `assets/images/<public_slug>.png`.

Public handoff MUST run only after full editorial validation succeeds for the active local Markdown + companion PNG pair.

Campaign metadata MUST record handoff and generation fields per the Handoff metadata recording requirement, including at minimum:

- `public_asset_handoff_status` and `public_asset_source` when applicable (`existing_public_asset`, `active_sibling_png`, or `comfyui_generated`);
- editorial image-relative path (queued or ready);
- public repository image-relative path;
- public image URL or equivalent existing fields.

#### Scenario: Handoff from queued-generated PNG after full validation

- **WHEN** editorial remediation generated `blog-posts/queued/01-example.png`, full validation succeeded, and handoff runs with configured public repo path
- **THEN** `assets/images/<public_slug>.png` exists in the public checkout and campaign metadata records queued editorial path and handoff success

#### Scenario: Legacy direct ready-path handoff preserved

- **WHEN** `handoff_public_blog_image` adopts `blog-posts/ready/01-example.png` into public assets after full validation on a direct ready publish path
- **THEN** existing ready-path handoff behavior is preserved
### Requirement: Active-folder sibling backfill before full validation

When a readable public asset exists at `assets/images/<public_slug>.png` and the active-folder sibling PNG `<active_source_folder>/<source_slug>.png` is missing, the worker MUST attempt active-folder sibling backfill by copying from the public asset during editorial remediation solely so full validation can operate on the local pair.

`<active_source_folder>` MUST be derived from `source_relative_path` as `blog-posts/ready` or `blog-posts/queued`.

The worker MUST NOT overwrite an existing active-folder sibling PNG during backfill.

When backfill succeeds, the worker MUST record `active_sibling_backfill_status` `copied` (or equivalent) in `blog_image_generation` metadata.

When backfill fails, the worker MUST return an explicit editorial remediation failure with stable error code `blog_image_active_sibling_backfill_failed` (or equivalent documented remediation code) classified as `retryable` or `repair_required` according to cause.

Backfill failure MUST NOT be classified as `blog_image_public_asset_handoff_failed`.

Backfill failure MUST NOT enter the full validation success path, MUST NOT invoke public handoff, and MUST NOT allow publish to proceed.

Full validation MUST NOT be skipped when the public asset exists but the active-folder sibling is missing and backfill did not succeed.

#### Scenario: Public asset reuse backfills active-folder sibling and passes full validation without ComfyUI

- **WHEN** public asset exists, front matter `image` is canonical or absent, `<active_source_folder>/<source_slug>.png` is missing, backfill copy succeeds, and ComfyUI generation is enabled
- **THEN** the worker creates the active-folder sibling from the public asset without calling ComfyUI, full validation succeeds on the local pair, and handoff may reuse the existing public asset

#### Scenario: Public asset reuse with failed active-folder sibling backfill does not publish

- **WHEN** public asset exists and is readable, active-folder sibling is missing, backfill fails (for example unwritable active folder), and full validation requires the local companion PNG
- **THEN** the worker does not call ComfyUI, does not enter the full validation success path, does not hand off or publish, and returns `blog_image_active_sibling_backfill_failed` (or equivalent) with `retryable` or `repair_required` classification per cause

#### Scenario: Active-folder backfill must not overwrite existing file

- **WHEN** public asset exists and `<active_source_folder>/<source_slug>.png` already exists
- **THEN** the worker does not overwrite the existing active-folder sibling PNG and records backfill status `not_needed` or equivalent
### Requirement: Public blog image handoff entry point

The worker SHALL provide public blog image handoff behavior (for example `handoff_public_blog_image` or an internal helper called only after full validation) that copies or reuses images at `assets/images/<public_slug>.png` inside the configured public GitHub Pages repository checkout (`SILVERMAN_GITHUB_PAGES_REPO_PATH`).

The handoff helper MUST accept an explicit active-folder companion image path and MUST NOT assume `blog-posts/ready/` when the active source is queued.

Handoff MUST NOT run inside editorial remediation or before `validate_ready_post()` succeeds in `publish_blog_post`.

On retry of `publish_blog_post` for the same source post, the worker MUST NOT invoke ComfyUI when a reusable image already exists at the public asset path and/or a valid active-folder sibling PNG can be adopted into public assets after full validation.

When a readable public asset already exists, handoff MAY record reuse without overwriting the public file.

#### Scenario: Handoff failure after successful full validation blocks publish

- **WHEN** companion PNG exists at `blog-posts/queued/01-example.png`, full validation succeeded, but public asset copy fails
- **THEN** handoff returns failure with `blog_image_public_asset_handoff_failed`, preserves the generated queued PNG, does not write public post files, and does not mask the error as `ready_post_image_missing`

#### Scenario: Full validation failure prevents handoff invocation

- **WHEN** `validate_ready_post` fails after editorial remediation for a queued source
- **THEN** handoff is not invoked and no public asset file is created or modified
### Requirement: Reuse existing public asset without regeneration

When `assets/images/<public_slug>.png` already exists in the configured public repo checkout and is a readable regular file, the worker MUST treat the Jekyll/public publishing image prerequisite as satisfied, MUST NOT call ComfyUI solely because the active-folder sibling PNG is missing, and MUST NOT overwrite the existing public file.

The worker MUST ensure front matter `image` equals `/assets/images/<public_slug>.png`.

When the active-folder sibling is missing, editorial remediation MUST attempt active-folder sibling backfill per the active-folder sibling backfill requirement before full validation.

#### Scenario: Public asset exists skips ComfyUI

- **WHEN** publish evaluates image prerequisites, `assets/images/deferring-is-not-avoiding-it-can-be-architecture.png` exists in the public repo, and ComfyUI generation is enabled
- **THEN** ComfyUI is not called, `blog_image_generation.status` is `skipped` with `skip_reason` indicating public asset reuse, and publish may continue only after active-folder backfill succeeds or the active-folder sibling already exists

#### Scenario: Public asset exists with missing active-folder sibling does not trigger ComfyUI

- **WHEN** public asset exists and is readable, front matter `image` is canonical or absent, and `<active_source_folder>/<source_slug>.png` is missing
- **THEN** ComfyUI is not called; editorial remediation attempts active-folder sibling backfill

#### Scenario: Legacy direct ready path with missing ready-folder sibling

- **WHEN** `publish_blog_post` is invoked directly with `blog-posts/ready/<source_slug>.md`, public asset exists, front matter `image` is canonical, and `blog-posts/ready/<source_slug>.png` is missing
- **THEN** ComfyUI is not called; editorial remediation attempts active-folder backfill into `blog-posts/ready/` before full validation
### Requirement: Adopt editorial sibling PNG into public assets

When `<active_source_folder>/<source_slug>.png` exists as a readable regular file (where `<active_source_folder>` is `blog-posts/ready` or `blog-posts/queued` derived from `source_relative_path`) and the public repo target `assets/images/<public_slug>.png` is missing, the worker MUST copy the active-folder sibling PNG into the public repo target during handoff after full validation.

The worker MUST NOT call ComfyUI solely because the public asset was missing when a valid active-folder sibling PNG already exists beside the active Markdown.

#### Scenario: Post 02 failure scenario adoption

- **WHEN** `blog-posts/ready/02-deferring-is-not-avoiding-it-can-be-architecture.md` has canonical `image`, active-folder sibling `blog-posts/ready/02-deferring-is-not-avoiding-it-can-be-architecture.png` exists (for example 1536×1024 PNG from a prior ComfyUI run), and public `assets/images/deferring-is-not-avoiding-it-can-be-architecture.png` is missing
- **THEN** the worker copies the active-folder sibling PNG into the public repo, records handoff metadata, does not call ComfyUI, and publish may continue

#### Scenario: Missing image front matter with active-folder sibling PNG

- **WHEN** front matter lacks `image`, active-folder sibling PNG exists beside the active Markdown, and public asset is missing
- **THEN** the worker patches front matter to the canonical path during editorial remediation, copies the active-folder sibling into public assets during handoff, and does not call ComfyUI
### Requirement: Handoff after ComfyUI generation

When ComfyUI generation produces PNG bytes and writes `<active_source_folder>/<source_slug>.png` during editorial remediation, the worker MUST hand off that PNG to `assets/images/<public_slug>.png` in the public repo checkout during the post-validation handoff phase when the public target is missing.

If handoff fails after successful ComfyUI write to the editorial path, the worker MUST return `status: failed` with `blog_image_public_asset_handoff_failed`.

#### Scenario: ComfyUI generate then handoff

- **WHEN** ComfyUI generation succeeds, editorial PNG is written beside the active Markdown, and public asset is missing
- **THEN** public `assets/images/<public_slug>.png` is created and `blog_image_generation.public_asset_handoff_status` is `copied` with `public_asset_source` `comfyui_generated`

#### Scenario: ComfyUI skipped when handoff not needed

- **WHEN** ComfyUI would run but public asset already exists
- **THEN** ComfyUI is not invoked and `public_asset_handoff_status` is `reused`
### Requirement: Handoff failure error code

When required copy or adoption **into** `assets/images/<public_slug>.png` fails (permissions, missing parent directory, I/O error, invalid repo layout) on the active-folder sibling → public-asset adoption path or post-ComfyUI handoff path, the worker MUST return `blog_image_public_asset_handoff_failed` as the stable error code.

Active-folder sibling backfill failures during editorial remediation MUST return `blog_image_active_sibling_backfill_failed` (or equivalent documented remediation code) and MUST NOT map to `blog_image_public_asset_handoff_failed`.

The worker MUST NOT map required public handoff failures to generic `blog_image_generation_failed` when the failure cause is public asset copy/adoption.

#### Scenario: Permission denied on public assets directory

- **WHEN** the worker cannot create `assets/images/<public_slug>.png` due to permission or I/O failure during handoff after full validation
- **THEN** `errors[]` includes `blog_image_public_asset_handoff_failed` and `blog_image_generation.error_code` is `blog_image_public_asset_handoff_failed`

#### Scenario: Active-folder backfill failure is not a handoff failure

- **WHEN** editorial remediation cannot backfill `<active_source_folder>/<source_slug>.png` from a readable public asset
- **THEN** `errors[]` includes `blog_image_active_sibling_backfill_failed` (or equivalent), handoff is not invoked, and `blog_image_public_asset_handoff_failed` is not returned for that cause
### Requirement: Retry without duplicate ComfyUI generation

On retry of `publish_blog_post` or `ensure_blog_image` for the same source post, the worker MUST NOT invoke ComfyUI when a reusable image already exists at the public asset path and/or a valid active-folder sibling PNG can be adopted into public assets.

Specifically:

- When a valid reusable image already exists at the public asset path, the worker MUST NOT invoke ComfyUI again.
- When a valid active-folder sibling PNG exists and the public asset is missing, the worker MUST adopt the active-folder sibling into public assets without invoking ComfyUI again.
- When a prior ComfyUI run wrote `<active_source_folder>/<source_slug>.png` but publish failed before completion, the worker MUST adopt or confirm public asset handoff without invoking ComfyUI again.

#### Scenario: Retry after local active-folder PNG exists

- **WHEN** a prior attempt wrote `<active_source_folder>/<source_slug>.png` but failed before publish completed, and publish is retried
- **THEN** ComfyUI is not called, the worker adopts or confirms public asset handoff, and publish may proceed

#### Scenario: Retry after public handoff succeeded

- **WHEN** public asset already exists from a prior handoff and front matter is canonical
- **THEN** ComfyUI is not called on retry

#### Scenario: Legacy retry after ComfyUI wrote ready-folder sibling

- **WHEN** a prior ComfyUI run created `blog-posts/ready/<source_slug>.png`, public `assets/images/<public_slug>.png` is still missing, and publish is retried on a direct ready path
- **THEN** ComfyUI is not called, the worker copies/adopts the existing active-folder sibling PNG into public assets, and publish may proceed when handoff succeeds
### Requirement: Permission-safe public asset writes

Copied public assets MUST be written as regular files readable by the blog repo checkout user/process (for example mode `0644`).

Implementation MUST NOT require manual `chown` by the operator for normal successful handoff.

Automated tests MUST NOT assume root ownership of files or directories.

#### Scenario: Copied asset is world-readable

- **WHEN** handoff copies a PNG into the public repo
- **THEN** the resulting file permissions allow read by the owning user and group/other read per `0644` (subject to process umask)
### Requirement: Handoff metadata recording

When handoff runs in a publish context with campaign metadata available, the worker MUST record on `blog_image_generation` at minimum:

- `public_asset_handoff_status`: one of `reused`, `copied`, `not_needed`, `failed`
- `public_asset_source` when applicable: one of `existing_public_asset`, `active_sibling_png`, `comfyui_generated`
- `public_repo_image_relative_path`: `assets/images/<public_slug>.png`
- `active_sibling_backfill_status` when applicable: one of `copied`, `not_needed`, `failed`

`public_asset_source` vocabulary MUST have these canonical meanings:

- `existing_public_asset` — handoff reused a readable public asset without overwriting it
- `active_sibling_png` — handoff copied or adopted the validated PNG from `<active_source_folder>/<source_slug>.png` where the active folder is `blog-posts/ready` or `blog-posts/queued`
- `comfyui_generated` — handoff copied a ComfyUI-generated PNG from the active folder into public assets

`ready_sibling_png` is a legacy persisted value from releases before active-folder terminology. Consumers MUST treat `ready_sibling_png` as semantically equivalent to `active_sibling_png` for ready-folder sources. New writes for both ready and queued sources MUST use `active_sibling_png`.

Queued-source handoff MUST NOT persist `ready_sibling_png`; queued siblings MUST use `active_sibling_png`.

#### Scenario: Reused public asset metadata

- **WHEN** an existing public asset is reused
- **THEN** campaign metadata records `public_asset_handoff_status` `reused` and `public_asset_source` `existing_public_asset`

#### Scenario: Adopted active-folder sibling metadata

- **WHEN** an active-folder sibling PNG is copied to public assets after full validation
- **THEN** campaign metadata records `public_asset_handoff_status` `copied` and `public_asset_source` `active_sibling_png`

#### Scenario: Queued active-folder sibling metadata

- **WHEN** `blog-posts/queued/<source_slug>.png` is copied to public assets after full validation
- **THEN** campaign metadata records `public_asset_source` `active_sibling_png`, not `ready_sibling_png`
### Requirement: Blog image public asset handoff tests

The repository SHALL include automated tests covering:

- public asset exists, active-folder sibling missing, backfill succeeds without ComfyUI
- public asset exists, active-folder sibling missing, backfill fails and publish is blocked with remediation error
- active-folder sibling exists, public asset missing, copy/adopt succeeds without ComfyUI
- active-folder sibling exists, public asset missing, copy/adopt failure returns stable `blog_image_public_asset_handoff_failed`
- ComfyUI generates image → handoff to public assets succeeds
- retry after local active-folder PNG exists → no duplicate ComfyUI call
- retry after public asset already exists → no duplicate ComfyUI call
- post `02-deferring-is-not-avoiding-it-can-be-architecture` failure scenario

Tests MUST use injectable fakes or temporary directories and MUST NOT require a live ComfyUI server or root privileges.

#### Scenario: Public asset reuse with successful backfill

- **WHEN** tests simulate readable public asset, canonical or absent front matter, missing active-folder sibling, and writable active folder
- **THEN** tests verify active-folder sibling is backfilled, ComfyUI client is not called, and publish image step succeeds

#### Scenario: Public asset reuse with failed backfill blocks publish

- **WHEN** tests simulate readable public asset, canonical or absent front matter, missing active-folder sibling, and unwritable active folder (or equivalent backfill failure)
- **THEN** tests verify ComfyUI client is not called, publish is blocked with `blog_image_active_sibling_backfill_failed` (or equivalent), and `blog_image_public_asset_handoff_failed` is not used to mask the failure

#### Scenario: Post 02 regression test

- **WHEN** tests simulate the post `02` ready pair with canonical front matter, existing active-folder sibling PNG, and missing public asset
- **THEN** tests verify public asset is created, ComfyUI client is not called, and publish image step succeeds

#### Scenario: Active-folder sibling adoption handoff failure

- **WHEN** tests simulate existing active-folder sibling PNG, missing public asset, and unwritable public `assets/images/` directory
- **THEN** tests verify ComfyUI client is not called and `blog_image_public_asset_handoff_failed` is returned
### Requirement: Operator documentation for automatic handoff

Operator documentation SHALL state that:

- manual image copy into the public blog repo is not required for normal Flow A publish
- an existing readable public asset at `assets/images/<public_slug>.png` is authoritative for Jekyll and satisfies the public image prerequisite without ComfyUI
- generated or pre-existing local active-folder PNGs are adopted automatically into `assets/images/<public_slug>.png` when the public asset is missing
- missing active-folder sibling PNGs may be backfilled from the public asset during editorial remediation so full validation can operate on the local pair; failed backfill blocks publish explicitly with a remediation error, not a handoff error
- front matter `image: /assets/images/<public_slug>.png` is the canonical Jekyll path
- retries reuse existing valid public or local images without redundant ComfyUI generation

#### Scenario: Ops doc mentions retry reuse

- **WHEN** an operator reads the blog publishing operations documentation
- **THEN** they find explicit guidance that retry after a partial image failure reuses existing PNGs when valid
### Requirement: Non-goals enforcement

This capability MUST NOT modify n8n workflow JSON, activate n8n schedules, add cron triggers, publish to LinkedIn, or modify `calendar.json`.

This capability MUST NOT modify archived OpenSpec changes.

#### Scenario: No n8n workflow changes

- **WHEN** this change is applied
- **THEN** no files under n8n workflow export paths are modified

### Requirement: Concurrent image paths re-check reusable assets before ComfyUI

On concurrent or repeated `publish_blog_post` / image-ensure paths for the same source post, the worker MUST re-check reusable image locations immediately before invoking ComfyUI:

- active-folder sibling PNG beside the active Markdown, and
- public checkout `assets/images/<public_slug>.png` when configured

When either location already provides a reusable readable asset, the worker MUST NOT call ComfyUI, MUST record a skipped/reuse outcome consistent with existing handoff metadata fields, and MUST NOT overwrite an existing readable public asset solely because a concurrent generation attempt also entered the image path.

Flow A connector executions that lost execution claim contention MUST NOT reach ComfyUI for the losing attempt (claim gate owns that prevention).

#### Scenario: Repeated publish with existing public asset skips ComfyUI

- **WHEN** a publish/image path runs and `assets/images/<public_slug>.png` already exists as a readable regular file
- **THEN** ComfyUI is not called and generation status reflects skipped/reuse

#### Scenario: Asset appears before provider call skips ComfyUI

- **WHEN** a reusable public or active-folder PNG becomes present after an earlier check but before the ComfyUI provider call
- **THEN** the worker skips ComfyUI and does not overwrite the reusable public asset

#### Scenario: Claim contention prevents a second ComfyUI attempt via connector

- **WHEN** a concurrent calendar Flow A execution fails with `flow_a_execution_already_claimed`
- **THEN** that execution does not invoke ComfyUI for the contested campaign
