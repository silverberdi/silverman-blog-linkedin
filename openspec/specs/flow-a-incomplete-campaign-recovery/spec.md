# flow-a-incomplete-campaign-recovery

## Purpose

Operator-facing incomplete Flow A campaign recovery contract for US-031: authenticated inspect of last-valid-stage from persisted campaign evidence, idempotent resume of unfinished worker stages, allowlisted metadata/filesystem repair, secret-safe operator-visible outcomes, and fail-closed ambiguity handling. LinkedIn API publication recovery remains owned by `linkedin-retry-recovery-classification`. US-032 recovery-action taxonomy, attempt-history persistence, and safe cancellation are out of scope.

## Requirements

### Requirement: Incomplete campaign recovery purpose and scope

The worker SHALL provide an authenticated incomplete Flow A campaign recovery capability that lets an operator identify the last valid durable stage of a campaign that has not reached consistent campaign lifecycle completion, resume unfinished worker stages without repeating confirmed durable side effects, and repair allowlisted metadata inconsistencies when evidence is unambiguous.

This capability MUST apply to `flow: flow_a` campaigns under `metadata/campaigns/`. It MUST NOT be the primary surface for LinkedIn API publication retry/recovery (owned by `linkedin-retry-recovery-classification`). It MUST NOT implement US-032 recovery-action taxonomy, dedicated recovery attempt-history persistence, or safe cancellation.

Campaign lifecycle state `flow_a_complete` remains campaign lifecycle metadata only and MUST NOT be described as unqualified product “Flow A complete.”

#### Scenario: Capability is scoped to Flow A incomplete-campaign recovery

- **WHEN** an operator invokes incomplete-campaign recovery for a Flow A campaign that stopped before consistent lifecycle completion
- **THEN** the worker derives last-valid-stage and supports inspect, resume, and allowlisted repair without invoking LinkedIn publication recovery as the primary path

#### Scenario: Non-Flow-A campaigns are rejected

- **WHEN** recovery is requested for a campaign whose `flow` is not `flow_a`
- **THEN** the worker rejects the request with a stable machine-readable error and performs no metadata or filesystem mutation

### Requirement: Authenticated inspect endpoint is read-only

The worker SHALL expose `GET /flow-a/incomplete-campaign-recovery/{campaign_id}` protected by API-key authentication through `Depends(require_api_key)`.

Inspect MUST resolve the campaign only under the configured editorial base path, derive recovery status from persisted evidence, and return structured JSON. Inspect MUST NOT write campaign metadata, move editorial files, call ComfyUI, DeepSeek, LinkedIn, OAuth, Git, or live-site endpoints, or accept client-supplied absolute filesystem paths.

Missing campaigns MUST return a stable not-found error. Authentication failure MUST return HTTP 401 without reading or mutating campaign artifacts beyond auth handling.

#### Scenario: Authenticated inspect returns last-valid-stage without mutation

- **WHEN** a client with a valid API key calls `GET /flow-a/incomplete-campaign-recovery/{campaign_id}` for an existing Flow A campaign
- **THEN** the worker returns HTTP 200 with `last_valid_stage`, effective `recovery_classification`, outcome visibility fields, and performs zero filesystem or metadata writes

#### Scenario: Inspect requires API-key authentication

- **WHEN** a client calls the inspect endpoint without a valid API key
- **THEN** the worker returns HTTP 401 and does not expose campaign recovery details

#### Scenario: Unknown campaign is a clear failure

- **WHEN** inspect is called for a `campaign_id` with no campaign metadata file
- **THEN** the worker returns a stable not-found error and does not create a campaign document

### Requirement: Derive last valid durable stage from persisted evidence

Incomplete-campaign recovery SHALL derive `last_valid_stage` as the highest confirmed durable milestone in this order:

`ready` → `validated` → `blog_published` → `derivatives_generated` → `distribution_scheduled` → `flow_a_complete`

Derivation MUST consider current pipeline `state`, `state_history` durable `to_state` values, and durable stage evidence. The worker MUST NOT invent new lifecycle state values for this derivation.

A milestone is confirmed only when its required durable evidence is present and consistent:

- `validated` — campaign is not solely in `validation_failed` and validation success evidence is present per lifecycle/validation contracts
- `blog_published` — `blog_publish.status` is `completed` or `already_published` with identity/idempotency evidence required by blog publish specs
- `derivatives_generated` — durable package/variant evidence required by LinkedIn package-generation specs is present
- `distribution_scheduled` — durable `linkedin_distribution` and per-variant schedule evidence required by scheduling specs is present
- `flow_a_complete` — `state` is `flow_a_complete` and `source_file_status.location` is `processed` with consistent consumption evidence

When evidence conflicts such that confirming a milestone would require guessing (for example state claims `blog_published` but `blog_publish` success evidence is absent or contradictory), the worker MUST fail closed: set inspect outcome to blocked with stable code `flow_a_recovery_evidence_ambiguous`, preserve or set `recovery_classification=repair_required` as appropriate, and MUST NOT treat the conflicting milestone as last-valid.

Pending intermediate states (`blog_publish_pending`, `derivatives_pending`) MUST NOT be reported as `last_valid_stage`.

#### Scenario: Last valid stage is blog_published after publish evidence

- **WHEN** campaign evidence confirms durable `blog_publish` success and does not confirm derivatives or schedule milestones
- **THEN** inspect reports `last_valid_stage=blog_published` and identifies package generation as the next unfinished worker stage

#### Scenario: Ambiguous publish evidence blocks stage confirmation

- **WHEN** campaign `state` or history suggests `blog_published` but `blog_publish.status` is not a confirmed success value
- **THEN** inspect reports blocked with `flow_a_recovery_evidence_ambiguous` and does not confirm `blog_published` as last-valid

#### Scenario: Consistent flow_a_complete is reported as terminal milestone

- **WHEN** `state` is `flow_a_complete` and `source_file_status.location` is `processed` with consistent evidence
- **THEN** inspect reports `last_valid_stage=flow_a_complete` and resume is a no-op skip rather than reprocessing completed stages

### Requirement: Authenticated resume endpoint is idempotent

The worker SHALL expose `POST /flow-a/incomplete-campaign-recovery/resume` protected by API-key authentication.

The JSON body MUST include `campaign_id` and MAY include:

- `dry_run` (boolean, default `false`)
- `stop_after_stage` (optional durable milestone name; when set, resume stops after completing that stage or determining it is already complete)

Resume MUST NOT accept client-supplied absolute filesystem paths. Default resume MUST NOT enable Git publication, live-site confirmation, or LinkedIn API publication.

When `dry_run` is `true`, resume MUST return the planned `last_valid_stage`, `next_stage`, and per-stage intents without writing metadata, moving files, or invoking mutating stage side effects.

When evidence is unambiguous and the campaign is eligible, resume MUST advance remaining unfinished Flow A worker stages in order (publish → package → schedule → source lifecycle completion), short-circuiting stages whose durable evidence already satisfies the corresponding milestone via existing idempotency contracts. Resume MUST NOT create a second campaign document, regenerate completed package artifacts, republish an already-published blog identity, or create duplicate schedule slots.

Resume MUST reject with `recovery_classification=manual_intervention_required` (or preserve that classification) when `execution_state=processing` and the claim is not stale. Stale claims MUST be reclaimed using existing stale/reclaim rules before continuing.

When `source_file_status.location=error`, resume MUST NOT silently requeue; it MUST return blocked with `requeue_required` and a clear operator-visible reason that explicit requeue is required before resume.

Ambiguous evidence MUST fail closed with `flow_a_recovery_evidence_ambiguous` and zero stage side effects.

#### Scenario: Resume skips completed blog publish and continues later stages

- **WHEN** resume runs for a campaign whose last-valid-stage is `blog_published` and package/schedule are unfinished
- **THEN** the worker does not overwrite public blog publish outputs for the existing identity, runs only unfinished later worker stages, and returns an understandable per-stage summary

#### Scenario: Dry-run resume plans without mutation

- **WHEN** resume is called with `dry_run=true` for an incomplete eligible campaign
- **THEN** the response describes intended skips and runs and campaign metadata bytes and editorial files are unchanged

#### Scenario: Active non-stale claim blocks resume

- **WHEN** resume is requested while `execution_state=processing` and the claim is not stale
- **THEN** the worker returns blocked with `manual_intervention_required` and performs no stage side effects

#### Scenario: Error-folder campaign requires explicit requeue before resume

- **WHEN** resume is requested for a campaign with `source_file_status.location=error`
- **THEN** the worker returns blocked with `requeue_required` and does not move the source or re-run pipeline stages

#### Scenario: Completed campaign resume is a visible no-op

- **WHEN** resume is requested for a campaign whose last-valid-stage is consistent `flow_a_complete`
- **THEN** the worker returns an understandable skip/no-op outcome and does not duplicate completed work

### Requirement: Authenticated repair endpoint is explicit and fail-closed

The worker SHALL expose `POST /flow-a/incomplete-campaign-recovery/repair` protected by API-key authentication.

The JSON body MUST include `campaign_id`, an explicit `repair_action`, and MAY include `dry_run` (boolean, default `false`). Repair MUST NOT accept client-supplied absolute filesystem paths.

Allowed `repair_action` values for this change are exactly:

- `sync_location_from_filesystem` — when the campaign Markdown identity resolves to exactly one approved editorial location (`ready`, `queued`, `processed`, or `error`) that disagrees with metadata `location`, update `source_file_status` and related path fields to the observed location without inventing stage success evidence
- `clear_stale_execution_claim` — when the campaign is stale by canonical stale rules, release/reclaim to `execution_state=idle` using existing helpers without erasing durable stage evidence
- `complete_partial_source_move` — when `physical_move_state=partial` and the remaining sibling move is unambiguous and safe, complete that move and update move evidence

Unknown `repair_action` values MUST return HTTP 422 with zero mutation.

Repair MUST refuse with a stable code and zero mutation when multiple locations match, identity/hash evidence conflicts, inventing `blog_publish` / package / schedule success would be required, marking `flow_a_complete` would be required without processed consumption evidence, or an active non-stale processing claim blocks safe mutation.

When `dry_run` is `true`, repair MUST describe the would-be before/after safe fields without writing.

#### Scenario: Location sync repairs unambiguous metadata mismatch

- **WHEN** repair `sync_location_from_filesystem` is requested and the source Markdown exists only under `blog-posts/queued/` while metadata `location` is `ready`
- **THEN** the worker updates location-related metadata to `queued`, returns an understandable before/after summary, and does not alter `blog_publish`, variants, or schedule evidence

#### Scenario: Ambiguous location repair fails closed

- **WHEN** repair `sync_location_from_filesystem` is requested and matching Markdown identity exists in more than one editorial folder or cannot be uniquely resolved
- **THEN** the worker returns a stable ambiguity/conflict error and performs no metadata or file mutation

#### Scenario: Repair refuses to invent blog publish success

- **WHEN** any repair action would require setting `blog_publish.status` to a success value without authoritative publish evidence
- **THEN** the worker rejects the repair with a stable error and leaves campaign evidence unchanged

#### Scenario: Unknown repair action is rejected

- **WHEN** repair is called with a `repair_action` outside the allowlist
- **THEN** the worker returns HTTP 422 and performs no mutation

### Requirement: Operator-visible outcomes and secret-safe payloads

Inspect, resume, and repair responses MUST be understandable without opening raw files. Each successful or blocked response MUST include at minimum:

- `campaign_id`
- `last_valid_stage` when derivable
- effective `recovery_classification` using the canonical five-value enum from `flow-a-operational-queue-lifecycle`
- `outcome` (`ok`, `blocked`, `failed`, `noop`, or `partial` as applicable)
- stable `reason_code` or per-stage reason codes when blocked or failed
- short human-readable `summary`

Mutating responses MUST additionally include whether `dry_run` was applied and a per-stage or before/after safe summary.

Payloads MUST NOT include Markdown or draft bodies, API keys, tokens, client secrets, authorization headers, raw external API bodies, arbitrary environment values, or the absolute editorial base path.

#### Scenario: Blocked state is clearly communicated

- **WHEN** resume is blocked by ambiguous evidence
- **THEN** the response includes `outcome` blocked, `reason_code=flow_a_recovery_evidence_ambiguous`, `recovery_classification=repair_required` (or an already more severe canonical classification), and a short summary an operator can understand

#### Scenario: Secrets and content bodies are excluded

- **WHEN** campaign documents contain tokens, secret-shaped fields, or content bodies
- **THEN** none of those values appear in inspect, resume, or repair responses

### Requirement: Existing completed work is preserved

Incomplete-campaign recovery MUST preserve confirmed durable side-effect evidence. Resume and repair MUST NOT duplicate blog publish outputs for an already-published identity, MUST NOT regenerate completed LinkedIn package artifacts when package idempotency says reuse, MUST NOT create duplicate distribution schedule slots when already scheduled, and MUST NOT unintentionally rewrite unrelated campaign fields.

Inspect MUST guarantee byte-identical campaign and editorial artifacts before and after the call.

#### Scenario: Inspect does not change on-disk artifacts

- **WHEN** inspect runs successfully against a campaign and editorial tree
- **THEN** campaign metadata and editorial files are byte-identical before and after the call

#### Scenario: Resume does not duplicate an already scheduled distribution

- **WHEN** resume reaches the schedule stage for a campaign that already has durable schedule evidence
- **THEN** scheduling short-circuits as already scheduled and no duplicate variant schedule records are created
