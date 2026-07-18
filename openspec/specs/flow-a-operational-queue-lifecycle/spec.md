# flow-a-operational-queue-lifecycle

## Purpose

Flow A operational source lifecycle for the `silverman-blog-linkedin` HTTP worker: operator-approved inbox (`blog-posts/ready/`), worker-accepted executable work (`blog-posts/queued/`), logical active execution (`processing`), successful consumption (`blog-posts/processed/`), and terminal failure (`blog-posts/error/`). Defines queue acceptance, execution claims, stale detection, recovery classification, coordinated Markdown/image moves, and compatibility with editorial calendar intake and existing Flow A idempotency contracts.

## Requirements

### Requirement: Operational source lifecycle purpose

The worker SHALL implement Flow A operational source lifecycle management that distinguishes operator-approved inbox input (`blog-posts/ready/`), worker-accepted executable work (`blog-posts/queued/`), logical active execution (`processing`), successful consumption (`blog-posts/processed/`), and terminal failure (`blog-posts/error/`).

Physical location MUST be recorded in `source_file_status.location` with values `ready`, `queued`, `processed`, or `error`.

Logical execution MUST be recorded in `source_file_status.execution_state` with values `idle`, `processing`, or `stale`.

Campaign pipeline `state` (canonical spec `flow-a-lifecycle`) MUST remain a separate dimension and MUST NOT be overloaded to mean physical folder location.

#### Scenario: Console-derivable operational display state

- **WHEN** campaign metadata is read for an operations view
- **THEN** display state `ready`, `queued`, `processing`, `processed`, `error`, `last_error`, `last_transition`, and `recovery_classification` can be derived from `source_file_status` and `last_error` without parsing free-form logs
### Requirement: Canonical recovery classification vocabulary

`source_file_status.recovery_classification` MUST use exactly these values when set:

- `no_action` — no operator action required; ready to proceed or already terminal
- `retryable` — automatic or scheduled retry expected (transient failure, stale reclaim)
- `repair_required` — physical/metadata mismatch or partial move; operator or repair tooling must reconcile
- `requeue_required` — terminal error state; explicit requeue needed before re-execution
- `manual_intervention_required` — active processing claim not stale; do not double-claim

Undocumented variants MUST NOT be used.

#### Scenario: Recovery classification uses canonical values only

- **WHEN** any operational lifecycle operation sets `recovery_classification`
- **THEN** the value is one of the five canonical enum values and no undocumented alias is persisted
### Requirement: Editorial folder semantics

`blog-posts/ready/` MUST remain the operator-approved inbox for pending source input not yet accepted by the worker.

`blog-posts/queued/` MUST contain source Markdown and companion images accepted for Flow A execution and not yet terminally consumed.

`blog-posts/processed/` MUST contain sources successfully consumed through scheduling and source lifecycle completion.

`blog-posts/error/` MUST contain sources moved per the approved error-folder policy.

There MUST NOT be a physical `blog-posts/processing/` folder in this change.

`blog-posts/queued/` MUST be included in expected editorial folder validation before queue operations.

#### Scenario: Queued folder required before acceptance

- **WHEN** queue acceptance runs and `blog-posts/queued/` is missing or not a directory
- **THEN** acceptance fails with stable error code `editorial_folders_not_ready` and no source is moved from `ready/`
### Requirement: State transition enforcement

The worker MUST enforce the operational transition table:

- `ready` → `queued` on successful queue acceptance (physical move, preserving editorial filename)
- `ready` → `error` on deterministic intake validation failure when calendar-selected (physical move)
- `ready` → `ready` when no eligible calendar item or intake not attempted (no move)
- `queued` + `idle` → `queued` + `processing` on execution claim (metadata only)
- `queued` + `processing` → `processed` + `idle` on successful lifecycle completion (physical move)
- `queued` + `processing` → `queued` + `idle` on transient recoverable failure (metadata only)
- `queued` + `processing` → `error` + `idle` on deterministic non-retryable failure before durable external side effects (physical move)
- `queued` + `processing` → `queued` + `idle` on failure after durable external side effects (metadata only; `repair_required`)
- `queued` + `processing` → `queued` + `stale` when inactivity threshold exceeded (metadata only)
- `queued` + `stale` → `queued` + `processing` on reclaim (metadata only)
- `error` + `idle` → `queued` + `idle` on requeue (physical move)
- Invalid transitions MUST be rejected with `invalid_operational_transition`

#### Scenario: Invalid ready to processed skip rejected

- **WHEN** an operation attempts to move a source directly from `blog-posts/ready/` to `blog-posts/processed/` without queue acceptance
- **THEN** the operation is rejected with `invalid_operational_transition` unless legacy compatibility repair mode is explicitly invoked for migration tooling (not default Flow A path)
### Requirement: Queue acceptance entry point and persistence protocol

The worker SHALL expose queue acceptance (for example `accept_flow_a_source_for_queue(base_path, *, source_relative_path, calendar_item_context)`) that moves an eligible source from `blog-posts/ready/` to `blog-posts/queued/` and records queue metadata.

Queue acceptance MUST follow this protocol in order:

1. Resolve calendar and campaign identity.
2. Perform safe minimum intake checks.
3. Prepare the intended metadata transition without persisting a false physical state.
4. Move Markdown from `ready/` to `queued/` preserving the original editorial filename.
5. Move the companion image if present beside the source in `ready/`.
6. Persist campaign metadata reflecting the actual observed move results.
7. Return `completed`, `partial`, `failed`, or `repair_required` status.

The worker MUST NOT persist `source_file_status.location=queued` before the Markdown file is physically accepted into `blog-posts/queued/`.

Acceptance MUST occur only when:

- The source resolves under `blog-posts/ready/` and is not a hidden filesystem artifact
- The calendar planner item is due, `selection_status=selected`, `review_required=false`, and Flow A eligible
- Minimum intake checks pass (exists, regular file, `.md`, readable, non-empty, path confinement)
- No blocking duplicate active campaign exists for the same identity
- `dry_run` is `false`

Markdown and companion image movement MUST be coordinated but MUST NOT be described or implemented as a transactionally atomic pair.

On success, campaign metadata MUST record `queued_source_relative_path`, optional `queued_image_relative_path`, `queued_at`, `last_transition_at`, `source_file_status.location=queued`, and `execution_state=idle`.

#### Scenario: Due valid source accepted and moved to queued with preserved filename

- **WHEN** a due, calendar-selected Flow A item references `blog-posts/ready/02-example.md`, intake checks pass, and `dry_run=false`
- **THEN** the Markdown exists at `blog-posts/queued/02-example.md` (same basename), no duplicate remains in `blog-posts/ready/`, campaign metadata records `queued_source_relative_path`, `source_slug` and `public_slug` are unchanged from the ready filename, and `source_file_status.location` is `queued`

#### Scenario: Ready source without eligible calendar item untouched

- **WHEN** a valid Markdown file exists in `blog-posts/ready/` but no eligible due calendar item references it
- **THEN** the file remains in `blog-posts/ready/`, is not marked `queued`, and queue acceptance is not invoked for that file

#### Scenario: Dry-run does not move to queued

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=true` for an eligible item
- **THEN** the source remains in `blog-posts/ready/`, no `processing` claim is recorded, and the item result reports a would-accept decision without fabricated queue paths

#### Scenario: Metadata write failure after successful Markdown move

- **WHEN** Markdown is physically in `blog-posts/queued/` but campaign metadata persistence fails before recording `location=queued`
- **THEN** `recovery_classification` is `repair_required`, metadata reconciliation can set `location=queued` from the observed physical path, and the source is not lost

#### Scenario: Lost queue acceptance response is idempotent

- **WHEN** queue acceptance physically succeeded but the caller retries with the same `campaign_id` and `source_content_sha256` and the queued destination already exists for that campaign
- **THEN** acceptance returns idempotent success or `skipped_already_queued` without duplicating the campaign or overwriting content
### Requirement: Queued destination collision handling

When moving `ready/` → `queued/`, the worker MUST preserve the original editorial filename.

If the queued destination already exists and belongs to the same campaign with the same `source_content_sha256`, acceptance MUST be treated as idempotent or already queued.

If the destination exists for different content, a different campaign, or cannot be safely reconciled, queue acceptance MUST be rejected with stable error code `flow_a_queue_destination_collision`, set `recovery_classification=repair_required`, and MUST NOT overwrite unrelated content.

Automatic suffix renaming (for example `<stem>-queued-<n>.md`) MUST NOT be used for `queued/` acceptance.

#### Scenario: Idempotent same-campaign same-hash queued destination

- **WHEN** `blog-posts/queued/02-example.md` already exists for the same `campaign_id` and `source_content_sha256` and acceptance is retried
- **THEN** acceptance succeeds idempotently, no overwrite occurs, and `queue_acceptance_status` is `skipped_already_queued` or `completed`

#### Scenario: Conflicting queued destination rejected

- **WHEN** `blog-posts/queued/02-example.md` exists for a different campaign or different `source_content_sha256` and acceptance attempts to move `blog-posts/ready/02-example.md`
- **THEN** acceptance fails with `flow_a_queue_destination_collision`, `recovery_classification` is `repair_required`, and neither file is overwritten

#### Scenario: Public slug unchanged after queue acceptance

- **WHEN** queue acceptance succeeds for `blog-posts/ready/01-why-architecture-matters.md`
- **THEN** `source_slug` and `public_slug` in campaign metadata match the values derived from the original ready filename and are not altered by the physical move to `queued/`
### Requirement: Processed and error destination collision handling

When collision suffixes (`-processed-<n>`, `-error-<n>`) are required in `processed/` or `error/` for compatibility, the worker MUST allocate a deterministic free name without overwriting unrelated content.

Physical collision suffixes MUST NOT change persisted logical `source_slug`, `public_slug`, `campaign_id`, or public URL identity.

#### Scenario: Processed collision suffix preserves logical slug

- **WHEN** lifecycle completion moves a source to `blog-posts/processed/02-example-processed-1.md` due to basename collision
- **THEN** campaign metadata retains the original `source_slug` and `public_slug` derived from the editorial filename, and `processed_source_relative_path` records the actual physical path
### Requirement: Execution claim and processing transition

The worker SHALL expose execution claim helpers (for example `claim_flow_a_execution` and `release_flow_a_execution`) that transition `execution_state` from `idle` or `stale` to `processing` without changing physical `location` from `queued`.

Claim MUST set `execution_attempt_id`, increment `attempt_count`, `processing_claimed_at`, `processing_started_at`, `last_progress_at`, and derived `processing_lease_expires_at` where `processing_lease_expires_at` equals `last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`.

Claim MUST be rejected when another active claim exists and the claim is not stale per the canonical stale rule.

`last_progress_at` and derived `processing_lease_expires_at` MUST be updated together at claim creation and after every completed Flow A stage boundary during execution.

`SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` MUST be validated as a positive integer with minimum 60 at configuration load; invalid values MUST fail fast with stable error code `flow_a_processing_stale_seconds_invalid`.

#### Scenario: Queued source transitions to logical processing

- **WHEN** Flow A real execution begins for a campaign with `source_file_status.location=queued` and `execution_state=idle`
- **THEN** `execution_state` becomes `processing`, physical file remains under `blog-posts/queued/`, and claim metadata including `last_progress_at` is persisted

#### Scenario: Dry-run does not leave processing claim

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=true`
- **THEN** no campaign records `execution_state=processing` and no `execution_attempt_id` is written
### Requirement: Claim release ownership

`complete_flow_a_source_lifecycle` MUST finish the terminal operational transition by setting `source_file_status.location=processed` and `execution_state=idle`.

`release_flow_a_execution` MUST be used for recoverable or failed non-terminal execution exits.

If `release_flow_a_execution` is invoked after successful lifecycle completion, it MUST be idempotent and return a no-op or `already_released` result without altering terminal processed state.

#### Scenario: Terminal completion closes execution claim

- **WHEN** `complete_flow_a_source_lifecycle` succeeds for a campaign
- **THEN** `source_file_status.location` is `processed`, `execution_state` is `idle`, and no active processing claim remains

#### Scenario: Defensive release after completion is idempotent

- **WHEN** the connector invokes `release_flow_a_execution` after successful lifecycle completion
- **THEN** the call returns `already_released` or equivalent no-op and terminal processed state is unchanged
### Requirement: Successful terminal completion from queued

After successful `schedule_linkedin_distribution`, `complete_flow_a_source_lifecycle` MUST move sources from `blog-posts/queued/` to `blog-posts/processed/` (not from `ready/`).

Successful completion MUST preserve existing terminal semantics including campaign `state` transition to `flow_a_complete`, path traceability fields, and idempotent skip when already processed.

#### Scenario: Successful Flow A completes from queued to processed

- **WHEN** Flow A executes through scheduling and lifecycle completion for a source in `blog-posts/queued/`
- **THEN** the source and companion image (when present) exist under `blog-posts/processed/`, `processed_source_relative_path` is recorded, `source_file_status.location` is `processed`, `execution_state` is `idle`, campaign `state` is `flow_a_complete`, and existing blog publish, package, and schedule artifacts are not duplicated
### Requirement: Image-related failure recovery and claim ownership

The worker MUST classify image-related Flow A failures into explicit recovery classes with one claim owner per case.

**ComfyUI unavailable, timeout, or transient generation failure**

Final state MUST be:

- `source_file_status.location=queued`;
- `execution_state=idle`;
- `recovery_classification=retryable`;
- preserve Markdown and any safe partial local artifacts;
- persist the specific `blog_image_generation_*` code;
- `last_error.category` `image_generation` or `transient_runtime` (documented stable value);
- `release_flow_a_execution` called exactly once by the connector when the claim remains `processing`;
- no public handoff, blog publish, package, schedule, or lifecycle completion.

**Local image write, frontmatter patch inconsistency, or active-folder sibling backfill failure**

Final state MUST be:

- remain physically reconcilable in `queued/` when possible;
- `recovery_classification` `retryable` or `repair_required` per cause;
- persist `blog_image_active_sibling_backfill_failed` when backfill from public asset fails during editorial remediation;
- no public handoff or publish;
- `release_flow_a_execution` called exactly once when the claim remains `processing`;
- preserve evidence and the specific error code.

**Public asset handoff failure after successful full validation**

Final state MUST be:

- `source_file_status.location=queued`;
- `execution_state=idle`;
- `recovery_classification=repair_required`;
- preserve generated or adopted editorial PNG;
- persist `blog_image_public_asset_handoff_failed`;
- `last_error.category` `public_asset_handoff` or equivalent documented value;
- `release_flow_a_execution` called exactly once;
- no blog post write, package, schedule, or lifecycle completion.

**Deterministic pre-generation or full-validation failure before public handoff**

Final state MUST follow the existing pre-side-effect deterministic error-move policy:

- source MAY move to `blog-posts/error/` when post-acceptance editorial validation policy applies;
- error move owns claim closure when it successfully or partially closes the claim;
- connector MUST NOT redundantly call `release_flow_a_execution` when error move already closed the claim;
- movement or metadata failure during error move MUST surface `repair_required`.

**Authorized hash metadata persistence failure**

Final state MUST be:

- `location=queued`;
- `execution_state=idle`;
- `recovery_classification=repair_required`;
- no public handoff or publish;
- `release_flow_a_execution` called exactly once when applicable.

#### Scenario: ComfyUI transient failure ends queued idle retryable with single release

- **WHEN** `publish_blog_post` fails with `blog_image_generation_timeout` after queue acceptance and no public handoff occurred
- **THEN** campaign ends with `location=queued`, `execution_state=idle`, `recovery_classification=retryable`, and connector invokes `release_flow_a_execution` exactly once

#### Scenario: Handoff failure ends queued idle repair_required with single release

- **WHEN** full validation succeeded but public handoff failed
- **THEN** campaign ends with `location=queued`, `execution_state=idle`, `recovery_classification=repair_required`, `last_error.category` documents public handoff, and connector invokes `release_flow_a_execution` exactly once

#### Scenario: Active-folder backfill failure ends queued with remediation error

- **WHEN** `publish_blog_post` fails with `blog_image_active_sibling_backfill_failed` during editorial remediation
- **THEN** campaign ends with `location=queued`, `execution_state=idle`, `recovery_classification` per cause, connector invokes `release_flow_a_execution` exactly once, and `blog_image_public_asset_handoff_failed` is not recorded

#### Scenario: Deterministic validation error move does not cause redundant release

- **WHEN** pre-generation or full validation fails before public handoff and post-acceptance error move closes the claim while moving source to `error/`
- **THEN** connector does not call `release_flow_a_execution` again after error move already released or closed the claim
### Requirement: Editorial validation at processing boundary

Queue acceptance SHALL perform minimum intake checks only (calendar eligibility, path confinement, regular file, non-hidden artifact).

Pre-generation editorial validation MUST run inside `publish_blog_post` before editorial image remediation and MUST NOT block solely on missing/empty generatable frontmatter `image` or a generatable missing companion PNG when ComfyUI generation is eligible.

Full editorial validation MUST run inside `publish_blog_post` after editorial image remediation and authorized hash reconciliation and MUST require canonical `image` and companion PNG per `ready-post-editorial-validation`.

Public asset handoff MUST run only after full validation succeeds inside `publish_blog_post`.

The connector MUST NOT run blocking full `validate_ready_post()` before `publish_blog_post`.

Deterministic editorial validation failures after queue acceptance and before public handoff MUST move the source to `blog-posts/error/` and record `last_error` with `category=editorial_validation` when the approved post-acceptance deterministic failure policy applies.

ComfyUI transient failures MUST remain in `blog-posts/queued/` with `recovery_classification=retryable` and MUST NOT be classified as `ready_post_image_missing`.

Public handoff failures after successful full validation MUST remain in `blog-posts/queued/` with `recovery_classification=repair_required`.

Sources MUST NOT be silently deleted or lost on validation or generation failure.

#### Scenario: Missing PNG or empty image does not block queue acceptance

- **WHEN** queue acceptance moves Markdown-only `blog-posts/ready/01-example.md` to `blog-posts/queued/01-example.md` with absent or empty frontmatter `image`
- **THEN** acceptance succeeds without requiring companion PNG or canonical `image` at acceptance time

#### Scenario: Post-acceptance pre-generation failure may move to error

- **WHEN** pre-generation validation fails deterministically inside `publish_blog_post` for a queued source (for example non-canonical non-empty frontmatter `image`)
- **THEN** the connector may move the source to `blog-posts/error/` per post-acceptance editorial validation failure policy and error move owns claim closure

#### Scenario: Post-acceptance full validation before handoff may move to error

- **WHEN** full editorial validation fails deterministically for a queued source after editorial remediation and before public handoff
- **THEN** the source may be moved to `blog-posts/error/`, `source_file_status.location` is `error`, no public asset write occurred, and `last_error` records `category=editorial_validation`

#### Scenario: Generation failure does not masquerade as ready_post_image_missing

- **WHEN** editorial remediation fails with `blog_image_generation_unavailable` for a queued Markdown-only source
- **THEN** the failure is recorded with the generation error code, the source remains in `blog-posts/queued/` for retry, and `ready_post_image_missing` is not used as the connector failure reason

#### Scenario: Missing companion does not block queued execution before publish

- **WHEN** a queued source has no companion PNG and absent, empty, or canonical frontmatter `image` before `publish_blog_post` is invoked
- **THEN** queue lifecycle does not treat the item as terminally failed solely for missing PNG; execution proceeds to publish-owned remediation
### Requirement: Deterministic intake failure movement policy

Intake failure handling MUST follow these rules:

- No calendar match: leave source in `ready/`; queue acceptance is not attempted.
- Missing source, path traversal, out-of-confinement path, non-regular file, or unresolvable path: do not move anything; report stable intake failure.
- Calendar-selected source failing deterministic intake or content validation before queue acceptance: MAY move to `blog-posts/error/` per approved stage policy.
- Unsafe or nonexistent paths MUST NEVER be moved to `error/`.
- Failure metadata MUST be persisted only when a valid campaign record can be safely identified or created.

Deterministic editorial validation failures after queue acceptance and before public handoff MUST move the source to `blog-posts/error/` and record `last_error` with `category=editorial_validation` when the approved post-acceptance deterministic failure policy applies.

Sources MUST NOT be silently deleted or lost on validation failure.

#### Scenario: No calendar match leaves source in ready

- **WHEN** a Markdown file exists in `blog-posts/ready/` but no eligible due calendar item references it
- **THEN** the file remains in `blog-posts/ready/`, queue acceptance is not attempted, and no `error/` move occurs

#### Scenario: Unsafe path is not moved to error

- **WHEN** intake detects path traversal or out-of-confinement path for a calendar-selected source
- **THEN** no file is moved, a stable intake failure is reported, and `recovery_classification` is not set on a fabricated campaign

#### Scenario: Pre-acceptance deterministic validation may move to error

- **WHEN** a calendar-selected ready source fails deterministic intake validation before queue acceptance
- **THEN** the source MAY be moved to `blog-posts/error/` with failure metadata recorded on a valid campaign record

#### Scenario: Post-acceptance editorial validation moves queued source to error

- **WHEN** full editorial validation fails deterministically for a queued source during processing
- **THEN** the source is moved to `blog-posts/error/`, `source_file_status.location` is `error`, and `last_error` records `category=editorial_validation`
### Requirement: Post-side-effect failure policy

The worker MUST separate deterministic failure handling before and after durable external Flow A side effects.

Before any durable external side effect (blog publish, derivative generation, or scheduling), a deterministic non-retryable failure MUST move the source to `blog-posts/error/` when the approved pre-side-effect error-folder policy applies.

After blog publish, derivative generation, or scheduling has produced durable side effects, failures MUST keep the source in `blog-posts/queued/` with `recovery_classification=repair_required` or `retryable` as appropriate.

Moving a post-side-effect source to `blog-posts/error/` MUST NOT use the generic pre-side-effect deterministic-failure rule; it requires a specific safe rule outside this change's default path.

Requeue from error MUST NOT erase blog publish, package, variant, scheduling, or state-history evidence.

A campaign with partial side effects MUST resume idempotently rather than appear to restart as a new campaign.

#### Scenario: Deterministic failure before blog publish moves to error

- **WHEN** a deterministic non-retryable failure occurs before `publish_blog_post` succeeds for a queued campaign
- **THEN** the source MAY be moved to `blog-posts/error/` with `recovery_classification` `requeue_required` or `manual_intervention_required` per error category

#### Scenario: Failure after blog publish stays in queued

- **WHEN** `publish_blog_post` has succeeded and a subsequent deterministic failure occurs before lifecycle completion
- **THEN** the source remains in `blog-posts/queued/`, `blog_publish` evidence is preserved, and `recovery_classification` is `repair_required` or `retryable`

#### Scenario: Failure after derivative generation stays in queued

- **WHEN** derivative generation has produced durable variant records and a subsequent failure occurs
- **THEN** the source remains in `blog-posts/queued/`, variant evidence is preserved, and retry resumes idempotently

#### Scenario: Scheduling or final move failure stays repairable in queued

- **WHEN** scheduling has succeeded but final move to `processed/` fails
- **THEN** campaign `state` remains `distribution_scheduled`, source remains addressable in `queued/` or partial processed state, and `recovery_classification` is `repair_required`
### Requirement: Transient runtime failure recovery

Transient runtime or dependency failures after queue acceptance MUST call `release_flow_a_execution`, set `execution_state=idle`, keep `location=queued`, set `recovery_classification=retryable`, and record `last_error` with `category=transient_runtime`.

Retries MUST reuse existing blog publish, derivative, and schedule idempotency keys and MUST NOT duplicate completed side effects.

#### Scenario: Transient failure preserves retry state without duplicate artifacts

- **WHEN** `publish_blog_post` fails with a retryable dependency error after queue acceptance and blog publish had not previously succeeded for the campaign
- **THEN** the source remains in `blog-posts/queued/`, `execution_state` returns to `idle`, `recovery_classification` is `retryable`, and a subsequent retry does not create duplicate public blog files when publish eventually succeeds
### Requirement: Partial completion and final move failure

When external Flow A side effects have succeeded but final physical move to `processed/` fails, the worker MUST NOT report `flow_a_complete` or `source_lifecycle_status=completed`.

The worker MUST record `physical_move_state` `partial` or `failed`, preserve scheduling metadata, set `recovery_classification=repair_required`, and keep campaign `state` at `distribution_scheduled` until lifecycle completion succeeds.

#### Scenario: Move to processed failure is repairable not false success

- **WHEN** scheduling succeeds but moving Markdown from `queued/` to `processed/` fails
- **THEN** campaign `state` remains `distribution_scheduled`, `recovery_classification` is `repair_required`, and the result reports `flow_a_source_move_failed` without falsely marking Flow A complete
### Requirement: Stale processing detection

The worker MUST detect stale processing when `execution_state=processing` and current UTC time is greater than or equal to `last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`.

`SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` defines the allowed inactivity period, not maximum total execution duration.

Stale detection MUST NOT use a `processing_lease_expires_at` value that diverges from `last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`.

Stale detection MUST set `execution_state=stale` and `recovery_classification=retryable` without moving files.

Reclaim after stale MUST allow idempotent resume using existing campaign evidence and completed-stage markers.

#### Scenario: Stale processing detected from last_progress_at

- **WHEN** campaign metadata shows `execution_state=processing`, `last_progress_at` plus configured stale seconds is in the past, and the source file exists under `blog-posts/queued/`
- **THEN** stale classification is `retryable`, `execution_state` may transition to `stale`, and a subsequent execution reclaim does not duplicate LinkedIn schedule slots
### Requirement: Idempotent re-run rules

Re-running Flow A for sources in `queued`, `processing`/`stale`, partially completed, `processed`, or `error` MUST follow explicit rules:

- `processed` / `flow_a_complete`: skip terminal moves; downstream idempotent skip only
- `queued` + `idle` or `stale`: claim and resume from pipeline `state`
- `processing` with non-stale claim: reject duplicate claim
- `error`: require explicit requeue before execution
- Same `campaign_id` and `source_content_sha256` MUST be preserved across retries unless operator creates a new campaign through a deliberate requeue policy

#### Scenario: Re-run queued item resumes without duplicate schedule

- **WHEN** Flow A is re-invoked for a campaign in `distribution_scheduled` with source in `blog-posts/queued/` and existing schedule metadata
- **THEN** scheduling returns already-scheduled outcomes, lifecycle completion moves to `processed/` once, and no duplicate variant schedule records are created
### Requirement: Requeue from error

The worker SHALL expose requeue (for example `requeue_flow_a_source_from_error(base_path, *, campaign_id)`) that moves sources from `blog-posts/error/` to `blog-posts/queued/`, preserves `campaign_id`, `source_slug`, `public_slug`, and content identity fields, resets `execution_state=idle`, updates `queued_source_relative_path`, and appends operational history.

Requeue MUST NOT silently create a duplicate campaign document.

Requeue MUST NOT erase `blog_publish`, `variants`, scheduling metadata, or `state_history` evidence.

Requeue MAY be invoked without a UI in this change.

#### Scenario: Requeue preserves identity and side-effect evidence

- **WHEN** `requeue_flow_a_source_from_error` succeeds for a campaign with prior blog publish evidence and `error_source_relative_path` set
- **THEN** the source exists under `blog-posts/queued/`, the same `campaign_id` metadata file is updated, `blog_publish` and variant records remain, no second campaign file is created, and `recovery_classification` is cleared or set to `no_action`
### Requirement: Coordinated Markdown and image movement

Markdown and companion image moves MUST be coordinated for acceptance, completion, error, and requeue operations.

Each individual same-filesystem rename MAY be atomic; the pair MUST NOT be treated as transactionally atomic.

Markdown is the primary source file and MUST be moved first.

Every successful and failed component move MUST be recorded.

When only one member of the pair moves, `physical_move_state` MUST be `partial` and `recovery_classification` MUST be `repair_required`.

No source MUST be silently lost.

Missing companion image MUST NOT block Markdown-only operations; image fields remain null.

#### Scenario: Partial image move detectable

- **WHEN** Markdown moves from `queued/` to `processed/` but companion image move fails
- **THEN** `physical_move_state` is `partial`, `recovery_classification` is `repair_required`, and metadata records which paths succeeded
### Requirement: Hidden macOS artifact filtering

Scanners and queue candidacy logic MUST ignore at minimum `.DS_Store`, files beginning with `._`, and any direct child of `blog-posts/ready/` or `blog-posts/queued/` whose basename begins with `.`.

Ignored artifacts MUST NOT be treated as Markdown candidates, companion images, duplicate sources, or queue acceptance targets.

#### Scenario: DS_Store ignored for queue candidacy

- **WHEN** `blog-posts/ready/` contains `.DS_Store` and `._02-example.md` alongside a valid post
- **THEN** hidden artifacts appear only in `ignored_files` with reason `hidden_artifact`, are not queue candidates, and do not cause false duplicate-source errors for the valid post
### Requirement: Legacy campaign compatibility

Campaigns without `queued_source_relative_path` or queue timestamps MUST remain readable.

When `source_file_status.location=processed` and `processed_source_relative_path` exists, behavior MUST match pre-change idempotent semantics.

When a legacy campaign has source only in `ready/` and is executed under the new worker, queue acceptance MUST run before publish.

Dry-run MUST NOT write queue metadata for legacy reconciliation.

#### Scenario: Legacy processed campaign unchanged

- **WHEN** a campaign completed before this change has `processed_source_relative_path` and no `queued_source_relative_path`
- **THEN** idempotent Flow A services resolve the processed path and skip moves without error
### Requirement: Calendar compatibility

Queue acceptance MUST be driven by editorial calendar due items with explicit `source_relative_path`; automatic folder polling scheduling MUST NOT be introduced.

Queue acceptance and Flow A execution MAY occur in one connector invocation with two explicit internal stages.

A queued source MUST remain executable after its original calendar due time until terminally consumed or moved to `error/`.

Calendar metadata changes after queue acceptance MUST NOT cancel queued work; matching uses persisted `campaign_id` and source path chain.

`calendar.json` MUST NOT be modified by this capability.

#### Scenario: Queued item executable after due time passes

- **WHEN** a source was queue-accepted on its due date but execution failed transiently before completion
- **THEN** a later connector invocation may reclaim and complete Flow A without moving the source back to `ready/`
### Requirement: LinkedIn publication exclusion

This capability MUST NOT invoke real LinkedIn publication, enable `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, call LinkedIn Posts API, or upload LinkedIn media.

#### Scenario: Lifecycle never publishes LinkedIn

- **WHEN** any operational lifecycle operation runs in real mode
- **THEN** no LinkedIn publication API is called
### Requirement: Automated test coverage requirements

The implementation MUST include automated tests covering at minimum:

- State transition rules and invalid transition rejection
- Ready-to-queued acceptance preserving filename and calendar gating
- Idempotent same-campaign/same-hash queued destination and conflicting queued destination rejection
- Public slug unchanged after queue acceptance
- Queued-to-processing claim transition
- Successful queued-to-processed Flow A path
- Already-queued connector retry behavior
- Intake failure categories (no calendar, unsafe path, deterministic validation)
- Post-acceptance editorial validation failure
- Pre-side-effect and post-side-effect deterministic failure handling
- Transient runtime failure and retry idempotency
- Stale-processing detection from `last_progress_at` and reclaim
- Queue-acceptance protocol reconciliation cases
- Missing-file and mismatched-metadata recovery classifications
- No duplicate blog artifacts, LinkedIn derivative packages, or schedule slots on retry
- Companion-image coordinated and partial moves
- Processed/error collision suffixes with unchanged logical slugs
- Claim release ownership and idempotent defensive release
- Dry-run behavior without physical moves or claims
- Hidden macOS artifact filtering
- Backward compatibility with legacy campaign metadata
- Regression coverage for existing Flow A blog publish, image handoff, publish-date safety, article preview, derivative generation, and scheduling tests

#### Scenario: Regression suite passes after implementation

- **WHEN** the full worker test suite runs after implementing this change
- **THEN** new operational lifecycle tests pass and existing Flow A regression tests pass without behavioral contract regression


### Requirement: Incomplete-campaign recovery reuses operational recovery vocabulary and re-run rules

Incomplete Flow A campaign recovery (capability `flow-a-incomplete-campaign-recovery`) MUST reuse this capability’s canonical `source_file_status.recovery_classification` vocabulary and existing claim, stale, reclaim, requeue, and idempotent re-run rules rather than inventing a parallel recovery ontology.

When incomplete-campaign recovery inspect, resume, repair, or cancel sets or clears `recovery_classification`, the value MUST remain one of: `no_action`, `retryable`, `repair_required`, `requeue_required`, `manual_intervention_required`.

Operator-facing recovery-action taxonomy values (`recommended_recovery_action` / `executed_recovery_action`) are complementary response and ledger vocabulary. They MUST NOT be persisted into `source_file_status.recovery_classification` and MUST NOT introduce additional classification enum members.

Cancel of incomplete-campaign recovery MUST NOT invent a sixth `recovery_classification` value. Cancel state MUST be represented under incomplete-campaign recovery metadata (`flow_a_recovery.cancelled`) rather than as a new queue classification.

Resume of an incomplete campaign MUST follow the existing idempotent re-run rules for `queued` / `stale` / `processing` / `processed` / `error` sources: non-stale `processing` claims remain rejected; `error` requires explicit requeue before execution; partial side-effect campaigns resume from persisted pipeline evidence without appearing as a new campaign. When incomplete-campaign recovery is cancelled, resume and repair MUST fail closed without bypassing those rules or inventing stage success.

This requirement MUST NOT redefine LinkedIn API publication recovery classification or re-queue confirmation semantics.

#### Scenario: Recovery classification remains canonical during incomplete-campaign recovery

- **WHEN** incomplete-campaign recovery resume or repair updates `recovery_classification`
- **THEN** the persisted value is one of the five canonical enum values and no undocumented alias is written

#### Scenario: Non-stale processing claim still blocks duplicate execution through recovery resume

- **WHEN** incomplete-campaign recovery resume is requested for a source with `execution_state=processing` that is not stale
- **THEN** resume is rejected consistently with existing duplicate-claim protection and no second execution claim is created

#### Scenario: Error location still requires explicit requeue before recovery resume

- **WHEN** incomplete-campaign recovery resume is requested while `source_file_status.location=error`
- **THEN** resume does not implicitly requeue and reports `requeue_required` using the canonical classification vocabulary

#### Scenario: Recovery-action taxonomy is not written as recovery_classification

- **WHEN** incomplete-campaign recovery returns `recommended_recovery_action=resume` (or another taxonomy value)
- **THEN** `source_file_status.recovery_classification` is not overwritten with that taxonomy string and remains a canonical five-value enum member when set

#### Scenario: Cancel does not invent a sixth recovery_classification value

- **WHEN** incomplete-campaign recovery cancel marks a campaign cancelled
- **THEN** no new `recovery_classification` enum member is persisted and cancel is visible via incomplete-campaign recovery cancel metadata

### Requirement: Concurrent execution claim uses atomic metadata compare-and-swap

`claim_flow_a_execution` MUST persist the transition to `execution_state=processing` using an atomic compare-and-swap (or equivalent) against the on-disk campaign metadata document so that two overlapping claim attempts cannot both successfully write a new active non-stale processing claim for the same `campaign_id`.

When CAS detects that another writer changed the campaign document, the claim helper MUST re-read current state and either:

- complete as the claim winner if still eligible, or
- fail closed with `flow_a_execution_already_claimed` when a non-stale peer claim now holds `processing`.

Claim contention losers MUST set `already_claimed=true` semantics and `recovery_classification=manual_intervention_required`, MUST NOT increment a successful peer’s logical ownership into a second active claim, and MUST NOT proceed as if they held the claim.

This requirement hardens the US-033 post-processing surface. Abandoned-claim stale detect and reclaim are US-034 deliverables (see the dedicated US-034 reclaim requirement below). Existing stale detection helpers remain the reclaim vocabulary.

#### Scenario: Racing idle claims produce one processing claim

- **WHEN** two concurrent claim calls both observe `execution_state=idle` for the same queued campaign
- **THEN** exactly one call returns completed with `execution_state=processing` and the other fails with `flow_a_execution_already_claimed`

#### Scenario: CAS loser does not leave split claim metadata

- **WHEN** a claim CAS attempt loses to a peer writer that already set `processing`
- **THEN** on-disk metadata shows a single `execution_attempt_id` for the active claim and the loser does not persist a second attempt as the active owner

### Requirement: Concurrent duplicate post processing remains visible to callers

Callers of `claim_flow_a_execution` (including the editorial calendar Flow A connector and incomplete-campaign recovery resume) MUST receive the stable already-claimed failure outcome when blocked by a non-stale active claim, without secret or content-body leakage.

Connector item results that fail at claim MUST include `flow_a_execution_already_claimed` in `errors` (or equivalent structured error list) so operators can distinguish claim contention from publish/image failures.

#### Scenario: Connector surfaces already-claimed on contention

- **WHEN** the calendar Flow A connector attempts execution for a campaign whose non-stale claim is already held
- **THEN** the item result is failed/blocked with `flow_a_execution_already_claimed` and does not invoke publish or ComfyUI for that attempt

#### Scenario: Recovery resume still blocked by non-stale claim

- **WHEN** incomplete-campaign recovery resume requests execution while `execution_state=processing` and the claim is not stale
- **THEN** resume is rejected with duplicate-claim protection and no second claim is created

### Requirement: Abandoned-claim stale detect and reclaim are operator-visible US-034 deliverables

Stale processing detection and reclaim MUST be treated as US-034 story deliverables with operator-visible outcomes, using the existing execution vocabulary (`processing`, `stale`, `idle`) and recovery classifications without inventing a parallel queue ontology.

`detect_stale_flow_a_execution` (or equivalent) MUST:

- complete with `execution_state=stale` and `recovery_classification=retryable` when a `processing` claim is past `last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`;
- skip without mutation when the claim is not yet stale or not in `processing`;
- leave physical `source_file_status.location` unchanged.

`claim_flow_a_execution` reclaim from `stale` MUST complete with `execution_state=processing`, a new `execution_attempt_id`, incremented `attempt_count`, and `reclaimed_from_stale=true` (or equivalent structured field) so operators can distinguish reclaim from a first claim.

Non-stale `processing` claims MUST continue to fail closed with `flow_a_execution_already_claimed` and `recovery_classification=manual_intervention_required`.

Reclaim and subsequent resume MUST use existing campaign evidence and completed-stage markers and MUST NOT create duplicate LinkedIn schedule slots or duplicate LinkedIn API publications when durable evidence already exists.

#### Scenario: Stale detect completed is operator-visible

- **WHEN** stale detection runs for an abandoned non-progressing `processing` claim past the configured inactivity threshold
- **THEN** the result status is completed, `execution_state` is `stale`, and `recovery_classification` is `retryable`

#### Scenario: Stale detect skipped when claim still active

- **WHEN** stale detection runs for a `processing` claim that is not past the inactivity threshold
- **THEN** the result is skipped (or equivalent non-mutating outcome), `execution_state` remains `processing`, and `recovery_classification` remains `manual_intervention_required` for duplicate-claim guidance

#### Scenario: Reclaim from stale is operator-visible

- **WHEN** claim runs for a campaign with `execution_state=stale`
- **THEN** claim completes with `execution_state=processing`, a new `execution_attempt_id`, and `reclaimed_from_stale=true` (or equivalent)

#### Scenario: Reclaim does not duplicate completed schedule or LinkedIn evidence

- **WHEN** a stale campaign that already has matching distribution schedule proof and/or published LinkedIn URN evidence is reclaimed and resumed
- **THEN** resume does not create duplicate schedule slots or a second LinkedIn API publication for identities that already have durable evidence
