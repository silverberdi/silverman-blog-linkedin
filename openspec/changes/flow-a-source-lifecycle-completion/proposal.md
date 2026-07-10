## Why

Flow A successfully publishes blogs, generates LinkedIn packages, and schedules distribution, but leaves source Markdown and companion PNG files in `blog-posts/ready/`. That contradicts folder semantics (`ready/` = pending operator input) and confuses operators who expect consumed sources in `blog-posts/processed/`. Prior lifecycle work (`flow-a-lifecycle`) deferred physical moves to a later orchestration child; image handoff, publish-date safety, and article preview are now complete, so this is the right slice to close the source lifecycle gap without activating LinkedIn publication or n8n.

## Goals

- After successful Flow A completion (blog publish → LinkedIn package → distribution scheduling), physically move source `.md` and companion image (when present) from `blog-posts/ready/` to `blog-posts/processed/`.
- Record original and processed source/image paths in campaign metadata with a `source_processed` lifecycle marker.
- Preserve idempotency: completed campaigns (`distribution_scheduled` or later) re-run without requiring the source file to remain in `ready/`.
- Do not move files on Flow A failure before successful scheduling.
- Surface a specific repairable error when post-scheduling source move fails after upstream steps succeeded.
- Add automated tests and operator documentation for folder semantics and traceability via campaign metadata.

## Non-Goals

- Dashboard/console, LinkedIn publication, LinkedIn API/media upload, n8n activation, cron/systemd timers.
- Modifying `calendar.json`, the public blog repo, or LinkedIn package text.
- Republishing blogs or altering public blog content on lifecycle completion.
- Manual operator file moves as the expected remediation path.
- Git commit/push as part of this change.

## What Changes

- Add OpenSpec change `flow-a-source-lifecycle-completion` implementing physical source lifecycle completion for Flow A.
- Add capability spec `flow-a-source-lifecycle-completion` covering move semantics, metadata path fields, collision handling, idempotency, and failure states.
- Add worker module (for example `flow_a_source_lifecycle.py`) with `complete_flow_a_source_lifecycle()` entry point invoked after successful distribution scheduling.
- Extend campaign metadata with `original_source_relative_path`, `processed_source_relative_path`, optional image path fields, and `source_file_status` physical-move timestamps.
- Integrate lifecycle completion into `editorial_calendar_flow_a_execute` real execution path (step after `schedule_linkedin_distribution`).
- Extend Flow A downstream services to resolve source files from campaign processed paths when `source_file_status.location` is `processed` and campaign state is `distribution_scheduled` or later (idempotent re-run without `ready/` source).
- Add tests for move success, image move, metadata paths, idempotent re-run, failure no-move, collision handling, and regression coverage for blog publish, image handoff, date safety, and article preview.
- Update operator/workflow docs explaining `ready/` vs `processed/` semantics and campaign metadata traceability.

No HTTP endpoint is required unless apply-time design chooses a thin internal-only hook; n8n and calendar remain unchanged.

## Capabilities

### New Capabilities

- `flow-a-source-lifecycle-completion`: Physical move of Flow A source Markdown and companion image from `ready/` to `processed/` after successful scheduling; campaign metadata path traceability; deterministic collision handling; idempotent skip when already processed; repairable post-success move failure; integration with Flow A execution connector.

### Modified Capabilities

- `flow-a-lifecycle`: Extend campaign metadata required/optional fields for original/processed source and image paths; update source file marking policy from metadata-only to metadata plus physical moves performed by `flow-a-source-lifecycle-completion`; add `source_processed` lifecycle semantics aligned with `source_file_status.location` `processed`.
- `editorial-calendar-flow-a-execution-connector`: After successful `schedule_linkedin_distribution`, invoke source lifecycle completion; report `source_lifecycle` outcome on item results; do not move files on failure or dry-run.
- `worker-blog-publishing-endpoint`: Idempotent publish and campaign resolution MUST succeed when campaign state is `distribution_scheduled` or later and source files reside under `processed/` per campaign metadata (no `blog_publish_source_not_ready` solely because `ready/` copy was moved).
- `linkedin-derivative-package-generation`: Package generation idempotency MUST resolve source Markdown from `processed_source_relative_path` when source was moved and campaign is post-schedule.
- `linkedin-distribution-scheduling-model`: Schedule idempotency and campaign resolution MUST accept campaigns whose source files are in `processed/` without requiring `ready/` paths.

## Impact

- **New module**: `src/silverman_blog_linkedin/flow_a_source_lifecycle.py` — move orchestration, collision suffix, metadata updates, structured result.
- **Lifecycle metadata**: `src/silverman_blog_linkedin/campaign_lifecycle.py` — new path fields, transition to `flow_a_complete` with physical processed marking.
- **Flow A connector**: `src/silverman_blog_linkedin/editorial_calendar_flow_a_execute.py` — invoke completion after schedule success; surface warnings/errors on partial post-schedule move failure.
- **Downstream services**: `blog_publish_flow.py`, `linkedin_package_flow.py`, `linkedin_distribution_schedule.py` — campaign-aware source path resolution for processed sources on idempotent re-run.
- **Tests**: New `tests/test_flow_a_source_lifecycle.py`; extend `tests/test_editorial_calendar_flow_a_execute.py`; regression runs for existing blog/image/package/schedule suites.
- **Documentation**: `docs/workflows/editorial-calendar-flow-a-execution-connector.md`, `docs/workflows/phase-1-target-flow.md` (or adjacent ops doc) — folder semantics and operator guidance.
- **Operations**: After successful Flow A, `ready/` no longer retains consumed posts; operators use `metadata/campaigns/<campaign-id>.json` for traceability instead of manual moves.
