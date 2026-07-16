# Tasks: store-linkedin-publication-evidence-us-019

Scope: US-019 only (BL-007 story 2). Spec + tests + docs + one small additive code change (design D3: evidence fields on `LinkedInAutoQueueVariantResult`). No US-020, no BL-008, no deploy, no n8n activation.

## 1. Preconditions and contract cross-check

- [x] 1.1 Re-read canonical `openspec/specs/linkedin-publication-integration/spec.md` and diff each MODIFIED block in this change's delta against it; confirm every modification is additive and the US-018 auto-queue contract is only extended with optional fields, never reshaped
- [x] 1.2 Run `openspec validate --strict` for this change and fix any delta formatting issues
- [x] 1.3 Inspect `src/silverman_blog_linkedin/linkedin_publication_flow.py` and `linkedin_client.py` against design D1–D2 (evidence fields, failure-context shape, blocked-vs-failed taxonomy, idempotent replay) and record any behavior gap found beyond the planned D3 change — report before any code edit

## 2. Additive code change (design D3)

- [x] 2.1 Add optional `linkedin_post_urn` and `published_at` fields (default `None`) to `LinkedInAutoQueueVariantResult` in `linkedin_publication_flow.py`
- [x] 2.2 Populate both fields in `auto_queue_results` entries when the publish phase confirms a published or already-published outcome for that variant, and from stored campaign metadata for an already-`published` variant skipped by the scan (`linkedin_publish_auto_queue_skipped_state`)
- [x] 2.3 Dedicated test: under `auto_queue_pending` (including the cross-campaign scan without `campaign_id`), assert `auto_queue_results` entries for published and already-published variants include non-null `linkedin_post_urn` and `published_at`; entries without publication evidence keep them absent or null
- [x] 2.4 Confirm no existing field of the US-018 response shape is renamed, removed, or retyped; existing auto-queue tests keep passing unmodified

## 3. Behavioral tests (spec scenarios → tests, no weakened assertions)

- [x] 3.1 Evidence completeness: mocked real publish success asserts non-empty `linkedin_post_urn`, UTC `published_at`, and `linkedin_publication` with `provider`, `post_urn` == `linkedin_post_urn`, `published_at`, `http_status`
- [x] 3.2 Failure context shape: mocked API error asserts `failed` with at minimum `last_error_code`, `last_failed_at`, `retryable`, numeric `http_status`; transport-error case asserts `http_status` null; assert no secrets/body text in metadata or response
- [x] 3.3 Content rejection: mocked LinkedIn content-rejection response asserts `failed` with `last_error_code` `linkedin_publish_content_invalid` (distinct from generic `linkedin_publish_api_error`) and numeric `http_status`
- [x] 3.4 Success-without-identifier: mocked 201 without post URN asserts `failed` with `linkedin_publish_api_error` (never `published` without URN)
- [x] 3.5 Blocked-vs-failed taxonomy: enablement off, OAuth `action_required`, missing member URN, and missing token each fail the response with the stable code while `publish_state` is unchanged
- [x] 3.6 Response evidence: per-variant HTTP result carries `linkedin_post_urn` and `published_at` for published and already-published outcomes
- [x] 3.7 Idempotency evidence: repeat runs (direct, `publish_now: true`, `auto_queue_pending: true`) over a `published` variant preserve stored `linkedin_post_urn` and `published_at` byte-for-byte with zero LinkedIn API calls; auto-queue phase reports `linkedin_publish_auto_queue_skipped_state` carrying the preserved evidence
- [x] 3.8 No automatic retry: mocked failed real attempt produces exactly one LinkedIn API call; subsequent publish/auto-queue runs exclude the `failed` variant
- [x] 3.9 Run targeted `pytest tests/test_linkedin_publication.py`; zero new warnings

## 4. Conditional code (only if 1.3 or group 3 proves a gap beyond D3)

- [ ] 4.1 If a test falsifies a D1–D2 rule: report the gap, then apply the smallest code diff in `linkedin_publication_flow.py` / `linkedin_client.py` restoring spec conformance — no refactors, no new endpoints/fields beyond the delta
- [x] 4.2 If no further gap found: record "no code change beyond the planned D3 addition" in the verification notes

## 5. Documentation

- [x] 5.1 Update operator LinkedIn publication documentation with the evidence field contract (mandatory vs optional, `http_status` mandatory and nullable only on transport failure), the failed-vs-blocked failure taxonomy including `linkedin_publish_content_invalid`, and where preserved URN evidence is observable on re-runs (publish-phase results and `auto_queue_results` entries)
- [x] 5.2 Update `docs/CURRENT-STATE.md`: US-019 slice implemented (spec formalization + tests + additive auto-queue evidence fields), qualified language, BL-007 still open, US-020 deferred; note the auto-queue evidence fields are implemented but not deployed; no RUNTIME-STATE change (no live flags touched)

## 6. Verification and business validation

- [x] 6.1 Full `pytest` (executable code changed in group 2); `git diff --check` clean; secrets audit on touched files
- [x] 6.2 Run `/opsx-verify`; re-run after any post-verify edit
- [x] 6.3 Business validation mapping only — no closure: map each US-019 acceptance criterion to demonstrated evidence (test names / doc sections) and update `docs/product/user-stories.md` US-019 checkboxes and `docs/product/progress-checklist.md` ONLY for criteria actually demonstrated at this point. Explicitly leave US-019 NOT marked as complete and BL-007 OPEN; record it as in progress. Any closure of US-019 (or of BL-007) is deferred to a separate, explicitly authorized validation step outside this change. Do not touch US-020.
