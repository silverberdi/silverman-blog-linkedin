## ADDED Requirements

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

## MODIFIED Requirements

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
