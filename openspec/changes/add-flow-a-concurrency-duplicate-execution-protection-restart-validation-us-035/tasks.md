## 1. Restart Contract Inspection and Baseline

- [x] 1.1 Confirm there is no worker startup / lifespan hook that auto-clears non-stale `execution_state=processing` claims; document the intended contract (stuck until stale TTL or allowlisted `clear_stale_execution_claim`).
- [x] 1.2 Inventory existing helpers/endpoints used for restart re-entry: `claim_flow_a_execution`, `detect_stale_flow_a_execution`, calendar/execute, publish/package/schedule, LinkedIn publish-due, incomplete-campaign recovery inspect/resume/repair, operational-status — no new primary endpoints unless a proven unavoidable gap appears.
- [x] 1.3 Map mid-flight interruption fixtures to durable evidence markers for claim-only, image, blog handoff, schedule, and LinkedIn (URN present vs BL-008 uncertain) using shortened `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` in tests.

## 2. Narrow Hardening Only If Gaps Appear

- [x] 2.1 Run the planned restart fixtures against current US-033/US-034/BL-012 paths; if any path can still duplicate under reclaim/resume, apply the smallest hardening that reuses existing CAS / pre-check / idempotency patterns.
- [x] 2.2 Do **not** add startup auto-reclaim, new lifecycle states, new repair actions, or LinkedIn auto-republish after mid-API interruption; keep BL-008 uncertain / confirmation contracts intact.
- [x] 2.3 Preserve US-033 claim/image/blog and US-034 schedule/LinkedIn/stale-reclaim behavior except narrow shared dependencies required by proven gaps.

## 3. Behavioral Restart Validation Tests

- [x] 3.1 Add claim-only interruption tests: non-stale post-restart claim/execute/resume blocked (`flow_a_execution_already_claimed` and/or `flow_a_recovery_active_non_stale_claim` + `manual_intervention_required`); after TTL, stale detect + reclaim with `reclaimed_from_stale` resumes without inventing publish/schedule/URN success.
- [x] 3.2 Add image and blog interruption tests: reclaim/resume skips/reuses ComfyUI when reusable PNG exists; matching blog identity returns `already_published`; unproven targets fail closed (`blog_publish_target_exists` / `flow_a_recovery_evidence_ambiguous`) without inventing success.
- [x] 3.3 Add schedule interruption tests: reclaim/resume leaves at most one durable matching schedule set; matching proof completed idempotent; mismatch `linkedin_schedule_metadata_mismatch`.
- [x] 3.4 Add LinkedIn interruption tests: durable URN → `linkedin_publish_already_published` with zero API calls and URN preserved; mid-API without URN → no Flow A auto-publish success path (BL-008 uncertain boundary asserted).
- [x] 3.5 Add concurrent re-trigger-immediately-after-restart test proving non-stale claim loser does not start a second pipeline; add regression that US-033, US-034, BL-012, and BL-008 modules remain behaviorally intact.

## 4. Documentation and Status

- [x] 4.1 Add operator docs for US-035 restart validation (prefer `docs/operations/flow-a-concurrency-duplicate-execution-protection-us-035.md`): pre-TTL block vs post-TTL stale reclaim, BL-012 resume/repair, LinkedIn mid-flight → BL-008, explicit non-goals (startup auto-clear, Git/live-site, deploy/n8n activation).
- [x] 4.2 Update `docs/CURRENT-STATE.md` after implementation verification to record US-035 restart validation as implemented/tested without claiming deployment, operational validation, US-035 acceptance, or BL-013 closure.
- [x] 4.3 Update `docs/product/progress-checklist.md` and US-035 status only to the demonstrated business-validation level; keep US-033 and US-034 accepted; leave BL-013 open until US-035 acceptance; do not mark US-035 accepted from code alone.

## 5. Verification and Business Validation

- [x] 5.1 Run targeted restart-interruption tests (claim, image, blog, schedule, LinkedIn, concurrent post-restart re-trigger) plus US-033 / US-034 / BL-012 / BL-008 regressions.
- [x] 5.2 Run the full pytest suite if executable worker code changed; if tests/docs-only, run the targeted suite; resolve any new warnings attributable to this change; run strict OpenSpec validation.
- [x] 5.3 Run `git diff --check` and a secrets/content-body audit over modified files and representative already-claimed / reclaim / resume / fail-closed responses.
- [x] 5.4 Demonstrate US-035 against controlled fixtures: validate behavior during restarts; show understandable outcomes; communicate blocks/failures; prove completed work (including US-033/US-034 protections and schedule / LinkedIn / blog / image evidence) is not duplicated or unintentionally changed.
- [x] 5.5 Obtain business review of every US-035 acceptance criterion before marking the story accepted; keep BL-013 open until that acceptance; do not reopen US-033 or US-034.
