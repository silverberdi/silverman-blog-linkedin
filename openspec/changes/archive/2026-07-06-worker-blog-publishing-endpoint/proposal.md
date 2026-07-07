## Why

The active Flow A umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` sequences automatic blog publication only after editorial validation and lifecycle metadata are in place. Child changes 1–3 delivered the editorial canon, campaign lifecycle foundation, and `validate_ready_post()` gate; child slice 4 is the first worker HTTP operation that turns a validated ready post into a publish-confirmed public blog URL. Without this endpoint, n8n cannot orchestrate Flow A blog publish over HTTP (ADR-0001) and downstream LinkedIn derivative generation lacks a confirmed `source_public_url`.

## Goals

- Expose `POST /publish-blog-post` as the worker HTTP entry point for Flow A blog publishing.
- Run preflight inspection, short-circuit idempotent `already_published` re-runs before validation, then call `validate_ready_post()` for non-published campaigns before any publish side effect.
- Transition campaign metadata through `validated` → `blog_publish_pending` → `blog_published` using `campaign_lifecycle.py`.
- Publish to the local public GitHub Pages repository checkout via `github_pages_publish.py` (file writes only; no git commit/push).
- Enforce blog publish idempotency and duplicate prevention using lifecycle idempotency keys and bridge non-overwrite rules.
- Return structured JSON suitable for n8n branching (`status`, campaign fields, `source_public_url`, `validation`, `blog_publish`, errors/warnings).
- Add `blog_publish_flow.py` service module and comprehensive tests.

## Non-Goals

- Generating LinkedIn derivative packages or scheduling LinkedIn distribution.
- Modifying n8n workflow JSON.
- Physically moving source files between `ready`, `processed`, or `error` folders.
- Git commit or git push of the public GitHub Pages repository from the worker.
- Implementing Flow B automatic publish paths.
- Archiving the umbrella or this child change.
- Committing or pushing repository changes.

## What Changes

- Add child OpenSpec change `worker-blog-publishing-endpoint` under active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 4).
- Introduce capability spec `worker-blog-publishing-endpoint` covering HTTP contract, publish flow, campaign state transitions, idempotency, stable error codes, and response shape.
- Add worker service module `src/silverman_blog_linkedin/blog_publish_flow.py` orchestrating validation, lifecycle transitions, and the GitHub Pages bridge.
- Add `POST /publish-blog-post` FastAPI route in `main.py` with API-key auth consistent with existing worker endpoints.
- Reuse `validate_ready_post()` from `ready_post_validation.py`, lifecycle helpers from `campaign_lifecycle.py`, and the existing `github_pages_publish.py` bridge (`build_plan`, `apply_plan`, `run_publish` — inspect actual signatures during apply; do not invent bridge APIs).
- Add `tests/test_blog_publish_flow.py` and HTTP endpoint tests.
- Update umbrella roadmap progress to mark slice 4 as proposed/active.

No LinkedIn draft generation, n8n exports, source file moves, or git operations are included.

## Capabilities

### New Capabilities

- `worker-blog-publishing-endpoint`: Flow A worker HTTP blog publish operation—ready-post validation gate, campaign lifecycle transitions (`validated` → `blog_publish_pending` → `blog_published`), GitHub Pages bridge integration, idempotent `already_published` handling, stable error codes, structured `BlogPublishResult` response, and API-key-protected `POST /publish-blog-post`.

### Modified Capabilities

<!-- No existing main spec requirements change. This child consumes ready-post-editorial-validation, flow-a-lifecycle, and github-pages-blog-publishing without modifying those canonical specs. -->

## Impact

- **Umbrella reference**: This change MUST cite `flow-a-automatic-blog-linkedin-publishing-roadmap` for Flow A policy, child sequencing, lifecycle, and publication strategy. The umbrella remains active.
- **Validation reference**: Canonical spec `openspec/specs/ready-post-editorial-validation/spec.md` and worker module `src/silverman_blog_linkedin/ready_post_validation.py`.
- **Lifecycle reference**: Canonical spec `openspec/specs/flow-a-lifecycle/spec.md` and worker module `src/silverman_blog_linkedin/campaign_lifecycle.py`.
- **Publishing bridge reference**: Canonical spec `openspec/specs/github-pages-blog-publishing/spec.md` and worker module `src/silverman_blog_linkedin/github_pages_publish.py`.
- **Editorial canon reference**: Policy alignment via canonical spec `openspec/specs/editorial-canon/spec.md` and artifact `content-strategy/silverman-editorial-system.md`.
- **OpenSpec**: New change directory `openspec/changes/worker-blog-publishing-endpoint/` with proposal, design, tasks, and `specs/worker-blog-publishing-endpoint/spec.md`.
- **Worker API**: New authenticated `POST /publish-blog-post` endpoint; new `blog_publish_flow.py` service module.
- **Configuration**: Reuses `SILVERMAN_BLOG_LINKEDIN_BASE_PATH`, `SILVERMAN_GITHUB_PAGES_REPO_PATH`, and site URL default `https://silverman.pro`.
- **Tests**: New `tests/test_blog_publish_flow.py`; endpoint tests in existing FastAPI test suite.
- **Future children**: `linkedin-derivative-package-generation` and `n8n-flow-a-blog-publish-orchestration` depend on publish-confirmed `source_public_url` from this slice.
