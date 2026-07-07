## 1. Planning artifacts

- [x] 1.1 Review and approve `proposal.md` — umbrella reference (slice 6), goals, non-goals, capability scope
- [x] 1.2 Review and approve `design.md` — service module shape, staggered strategy, lifecycle transitions, idempotency, metadata shape
- [x] 1.3 Review and approve `specs/linkedin-distribution-scheduling-model/spec.md` — testable requirements and error codes
- [x] 1.4 Run `openspec validate linkedin-distribution-scheduling-model --strict` and fix any issues

## 2. LinkedIn distribution schedule module

> **Implementation note (apply):** Before coding, inspect real signatures and existing contracts in `campaign_lifecycle.py`, `linkedin_package_flow.py`, `main.py`, and `tests/test_linkedin_package_generation.py`. Use actual signatures — do not invent APIs. Verify especially `CANONICAL_VARIANT_IDS`, `transition_state`, `write_campaign_metadata`, `read_campaign_metadata`, `build_package_idempotency_key`, and campaign metadata shapes from slice 5.

- [x] 2.1 Create `src/silverman_blog_linkedin/linkedin_distribution_schedule.py` with `LinkedInDistributionScheduleResult` dataclass and stable error code constants
- [x] 2.2 Implement `build_schedule_idempotency_key(campaign_id, source_content_sha256, package_idempotency_key, variant_ids, strategy, anchor_utc, flow)` with sorted variant list
- [x] 2.3 Implement `build_variant_schedule_idempotency_key(campaign_id, variant, derivative_content_sha256, scheduled_at_utc, flow)` per variant
- [x] 2.4 Implement `DEFAULT_STAGGER_STRATEGY` (`flow_a_staggered`) with audience sequencing and ≥3-day calendar spacing aligned with editorial canon
- [x] 2.5 Implement campaign resolution from `campaign_id` or `source_relative_path` via `read_campaign_metadata`
- [x] 2.6 Implement eligibility checks: Flow B rejection, state validation (`derivatives_generated` or idempotent `distribution_scheduled`), `linkedin_package` required, `variants[]` match package `variant_ids`
- [x] 2.7 Implement artifact existence and `derivative_content_sha256` verification for each variant
- [x] 2.8 Implement idempotent short-circuit when `distribution_scheduled` with matching schedule idempotency key and unchanged `scheduled_at_utc` values
- [x] 2.9 Implement metadata mismatch guard (`linkedin_schedule_metadata_mismatch`) when `distribution_scheduled` but proof differs
- [x] 2.10 Implement schedule anchor resolution: explicit `start_at_utc` or deterministic default (preferred weekday, 14:00 UTC); fail invalid anchor with `linkedin_schedule_invalid_anchor`
- [x] 2.11 Implement staggered schedule computation (no simultaneous timestamps; max 1 variant per calendar day)
- [x] 2.12 On success update `variants[]` with `scheduled_at_utc`, `publish_state` `pending`, `schedule_idempotency_key`; write `linkedin_distribution` object (paths, hashes, schedule fields only — no body text)
- [x] 2.13 On first success transition `derivatives_generated` → `distribution_scheduled` via `transition_state(..., actor="worker")`
- [x] 2.14 On metadata write failure return structured errors with `linkedin_schedule_metadata_write_failed`
- [x] 2.15 Confirm no LinkedIn API import or call; `publish_state` remains `pending` only

## 3. HTTP endpoint

- [x] 3.1 Add `ScheduleLinkedInDistributionRequest` Pydantic model (`campaign_id` or `source_relative_path`, optional `strategy`, optional `start_at_utc`, optional `timezone`; `extra="forbid"`)
- [x] 3.2 Add `POST /schedule-linkedin-distribution` route in `main.py` with `Depends(require_api_key)`
- [x] 3.3 Wire route to `schedule_linkedin_distribution()` using settings from `load_settings()`
- [x] 3.4 Serialize `LinkedInDistributionScheduleResult` to JSON response with all required fields (`status`, `campaign_id`, `state`, `distribution_id`, `variant_schedules`, `errors`, `warnings`, `metadata_written`, `metadata_error_code`); response MUST NOT include variant body text

## 4. Tests

- [x] 4.1 Add `tests/test_linkedin_distribution_scheduling.py` with temp editorial base, campaign fixtures in `derivatives_generated` state with `linkedin_package` and `variants[]`, and generated artifact files
- [x] 4.2 Test campaign not found fails with `linkedin_schedule_campaign_not_found`
- [x] 4.3 Test Flow B campaign fails with `linkedin_schedule_flow_not_allowed`
- [x] 4.4 Test campaign before `derivatives_generated` fails with `linkedin_schedule_invalid_campaign_state`
- [x] 4.5 Test missing `linkedin_package` fails with `linkedin_schedule_package_missing`
- [x] 4.6 Test missing variant entry fails with `linkedin_schedule_variant_metadata_missing`
- [x] 4.7 Test missing artifact fails with `linkedin_schedule_artifact_missing`
- [x] 4.8 Test artifact hash changed fails with `linkedin_schedule_artifact_hash_changed`
- [x] 4.9 Test successful scheduling writes per-variant `scheduled_at_utc`, `publish_state` `pending`, and `schedule_idempotency_key`
- [x] 4.10 Test campaign transitions to `distribution_scheduled` with state history on first success
- [x] 4.11 Test variants are staggered (distinct timestamps, ≥3 calendar days apart for 4-variant package)
- [x] 4.12 Test campaign metadata and HTTP response store schedule fields only, not generated body text
- [x] 4.13 Test idempotent rerun after `distribution_scheduled` returns `completed` without duplicate `state_history` or schedule rewrite
- [x] 4.14 Test scheduling mismatch (different anchor) fails with `linkedin_schedule_metadata_mismatch`
- [x] 4.15 Test invalid strategy fails with `linkedin_schedule_invalid_strategy`
- [x] 4.16 Test invalid anchor fails with `linkedin_schedule_invalid_anchor`
- [x] 4.17 Add HTTP endpoint tests: auth required, successful response shape, unauthorized rejected, invalid body 422
- [x] 4.18 Confirm no n8n workflow JSON changed
- [x] 4.19 Confirm no LinkedIn API publication attempted
- [x] 4.20 Run full test suite (`pytest`) and confirm existing tests still pass

## 5. Verification

- [x] 5.1 Confirm no source file moves, git commit/push, or LinkedIn API integration added
- [x] 5.2 Confirm umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` remains active (not archived)
- [x] 5.3 Run `openspec validate --all` and confirm all changes pass
