## 1. Planning artifacts

- [x] 1.1 Review and approve `proposal.md` — umbrella reference (slice 5), goals, non-goals, capability scope
- [x] 1.2 Review and approve `design.md` — service module shape, artifact layout, lifecycle transitions, idempotency, generation reuse
- [x] 1.3 Review and approve `specs/linkedin-derivative-package-generation/spec.md` — testable requirements and error codes
- [x] 1.4 Run `openspec validate linkedin-derivative-package-generation --strict` and fix any issues

## 2. LinkedIn package flow module

> **Implementation note (apply):** Before coding, inspect real signatures and existing contracts in `campaign_lifecycle.py`, `linkedin_prompt.py`, `deepseek_client.py`, `draft_writer.py`, `main.py`, and `run_metadata.py`. Use actual signatures — do not invent APIs. Verify especially `CANONICAL_VARIANT_IDS`, `build_derivative_idempotency_key`, `transition_state`, `write_campaign_metadata`, `build_chat_messages`, and `generate_linkedin_draft_content`. If an existing helper is too single-draft-specific, add a thin package-specific wrapper without changing the `POST /generate-linkedin-draft` contract.

- [x] 2.1 Create `src/silverman_blog_linkedin/linkedin_package_flow.py` with `LinkedInPackageResult` dataclass and stable error code constants
- [x] 2.2 Implement `build_package_idempotency_key(campaign_id, source_content_sha256, variant_ids, flow)` with sorted variant list
- [x] 2.3 Implement `DEFAULT_VARIANT_EDITORIAL_MAP` for canonical variant `audience` and `tone` hints aligned with editorial canon
- [x] 2.4 Implement campaign resolution from `campaign_id` or `source_relative_path` via `read_campaign_metadata`
- [x] 2.5 Implement eligibility checks: Flow B rejection, state validation, `source_public_url` required, source file exists, hash match, public URL change guard
- [x] 2.6 Implement idempotent short-circuit when `derivatives_generated` with matching package idempotency key and variant hashes
- [x] 2.7 Implement orphan file guard (`linkedin_package_target_exists`) when artifacts exist without metadata proof
- [x] 2.8 Implement variant list resolution (default all `CANONICAL_VARIANT_IDS`; validate requested subset)
- [x] 2.9 Implement `blog_published` → `derivatives_pending` transition before generation
- [x] 2.10 Pre-check `linkedin-posts/generated/` readiness before DeepSeek calls: create directory and campaign subfolder when editorial base path is valid; fail with `linkedin_package_generated_dir_not_ready` if path exists but is not a directory; fail with `linkedin_package_generated_dir_not_writable` if not writable
- [x] 2.11 Implement per-variant generation helper reusing `linkedin_prompt.build_chat_messages` and injectable `generate_linkedin_draft_content`
- [x] 2.12 Implement deterministic artifact writer for `linkedin-posts/generated/<campaign_id>/<variant_id>.md` with exclusive create
- [x] 2.13 Validate each generated variant contains `source_public_url` exactly once before write or before finalizing metadata; treat zero or more than one occurrence as `linkedin_package_generation_failed` for that variant and fail the whole package
- [x] 2.14 On success update `variants[]` and `linkedin_package` in campaign metadata (paths, hashes, variant IDs, provider/model, status only — no generated body text); transition `derivatives_pending` → `derivatives_generated`
- [x] 2.15 On any variant failure return package `status` `failed` with `linkedin_package_generation_failed`; do not implement partial variant retry in this slice
- [x] 2.16 On metadata write failure return structured errors; handle `linkedin_package_metadata_write_failed`
- [x] 2.17 Persist campaign metadata via `write_campaign_metadata`; preserve metadata body exclusion

## 3. HTTP endpoint

- [x] 3.1 Add `GenerateLinkedInPackageRequest` Pydantic model (`campaign_id` or `source_relative_path`, optional `variants`, optional `topic_theme`, optional `site_url`; `extra="forbid"`)
- [x] 3.2 Add `POST /generate-linkedin-package` route in `main.py` with `Depends(require_api_key)`
- [x] 3.3 Wire route to `generate_linkedin_package()` using settings from `load_settings()` and DeepSeek config
- [x] 3.4 Serialize `LinkedInPackageResult` to JSON response with all required fields (`status`, campaign fields, `package`, `variants`, `errors`, `warnings`, `metadata_written`, `metadata_error_code`); response MUST NOT include `generated_draft_content` or variant body text

## 4. Tests

- [x] 4.1 Add `tests/test_linkedin_package_generation.py` with temp editorial base, campaign fixtures in `blog_published` state, and mocked generator that returns `source_public_url` exactly once per variant
- [x] 4.2 Test campaign not found fails with `linkedin_package_campaign_not_found`
- [x] 4.3 Test Flow B campaign fails with `linkedin_package_flow_not_allowed`
- [x] 4.4 Test campaign before `blog_published` fails with `linkedin_package_invalid_campaign_state`
- [x] 4.5 Test missing `source_public_url` fails with `linkedin_package_missing_source_public_url`
- [x] 4.6 Test source hash changed fails with `linkedin_package_source_hash_changed`
- [x] 4.7 Test successful package generation from `blog_published` writes four artifact files under `linkedin-posts/generated/<campaign_id>/`
- [x] 4.8 Test campaign transitions to `derivatives_generated` with state history
- [x] 4.9 Test each generated variant contains `source_public_url` exactly once (mocked generator returns URL once)
- [x] 4.10 Test variant with zero or more than one URL occurrence fails package with `linkedin_package_generation_failed`
- [x] 4.11 Test campaign metadata and HTTP response store paths/hashes/variant IDs/provider/model/status only, not generated body text
- [x] 4.12 Test idempotent rerun after `derivatives_generated` returns `completed` without regeneration or duplicate state history
- [x] 4.13 Test target artifact exists without matching metadata fails with `linkedin_package_target_exists`
- [x] 4.14 Test invalid requested variant fails with `linkedin_package_invalid_variant`
- [x] 4.15 Test `linkedin-posts/generated/` path exists but is not a directory fails with `linkedin_package_generated_dir_not_ready`
- [x] 4.16 Test `linkedin-posts/generated/` not writable fails with `linkedin_package_generated_dir_not_writable`
- [x] 4.17 Add HTTP endpoint tests: auth required, successful response shape excludes `generated_draft_content`, unauthorized rejected
- [x] 4.18 Confirm no n8n workflow JSON changed
- [x] 4.19 Confirm no scheduling metadata (`schedule_at`, `publish_state`) created
- [x] 4.20 Confirm no LinkedIn API publication attempted
- [x] 4.21 Run full test suite (`pytest`) and confirm existing `test_generate_linkedin_draft.py` still passes

## 5. Verification

- [x] 5.1 Confirm no source file moves, git commit/push, or scheduling logic added
- [x] 5.2 Confirm umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` remains active (not archived)
- [x] 5.3 Run `openspec validate --all` and confirm all changes pass
