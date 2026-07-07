## Why

The active Flow A umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` sequences LinkedIn distribution scheduling only after derivative package generation is complete. Completed child slice 5 (`linkedin-derivative-package-generation`) delivers multi-variant artifacts under `linkedin-posts/generated/<campaign_id>/` and campaign metadata (`linkedin_package`, `variants[]`) with lifecycle state `derivatives_generated`. Without slice 6, n8n cannot orchestrate distribution scheduling over HTTP (ADR-0001), downstream publication integration lacks per-variant `scheduled_at_utc` and `publish_state` metadata, and the editorial canon requirement to stagger variants (≥3 calendar days apart, never simultaneous) cannot be enforced in campaign metadata.

## Goals

- Schedule Flow A LinkedIn derivative variants after package generation, applying editorial distribution strategy defaults.
- Consume `campaign.linkedin_package`, `campaign.variants[]`, and on-disk artifacts at `linkedin-posts/generated/<campaign_id>/<variant_id>.md`.
- Persist per-variant scheduling metadata in campaign JSON (paths, hashes, `scheduled_at_utc`, `publish_state` `pending`, idempotency keys — no generated body text).
- Transition campaign lifecycle: `derivatives_generated` → `distribution_scheduled`.
- Expose `POST /schedule-linkedin-distribution` returning structured JSON for n8n branching.
- Implement idempotent re-runs when scheduling intent proof matches; fail safely on metadata mismatch.
- Default strategy MUST stagger variants (not simultaneous), aligned with editorial canon (`#linkedin-distribution-strategy`).
- Add comprehensive tests in `tests/test_linkedin_distribution_scheduling.py`.

## Non-Goals

- LinkedIn API publication or changing `publish_state` beyond `pending`.
- Modifying n8n workflow JSON.
- Moving source blog files between editorial folders.
- Regenerating derivative package content.
- Flow B scheduling.
- Git commit or git push.
- Archiving the umbrella or this child change.

## What Changes

- Add child OpenSpec change `linkedin-distribution-scheduling-model` under active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 6).
- Introduce capability spec `linkedin-distribution-scheduling-model` covering HTTP contract, scheduling flow, campaign state transitions, per-variant schedule metadata, idempotency, stable error codes, and response shape.
- Add worker service module `src/silverman_blog_linkedin/linkedin_distribution_schedule.py` orchestrating campaign reads, eligibility checks, artifact verification, schedule computation, and campaign metadata updates.
- Add `POST /schedule-linkedin-distribution` FastAPI route in `main.py` with API-key auth (`Depends(require_api_key)`) consistent with existing worker endpoints.
- Integrate `campaign_lifecycle.py` for state transitions and metadata sanitization.
- Add `tests/test_linkedin_distribution_scheduling.py` and HTTP endpoint tests.
- Update umbrella roadmap progress to mark slice 6 as proposed/active.

No n8n exports, LinkedIn API calls, source file moves, or git operations are included.

## Capabilities

### New Capabilities

- `linkedin-distribution-scheduling-model`: Flow A worker LinkedIn distribution scheduling—campaign eligibility (`derivatives_generated`, package metadata present), lifecycle transition (`distribution_scheduled`), per-variant staggered `scheduled_at_utc` and `publish_state` `pending`, artifact hash verification, idempotent re-runs, stable error codes, structured `LinkedInDistributionScheduleResult` response, and API-key-protected `POST /schedule-linkedin-distribution`.

### Modified Capabilities

<!-- No existing main spec requirements change. This child consumes editorial-canon, flow-a-lifecycle, and linkedin-derivative-package-generation without modifying those canonical specs. -->

## Impact

- **Umbrella reference**: This change MUST cite `flow-a-automatic-blog-linkedin-publishing-roadmap` for Flow A policy, child sequencing, lifecycle, and distribution strategy. The umbrella remains active.
- **Editorial canon reference**: Canonical spec `openspec/specs/editorial-canon/spec.md` and artifact `content-strategy/silverman-editorial-system.md` for cadence defaults (≥3-day spacing, audience sequencing, anti-simultaneous publish).
- **Lifecycle reference**: Canonical spec `openspec/specs/flow-a-lifecycle/spec.md` and worker module `src/silverman_blog_linkedin/campaign_lifecycle.py`.
- **Package generation reference**: Canonical spec `openspec/specs/linkedin-derivative-package-generation/spec.md` and worker module `src/silverman_blog_linkedin/linkedin_package_flow.py` for `linkedin_package`, `variants[]`, and artifact paths/hashes.
- **OpenSpec**: New change directory `openspec/changes/linkedin-distribution-scheduling-model/` with proposal, design, tasks, and `specs/linkedin-distribution-scheduling-model/spec.md`.
- **Worker API**: New authenticated `POST /schedule-linkedin-distribution` endpoint; new `linkedin_distribution_schedule.py` service module.
- **Campaign metadata**: Extended with `linkedin_distribution` object and per-variant scheduling fields (`scheduled_at_utc`, `publish_state`, schedule idempotency keys).
- **Tests**: New `tests/test_linkedin_distribution_scheduling.py`; endpoint tests in existing FastAPI test suite.
- **Future children**: `n8n-flow-a-blog-publish-orchestration` depends on scheduling metadata from this slice; `linkedin-publication-integration` reads `publish_state` and `scheduled_at_utc` when API publish is implemented.
