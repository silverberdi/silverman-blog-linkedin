## Why

The active Flow A umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` defines lifecycle states, idempotency expectations, and campaign metadata as foundational requirements before validation, blog publish, LinkedIn package generation, scheduling, and n8n orchestration—but no shared schema, state machine, or duplicate-prevention keys exist in the worker today. Without this child change, each future endpoint would invent its own metadata shape and re-run behavior, risking duplicate blog publishes, duplicate LinkedIn drafts, and untraceable Flow A campaigns.

## Goals

- Define the canonical `metadata/campaigns/<campaign-id>.json` schema for Flow A lifecycle tracking.
- Specify lifecycle state transitions, state history, and machine-readable error recording.
- Define idempotency keys for blog publication intent, LinkedIn derivative variants, and future LinkedIn publication schedule slots using canonical variant IDs from the editorial canon (`executive-recruiter`, `technical-architect`, `engineering-leadership`, `short-provocative`).
- Document how source files are marked processed or error (metadata-first; defer physical file moves to orchestration children).
- Ensure campaign metadata excludes full content bodies (`markdown_content`, `generated_draft_content`).
- Implement worker lifecycle metadata models/helpers and tests when project structure allows.
- Reference umbrella policy, canonical spec `editorial-canon`, and artifact `content-strategy/silverman-editorial-system.md` for Flow A vs Flow B boundaries.

## Non-Goals

- Implementing `POST /validate-ready-post`, `POST /publish-blog-post`, `POST /generate-linkedin-package`, or `POST /schedule-linkedin-package`.
- Modifying n8n workflow JSON or implementing LinkedIn API publishing.
- Implementing Flow B content generation or approval workflow (reserve `flow_b` value only).
- Runtime loading or parsing of editorial canon content (deferred to validation/generation children).
- Archiving the umbrella or this child change.
- Committing or pushing repository changes.

## What Changes

- Add child OpenSpec change `flow-a-lifecycle-and-duplicate-prevention` under active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 2).
- Introduce capability spec `flow-a-lifecycle` with campaign metadata schema, state machine, idempotency keys, canonical variant ID rules (aligned with `content-strategy/silverman-editorial-system.md`), and metadata body exclusion rules.
- Add worker module `campaign_lifecycle.py` (or equivalent) with campaign ID generation, metadata builders, state transition helpers, idempotency key functions, and JSON persistence aligned with existing `run_metadata.py` patterns.
- Add unit tests for campaign ID format, metadata creation, state transitions, invalid transition rejection, idempotency keys, Flow B guardrails, and metadata serialization excluding content bodies.
- Document file-move vs metadata-only marking policy for future validation/orchestration children.

No HTTP endpoints, n8n exports, editorial canon parsing, or LinkedIn API integration are included.

## Capabilities

### New Capabilities

- `flow-a-lifecycle`: Campaign metadata schema at `metadata/campaigns/<campaign-id>.json`, Flow A lifecycle state machine, state history with actor/reason/error codes, idempotency keys for blog publish / derivative variants / LinkedIn schedule slots (using canonical hyphenated variant IDs from editorial canon), source file marking policy, and metadata body exclusion rules.

### Modified Capabilities

<!-- No existing main spec requirements change. Future children will consume flow-a-lifecycle without modifying editorial-canon or github-pages-blog-publishing in this change. -->

## Impact

- **Umbrella reference**: This change MUST cite `flow-a-automatic-blog-linkedin-publishing-roadmap` for Flow A policy, lifecycle, child sequencing, and publication strategy. The umbrella remains active.
- **Editorial canon reference**: Policy alignment via canonical spec `openspec/specs/editorial-canon/spec.md` and artifact `content-strategy/silverman-editorial-system.md`; no runtime canon loading in this change.
- **OpenSpec**: New change directory `openspec/changes/flow-a-lifecycle-and-duplicate-prevention/` with proposal, design, tasks, and `specs/flow-a-lifecycle/spec.md`.
- **Worker**: New lifecycle metadata module under `src/silverman_blog_linkedin/`; `metadata/campaigns/` already listed in `paths.py` expected folders.
- **Tests**: New `tests/test_campaign_lifecycle.py` (or equivalent).
- **Future children** (not implemented here): `ready-post-editorial-validation`, `worker-blog-publishing-endpoint`, `linkedin-derivative-package-generation`, `linkedin-distribution-scheduling-model`, `n8n-flow-a-blog-publish-orchestration` will read/write campaign metadata using this schema.
- **n8n**: No workflow changes.
- **HTTP API**: No new endpoints; existing endpoints unchanged.
