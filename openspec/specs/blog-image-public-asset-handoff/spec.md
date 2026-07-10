# blog-image-public-asset-handoff Specification

## Purpose
TBD - created by archiving change blog-image-public-asset-handoff. Update Purpose after archive.
## Requirements
### Requirement: Public blog image asset handoff entry point

The worker SHALL provide public blog image handoff behavior (integrated into `ensure_blog_image()` or an internal helper it calls) that copies or reuses images at `assets/images/<public_slug>.png` inside the configured public GitHub Pages repository checkout (`SILVERMAN_GITHUB_PAGES_REPO_PATH`).

Handoff MUST use the same `public_slug` derivation rules as `github-pages-blog-publishing`.

Handoff MUST NOT run `git commit` or `git push`.

Handoff MUST NOT overwrite an existing `assets/images/<public_slug>.png` file in the public repo checkout.

#### Scenario: Handoff target path

- **WHEN** handoff runs for source slug `02-deferring-is-not-avoiding-it-can-be-architecture`
- **THEN** the public repo target is `assets/images/deferring-is-not-avoiding-it-can-be-architecture.png` and front matter `image` remains `/assets/images/deferring-is-not-avoiding-it-can-be-architecture.png`

#### Scenario: Public repo not configured blocks handoff

- **WHEN** `SILVERMAN_GITHUB_PAGES_REPO_PATH` is unset or the checkout lacks `assets/images/`
- **THEN** handoff fails with `blog_image_public_asset_handoff_failed` or `blog_publish_public_repo_not_configured` according to publish-flow policy, and publish does not continue

### Requirement: Reuse existing public asset without regeneration

When `assets/images/<public_slug>.png` already exists in the configured public repo checkout and is a readable regular file, the worker MUST treat the Jekyll/public publishing image prerequisite as satisfied, MUST NOT call ComfyUI solely because the editorial ready sibling PNG is missing, and MUST NOT overwrite the existing public file.

The worker MUST ensure front matter `image` equals `/assets/images/<public_slug>.png`.

#### Scenario: Public asset exists skips ComfyUI

- **WHEN** publish evaluates image prerequisites, `assets/images/deferring-is-not-avoiding-it-can-be-architecture.png` exists in the public repo, and ComfyUI generation is enabled
- **THEN** ComfyUI is not called, `blog_image_generation.status` is `skipped` with `skip_reason` indicating public asset reuse, and publish may continue

#### Scenario: Public asset exists with missing ready sibling does not trigger ComfyUI

- **WHEN** public asset exists and is readable, front matter `image` is canonical, and `blog-posts/ready/<source_slug>.png` is missing
- **THEN** ComfyUI is not called solely because the ready sibling is missing

### Requirement: Ready sibling backfill from public asset for compatibility

When a readable public asset exists at `assets/images/<public_slug>.png` and the editorial ready sibling PNG `blog-posts/ready/<source_slug>.png` is missing, the worker MUST attempt ready sibling backfill by copying from the public asset solely for compatibility with existing bridge/publish expectations when the ready sibling path is writable.

The worker MUST NOT overwrite an existing ready sibling PNG during backfill.

When backfill succeeds, the worker MUST record `ready_sibling_backfill_status` `copied` in `blog_image_generation` metadata when applicable.

When backfill fails but the public asset remains readable and satisfies Jekyll/public publishing prerequisites, the worker SHOULD record a non-blocking warning (for example `ready_sibling_backfill_failed` in `warnings[]`) and MUST allow publish to continue when downstream validation/publish can proceed safely using the public asset.

The worker MUST return `blog_image_public_asset_handoff_failed` for backfill failures only when downstream validation or publish truly requires the ready sibling and cannot proceed without it.

#### Scenario: Public asset exists with missing ready sibling backfill succeeds

- **WHEN** public asset exists, front matter `image` is canonical, `blog-posts/ready/<source_slug>.png` is missing, and backfill copy succeeds
- **THEN** the worker creates `blog-posts/ready/<source_slug>.png` from the public asset without calling ComfyUI, does not overwrite any existing ready sibling, and publish may continue

#### Scenario: Public asset exists with missing ready sibling backfill fails but publish proceeds

- **WHEN** public asset exists and is readable, front matter `image` is canonical, `blog-posts/ready/<source_slug>.png` is missing, backfill fails (for example unwritable `blog-posts/ready/`), and downstream validation/publish can proceed using the public asset
- **THEN** the worker does not call ComfyUI, records a non-blocking backfill warning, does not return `blog_image_public_asset_handoff_failed`, and publish may continue

#### Scenario: Ready sibling backfill must not overwrite existing file

- **WHEN** public asset exists and `blog-posts/ready/<source_slug>.png` already exists
- **THEN** the worker does not overwrite the existing ready sibling PNG and records `ready_sibling_backfill_status` `not_needed` or equivalent

### Requirement: Adopt editorial sibling PNG into public assets

When `blog-posts/ready/<source_slug>.png` exists as a readable regular file and the public repo target `assets/images/<public_slug>.png` is missing, the worker MUST copy the ready sibling PNG into the public repo target before publish validation continues.

The worker MUST NOT call ComfyUI solely because the public asset was missing when a valid ready sibling PNG already exists.

#### Scenario: Post 02 failure scenario adoption

- **WHEN** `blog-posts/ready/02-deferring-is-not-avoiding-it-can-be-architecture.md` has canonical `image`, sibling `blog-posts/ready/02-deferring-is-not-avoiding-it-can-be-architecture.png` exists (for example 1536×1024 PNG from a prior ComfyUI run), and public `assets/images/deferring-is-not-avoiding-it-can-be-architecture.png` is missing
- **THEN** the worker copies the sibling PNG into the public repo, records handoff metadata, does not call ComfyUI, and publish may continue

#### Scenario: Missing image front matter with sibling PNG

- **WHEN** front matter lacks `image`, sibling PNG exists under `blog-posts/ready/`, and public asset is missing
- **THEN** the worker patches front matter to the canonical path, copies the sibling into public assets, and does not call ComfyUI

### Requirement: Handoff after ComfyUI generation

When ComfyUI generation produces PNG bytes and writes `blog-posts/ready/<source_slug>.png`, the worker MUST immediately hand off that PNG to `assets/images/<public_slug>.png` in the public repo checkout when the public target is missing.

If handoff fails after successful ComfyUI write to the editorial ready path, the worker MUST return `status: failed` with `blog_image_public_asset_handoff_failed`.

#### Scenario: ComfyUI generate then handoff

- **WHEN** ComfyUI generation succeeds, editorial PNG is written, and public asset is missing
- **THEN** public `assets/images/<public_slug>.png` is created and `blog_image_generation.public_asset_handoff_status` is `copied` with `public_asset_source` `comfyui_generated`

#### Scenario: ComfyUI skipped when handoff not needed

- **WHEN** ComfyUI would run but public asset already exists
- **THEN** ComfyUI is not invoked and `public_asset_handoff_status` is `reused`

### Requirement: Handoff failure error code

When required copy or adoption **into** `assets/images/<public_slug>.png` fails (permissions, missing parent directory, I/O error, invalid repo layout) on the ready-sibling → public-asset adoption path or post-ComfyUI handoff path, the worker MUST return `blog_image_public_asset_handoff_failed` as the stable error code.

Ready sibling backfill failures when a readable public asset already exists MUST NOT map to `blog_image_public_asset_handoff_failed` unless downstream validation or publish cannot proceed without the ready sibling.

The worker MUST NOT map required public handoff failures to generic `blog_image_generation_failed` when the failure cause is public asset copy/adoption.

#### Scenario: Permission denied on public assets directory

- **WHEN** the worker cannot create `assets/images/<public_slug>.png` due to permission or I/O failure
- **THEN** `errors[]` includes `blog_image_public_asset_handoff_failed` and `blog_image_generation.error_code` is `blog_image_public_asset_handoff_failed`

### Requirement: Retry without duplicate ComfyUI generation

On retry of `publish_blog_post` or `ensure_blog_image` for the same source post, the worker MUST NOT invoke ComfyUI when a reusable image already exists at the public asset path and/or a valid editorial sibling PNG can be adopted into public assets.

Specifically:
- When a valid reusable image already exists at the public asset path, the worker MUST NOT invoke ComfyUI again.
- When a valid editorial sibling PNG exists and the public asset is missing, the worker MUST adopt the sibling into public assets without invoking ComfyUI again.
- When a prior ComfyUI run wrote `blog-posts/ready/<source_slug>.png` but publish failed before completion, the worker MUST adopt or confirm public asset handoff without invoking ComfyUI again.

#### Scenario: Retry after local PNG exists

- **WHEN** a prior attempt wrote `blog-posts/ready/<source_slug>.png` but failed before publish completed, and publish is retried
- **THEN** ComfyUI is not called, the worker adopts or confirms public asset handoff, and publish may proceed

#### Scenario: Retry after public handoff succeeded

- **WHEN** public asset already exists from a prior handoff and front matter is canonical
- **THEN** ComfyUI is not called on retry

#### Scenario: Retry after ComfyUI wrote sibling but public asset still missing

- **WHEN** a prior ComfyUI run created `blog-posts/ready/<source_slug>.png`, public `assets/images/<public_slug>.png` is still missing, and publish is retried
- **THEN** ComfyUI is not called, the worker copies/adopts the existing sibling PNG into public assets, and publish may proceed when handoff succeeds

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
- `public_asset_source` when applicable: one of `existing_public_asset`, `ready_sibling_png`, `comfyui_generated`
- `public_repo_image_relative_path`: `assets/images/<public_slug>.png`
- `ready_sibling_backfill_status` when applicable: one of `copied`, `not_needed`, `failed`
- `warnings[]` when applicable: include `ready_sibling_backfill_failed` when backfill fails but publish proceeds using the public asset

#### Scenario: Reused public asset metadata

- **WHEN** an existing public asset is reused
- **THEN** campaign metadata records `public_asset_handoff_status` `reused` and `public_asset_source` `existing_public_asset`

#### Scenario: Adopted sibling metadata

- **WHEN** a ready sibling PNG is copied to public assets
- **THEN** campaign metadata records `public_asset_handoff_status` `copied` and `public_asset_source` `ready_sibling_png`

### Requirement: Blog image public asset handoff tests

The repository SHALL include automated tests covering:

- public asset exists, ready sibling missing, backfill succeeds without ComfyUI
- public asset exists, ready sibling missing, backfill fails but publish can still proceed when the public asset is sufficient
- ready sibling exists, public asset missing, copy/adopt succeeds without ComfyUI
- ready sibling exists, public asset missing, copy/adopt failure returns stable `blog_image_public_asset_handoff_failed`
- ComfyUI generates image → handoff to public assets succeeds
- retry after local sibling PNG exists → no duplicate ComfyUI call
- retry after public asset already exists → no duplicate ComfyUI call
- post `02-deferring-is-not-avoiding-it-can-be-architecture` failure scenario

Tests MUST use injectable fakes or temporary directories and MUST NOT require a live ComfyUI server or root privileges.

#### Scenario: Public asset reuse with successful backfill

- **WHEN** tests simulate readable public asset, canonical front matter, missing ready sibling, and writable `blog-posts/ready/`
- **THEN** tests verify ready sibling is backfilled, ComfyUI client is not called, and publish image step succeeds

#### Scenario: Public asset reuse with failed backfill but safe publish

- **WHEN** tests simulate readable public asset, canonical front matter, missing ready sibling, and unwritable `blog-posts/ready/` (or equivalent backfill failure), and downstream publish can proceed using the public asset
- **THEN** tests verify ComfyUI client is not called, a non-blocking backfill warning is recorded, `blog_image_public_asset_handoff_failed` is not returned, and publish may continue

#### Scenario: Post 02 regression test

- **WHEN** tests simulate the post `02` ready pair with canonical front matter, existing sibling PNG, and missing public asset
- **THEN** tests verify public asset is created, ComfyUI client is not called, and publish image step succeeds

#### Scenario: Ready sibling adoption handoff failure

- **WHEN** tests simulate existing ready sibling PNG, missing public asset, and unwritable public `assets/images/` directory
- **THEN** tests verify ComfyUI client is not called and `blog_image_public_asset_handoff_failed` is returned

### Requirement: Operator documentation for automatic handoff

Operator documentation SHALL state that:

- manual image copy into the public blog repo is not required for normal Flow A publish
- an existing readable public asset at `assets/images/<public_slug>.png` is authoritative for Jekyll and satisfies the public image prerequisite without ComfyUI
- generated or pre-existing local ready PNGs are adopted automatically into `assets/images/<public_slug>.png` when the public asset is missing
- missing ready sibling PNGs may be backfilled from the public asset for compatibility; backfill failures are warnings when publish can still proceed using the public asset
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

