# linkedin-distribution-scheduling-model

## Purpose

Flow A LinkedIn distribution scheduling for the `silverman-blog-linkedin` HTTP worker: campaign eligibility after derivative package generation, lifecycle transition (`derivatives_generated` → `distribution_scheduled`), per-variant staggered `scheduled_at_utc` and `publish_state` `pending`, artifact hash verification, schedule idempotency, and `POST /schedule-linkedin-distribution`. Implements child slice 6 under umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`.

## Requirements

### Requirement: Umbrella and dependency references

This child change SHALL implement Flow A LinkedIn distribution scheduling under active umbrella change `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 6).

Scheduling behavior MUST align with Flow A distribution policy in canonical spec `editorial-canon` and artifact `content-strategy/silverman-editorial-system.md` (`#linkedin-distribution-strategy`, `#no-redundancy-rules`).

Campaign metadata, state transitions, variant IDs, and idempotency keys MUST use canonical spec `flow-a-lifecycle` and worker module `campaign_lifecycle.py`.

Scheduling MUST consume package metadata and artifacts produced by canonical spec `linkedin-derivative-package-generation` and worker module `linkedin_package_flow.py` (`linkedin_package`, `variants[]`, `linkedin-posts/generated/<campaign_id>/<variant_id>.md`).

Flow B campaigns MUST NOT enter this scheduling path.

#### Scenario: Child change cites umbrella and completed siblings

- **WHEN** this capability is documented or implemented
- **THEN** it references umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`, editorial canon child `editorial-canon-and-linkedin-distribution-strategy`, lifecycle child `flow-a-lifecycle-and-duplicate-prevention`, and package generation child `linkedin-derivative-package-generation`

#### Scenario: Flow B blocked

- **WHEN** `schedule_linkedin_distribution` is invoked for a campaign with `flow` `flow_b`
- **THEN** the operation fails with error code `linkedin_schedule_flow_not_allowed` and does not write scheduling metadata

### Requirement: LinkedIn distribution scheduling service entry point

The worker SHALL expose a distribution scheduling service entry point (for example `schedule_linkedin_distribution(base_path, *, campaign_id=None, source_relative_path=None, strategy=None, start_at_utc=None, timezone=None)`) that orchestrates campaign eligibility, artifact verification, schedule computation, campaign metadata updates, and lifecycle transitions for one Flow A campaign.

The entry point MUST return a structured `LinkedInDistributionScheduleResult` (or equivalent dataclass) serializable to JSON for HTTP and n8n consumers.

The entry point MUST NOT move editorial source files between `ready`, `processed`, or `error` folders.

The entry point MUST NOT run `git commit` or `git push`.

The entry point MUST NOT call LinkedIn API publish endpoints.

The entry point MUST NOT change `publish_state` to any value other than `pending`.

The entry point MUST NOT perform immediate LinkedIn publication.

#### Scenario: Schedule distribution by campaign_id

- **WHEN** `schedule_linkedin_distribution` is called with `campaign_id` for a `flow_a` campaign in state `derivatives_generated` with valid `linkedin_package`, matching `variants[]`, and on-disk artifacts with matching hashes
- **THEN** the function computes staggered per-variant schedules, updates campaign metadata, transitions to `distribution_scheduled`, and returns a structured result without relocating source Markdown files

#### Scenario: Schedule distribution by source_relative_path

- **WHEN** `schedule_linkedin_distribution` is called with `source_relative_path` and campaign metadata exists for that path
- **THEN** the function resolves `campaign_id` from campaign metadata and proceeds with distribution scheduling

#### Scenario: No LinkedIn API side effects

- **WHEN** this child change is applied and distribution scheduling succeeds
- **THEN** no LinkedIn API publish is attempted and every scheduled variant has `publish_state` `pending`

### Requirement: Campaign eligibility for distribution scheduling

Distribution scheduling MUST require an existing campaign metadata document at `metadata/campaigns/<campaign-id>.json`.

The campaign MUST have `flow` `flow_a`.

The campaign `state` MUST be `derivatives_generated`, or `distribution_scheduled` for idempotent re-run only when idempotency rules below match.

The campaign MUST have a non-null `linkedin_package` object with `idempotency_key` and `variant_ids`.

The campaign MUST have `variants[]` entries matching each `linkedin_package.variant_ids` entry.

Each referenced artifact at `artifact_relative_path` MUST exist on disk under the editorial base path.

The current artifact SHA-256 MUST match stored `derivative_content_sha256` in the matching `variants[]` entry.

Distribution scheduling MUST be rejected when:

- campaign metadata does not exist (`linkedin_schedule_campaign_not_found`)
- `flow` is not `flow_a` (`linkedin_schedule_flow_not_allowed`)
- `state` is before `derivatives_generated` (`linkedin_schedule_invalid_campaign_state`)
- `state` is `distribution_complete` or `flow_a_complete` (`linkedin_schedule_invalid_campaign_state`)
- `linkedin_package` is missing (`linkedin_schedule_package_missing`)
- `variants[]` is missing a required variant entry (`linkedin_schedule_variant_metadata_missing`)
- artifact file is missing (`linkedin_schedule_artifact_missing`)
- artifact content hash differs from stored hash (`linkedin_schedule_artifact_hash_changed`)
- variant list is empty (`linkedin_schedule_no_variants`)

#### Scenario: Campaign not found

- **WHEN** distribution scheduling is requested for a `campaign_id` with no metadata file
- **THEN** the operation fails with `linkedin_schedule_campaign_not_found`

#### Scenario: State before derivatives_generated rejected

- **WHEN** distribution scheduling is requested for a campaign in state `blog_published`
- **THEN** the operation fails with `linkedin_schedule_invalid_campaign_state`

#### Scenario: Missing linkedin_package rejected

- **WHEN** distribution scheduling is requested for a `derivatives_generated` campaign without `linkedin_package` metadata
- **THEN** the operation fails with `linkedin_schedule_package_missing`

#### Scenario: Missing artifact rejected

- **WHEN** distribution scheduling is requested and a variant's `artifact_relative_path` does not exist on disk
- **THEN** the operation fails with `linkedin_schedule_artifact_missing`

#### Scenario: Artifact hash changed rejected

- **WHEN** distribution scheduling is requested and an on-disk artifact SHA-256 differs from stored `derivative_content_sha256`
- **THEN** the operation fails with `linkedin_schedule_artifact_hash_changed`

### Requirement: Default staggered scheduling strategy

The default scheduling strategy MUST be named `flow_a_staggered`.

The default strategy MUST schedule canonical variants on separate calendar days with minimum spacing of 3 calendar days between consecutive variants in the same campaign.

The default strategy MUST NOT schedule two variants at the same `scheduled_at_utc` timestamp.

The default strategy MUST apply audience-aware sequencing aligned with editorial canon `#linkedin-distribution-strategy`:

1. `executive-recruiter` first
2. `engineering-leadership` second (when present)
3. `technical-architect` third (when present)
4. `short-provocative` last (when present)

When the package contains a subset of canonical variants, the strategy MUST preserve relative order from the full sequence and apply the same day-offset spacing from the schedule anchor.

Request MAY supply an alternate `strategy` name. Unknown strategy names MUST fail with `linkedin_schedule_invalid_strategy`.

#### Scenario: Variants are staggered not simultaneous

- **WHEN** distribution scheduling succeeds for a campaign with four canonical variants using default strategy
- **THEN** each variant has a distinct `scheduled_at_utc` and consecutive variants are at least 3 calendar days apart

#### Scenario: Invalid strategy rejected

- **WHEN** distribution scheduling is requested with `strategy` set to an unknown name
- **THEN** the operation fails with `linkedin_schedule_invalid_strategy`

### Requirement: Schedule anchor and UTC storage

The worker MUST accept an optional `start_at_utc` request field as a UTC ISO 8601 timestamp anchoring the first variant's schedule.

When `start_at_utc` is omitted, the worker MUST compute a deterministic default anchor (next eligible preferred weekday at default publish window in UTC).

All `scheduled_at_utc` values MUST be stored and returned in UTC.

Invalid `start_at_utc` format MUST fail with `linkedin_schedule_invalid_anchor`.

#### Scenario: Explicit anchor used

- **WHEN** distribution scheduling is called with `start_at_utc` `2026-07-07T14:00:00Z`
- **THEN** the first variant in sequence is scheduled at `2026-07-07T14:00:00Z` and subsequent variants follow staggered offsets from that anchor

#### Scenario: Invalid anchor rejected

- **WHEN** distribution scheduling is called with `start_at_utc` that is not valid UTC ISO 8601
- **THEN** the operation fails with `linkedin_schedule_invalid_anchor`

### Requirement: Per-variant scheduling metadata

For each scheduled variant, campaign metadata MUST record:

- `variant` (canonical variant ID)
- `artifact_relative_path`
- `derivative_content_sha256`
- `scheduled_at_utc`
- `publish_state` set to `pending`
- `schedule_idempotency_key` (stable per-variant scheduling idempotency key)

Campaign metadata MUST also include a `linkedin_distribution` object with at minimum:

- `distribution_id`
- `idempotency_key` (schedule-level)
- `strategy`
- `anchor_utc`
- `variant_ids`

Campaign metadata and HTTP responses MUST NOT include generated variant body text (`markdown_content`, `generated_draft_content`, or equivalent).

Existing variant fields from package generation MUST be preserved when adding scheduling fields.

#### Scenario: Per-variant schedule metadata written

- **WHEN** distribution scheduling succeeds for the first time
- **THEN** each variant in `variants[]` gains `scheduled_at_utc`, `publish_state` `pending`, and `schedule_idempotency_key`, and `linkedin_distribution` is written

#### Scenario: Metadata excludes body text

- **WHEN** distribution scheduling succeeds
- **THEN** campaign metadata JSON and HTTP response do not contain generated LinkedIn post body text

### Requirement: Distribution scheduling idempotency

The worker MUST define a stable schedule-level idempotency key from:

- `campaign_id`
- `source_content_sha256`
- `linkedin_package.idempotency_key`
- sorted variant list
- `strategy`
- schedule anchor (`anchor_utc`)
- `flow_a`

When campaign `state` is `distribution_scheduled` and stored schedule idempotency proof matches the expected key and per-variant `scheduled_at_utc` values:

- the operation MUST return `status` `completed`
- the operation MUST NOT append duplicate `state_history` entries
- the operation MUST NOT rewrite `scheduled_at_utc` values

When campaign `state` is `distribution_scheduled` but stored scheduling metadata does not match the idempotency proof:

- the operation MUST fail with `linkedin_schedule_metadata_mismatch`

#### Scenario: Idempotent rerun returns completed

- **WHEN** distribution scheduling is invoked again for a `distribution_scheduled` campaign with matching schedule idempotency proof
- **THEN** the operation returns `status` `completed` without duplicate `state_history` and without changing `scheduled_at_utc` values

#### Scenario: Scheduling mismatch fails safely

- **WHEN** distribution scheduling is invoked for a `distribution_scheduled` campaign with a different `start_at_utc` than stored `anchor_utc`
- **THEN** the operation fails with `linkedin_schedule_metadata_mismatch`

### Requirement: Campaign lifecycle transition

On successful first-time distribution scheduling, the worker MUST transition campaign state from `derivatives_generated` to `distribution_scheduled` using `transition_state(..., actor="worker")`.

The worker MUST NOT transition beyond `distribution_scheduled` in this child change.

Failed eligibility or verification MUST NOT change campaign state.

#### Scenario: Successful scheduling transitions state

- **WHEN** distribution scheduling succeeds for a campaign in `derivatives_generated`
- **THEN** campaign `state` becomes `distribution_scheduled` with a `state_history` entry recording the transition

#### Scenario: Failed scheduling does not transition

- **WHEN** distribution scheduling fails due to missing artifact
- **THEN** campaign `state` remains unchanged

### Requirement: HTTP endpoint POST /schedule-linkedin-distribution

The worker HTTP API SHALL expose `POST /schedule-linkedin-distribution` protected by API key authentication (`Depends(require_api_key)`), consistent with `POST /generate-linkedin-package` and `POST /publish-blog-post`.

The request body MUST accept exactly one of `campaign_id` or `source_relative_path`.

The request body MAY accept optional `strategy`, `start_at_utc`, and `timezone`.

The request Pydantic model MUST use `extra="forbid"`.

The response MUST be JSON containing at minimum:

- `status` (`completed` or `failed`)
- `campaign_id`
- `state`
- `distribution_id` (or `schedule_id`)
- `variant_schedules` (per-variant summary array)
- `errors`
- `warnings`
- `metadata_written`
- `metadata_error_code`

Invalid request bodies MUST return HTTP 422.

Unauthorized requests MUST be rejected.

#### Scenario: HTTP endpoint requires auth

- **WHEN** `POST /schedule-linkedin-distribution` is called without a valid API key
- **THEN** the request is rejected with an unauthorized response

#### Scenario: HTTP successful response shape

- **WHEN** `POST /schedule-linkedin-distribution` succeeds
- **THEN** the JSON response includes `status`, `campaign_id`, `state`, `distribution_id`, `variant_schedules`, `errors`, `warnings`, `metadata_written`, and `metadata_error_code`, and does not include variant body text

#### Scenario: HTTP invalid body returns 422

- **WHEN** `POST /schedule-linkedin-distribution` is called with an empty body or both `campaign_id` and `source_relative_path`
- **THEN** the API returns HTTP 422

### Requirement: Stable error codes

Distribution scheduling MUST use stable machine-readable error codes including at minimum:

- `linkedin_schedule_campaign_not_found`
- `linkedin_schedule_flow_not_allowed`
- `linkedin_schedule_invalid_campaign_state`
- `linkedin_schedule_package_missing`
- `linkedin_schedule_variant_metadata_missing`
- `linkedin_schedule_artifact_missing`
- `linkedin_schedule_artifact_hash_changed`
- `linkedin_schedule_metadata_mismatch`
- `linkedin_schedule_no_variants`
- `linkedin_schedule_invalid_strategy`
- `linkedin_schedule_invalid_anchor`
- `linkedin_schedule_metadata_write_failed`

#### Scenario: Error codes are stable strings

- **WHEN** distribution scheduling fails for a known eligibility violation
- **THEN** the `errors` array contains the corresponding stable error code string

### Requirement: Test coverage

The repository MUST include `tests/test_linkedin_distribution_scheduling.py` covering at minimum:

- campaign not found
- Flow B rejected
- campaign before `derivatives_generated` rejected
- missing `linkedin_package` rejected
- missing variants rejected
- missing artifact rejected
- artifact hash changed rejected
- successful scheduling writes per-variant schedule metadata
- successful scheduling transitions to `distribution_scheduled`
- `publish_state` is `pending` for every variant
- variants are staggered, not simultaneous
- no LinkedIn API publication attempted
- no n8n workflow JSON changed
- metadata and response do not include generated body text
- idempotent rerun returns `completed` without duplicate `state_history`
- scheduling mismatch fails safely
- HTTP endpoint requires auth
- HTTP successful response shape
- HTTP invalid body returns 422

Full `pytest` and `openspec validate --all` MUST pass after apply.

#### Scenario: Test module exists and passes

- **WHEN** `pytest` runs after this child change is applied
- **THEN** `tests/test_linkedin_distribution_scheduling.py` passes and no n8n workflow JSON files are modified

### Requirement: Processed source path resolution for scheduling idempotency

When resolving a campaign by `source_relative_path`, `schedule_linkedin_distribution` MUST match `original_source_relative_path`, `queued_source_relative_path`, `processed_source_relative_path`, or active `source_relative_path` on the campaign document.

Idempotent re-run for campaigns in `distribution_scheduled` or later MUST NOT fail campaign resolution solely because the source Markdown is absent from `blog-posts/ready/` when `processed_source_relative_path` exists on disk.

Idempotent scheduling for active Flow A campaigns MUST NOT fail campaign resolution solely because the source Markdown is absent from `blog-posts/ready/` when `queued_source_relative_path` exists on disk.

Scheduling MUST continue to NOT relocate editorial source files; physical moves remain owned by `flow-a-operational-queue-lifecycle` and `flow-a-source-lifecycle-completion`.

#### Scenario: Schedule idempotency by original ready path after move

- **WHEN** `schedule_linkedin_distribution` is called with `source_relative_path` equal to a campaign's `original_source_relative_path` after lifecycle completion
- **THEN** the campaign is resolved and idempotent already-scheduled behavior applies

#### Scenario: Schedule idempotency by campaign_id without ready copy

- **WHEN** `schedule_linkedin_distribution` is called with `campaign_id` for a campaign in `distribution_scheduled` whose source exists only under `blog-posts/processed/`
- **THEN** the campaign is resolved and idempotent already-scheduled behavior applies without requiring `blog-posts/ready/`

#### Scenario: Schedule resolves queued source during active Flow A

- **WHEN** `schedule_linkedin_distribution` is called for a campaign whose source exists only under `blog-posts/queued/` during an in-progress Flow A execution
- **THEN** scheduling proceeds without campaign resolution failure due to missing `ready/` copy

### Requirement: Supervised defer of scheduled_at_utc while pending

The worker MUST allow operator defer (US-017) to update per-variant `scheduled_at_utc` while `publish_state` is `pending`.

Supervised defer MUST NOT rewrite schedule idempotency proof keys from the original Flow A schedule operation unless a new OpenSpec change explicitly defines reschedule idempotency semantics.

Supervised defer MUST append deferral history under `operator_supervision.deferral_history` on the variant entry.

Supervised defer MUST preserve stagger ordering intent: `new_scheduled_at_utc` for one variant MUST NOT require automatic sibling rescheduling in US-017 (sibling spacing adjustments are operator responsibility or future work).

Supervised defer MUST NOT transition campaign `state` away from `distribution_scheduled`.

#### Scenario: Defer updates only target variant schedule

- **WHEN** defer succeeds for one variant in a multi-variant campaign
- **THEN** only that variant's `scheduled_at_utc` changes and sibling variant schedules are unchanged

#### Scenario: Defer does not reset original schedule idempotency

- **WHEN** defer succeeds for a variant on an idempotent-completed schedule campaign
- **THEN** the original schedule idempotency proof remains intact and a repeat `POST /schedule-linkedin-distribution` with the same key still returns `completed` without rewriting original stagger proof

### Requirement: Supervised reschedule validation

Defer MUST reject `new_scheduled_at_utc` that is not strictly in the future relative to worker UTC now.

Defer MUST accept variants in `publish_state` **`pending` or `queued`** (US-084 not-yet-live postpone). Defer MUST reject variants that are Live on LinkedIn (`published`), `cancelled`, `failed`, or in-flight `publishing` (when distinguished), with a stable supervision error and no schedule mutation.

Defer MUST store all schedule timestamps in UTC ISO8601.

Defer MUST NOT call LinkedIn API as part of supervised reschedule.

#### Scenario: Future-only defer times

- **WHEN** defer is requested with `new_scheduled_at_utc` equal to or before current UTC time
- **THEN** the operation fails with `linkedin_supervision_defer_time_invalid`

#### Scenario: Defer accepts queued publish state

- **WHEN** defer is requested for a variant with `publish_state` `queued` and a valid future `new_scheduled_at_utc`
- **THEN** the operation is allowed under supervised reschedule validation (subject to density/cadence and other existing checks) and MUST NOT fail solely because the variant is queued

#### Scenario: Defer rejects published variant

- **WHEN** defer is requested for a variant with `publish_state` `published`
- **THEN** the operation fails with a stable supervision error and schedule is unchanged

### Requirement: Concurrent first-time distribution scheduling uses atomic metadata compare-and-swap

First-time distribution scheduling that persists the transition from `derivatives_generated` to `distribution_scheduled` and writes `linkedin_distribution` / per-variant schedule fields MUST use an atomic compare-and-swap (or equivalent) against the on-disk campaign metadata document so that two overlapping schedule attempts cannot both successfully write a first-time schedule for the same `campaign_id`.

When CAS detects that another writer changed the campaign document, the schedule service MUST re-read current state and either:

- return `status` `completed` when the campaign is already `distribution_scheduled` with matching schedule idempotency proof, without appending duplicate `state_history` or rewriting `scheduled_at_utc`, or
- fail closed with `linkedin_schedule_metadata_mismatch` when stored scheduling metadata does not match the expected proof.

This requirement hardens the US-034 duplicate-scheduling surface. It MUST NOT change eligibility rules, staggered strategy semantics, or the schedule-level idempotency key composition already defined by this capability.

#### Scenario: Racing first-time schedules produce one durable schedule write

- **WHEN** two concurrent `schedule_linkedin_distribution` calls both observe `derivatives_generated` for the same eligible campaign
- **THEN** at most one call persists a successful first-time `distribution_scheduled` write and the other ends as completed idempotent or fail-closed without a second distinct schedule set

#### Scenario: CAS loser observing matching peer schedule is idempotent completed

- **WHEN** a schedule CAS attempt loses to a peer that already wrote matching `distribution_scheduled` proof
- **THEN** the loser returns `status` `completed` without duplicate `state_history` and without changing peer `scheduled_at_utc` values

#### Scenario: CAS loser observing mismatched peer schedule fails closed

- **WHEN** a schedule CAS attempt loses to a peer whose stored schedule proof does not match this request’s expected key or anchors
- **THEN** the loser fails with `linkedin_schedule_metadata_mismatch` and does not overwrite peer schedule metadata

### Requirement: Flow B spill algorithm A scheduling strategy

The worker SHALL support LinkedIn distribution scheduling strategy `flow_b_spill_a` for Flow A campaigns that originated from a promoted Flow B blog (Flow B provenance with usable gap context). When `flow_b_spill_a` applies, per-variant `scheduled_at_utc` placement MUST follow spill algorithm A under US-040K local-day density max 2 (settings `density_max_per_local_day` default 2, never exceeding max 2): (1) target-week gap days (`empty_days[]`) chronological with remaining capacity; (2) other days in the target week with remaining capacity; (3) forward day-by-day after the week with remaining capacity. Occupancy MUST count LinkedIn members in `pending` / `queued` / `published` for density. Scheduling MUST NOT call LinkedIn API publish. If no day can be assigned without exceeding max 2, the operation MUST fail closed with a structured error.

#### Scenario: Spill A strategy places onto gap days first

- **WHEN** `schedule_linkedin_distribution` runs with strategy `flow_b_spill_a` for a `flow_a` campaign that has Flow B `target_week` and non-empty `empty_days[]` with available density capacity
- **THEN** the earliest variants receive `scheduled_at_utc` on those gap days in chronological order
- **AND** no local day receives more than density max 2 LinkedIn members

#### Scenario: Spill A spills within week then forward

- **WHEN** `flow_b_spill_a` scheduling has exhausted gap-day capacity and variants remain
- **THEN** remaining variants are placed on other days in the target week with remaining capacity
- **AND** then on subsequent local days after the week under max 2

#### Scenario: Spill A fails closed when density exhausted

- **WHEN** `flow_b_spill_a` cannot place a remaining variant without exceeding max 2 on candidate days in policy order
- **THEN** the operation fails with a structured scheduling error
- **AND** it does not write a partial schedule that exceeds density max 2

### Requirement: Auto-select spill A for Flow B provenance

When `schedule_linkedin_distribution` is invoked without an explicit alternate strategy (or with default strategy) and the campaign carries Flow B origin provenance with usable `target_week` / `empty_days[]` (from promoted sidecar or equivalent campaign metadata), the worker MUST resolve scheduling to `flow_b_spill_a`. When Flow B gap provenance is absent, the worker MUST continue to use default `flow_a_staggered`. An explicit request for `flow_a_staggered` MUST remain honored even for Flow B–origin campaigns. Unknown strategy names MUST continue to fail with `linkedin_schedule_invalid_strategy`. Campaign `flow` MUST remain `flow_a` for promoted Flow B blogs (Flow B provenance MUST NOT set campaign `flow` to `flow_b`).

#### Scenario: Default strategy selects spill A for Flow B origin with gap context

- **WHEN** `schedule_linkedin_distribution` is called for a `flow_a` campaign with Flow B provenance including `empty_days[]` and no explicit non-default strategy override
- **THEN** scheduling uses `flow_b_spill_a`

#### Scenario: Default strategy keeps stagger without Flow B gap provenance

- **WHEN** `schedule_linkedin_distribution` is called for a `flow_a` campaign without Flow B gap provenance and strategy is default
- **THEN** scheduling uses `flow_a_staggered`

#### Scenario: Explicit stagger override remains available

- **WHEN** `schedule_linkedin_distribution` is called with `strategy` `flow_a_staggered` for a Flow B–origin campaign
- **THEN** staggered scheduling is used
- **AND** spill algorithm A is not required for that request

### Requirement: Cadence-aware schedule-time placement and shift-forward (US-088)

When `schedule_linkedin_distribution` (including HTTP `POST /schedule-linkedin-distribution`) computes LinkedIn variant `scheduled_at_utc` values for strategies `flow_a_staggered` and `flow_b_spill_a`, the worker MUST evaluate same-campaign cadence feasibility at each candidate slot under the US-051 / US-020 meaning: the same gate as live `linkedin_publish_blocked_cadence` / related cadence skip at that candidate instant (minimum real interval of **72 hours** against same-campaign successful `published` evidence), using the same interval constant / shared helpers as the publish-time guard and US-087 projection (`CADENCE_MINIMUM_INTERVAL` / equivalent). The worker MUST NOT invent a second cadence engine or disagreeing 72h constant.

When the strategy’s preferred/candidate slot is **cadence-infeasible**, the worker MUST **shift forward** to the next **feasible** slot. A feasible slot MUST satisfy all of:

1. Not cadence-conflicted under the meaning above at that `scheduled_at_utc`
2. Remaining capacity under interim US-040K max **2** LinkedIn density members per operator-local day (including already-accepted slots in the current schedule batch)
3. Existing distribution strategy constraints for the path in use (`flow_a_staggered` audience order and minimum 3 calendar days between consecutive accepted variants; `flow_b_spill_a` empty-day → other week days → forward order)

While scanning forward, the worker MUST prefer US-052 preferred publishing windows as placement guidance (preferred local days Tuesday–Thursday; preferred local clocks 08:00–10:00 or 16:00–18:00; operator timezone America/Bogota) without treating those windows as a second publish-time cadence engine.

The worker MUST NOT silently keep a known cadence-infeasible preferred/candidate time as `scheduled_at_utc`. Successful schedule results and campaign metadata MUST record the shifted feasible `scheduled_at_utc` values so calendar / schedule-visibility times reflect the placement.

Cadence-infeasible MUST NOT be redefined to mean density-full alone, sequence-alone, OAuth missing, or publication enablement off.

#### Scenario: Preferred slot shifts forward when cadence-infeasible

- **WHEN** `schedule_linkedin_distribution` computes a preferred candidate `scheduled_at_utc` that would hit same-campaign US-020 cadence refuse/skip against existing `published` evidence
- **THEN** the worker does not write that infeasible preferred time
- **AND** it assigns a later feasible `scheduled_at_utc` that clears cadence and respects density max 2 and the active strategy constraints
- **AND** the schedule result / campaign metadata expose the shifted time

#### Scenario: Feasible preferred slot is kept

- **WHEN** the preferred candidate slot is cadence-feasible and satisfies density max 2 and strategy constraints
- **THEN** the worker schedules that slot without unnecessary forward shift

#### Scenario: Density is respected during shift-forward

- **WHEN** shift-forward considers a candidate local day that already has 2 density members (excluding capacity freed only by rules already defined for density evaluation)
- **THEN** that day is not accepted as a feasible slot
- **AND** scanning continues forward within bounds

#### Scenario: Stagger strategy preserves sequence and day spacing after shift

- **WHEN** `flow_a_staggered` shifts a later variant forward for cadence
- **THEN** audience sequencing order is preserved
- **AND** consecutive accepted variants remain at least 3 calendar days apart

#### Scenario: Spill A order remains authoritative for day priority

- **WHEN** `flow_b_spill_a` placement encounters a spill-ordered candidate day that is cadence-infeasible
- **THEN** the worker advances to a later feasible slot without inverting spill priority (empty days before other week days before post-week forward days)
- **AND** density max 2 remains enforced

#### Scenario: Cadence meaning matches publish-time / US-087 helpers

- **WHEN** schedule-time cadence feasibility is evaluated for a candidate slot
- **THEN** evaluation uses the same 72h interval and published-evidence semantics as the publish-time guard / US-087 projection helpers
- **AND** density-full alone, sequence-alone, OAuth, and enablement-off are not labeled as cadence conflict

### Requirement: Fail-closed when no feasible slot within US-052 horizon (US-088)

Forward search for a feasible `scheduled_at_utc` MUST be finite. The default horizon MUST be **28 operator-local days** measured from the original preferred/candidate slot’s operator-local calendar day as **day 0**, searching day 0 (at/after the candidate clock under window/strategy rules) and local days **1…28** inclusive, per `docs/operations/linkedin-publishing-windows-and-shift-forward-policy.md`. Infinite scan is forbidden.

If no feasible slot exists within that horizon for a required variant, scheduling MUST **fail closed** with structured error code `linkedin_schedule_no_feasible_slot` (operator-visible via schedule result / HTTP error mapping consistent with existing LinkedIn schedule errors). The worker MUST NOT write a partial schedule that leaves a known cadence-infeasible preferred time in place for the failing variant.

This failure mode MUST remain distinct from `linkedin_schedule_spill_density_exhausted` when the failure is specifically inability to find any cadence+density+strategy-feasible slot within the horizon (implementations MAY still return density-exhausted when spill density is exhausted under existing spill-only rules without a cadence horizon search applying).

#### Scenario: No feasible slot within 28 local days fails closed

- **WHEN** cadence-aware shift-forward cannot find a feasible slot within 28 operator-local days from the original candidate local day
- **THEN** scheduling fails with `linkedin_schedule_no_feasible_slot`
- **AND** it does not silently persist an infeasible preferred `scheduled_at_utc` for the affected placement

#### Scenario: Infinite scan is forbidden

- **WHEN** schedule-time shift-forward runs
- **THEN** candidate search does not continue past the documented 28 operator-local-day horizon

### Requirement: Schedule-time shift-forward does not publish or bypass enablement (US-088)

Cadence-aware placement and shift-forward MUST NOT call LinkedIn API publish endpoints and MUST NOT bypass or force-enable `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. Scheduled variants MUST remain `publish_state` `pending` on first-time schedule success (unchanged from existing scheduling contracts). US-020 publish-time cadence evaluation remains authoritative at send. US-087 schedule-visibility `cadence_conflict` projection MUST NOT be weakened by this change; residual post-placement cadence conflicts (rare) MUST still be projectable/warnable.

#### Scenario: Successful cadence-aware schedule does not publish

- **WHEN** cadence-aware `schedule_linkedin_distribution` succeeds (with or without shifting)
- **THEN** no LinkedIn API publish is attempted
- **AND** scheduled variants have `publish_state` `pending`

#### Scenario: Enablement is not bypassed by scheduling

- **WHEN** cadence-aware scheduling runs while publication enablement is off
- **THEN** scheduling still does not call LinkedIn API publish and does not force enablement on

#### Scenario: Residual cadence conflict projection remains available

- **WHEN** after placement a not-yet-Live LinkedIn item remains cadence-infeasible at its written `scheduled_at_utc` (edge case)
- **THEN** schedule-visibility MAY still project `cadence_conflict` true under existing US-087 rules
- **AND** this change does not remove or redefine that projection to ignore true cadence conflicts
