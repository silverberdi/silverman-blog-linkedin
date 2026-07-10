## ADDED Requirements

### Requirement: Authorized image-remediation source hash mutation

When editorial image remediation patches or normalizes the canonical frontmatter `image` field as the only authorized Markdown mutation, the worker MUST follow this protocol on the same campaign:

1. Record or retain the queue/intake digest for traceability in `intake_source_content_sha256` when not already set; otherwise preserve the existing intake value.
2. Allow only the expected canonical `image` frontmatter mutation by the image-remediation phase.
3. Recompute active `source_content_sha256` from updated Markdown bytes via `compute_source_content_sha256`.
4. Persist the updated active hash on the same campaign before full validation and publish idempotency checks.
5. Recompute the blog publish idempotency key from the updated active hash per existing namespaced key format.
6. Preserve `campaign_id`, `source_slug`, `public_slug`, original path chain, queue metadata, attempt metadata, and `state_history`.
7. MUST NOT classify authorized remediation as `campaign_content_hash_changed` or `blog_publish_content_hash_changed`.
8. Any unrelated body or frontmatter mutation MUST still fail with the existing content-hash guard.
9. Metadata-write failure during authorized hash reconciliation MUST block publish, return a stable explicit metadata error, and MUST NOT write public repo files.

Authorized remediation MUST NOT create a new campaign document.

#### Scenario: Missing image field patched by worker changes hash safely

- **WHEN** editorial remediation adds `image: /assets/images/<public_slug>.png` to a queued source that omitted `image`
- **THEN** `source_content_sha256` updates to the new digest, `intake_source_content_sha256` retains the pre-remediation digest, and `campaign_content_hash_changed` is not raised

#### Scenario: Same campaign retained after authorized hash update

- **WHEN** authorized hash reconciliation succeeds after frontmatter patch
- **THEN** `campaign_id`, `source_slug`, `public_slug`, and queue path metadata remain unchanged on the same campaign document

#### Scenario: Active hash and idempotency key updated

- **WHEN** authorized hash reconciliation succeeds
- **THEN** stored `source_content_sha256` and `blog_publish.idempotency_key` reflect the post-remediation digest before full validation and publish proceed

#### Scenario: Body mutation still rejected

- **WHEN** Markdown body bytes change between queue acceptance and publish outside authorized image remediation
- **THEN** validation or publish guards fail with `campaign_content_hash_changed` or `blog_publish_content_hash_changed` and do not overwrite progressed metadata

#### Scenario: Hash metadata persistence failure blocks handoff and publish

- **WHEN** authorized hash reconciliation cannot persist campaign metadata
- **THEN** publish returns failed with primary error `blog_publish_hash_reconciliation_failed`, public handoff is not invoked, and no public repo files are written

## MODIFIED Requirements

### Requirement: Campaign metadata required fields

Each campaign metadata document MUST include at minimum the existing required fields per canonical `flow-a-lifecycle`.

When queue acceptance records an intake digest, the document MUST also include `intake_source_content_sha256` set to the SHA-256 digest at acceptance time.

`source_content_sha256` MUST always represent the active canonical source digest used for publish and derivative idempotency. After authorized image-remediation frontmatter patch, `source_content_sha256` MUST be updated to the post-remediation digest while `intake_source_content_sha256` preserves the pre-remediation digest for traceability.

#### Scenario: Intake hash preserved after authorized remediation

- **WHEN** editorial remediation patches frontmatter `image` after queue acceptance
- **THEN** `intake_source_content_sha256` remains the acceptance-time digest and `source_content_sha256` reflects the updated Markdown bytes
