## 1. Planning artifacts

- [x] 1.1 Review and approve `proposal.md` — umbrella reference, goals, non-goals, capability scope
- [x] 1.2 Review and approve `design.md` — schema, state machine, idempotency keys, file-marking policy
- [x] 1.3 Review and approve `specs/flow-a-lifecycle/spec.md` — testable requirements
- [x] 1.4 Run `openspec validate flow-a-lifecycle-and-duplicate-prevention --strict` and fix any issues

## 2. Campaign lifecycle module

- [x] 2.1 Create `src/silverman_blog_linkedin/campaign_lifecycle.py` with constants (`METADATA_CAMPAIGNS_RELATIVE`, flow values, lifecycle states, canonical variant IDs from editorial canon, forbidden fields)
- [x] 2.2 Implement `generate_campaign_id()` with safe slug/date validation per design
- [x] 2.3 Implement idempotency key builders: `build_blog_publish_idempotency_key`, `build_derivative_idempotency_key`, `build_schedule_idempotency_key`
- [x] 2.4 Implement `compute_source_content_sha256()` for Markdown byte/string input
- [x] 2.5 Implement `build_initial_campaign_metadata()` with required top-level fields and nested `blog_publish`, `variants`, `state_history`, `source_file_status`
- [x] 2.6 Implement `transition_state()` with Flow A valid-transition map, history append, `errors[]` on failure, and Flow B guard (`flow_b_not_eligible_for_flow_a`)
- [x] 2.7 Implement `sanitize_campaign_metadata()` stripping `markdown_content`, `generated_draft_content`, `draft_content`, and secrets
- [x] 2.8 Implement `check_metadata_campaigns_ready()`, `campaign_metadata_relative_path()`, `read_campaign_metadata()`, `write_campaign_metadata()` aligned with `run_metadata.py` patterns
- [x] 2.9 Implement metadata-only helpers `mark_source_processed()` and `mark_source_error()` updating `source_file_status`

## 3. Tests

- [x] 3.1 Add `tests/test_campaign_lifecycle.py`
- [x] 3.2 Test canonical campaign ID: `flow-a-2026-07-06-why-i-did-not-start-with-the-database`
- [x] 3.3 Test unsafe slug rejection in campaign ID generation
- [x] 3.4 Test initial metadata shape and required fields (no content bodies)
- [x] 3.5 Test happy-path state transitions from `ready` through `flow_a_complete`
- [x] 3.6 Test invalid transition rejection (`invalid_state_transition`)
- [x] 3.7 Test failure transitions require `error_code` in history and `errors[]`
- [x] 3.8 Test blog, derivative, and schedule idempotency key formats and stability using canonical variant IDs (`executive-recruiter`, `technical-architect`, `short-provocative`)
- [x] 3.9 Test non-canonical variant IDs (`executive`, `short_provocative`) are rejected with `invalid_variant_id`
- [x] 3.10 Test `sanitize_campaign_metadata` removes forbidden fields
- [x] 3.11 Test Flow B campaign rejected by Flow A transition helper
- [x] 3.12 Test campaign metadata write/read round-trip under `tmp_path` with `metadata/campaigns/` readiness checks
- [x] 3.13 Run full test suite (`pytest`) and confirm no regressions

## 4. Verification

- [x] 4.1 Confirm no HTTP endpoints, n8n workflow JSON, or editorial canon runtime loading added
- [x] 4.2 Confirm umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` remains active (not archived)
- [x] 4.3 Run `openspec validate --all` and confirm all changes pass
