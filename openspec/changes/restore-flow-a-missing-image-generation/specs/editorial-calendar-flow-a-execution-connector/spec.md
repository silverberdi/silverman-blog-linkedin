## ADDED Requirements

### Requirement: Connector does not block on missing generatable PNG or image before publish

The connector MUST NOT invoke blocking full `validate_ready_post()` before `publish_blog_post` for eligible real-execution items.

Pre-generation validation and full validation MUST be owned by `publish_blog_post` per `worker-blog-publishing-endpoint`.

The connector MUST NOT fail an item with `ready_post_image_missing` before `publish_blog_post` when the source is Markdown-only with absent, empty, or canonical frontmatter `image` and automatic generation is eligible.

#### Scenario: Markdown-only queued source reaches publish without connector image failure

- **WHEN** real execution queue-accepts Markdown-only `blog-posts/ready/01-example.md` to `blog-posts/queued/01-example.md` with absent `image` and no PNG
- **THEN** the connector invokes `publish_blog_post` without prior full validation failure and does not record `ready_post_image_missing` at the connector validation step

#### Scenario: Connector does not stub away validation in integration tests

- **WHEN** integration tests prove the Markdown-only connector path
- **THEN** tests MUST NOT patch or autouse-stub `validate_ready_post` or `validate_ready_post_pre_generation` for assertions on that path

### Requirement: Image-related failure claim-release matrix

For image-related `publish_blog_post` failures after `claim_flow_a_execution`, the connector MUST apply exactly one claim-release path per case:

| Failure class | `release_flow_a_execution` | Notes |
|---------------|---------------------------|-------|
| ComfyUI transient (`blog_image_generation_*` retryable) | Exactly once | No downstream steps |
| Local write/patch inconsistency | Exactly once when claim `processing` | `repair_required` |
| Public handoff after full validation | Exactly once | `repair_required`; preserve editorial PNG |
| Hash metadata persistence failure | Exactly once when applicable | No handoff or publish |
| Deterministic pre/full validation before handoff with error move | Error move owns closure | Connector MUST NOT redundantly release |
| Error move or metadata failure during deterministic move | Per `repair_required` policy | No redundant release |

The connector MUST NOT invoke `generate_linkedin_package`, `schedule_linkedin_distribution`, or `complete_flow_a_source_lifecycle` on any image-related publish failure.

Integration tests MUST assert persisted campaign state and exact `release_flow_a_execution` call count for representative failure classes.

#### Scenario: ComfyUI transient failure releases claim once

- **WHEN** `publish_blog_post` fails with `blog_image_generation_timeout` after claim
- **THEN** connector calls `release_flow_a_execution` exactly once, leaves source in `queued/`, and does not invoke downstream steps

#### Scenario: Handoff failure releases claim once

- **WHEN** `publish_blog_post` fails with `blog_image_public_asset_handoff_failed` after full validation
- **THEN** connector calls `release_flow_a_execution` exactly once, sets `repair_required`, and does not invoke downstream steps

#### Scenario: Deterministic validation error move does not double-release

- **WHEN** post-acceptance editorial validation error move closes the claim while moving source to `error/`
- **THEN** connector does not call `release_flow_a_execution` again

## MODIFIED Requirements

### Requirement: Real execution Flow A sequence with result chaining

When `dry_run` is `false`, the connector MUST execute Flow A only for items where:

- Planner `selection_status` is `selected`
- `review_required` is `false`
- `flow_type` is `flow_a_ready_blog_post` and `content_mode` is `user_provided_approved_blog`
- Item is not skipped per existing-campaign or other skip rules

For each eligible item, the connector MUST invoke internal services in strict order:

0. `accept_flow_a_source_for_queue` (canonical spec `flow-a-operational-queue-lifecycle`) when source is in `blog-posts/ready/`; or resolve already-queued campaign per already-queued connector requirement when source has previously been accepted
1. `claim_flow_a_execution` then `publish_blog_post` — which owns pre-generation validation, editorial image remediation, authorized hash reconciliation, full validation, public handoff, and blog publication
2. `generate_linkedin_package`
3. `schedule_linkedin_distribution`
4. `complete_flow_a_source_lifecycle` (canonical spec `flow-a-source-lifecycle-completion`) — terminal completion sets `location=processed` and `execution_state=idle`
5. `release_flow_a_execution` ONLY on recoverable or failed non-terminal exits not already closed by error move; if invoked after successful lifecycle completion it MUST be idempotent (`already_released`)

The connector MUST NOT call `validate_ready_post()` or `validate_ready_post_pre_generation()` as a separate blocking step before `publish_blog_post`.

Each subsequent step MUST use the actual result object from the immediately prior step as its primary input source:

- After queue acceptance or already-queued resolution: publish MUST use `campaign_id` and active queued `source_relative_path` from acceptance or skip result
- After publish: `generate_linkedin_package` MUST prefer `campaign_id` from the publish result; when absent, MUST use `source_relative_path` from the publish result. Calendar `site_url` and other supported calendar fields MAY be passed when present.
- After package: `schedule_linkedin_distribution` MUST prefer `campaign_id` from the package result; when absent, MUST use `source_relative_path` from the package result. Calendar `strategy` MAY be passed when present and supported.
- After schedule: `complete_flow_a_source_lifecycle` MUST prefer `campaign_id` from the schedule result; when absent, MUST use `source_relative_path` from the schedule result.

The publish step result (`BlogPublishResult`) is the source of truth for resolved `campaign_id`, `source_public_url`, published blog path (`source_relative_path`), and blog publish status. Calendar hints MUST NOT override resolved publish/package outputs for subsequent steps.

The connector MUST preserve existing idempotency behavior of downstream services.

Lifecycle completion MUST NOT run when `schedule_linkedin_distribution` fails.

When scheduling succeeds but lifecycle completion fails, item `execution_status` MUST remain `executed` (scheduling succeeded) and item results MUST include `source_lifecycle_status` `failed` with lifecycle `errors[]` and `warnings[]` merged without exposing secrets.

When lifecycle completion succeeds or skips as already processed, item results MUST include `source_lifecycle_status` `completed` or `skipped`.

Item results MUST include `queue_acceptance_status` (`completed`, `skipped_already_queued`, `failed`, `partial`, `repair_required`) when queue stage runs.

When `publish_blog_post` fails with pre-generation or full validation errors before public handoff after queue acceptance, the connector MUST apply existing post-acceptance editorial validation failure policy (move to `error/` when deterministic) and MUST NOT redundantly release a claim already closed by error move.

When `publish_blog_post` fails with ComfyUI transient errors, the connector MUST apply retryable queued policy, call `release_flow_a_execution` exactly once, and MUST NOT classify the failure as `ready_post_image_missing`.

When `publish_blog_post` fails with public handoff errors after full validation, the connector MUST apply `repair_required` queued policy, call `release_flow_a_execution` exactly once, and preserve editorial PNG evidence.

#### Scenario: Real mode Markdown-only executes remediation inside publish

- **WHEN** `dry_run=false`, one eligible due Flow A item exists with Markdown-only source in `blog-posts/ready/` (absent `image`), queue acceptance succeeds, and ComfyUI generation is enabled
- **THEN** `publish_blog_post` is invoked with queued `source_relative_path`, editorial remediation and handoff run inside publish in staged order, blog publication proceeds on success, and lifecycle completion moves both queued Markdown and generated PNG to `blog-posts/processed/`

#### Scenario: Real mode executes queue acceptance then Flow A sequence

- **WHEN** `dry_run=false`, one eligible due Flow A item exists with source in `blog-posts/ready/`, and no skip rule applies
- **THEN** `accept_flow_a_source_for_queue`, `publish_blog_post`, `generate_linkedin_package`, `schedule_linkedin_distribution`, and `complete_flow_a_source_lifecycle` are invoked in order, the source ends under `blog-posts/processed/`, and the item `execution_status` is `executed` when scheduling succeeds

#### Scenario: Real mode uses internal services not HTTP self-calls

- **WHEN** real execution runs for an eligible item
- **THEN** the connector invokes Python service functions directly rather than HTTP loopback to worker endpoints

#### Scenario: Schedule failure skips lifecycle completion

- **WHEN** `schedule_linkedin_distribution` fails for an item in real execution mode after queue acceptance
- **THEN** `complete_flow_a_source_lifecycle` is not invoked and source files remain in `blog-posts/queued/`

#### Scenario: ComfyUI failure keeps source in queued with single release

- **WHEN** `publish_blog_post` fails with `blog_image_generation_timeout` after queue acceptance
- **THEN** the connector does not invoke lifecycle completion, source remains in `blog-posts/queued/`, `release_flow_a_execution` is called exactly once, and generated partial artifacts are preserved when present
