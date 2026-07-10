## Why

The archived change `flow-a-operational-queue-lifecycle` regressed canonical Flow A behavior: approximately 99% of approved posts arrive in `blog-posts/ready/` as Markdown only with a canonical frontmatter `image` path (or missing/empty `image`), and a missing companion PNG must trigger automatic ComfyUI generation before full editorial validation blocks publish. The connector now runs blocking `validate_ready_post()` on the queued source before `publish_blog_post`, failing with `ready_post_image_missing` and never reaching image remediation. Image generation and GitHub Pages source resolution still hardcode `blog-posts/ready/`, so even a corrected connector ordering would not write or resolve images beside queued sources.

A prior proposal pass also incorrectly required canonical non-empty `image` in pre-generation validation (blocking ComfyUI frontmatter patching) and ordered public asset handoff before full validation (durable external side effect inconsistent with deterministic error-move policy).

## Goals

- Restore Markdown-only Flow A execution: queue acceptance → claim → pre-generation validation → editorial image remediation → authorized hash reconciliation → full validation → public asset handoff → publish → package → schedule → lifecycle completion.
- Separate pre-generation deterministic validation from post-remediation full validation (including required PNG and canonical `image`).
- Stage image workflow so public handoff occurs only after full validation succeeds.
- Define authorized frontmatter-patch hash mutation and campaign reconciliation.
- Define explicit connector failure-state and claim-release semantics for image-related failures.
- Refactor image generation and publish source resolution to derive companion paths from the active Markdown folder (`ready/` or `queued/`).
- Preserve direct `publish_blog_post` behavior for legacy or non-connector calls using `blog-posts/ready/`.
- Require integration-oriented automated tests that prove the real Markdown-only connector path without stubbing editorial validation.

## Non-Goals

- Deployment, push, `calendar.json` edits, n8n activation, cron/systemd, or real LinkedIn publication.
- Redesigning queue lifecycle beyond queued-path image compatibility, staged handoff ordering, and validation ordering.
- UI or dashboard work; modifying archived OpenSpec changes.
- Calling real ComfyUI during tests or touching the production public blog repository.

## What Changes

- Introduce two-phase editorial validation: **pre-generation gate** (deterministic Markdown/frontmatter/slug/campaign rules; missing/empty generatable `image` and missing generatable PNG are non-blocking when generation enabled) and **full validation** (canonical `image` and companion PNG required after editorial remediation).
- Remove connector-level blocking `validate_ready_post()` before `publish_blog_post`; delegate validation phases to `publish_blog_post`.
- Split image workflow into **editorial remediation** (detect, generate/adopt/backfill locally, patch frontmatter, no public write) and **public handoff** (after full validation).
- Define authorized source-hash mutation when image remediation patches frontmatter; persist active `source_content_sha256` before full validation/idempotency.
- Refactor missing-image detection and editorial writes to use active source folder (`ready/` or `queued/`).
- Refactor `github_pages_publish.resolve_source_paths` to accept active `ready/`, `queued/`, and `processed/` sources.
- Clarify public-asset reuse: backfill active-folder sibling when needed; full validation always uses local pair; failed backfill blocks publish.
- Ensure lifecycle completion moves generated queued companion PNG with Markdown to `processed/`.
- Define connector claim-release ownership per image failure class.
- Add integration tests proving Markdown-only queue path, staged handoff, hash reconciliation, failure semantics, and lifecycle completion.
- Preserve backward compatibility: existing ready direct-publish, adopted PNG, public backfill, idempotency, and queue lifecycle semantics.

## Capabilities

### New Capabilities

_None — corrective change restoring specified behavior within existing capabilities._

### Modified Capabilities

- `ready-post-editorial-validation`: Split pre-generation and full validation; allow missing/empty `image` in pre-generation when generation eligible; full validation requires canonical `image` and PNG after remediation.
- `comfyui-blog-image-generation`: Staged editorial vs public handoff; active-source-folder companion path; support missing/empty frontmatter remediation.
- `blog-image-public-asset-handoff`: Handoff runs only after full validation; active-folder backfill before validation; no publish bypass without local companion.
- `worker-blog-publishing-endpoint`: Staged publish orchestration; authorized hash reconciliation; handoff deferred until after full validation.
- `editorial-calendar-flow-a-execution-connector`: Remove pre-publish blocking full validation; explicit image failure claim-release matrix.
- `flow-a-automatic-publishing`: Document canonical Markdown-only → remediation → validation → handoff → publish path.
- `github-pages-blog-publishing`: `resolve_source_paths` supports ready, queued, and processed active sources.
- `flow-a-source-lifecycle-completion`: Discover and move generated queued companion PNG; metadata for queued-generated images.
- `flow-a-operational-queue-lifecycle`: Missing/empty generatable image not a queue-acceptance blocker; image failure recovery and claim-release semantics.
- `flow-a-lifecycle`: Authorized image-remediation hash mutation; optional `intake_source_content_sha256` traceability field.

## Impact

- **Validation**: `ready_post_validation.py` — pre-generation gate allowing missing/empty generatable `image`; full validation after remediation.
- **Image generation**: `blog_image_generation.py` — staged editorial remediation vs public handoff; active-folder path derivation.
- **Publish flow**: `blog_publish_flow.py` — orchestrate validation → editorial remediation → hash reconciliation → full validation → handoff → publish.
- **Connector**: `editorial_calendar_flow_a_execute.py` — remove pre-publish validation; apply failure/claim matrix.
- **Lifecycle metadata**: `campaign_lifecycle.py` — authorized hash reconciliation fields.
- **GitHub Pages bridge**: `github_pages_publish.py` — active-folder source resolution.
- **Tests**: Extended integration matrix with hash, handoff-ordering, and claim-release assertions.
- **HTTP boundary**: No new endpoints; worker remains HTTP-only for n8n (ADR-0001).
