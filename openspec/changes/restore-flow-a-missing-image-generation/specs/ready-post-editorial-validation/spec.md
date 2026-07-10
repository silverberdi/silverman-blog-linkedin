## ADDED Requirements

### Requirement: Pre-generation validation entry point

The worker SHALL expose a pure pre-generation validation entry point (for example `validate_ready_post_pre_generation(base_path, source_relative_path, *, site_url=None, image_generation_enabled=None)`) that validates deterministic editorial requirements without requiring a companion PNG or canonical non-empty frontmatter `image` when automatic image generation is eligible.

Pre-generation validation MUST validate:

- safe confined Markdown path under `blog-posts/ready/` or `blog-posts/queued/`;
- `.md` extension;
- readable non-empty content;
- frontmatter parsing;
- required editorial fields except generatable `image` when remediation is eligible;
- canonical public slug derivation;
- publication-date rules;
- campaign identity and source hash compatibility when campaign context is supplied.

Pre-generation validation MUST NOT fail with `ready_post_image_missing` when:

- frontmatter `image` is absent, empty/whitespace-only, OR equals `/assets/images/<public_slug>.png`;
- no same-basename companion PNG exists beside the active Markdown;
- image generation is enabled and available for the Flow A path;
- the source is eligible for automatic ComfyUI generation per `comfyui-blog-image-generation`;
- no unsafe or conflicting image reference exists (for example same-basename non-PNG extension).

Pre-generation validation MUST still fail for:

- non-empty non-canonical frontmatter `image` (any value other than `/assets/images/<public_slug>.png`);
- conflicting same-basename non-PNG extensions;
- unsafe paths;
- unreadable or empty content;
- other deterministic non-image requirements.

When image generation is disabled, pre-generation validation MUST NOT waive missing/empty `image` or missing PNG requirements that full validation will enforce; generation-disabled behavior remains strict.

#### Scenario: Markdown-only queued source with absent image field passes pre-generation validation

- **WHEN** `validate_ready_post_pre_generation` is called for `blog-posts/queued/01-example.md` with frontmatter omitting `image`, no companion PNG on disk, and ComfyUI generation enabled
- **THEN** the result has `ok: true` and does not include `ready_post_image_missing` or a frontmatter image error in `errors[]`

#### Scenario: Markdown-only queued source with empty image passes pre-generation validation

- **WHEN** `validate_ready_post_pre_generation` is called for `blog-posts/queued/01-example.md` with frontmatter `image` empty or whitespace-only, no companion PNG, and ComfyUI generation enabled
- **THEN** the result has `ok: true` and does not include `ready_post_image_missing` in `errors[]`

#### Scenario: Non-canonical non-empty image blocks pre-generation

- **WHEN** `validate_ready_post_pre_generation` is called and frontmatter `image` is `/assets/images/wrong-slug.png`
- **THEN** the result has `ok: false` with a frontmatter image error and does not proceed as generation-eligible

#### Scenario: Generation disabled does not bypass strict image requirements at full validation

- **WHEN** `validate_ready_post_pre_generation` is called for Markdown-only source with absent `image` and generation disabled, pre-generation may pass, and `validate_ready_post` is subsequently called after editorial remediation is skipped
- **THEN** full validation fails with an appropriate image error (`ready_post_image_missing` or frontmatter image error) and publish does not proceed

#### Scenario: Non-PNG same-basename blocks pre-generation

- **WHEN** `validate_ready_post_pre_generation` is called, companion `.png` is absent, and a same-basename `.jpg` exists beside the Markdown
- **THEN** the result has `ok: false` with error code `ready_post_image_invalid_extension`

## MODIFIED Requirements

### Requirement: Image validation

The expected companion image MUST be exactly `<active_source_folder>/<source_slug>.png` where `<active_source_folder>` is `blog-posts/ready` or `blog-posts/queued` derived from `source_relative_path` — same basename as the Markdown file with `.png` extension.

Example (ready): `blog-posts/ready/01-why-i-did-not-start-with-the-database.png` for source `blog-posts/ready/01-why-i-did-not-start-with-the-database.md`.

Example (queued): `blog-posts/queued/01-why-i-did-not-start-with-the-database.png` for source `blog-posts/queued/01-why-i-did-not-start-with-the-database.md`.

Image extension MUST be `.png` for Flow A (current publishing bridge expects PNG).

Full validation (`validate_ready_post`) MUST enforce:

- canonical non-empty frontmatter `image` equal to `/assets/images/<public_slug>.png`;
- companion PNG presence, extension, and readability beside the active source folder;

when invoked by `publish_blog_post` after editorial image remediation.

When the expected `.png` is missing during **full** validation:

- If a same-basename file with a non-`.png` extension exists (for example `.jpg`, `.webp`), validation MUST fail with error code `ready_post_image_invalid_extension`.
- If no same-basename image file exists at all, validation MUST fail with error code `ready_post_image_missing`.

Pre-generation validation MUST NOT apply the missing-PNG or missing/empty-`image` failure when generation eligibility conditions are met (see pre-generation validation requirement).

#### Scenario: Matching PNG present in queued folder

- **WHEN** both `blog-posts/queued/01-why-i-did-not-start-with-the-database.md` and `blog-posts/queued/01-why-i-did-not-start-with-the-database.png` exist and frontmatter `image` is canonical
- **THEN** `validate_ready_post` returns `image_relative_path` `blog-posts/queued/01-why-i-did-not-start-with-the-database.png` and no image error is recorded

#### Scenario: Missing PNG fails full validation after remediation step

- **WHEN** `validate_ready_post` is called after editorial image remediation was required but did not produce a companion PNG
- **THEN** validation fails with error code `ready_post_image_missing`

#### Scenario: Missing image field does not fail pre-generation when generation eligible

- **WHEN** `validate_ready_post_pre_generation` is called for Markdown-only `blog-posts/queued/01-example.md` with absent `image` and generation enabled
- **THEN** validation does not fail with `ready_post_image_missing` or a frontmatter image error

#### Scenario: Non-PNG same-basename image only

- **WHEN** the Markdown file exists, the expected `.png` is absent, but a same-basename `.jpg` or other non-`.png` image exists beside the Markdown in the active folder
- **THEN** full validation fails with error code `ready_post_image_invalid_extension` and NOT `ready_post_image_missing`

### Requirement: Validation entry point

The worker SHALL expose a pure full validation entry point `validate_ready_post(base_path, source_relative_path)` that validates one ready or queued blog post without publishing or moving files, including canonical `image` and companion PNG requirements after remediation.

The worker SHALL also expose `validate_ready_post_pre_generation()` for the deterministic pre-generation gate defined in this change.

The entry point MUST return a structured `ReadyPostValidationResult` (or equivalent dataclass) serializable to JSON for future HTTP and n8n consumers.

#### Scenario: Validate by relative path in ready folder

- **WHEN** `validate_ready_post` is called with `source_relative_path` `blog-posts/ready/01-why-i-did-not-start-with-the-database.md` and a valid editorial base path after editorial remediation
- **THEN** the function returns a result including `source_relative_path`, slug fields, and validation outcome without modifying file locations on disk

#### Scenario: Validate by relative path in queued folder

- **WHEN** `validate_ready_post` is called with `blog-posts/queued/01-why-i-did-not-start-with-the-database.md` during Flow A processing after editorial image remediation
- **THEN** validation resolves companion image under `blog-posts/queued/` and returns structured outcome

#### Scenario: No HTTP endpoint in this change

- **WHEN** this child change is applied
- **THEN** no new FastAPI route is required; validation is callable as a library module and covered by unit tests

### Requirement: Campaign metadata integration

On validation when `publication_date` and `public_slug` are derivable, the worker MUST create or update `metadata/campaigns/<campaign-id>.json` using lifecycle helpers.

Campaign ID MUST follow `flow-a-YYYY-MM-DD-<public-slug>`.

Campaign `flow` MUST be `flow_a`.

Campaign MUST include `source_content_sha256` computed via `compute_source_content_sha256` from lifecycle module.

Metadata-only state transitions:

- Success: `ready` → `validated`
- Failure: `ready` → `validation_failed`

Validation failure MUST append blocking error codes to campaign metadata `errors[]` via lifecycle transition rules.

Validation MUST NOT physically move source files in this child.

On `validation_failed`, lifecycle helpers MUST mark metadata-only error state (`source_file_status.location` = `error`).

**Pre-remediation hash compatibility (pre-generation validation):**

- When campaign context is supplied, pre-generation validation MUST compare the current source digest against intake/pre-remediation evidence.
- Operator or unrelated source mutations after queue acceptance MUST fail with `campaign_content_hash_changed` or `blog_publish_content_hash_changed` per existing guards.
- Compatibility checks MUST use `intake_source_content_sha256` when present; otherwise the stored pre-remediation `source_content_sha256` at queue acceptance.
- Absence or normalization of the canonical `image` frontmatter field is the only authorized mutation deferred to editorial remediation; pre-generation validation MUST NOT treat that deferred mutation alone as `campaign_content_hash_changed`.

**Post-remediation hash compatibility (full validation):**

- When editorial remediation patches or normalizes the canonical `image` field as the only authorized mutation, authorized hash reconciliation per `flow-a-lifecycle` MUST run before full validation.
- After reconciliation, `source_content_sha256` MUST represent the active post-remediation digest.
- `intake_source_content_sha256` MUST remain immutable once recorded at queue acceptance.
- Full validation MUST compare the current Markdown bytes against the reconciled active `source_content_sha256`.
- Authorized remediation MUST NOT produce `campaign_content_hash_changed` or `blog_publish_content_hash_changed`.
- Unrelated body or frontmatter mutation outside authorized image remediation MUST still fail with `campaign_content_hash_changed` or `blog_publish_content_hash_changed`.

**Existing campaign metadata behavior:**

- When campaign metadata already exists in `ready` state, validation MAY transition to `validated` or `validation_failed` per outcome.
- When campaign metadata already exists in `validated` state and `source_content_sha256` matches the current ready post content, validation MUST be idempotent: return `ok: true` without appending duplicate state history entries.
- When campaign metadata already exists with a different `source_content_sha256` than the current post content after authorized reconciliation is not applicable, validation MUST fail with error code `campaign_content_hash_changed` and MUST NOT silently overwrite metadata; reset/revalidation behavior is deferred to a later child.
- When campaign metadata already exists in a state beyond `validated` (for example `blog_published`, `derivatives_generated`), validation MUST NOT silently overwrite or regress the campaign; return blocking error `campaign_invalid_existing_state`.

Future `worker-blog-publishing-endpoint` depends on idempotent re-validation when campaign is already `validated` with unchanged content.

#### Scenario: Successful validation transitions campaign

- **WHEN** all blocking checks pass for a new ready post with `publication_date` `2026-07-06` and `public_slug` `why-i-did-not-start-with-the-database`
- **THEN** campaign ID `flow-a-2026-07-06-why-i-did-not-start-with-the-database` is created or updated, `state` becomes `validated`, and `metadata_written` is `true`

#### Scenario: Failed validation transitions campaign from ready

- **WHEN** a blocking check fails after campaign metadata exists in `ready` state
- **THEN** campaign transitions to `validation_failed` with `errors[]` containing stable error codes and `metadata_written` is `true` when persistence succeeds

#### Scenario: Idempotent re-validation when already validated with same content hash

- **WHEN** campaign metadata exists in `validated` state and `source_content_sha256` matches the current post content after any authorized reconciliation
- **THEN** validation returns `ok: true`, `state` remains `validated`, and no duplicate state history entry is appended

#### Scenario: Content hash changed on existing campaign

- **WHEN** campaign metadata exists and stored active `source_content_sha256` differs from the hash computed for the current post outside authorized image remediation
- **THEN** validation fails with error code `campaign_content_hash_changed`, does not overwrite progressed metadata, and `metadata_written` is `false` or records explicit metadata error per lifecycle rules

#### Scenario: Authorized image remediation does not fail hash guard

- **WHEN** editorial remediation patches only the canonical `image` frontmatter field, hash reconciliation succeeds, and full validation runs
- **THEN** validation does not fail with `campaign_content_hash_changed` and compares against the reconciled active digest

#### Scenario: Body mutation after queue acceptance still fails

- **WHEN** Markdown body bytes change between queue acceptance and full validation outside authorized image remediation
- **THEN** pre-generation or full validation fails with `campaign_content_hash_changed` or `blog_publish_content_hash_changed` per existing guards

#### Scenario: Campaign already progressed beyond validated

- **WHEN** campaign metadata exists in a state beyond `validated` (for example `blog_published`)
- **THEN** validation fails with error code `campaign_invalid_existing_state` and does not modify campaign state or history

#### Scenario: Metadata write failure surfaces in result

- **WHEN** `metadata/campaigns/` is not writable
- **THEN** result includes `metadata_written: false` and `metadata_error_code` from lifecycle write result (for example `metadata_campaigns_not_writable` or `campaign_metadata_write_failed`)
