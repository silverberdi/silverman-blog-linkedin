# flow-a-source-lifecycle-completion

## Purpose

Flow A source lifecycle completion for the `silverman-blog-linkedin` HTTP worker: physical move of editorial source files from `blog-posts/ready/` to `blog-posts/processed/` after successful distribution scheduling, campaign metadata path traceability, idempotent re-run support, and integration as step 4 in the editorial calendar Flow A execution connector.

## Requirements

### Requirement: Flow A source lifecycle completion entry point

The worker SHALL expose a source lifecycle completion entry point (for example `complete_flow_a_source_lifecycle(base_path, *, campaign_id, source_relative_path=None)`) that physically moves Flow A editorial source files from `blog-posts/queued/` to `blog-posts/processed/` after successful distribution scheduling.

When `queued_source_relative_path` is absent on legacy campaigns, the entry point MAY fall back to `blog-posts/ready/` for backward compatibility only when `source_file_status.location` is not `queued`.

The entry point MUST return a structured `FlowASourceLifecycleResult` (or equivalent dataclass) serializable to JSON with at minimum: `status`, `campaign_id`, `original_source_relative_path`, `processed_source_relative_path`, `original_image_relative_path` (nullable), `processed_image_relative_path` (nullable), `queued_source_relative_path` (nullable), `source_file_status`, `errors[]`, and `warnings[]`.

The entry point MUST atomically/logically finish the terminal operational transition by setting `source_file_status.location=processed` and `execution_state=idle`.

The entry point MUST NOT republish the blog, alter public blog content, alter LinkedIn package text, publish to LinkedIn, enable LinkedIn publication, modify `calendar.json`, or invoke n8n.

#### Scenario: Successful lifecycle completion moves Markdown from queued

- **WHEN** `complete_flow_a_source_lifecycle` is called for a campaign in `distribution_scheduled` with source Markdown at `blog-posts/queued/<name>.md` and scheduling has already succeeded
- **THEN** the Markdown file exists at `blog-posts/processed/<name>.md` (or collision suffix path when required), no duplicate remains in `blog-posts/queued/`, `execution_state` is `idle`, and the result `status` is `completed`

### Requirement: Ready-path HTTP may invoke lifecycle completion

The Python entry point `complete_flow_a_source_lifecycle` MUST remain the sole filesystem lifecycle implementation used by authenticated HTTP ready-path completion (`POST /complete-flow-a-ready-path` per capability `flow-a-ready-path-completion`) after successful distribution scheduling on the ready-folder n8n path.

When invoked that way, lifecycle semantics MUST match this capability (including legacy `blog-posts/ready/` fallback). Calendar mutation MUST remain outside `complete_flow_a_source_lifecycle` itself and MUST be owned by the ready-path completion wrapper when requested.

#### Scenario: HTTP ready-path uses the same lifecycle entry point

- **WHEN** `POST /complete-flow-a-ready-path` runs for an eligible `distribution_scheduled` campaign whose Markdown is still under `blog-posts/ready/`
- **THEN** `complete_flow_a_source_lifecycle` performs the physical move to `blog-posts/processed/` and transitions campaign state to `flow_a_complete` on success

#### Scenario: Lifecycle entry point still does not write calendar.json

- **WHEN** `complete_flow_a_source_lifecycle` runs successfully
- **THEN** it does not itself modify `editorial-calendar/calendar.json` (calendar updates remain a separate ready-path completion concern)

### Requirement: Queued generated companion image lifecycle move

When ComfyUI generates `blog-posts/queued/<source_slug>.png` during Flow A execution, lifecycle completion MUST discover that companion PNG beside the queued Markdown and move it with the Markdown to `blog-posts/processed/`.

The companion image MAY be absent at queue acceptance.

The companion image MAY be generated during queued publish execution (editorial remediation inside `publish_blog_post`).

Lifecycle completion MUST discover the queued companion beside queued Markdown when metadata was not set earlier.

`queued_image_relative_path` MUST be recorded when the image becomes present or is discovered at lifecycle completion, not only when the PNG existed at queue acceptance time.

`processed_image_relative_path` MUST be recorded after successful move to `blog-posts/processed/`.

Logical `source_slug`, `public_slug`, `source_content_sha256`, generated-image metadata, and public asset handoff metadata MUST be preserved across the move.

Partial-move recovery semantics MUST apply when Markdown moves but image move fails (`physical_move_state=partial`, `recovery_classification=repair_required`).

#### Scenario: Generated queued PNG moves to processed with Markdown

- **WHEN** Flow A completes scheduling for a campaign whose queued source is `blog-posts/queued/01-example.md` and ComfyUI generated `blog-posts/queued/01-example.png` during publish execution
- **THEN** lifecycle completion moves both files to `blog-posts/processed/`, no copy remains in `blog-posts/queued/`, metadata records `queued_image_relative_path` when discovered, and `processed_image_relative_path` after move

#### Scenario: No Markdown or PNG remains in ready or queued after success

- **WHEN** lifecycle completion succeeds after queue acceptance and generation during publish
- **THEN** neither the Markdown nor the generated PNG remains under `blog-posts/ready/` or `blog-posts/queued/`

#### Scenario: Image discovered at completion records queued_image_relative_path

- **WHEN** companion PNG was created in `blog-posts/queued/` during publish but `queued_image_relative_path` was not set at queue acceptance
- **THEN** lifecycle completion discovers the PNG beside queued Markdown, records `queued_image_relative_path`, and moves it to processed with `processed_image_relative_path` recorded
### Requirement: Successful lifecycle completion moves companion image when present

When `complete_flow_a_source_lifecycle` is called and the companion PNG exists beside the queued source Markdown (including ComfyUI-generated `blog-posts/queued/<source_slug>.png`), the PNG MUST be moved to `blog-posts/processed/` (same basename unless collision handling applies), and `processed_image_relative_path` MUST be recorded in the result.

When no companion PNG exists, lifecycle completion MUST proceed with Markdown only and `processed_image_relative_path` MUST be null.

#### Scenario: Successful lifecycle completion moves companion image when present

- **WHEN** `complete_flow_a_source_lifecycle` is called and the companion PNG exists beside the queued source Markdown
- **THEN** the PNG is moved to `blog-posts/processed/` (same basename unless collision handling applies), and `processed_image_relative_path` is recorded in the result

#### Scenario: Generated image discovered at completion time

- **WHEN** companion PNG was created in `blog-posts/queued/` during publish but `queued_image_relative_path` was not set at queue acceptance
- **THEN** lifecycle completion discovers the PNG beside queued Markdown and moves it to processed
### Requirement: Campaign metadata path traceability

On successful source lifecycle completion, campaign metadata MUST retain:

- `original_source_relative_path` — the ready-folder path used at first Flow A processing (immutable once set)
- `queued_source_relative_path` — the queued-folder path when queue lifecycle applied
- `processed_source_relative_path` — the processed-folder path after move
- `original_image_relative_path` when a companion image was present at queue or completion time
- `processed_image_relative_path` when a companion image was moved
- `source_content_sha256` unchanged from pre-move digest unless source bytes changed before move (move itself MUST NOT alter content hash)
- `source_slug` and `public_slug` unchanged from editorial identity regardless of physical collision suffix in `processed_source_relative_path`
- `source_file_status.location` `processed` with `execution_state` `idle`, `marked_processed_at` and `physical_move_completed_at` timestamps

The active `source_relative_path` field MUST be updated to `processed_source_relative_path` after successful move while preserving `original_source_relative_path` and `queued_source_relative_path`.

Campaign `state` MUST transition to `flow_a_complete` when lifecycle completion succeeds.

#### Scenario: Metadata records original queued and processed paths

- **WHEN** source lifecycle completes for a source queue-accepted from `blog-posts/ready/02-example.md` through `blog-posts/queued/02-example.md`
- **THEN** campaign metadata includes `original_source_relative_path`, `queued_source_relative_path`, `processed_source_relative_path`, and `source_file_status.location` `processed`

#### Scenario: Source identity preserved for reconciliation

- **WHEN** source lifecycle completes successfully
- **THEN** `source_content_sha256` remains available on the campaign document for idempotency and reconciliation
### Requirement: Idempotent lifecycle completion

When campaign `source_file_status.location` is already `processed` and `processed_source_relative_path` points to an existing file, `complete_flow_a_source_lifecycle` MUST return `status: skipped` (or `completed` with `already_processed: true`) without requiring the source Markdown to exist in `blog-posts/ready/`.

Re-running MUST NOT duplicate moves, republish content, or fail solely because the ready copy is absent.

#### Scenario: Already processed campaign skips move

- **WHEN** lifecycle completion is invoked for a campaign already marked `processed` with valid processed paths on disk
- **THEN** the result indicates skip/already-processed, files are not moved again, and `status` is not `failed`

#### Scenario: Post-schedule Flow A re-run without ready source

- **WHEN** Flow A downstream services are invoked by `campaign_id` for a campaign in `distribution_scheduled` or later with source files only under `blog-posts/processed/`
- **THEN** operations return idempotent skip/completed outcomes without error `blog_publish_source_not_ready` solely due to missing ready copy
### Requirement: Failure and partial-move behavior

If Flow A fails before successful `schedule_linkedin_distribution`, source files MUST remain in `blog-posts/queued/` (when queue acceptance succeeded) or `blog-posts/ready/` (when queue acceptance did not run), and lifecycle completion MUST NOT have been invoked.

If scheduling succeeded but physical move fails, the result MUST use `status: failed` with stable error code `flow_a_source_move_failed` (or `flow_a_source_move_partial` when Markdown moved but image move failed). Campaign `state` MUST remain `distribution_scheduled` until lifecycle completion succeeds. The result MUST include repair guidance in `warnings[]` without exposing secrets.

The worker MUST NOT leave duplicate Markdown in both `queued/` and `processed/` without recording partial state in `source_file_status.physical_move_state`.

Markdown and companion image moves during lifecycle completion MUST be coordinated but MUST NOT be treated as transactionally atomic; partial image failure MUST set `physical_move_state=partial` and `recovery_classification=repair_required`.

#### Scenario: Failed Flow A before scheduling keeps source in queued

- **WHEN** `schedule_linkedin_distribution` fails during Flow A execution after queue acceptance
- **THEN** source Markdown and companion image remain in `blog-posts/queued/` and lifecycle completion is not invoked

#### Scenario: Move failure after scheduling preserves schedule work

- **WHEN** scheduling succeeds but moving Markdown from `queued/` to `processed/` fails
- **THEN** campaign remains `distribution_scheduled`, scheduling metadata is unchanged, `recovery_classification` is `repair_required`, and the lifecycle result reports `flow_a_source_move_failed`
### Requirement: Deterministic processed-path collision handling

When the target path `blog-posts/processed/<filename>` already exists and is not the same file being moved, the worker MUST allocate a deterministic alternate name using suffix pattern `<stem>-processed-<n><ext>` starting at `n=1` and incrementing until a free name is found or `flow_a_source_move_collision_exhausted` is returned.

Collision handling MUST apply independently to Markdown and image files.

#### Scenario: Collision uses deterministic suffix

- **WHEN** `blog-posts/processed/02-example.md` already exists for a different campaign and lifecycle completion moves `blog-posts/ready/02-example.md`
- **THEN** the moved file is written to `blog-posts/processed/02-example-processed-1.md` and metadata records that processed path
### Requirement: Folder semantics

`blog-posts/ready/` MUST contain only pending operator-approved input not yet accepted into the operational queue.

`blog-posts/queued/` MUST contain worker-accepted sources awaiting or undergoing Flow A execution.

`blog-posts/processed/` MUST contain source editorial files successfully consumed by Flow A through scheduling and lifecycle completion.

`blog-posts/error/` contains failed input per operational queue error policy.

Lifecycle completion MUST NOT write to `blog-posts/error/` on success.

#### Scenario: Ready and queued empty after successful Flow A

- **WHEN** Flow A completes through queue acceptance, scheduling, and source lifecycle for a post with Markdown and companion image
- **THEN** those filenames are absent from `blog-posts/ready/` and `blog-posts/queued/` and present under `blog-posts/processed/`
### Requirement: Automated test coverage

The test suite MUST cover at minimum:

1. Successful Flow A lifecycle moves `.md` from `ready/` to `processed/`.
2. Successful Flow A lifecycle moves companion image when present.
3. Campaign metadata records original and processed source paths.
4. Re-running completed campaign succeeds/skips without requiring source in `ready/`.
5. Failed Flow A before scheduling does not move sources.
6. Move collision is handled deterministically.
7. Existing blog publish, image handoff, publish-date safety, and article preview tests continue to pass without modification of their behavioral contracts.

#### Scenario: Regression suite passes

- **WHEN** the full worker test suite runs after implementing this change
- **THEN** new lifecycle tests pass and existing blog publish, image handoff, date safety, and article preview tests pass
