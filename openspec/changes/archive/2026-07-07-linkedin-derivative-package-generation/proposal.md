## Why

The active Flow A umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` sequences LinkedIn derivative generation only after blog publication is confirmed and a publish-confirmed `source_public_url` is recorded in campaign metadata. Completed child slices 1–4 delivered editorial canon, campaign lifecycle, ready-post validation, and `POST /publish-blog-post`; slice 5 is the first worker operation that turns a `blog_published` campaign into a coordinated multi-variant LinkedIn derivative package. Without this capability, n8n cannot orchestrate Flow A package generation over HTTP (ADR-0001), downstream scheduling lacks variant artifacts, and the existing `POST /generate-linkedin-draft` endpoint remains limited to one variant per call without campaign lifecycle integration.

## Goals

- Generate a complete LinkedIn derivative package for a Flow A campaign after blog publication is confirmed.
- Require campaign state `blog_published` and a non-null publish-confirmed `source_public_url`.
- Generate all canonical editorial variants by default (`executive-recruiter`, `technical-architect`, `engineering-leadership`, `short-provocative`) unless the request narrows the variant list.
- Persist each variant as a separate artifact file with per-variant metadata; store paths/hashes only in campaign metadata (no full bodies).
- Transition campaign lifecycle: `blog_published` → `derivatives_pending` → `derivatives_generated`.
- Expose `POST /generate-linkedin-package` returning structured JSON for n8n branching.
- Implement idempotent re-runs when package idempotency proof matches; fail safely when orphan files exist without metadata proof.
- Reuse existing prompt, DeepSeek client, and draft-writing patterns without duplicating generation logic.
- Add comprehensive tests in `tests/test_linkedin_package_generation.py`.

## Non-Goals

- Scheduling LinkedIn distribution or writing `schedule_at` / `publish_state` scheduling metadata (child slice 6 `linkedin-distribution-scheduling-model`).
- Modifying n8n workflow JSON.
- Implementing LinkedIn API publication.
- Implementing Flow B automatic package generation.
- Physically moving source blog files between editorial folders.
- Git commit or git push.
- Archiving the umbrella or this child change.
- Committing or pushing repository changes.

## What Changes

- Add child OpenSpec change `linkedin-derivative-package-generation` under active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 5).
- Introduce capability spec `linkedin-derivative-package-generation` covering HTTP contract, package generation flow, campaign state transitions, artifact layout, idempotency, stable error codes, and response shape.
- Add worker service module `src/silverman_blog_linkedin/linkedin_package_flow.py` orchestrating campaign reads, lifecycle transitions, multi-variant generation, artifact writes, and campaign metadata updates.
- Add `POST /generate-linkedin-package` FastAPI route in `main.py` with API-key auth consistent with existing worker endpoints.
- Reuse `linkedin_prompt.build_chat_messages`, `deepseek_client.generate_linkedin_draft_content`, and draft-writing utilities; extend or wrap draft writer for deterministic `linkedin-posts/generated/<campaign_id>/<variant_id>.md` paths without breaking existing `POST /generate-linkedin-draft` behavior.
- Integrate `campaign_lifecycle.py` for state transitions, derivative idempotency keys, variant validation, and metadata sanitization.
- Add `tests/test_linkedin_package_generation.py` and HTTP endpoint tests with injected/mocked generation for determinism.
- Update umbrella roadmap progress to mark slice 5 as proposed/active.

No n8n exports, scheduling metadata, LinkedIn API calls, source file moves, or git operations are included.

## Capabilities

### New Capabilities

- `linkedin-derivative-package-generation`: Flow A worker multi-variant LinkedIn package generation—campaign eligibility (`blog_published`, confirmed URL), lifecycle transitions (`derivatives_pending` → `derivatives_generated`), per-variant artifact persistence under `linkedin-posts/generated/`, package metadata in campaign JSON, idempotent re-runs, stable error codes, structured `LinkedInPackageResult` response, and API-key-protected `POST /generate-linkedin-package`.

### Modified Capabilities

<!-- No existing main spec requirements change. This child consumes editorial-canon, flow-a-lifecycle, worker-blog-publishing-endpoint, and deepseek-linkedin-draft-generation without modifying those canonical specs. -->

## Impact

- **Umbrella reference**: This change MUST cite `flow-a-automatic-blog-linkedin-publishing-roadmap` for Flow A policy, child sequencing, lifecycle, and publication strategy. The umbrella remains active.
- **Editorial canon reference**: Canonical spec `openspec/specs/editorial-canon/spec.md` and artifact `content-strategy/silverman-editorial-system.md` for canonical variant IDs, audience lenses, and CTA rules.
- **Lifecycle reference**: Canonical spec `openspec/specs/flow-a-lifecycle/spec.md` and worker module `src/silverman_blog_linkedin/campaign_lifecycle.py`.
- **Blog publish reference**: Canonical spec `openspec/specs/worker-blog-publishing-endpoint/spec.md` and worker module `src/silverman_blog_linkedin/blog_publish_flow.py` for publish-confirmed `source_public_url` prerequisite.
- **Validation reference**: Canonical spec `openspec/specs/ready-post-editorial-validation/spec.md` (indirect; campaign must have passed validation before publish).
- **Single-draft generation reference**: Canonical spec `openspec/specs/deepseek-linkedin-draft-generation/spec.md` and modules `linkedin_prompt.py`, `deepseek_client.py`, `draft_writer.py`, `run_metadata.py`.
- **OpenSpec**: New change directory `openspec/changes/linkedin-derivative-package-generation/` with proposal, design, tasks, and `specs/linkedin-derivative-package-generation/spec.md`.
- **Worker API**: New authenticated `POST /generate-linkedin-package` endpoint; new `linkedin_package_flow.py` service module.
- **Editorial folders**: New usage of `linkedin-posts/generated/<campaign_id>/`; campaign metadata extended with `linkedin_package` object and `variants[]` entries (paths/hashes only).
- **Configuration**: Reuses `SILVERMAN_BLOG_LINKEDIN_BASE_PATH`, DeepSeek env vars, and campaign `source_public_url`.
- **Tests**: New `tests/test_linkedin_package_generation.py`; endpoint tests in existing FastAPI test suite.
- **Future children**: `linkedin-distribution-scheduling-model` and `n8n-flow-a-blog-publish-orchestration` depend on package artifacts and metadata from this slice.
