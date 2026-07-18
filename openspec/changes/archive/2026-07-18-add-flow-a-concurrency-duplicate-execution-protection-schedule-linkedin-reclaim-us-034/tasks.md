## 1. Schedule Duplicate-Protection Hardening

- [x] 1.1 Inspect `schedule_linkedin_distribution` / `write_campaign_metadata` and reuse US-033 `campaign_metadata_content_fingerprint` + `write_campaign_metadata_cas` (or equivalent) for first-time schedule apply only.
- [x] 1.2 Persist `derivatives_generated` → `distribution_scheduled` schedule writes via CAS with bounded retry; on peer win, re-read and return completed idempotent matching proof or fail closed with `linkedin_schedule_metadata_mismatch`.
- [x] 1.3 Preserve sequential schedule idempotency (matching completed, mismatch fail-closed, no duplicate `state_history`, no `scheduled_at_utc` rewrite) and do not change staggered strategy or eligibility rules.

## 2. LinkedIn Once-Only Publish Under Contention

- [x] 2.1 Add pre-LinkedIn-API publication evidence re-check on real publish-due so already-published + URN short-circuits with `linkedin_publish_already_published` and zero API calls (including `publish_now` / `auto_queue_pending` paths).
- [x] 2.2 Persist successful first-publish URN / `published_at` / `publish_state=published` via CAS (or equivalent); on peer evidence win, preserve peer URN and fail closed / already-published without clearing winner evidence.
- [x] 2.3 Keep BL-008 uncertain-outcome / recovery-confirmation / retry-limit contracts unchanged; keep enablement and OAuth guards fail-closed without incorrect `failed` transitions; dry-run must not mutate or call LinkedIn.

## 3. Abandoned-Claim Stale Detect and Reclaim Deliverable

- [x] 3.1 Confirm `detect_stale_flow_a_execution` outcomes are operator-visible (completed → `stale` + `retryable`; skipped when not yet stale / not processing) without file moves; add CAS for stale-mark writes only if a focused race test proves it is required.
- [x] 3.2 Confirm `claim_flow_a_execution` reclaim from `stale` yields new `execution_attempt_id`, incremented `attempt_count`, and `reclaimed_from_stale=true` (or equivalent); non-stale `processing` remains `flow_a_execution_already_claimed` + `manual_intervention_required`.
- [x] 3.3 Ensure reclaim/resume inherits schedule and LinkedIn idempotency so reclaim does not duplicate schedule slots or LinkedIn API posts when durable evidence already exists; leave US-033 claim CAS / image / blog paths intact except shared CAS helper reuse.

## 4. Behavioral Tests

- [x] 4.1 Add concurrent overlapping first-time schedule tests proving one durable `distribution_scheduled` write, idempotent loser or mismatch fail-closed, and no duplicate `state_history` / conflicting anchors for matching identity.
- [x] 4.2 Add concurrent/repeated LinkedIn publish-due tests proving already-published skip, pre-API evidence re-check, single retained URN under first-publish race fixtures, and `publish_now` does not bypass already-published protection.
- [x] 4.3 Add stale detect + reclaim tests proving operator-visible detect completed/skipped, reclaim `reclaimed_from_stale`, non-stale already-claimed block, and no duplicate schedule/LinkedIn side effects when evidence exists.
- [x] 4.4 Add regression coverage that US-033 claim/image/blog concurrency tests, sequential schedule idempotency, LinkedIn already-published sequential tests, BL-012 recovery claim rejection, and BL-008 recovery modules remain behaviorally intact.

## 5. Documentation and Status

- [x] 5.1 Document US-034 operator-visible outcomes (schedule completed vs mismatch, LinkedIn already-published, stale detect completed/skipped, reclaim `reclaimed_from_stale`, already-claimed) and explicit non-goals (US-033 rework, US-035, deploy/n8n activation) in operator docs as needed.
- [x] 5.2 Update `docs/CURRENT-STATE.md` after implementation verification to record US-034 concurrency protection as implemented/tested without claiming deployment, operational validation, US-035, US-034 acceptance, or BL-013 closure.
- [x] 5.3 Update `docs/product/progress-checklist.md` and US-034 status only to the demonstrated business-validation level; keep US-033 accepted; leave US-035 and BL-013 open; do not mark US-034 accepted from code alone.

## 6. Verification and Business Validation

- [x] 6.1 Run targeted tests for schedule CAS/idempotency under race, LinkedIn once-only under race, stale detect/reclaim visibility, and US-033 / BL-012 / BL-008 regressions.
- [x] 6.2 Run the full pytest suite because executable worker code changes; resolve any new warnings attributable to this change; run strict OpenSpec validation.
- [x] 6.3 Run `git diff --check` and a secrets/content-body audit over modified files and representative schedule / LinkedIn / reclaim responses.
- [x] 6.4 Demonstrate US-034 against controlled fixtures: prevent duplicate scheduling; prevent duplicate LinkedIn publication; recover abandoned processing claims; show understandable outcomes; communicate blocks/failures; prove completed work (including US-033 and schedule/LinkedIn evidence) is not duplicated or unintentionally changed.
- [x] 6.5 Obtain business review of every US-034 acceptance criterion before marking the story accepted; keep US-035 and BL-013 open.
