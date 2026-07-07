## Why

The active Flow A umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` defines automatic publication only after editorial validation passes, but the worker has no validation gate for posts in `blog-posts/ready/`. Child changes 1–2 established the editorial canon and lifecycle metadata foundation; without slice 3, n8n and future publish endpoints cannot decide whether a ready post is structurally and editorially eligible to continue Flow A.

## Goals

- Define and implement automated validation for ready blog posts before Flow A automatic publication.
- Validate source file location, naming, companion PNG image, YAML frontmatter, body structure, and basic editorial/canon rules suitable for Flow A.
- Create or update campaign metadata via `campaign_lifecycle.py`, recording validation success (`ready` → `validated`) or failure (`ready` → `validation_failed`) with machine-readable error codes and non-blocking warnings.
- Define idempotent re-validation when campaign is already `validated` with unchanged `source_content_sha256`; block with `campaign_content_hash_changed` or `campaign_invalid_existing_state` when content or lifecycle state forbids overwrite.
- Return a structured validation result for n8n branching and future HTTP endpoints.
- Add worker module `ready_post_validation.py` and unit tests.

## Non-Goals

- Publishing to GitHub Pages or implementing `POST /publish-blog-post`.
- Implementing `POST /generate-linkedin-package`, scheduling, LinkedIn API publishing, or Flow B.
- Modifying n8n workflow JSON.
- Physically moving files between `ready`, `processed`, or `error` folders (metadata-only error marking in this child).
- Runtime parsing of the full editorial canon artifact (policy is encoded in spec and module rules).
- Archiving the umbrella or this child change.
- Committing or pushing repository changes.

## What Changes

- Add child OpenSpec change `ready-post-editorial-validation` under active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 3).
- Introduce capability spec `ready-post-editorial-validation` covering file/slug/image checks, frontmatter rules, content blockers vs anti-AI warnings, campaign metadata transitions, stable error codes, and structured validation result shape.
- Add worker module `src/silverman_blog_linkedin/ready_post_validation.py` as a pure service (no HTTP endpoint in this child).
- Reuse `campaign_lifecycle.py` for campaign ID, content hash, metadata writes, and state transitions; reuse slug/date/URL helpers from `github_pages_publish.py` and existing file/frontmatter utilities where present.
- Add `tests/test_ready_post_validation.py` covering pass, blocking failures, warnings-only anti-AI cases, and metadata transitions.

No HTTP routes, n8n exports, file moves, or GitHub publish behavior are included.

## Capabilities

### New Capabilities

- `ready-post-editorial-validation`: Automated validation gate for Flow A ready blog posts—file location and extension, source/public slug derivation, PNG image presence, required frontmatter and values, blocking content checks, non-blocking anti-AI editorial warnings, campaign metadata create/update with lifecycle transitions, stable error codes, and machine-readable `ReadyPostValidationResult`.

### Modified Capabilities

<!-- No existing main spec requirements change. Validation consumes editorial-canon policy, flow-a-lifecycle metadata, and github-pages-blog-publishing slug rules without modifying those specs. -->

## Impact

- **Umbrella reference**: This change MUST cite `flow-a-automatic-blog-linkedin-publishing-roadmap` for Flow A policy, child sequencing, and publication strategy. The umbrella remains active.
- **Editorial canon reference**: Policy alignment via canonical spec `openspec/specs/editorial-canon/spec.md` and artifact `content-strategy/silverman-editorial-system.md`.
- **Lifecycle reference**: Campaign metadata via canonical spec `openspec/specs/flow-a-lifecycle/spec.md` and worker module `src/silverman_blog_linkedin/campaign_lifecycle.py`.
- **Slug/URL reference**: Public slug derivation and URL readiness aligned with `openspec/specs/github-pages-blog-publishing/spec.md` and `github_pages_publish.py`.
- **OpenSpec**: New change directory `openspec/changes/ready-post-editorial-validation/` with proposal, design, tasks, and `specs/ready-post-editorial-validation/spec.md`.
- **Worker**: New validation module; no new HTTP endpoints until future child `worker-blog-publishing-endpoint` or a dedicated validate endpoint child.
- **Tests**: New `tests/test_ready_post_validation.py`.
- **Future children**: `worker-blog-publishing-endpoint`, LinkedIn package generation, and n8n Flow A orchestration will call validation before publish.
