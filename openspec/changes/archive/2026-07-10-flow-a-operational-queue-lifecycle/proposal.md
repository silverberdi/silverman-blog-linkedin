## Why

Flow A is deployed and validated, but its source lifecycle (`blog-posts/ready/` → `blog-posts/processed/`) is too coarse for reliable operations. Operators and future automation cannot distinguish operator-approved input, worker-accepted work, active execution, successful consumption, recoverable failures, and stale attempts. The worker needs a formal operational queue lifecycle without breaking the established Flow A happy path or redesigning calendar control, LinkedIn publication, or n8n integration.

## Goals

- Introduce a filesystem-backed operational lifecycle: `ready` (inbox) → `queued` → logical `processing` → `processed` or `error`.
- Preserve `blog-posts/ready/` as the operator-approved inbox; add physical `blog-posts/queued/`.
- Define queue acceptance, execution ownership, stale detection, error classification, retry/idempotency, and metadata evolution.
- Keep editorial-calendar-driven intake; calendar.json remains read-only.
- Maintain backward compatibility with existing campaigns, `flow_a_complete`, and downstream idempotency contracts.
- Specify automated test coverage requirements without implementing tests in this phase.

## Non-Goals

- Production code implementation during `/opsx:propose`.
- Operations console or dashboard UI; polished retry/requeue UI.
- Real LinkedIn publication, LinkedIn Posts API, media upload, or enabling `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- n8n activation, cron, systemd timers, or background workers beyond the existing execution model.
- Public blog repository modifications; automatic Git commit/push; GitHub credential changes.
- `calendar.json` modification; calendar-model redesign; new scheduling model.
- Database-backed queueing; Redis; message brokers; generalized distributed queue infrastructure.
- Renaming `blog-posts/ready/` to `inbox/`.
- Source data migration during proposal phase.
- Deployment, server state changes, or archived OpenSpec change modifications.

## What Changes

- Add capability `flow-a-operational-queue-lifecycle` defining canonical operational states, transitions, acceptance policy, ownership/claim model, stale recovery, error-folder policy, filesystem safety, and compatibility rules.
- Add physical folder `blog-posts/queued/` to expected editorial layout; sources move `ready/` → `queued/` on queue acceptance, then `queued/` → `processed/` or `error/` on terminal outcomes.
- Treat `processing` as a logical execution dimension on campaign `source_file_status` (not a physical folder).
- Insert an explicit queue-acceptance stage before Flow A execution in the editorial calendar connector (same HTTP command; two internal stages).
- Extend campaign metadata with queue/error path fields, execution attempt fields, transition timestamps, failure categories, and recovery classifications.
- Apply deterministic intake-failure movement policy: no calendar match leaves sources in `ready/`; unsafe paths are never moved; calendar-selected deterministic validation failures may move to `error/` before queue acceptance; post-acceptance editorial validation failures move queued sources to `error/`.
- Separate deterministic failure handling before and after durable external side effects (blog publish, derivative generation, scheduling): pre-side-effect failures may move to `error/`; post-side-effect failures normally remain in `queued/` with `repair_required`.
- Preserve editorial filename identity during `ready/` → `queued/` movement; queued collision rejects conflicting destinations rather than suffix-renaming.
- Use coordinated (non-transactional) Markdown+image movement with partial-move recording.
- Use one canonical move/metadata persistence protocol for queue acceptance.
- Use one canonical stale-detection clock based on `last_progress_at` and `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`.
- Normalize recovery classification vocabulary to a single canonical enum.
- Filter macOS artifacts (`.DS_Store`, `._*`, and hidden dotfiles) from queue candidacy across scanners.
- Update delta specs for `flow-a-lifecycle`, `flow-a-source-lifecycle-completion`, `editorial-calendar-flow-a-execution-connector`, `ready-blog-post-processing`, `ready-post-editorial-validation`, `worker-blog-publishing-endpoint`, `linkedin-derivative-package-generation`, and `linkedin-distribution-scheduling-model`.
- Define requeue-from-error as an internal service contract (implementation in this change; no UI).

Worker file I/O and lifecycle transitions remain owned by the HTTP worker (ADR-0001), not n8n Execute Command.

## Capabilities

### New Capabilities

- `flow-a-operational-queue-lifecycle`: Canonical operational source lifecycle for Flow A — physical `ready`/`queued`/`processed`/`error` folders, logical `processing` execution state, transition table, queue acceptance, claim/stale detection, error classification, retry/idempotency, filesystem safety, hidden-artifact filtering, compatibility, and operator-console derivable state fields.

### Modified Capabilities

- `flow-a-lifecycle`: Separate physical `source_file_status.location` from logical `execution_state`; add `queued` location; extend metadata fields for queue/error paths, attempts, transitions, failures, and recovery classifications; preserve existing campaign `state` machine.
- `flow-a-source-lifecycle-completion`: Terminal move source changes from `blog-posts/ready/` to `blog-posts/queued/` → `blog-posts/processed/`; terminal completion sets `execution_state=idle`; extend path traceability for queued paths.
- `editorial-calendar-flow-a-execution-connector`: Add queue-acceptance stage before publish; handle already-queued campaigns without requiring ready file; dry-run reports acceptance decisions without physical moves or claims; real execution chains queue → processing → existing Flow A steps; claim release ownership clarified.
- `ready-blog-post-processing`: Ignore hidden macOS artifacts; document `queued/` in folder semantics; scanner remains read-only for `queued/`.
- `ready-post-editorial-validation`: Accept validation against sources in `blog-posts/queued/` during processing; intake validation against `ready/` at acceptance boundary.
- `worker-blog-publishing-endpoint`: Resolve active source path from `queued_source_relative_path` when location is `queued` or `processing`; preserve processed-path idempotency for post-schedule campaigns.
- `linkedin-derivative-package-generation`: Resolve source from queued or processed paths per `source_file_status.location`.
- `linkedin-distribution-scheduling-model`: Campaign resolution accepts queued and processed source locations without requiring `ready/` copy.

## Impact

- **Queue lifecycle and source moves**: Responsibilities for queue acceptance, coordinated Markdown+image moves, error moves, and requeue — likely extending or colocated with existing Flow A lifecycle modules (`flow_a_source_lifecycle.py`, `campaign_lifecycle.py`). New modules may be introduced during apply only when justified by cohesion and current repository structure.
- **Lifecycle metadata**: `campaign_lifecycle.py` — new `source_file_status` fields, `SOURCE_LOCATION_QUEUED`, execution helpers, canonical recovery classification enum.
- **Paths**: `paths.py` — add `blog-posts/queued` to `EXPECTED_FOLDERS`.
- **Flow A connector**: `editorial_calendar_flow_a_execute.py` — queue acceptance before publish; already-queued campaign resolution; processing claim around execution; idempotent defensive release only on non-terminal exits.
- **Source lifecycle**: `flow_a_source_lifecycle.py` — move from `queued/` not `ready/`; terminal completion sets `location=processed` and `execution_state=idle`.
- **Scanning**: `ready_scan.py` (and shared artifact filter helper) — hidden file filtering.
- **Downstream services**: `blog_publish_flow.py`, `linkedin_package_flow.py`, `linkedin_distribution_schedule.py`, `campaign_lifecycle.resolve_campaign_source_paths` — queued path resolution.
- **Configuration**: `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` — fail-fast positive integer validation (minimum 60 seconds; default 3600).
- **Tests**: New lifecycle/queue test modules; extend connector, source lifecycle, and regression suites per tasks.
- **Documentation**: Workflow docs for `ready/` vs `queued/` vs `processed/` vs `error/`, recovery classifications, and queue acceptance protocol.
- **Operations**: Deployments must create `blog-posts/queued/`; no automatic migration of existing `ready/` sources.
