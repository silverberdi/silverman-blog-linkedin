## 1. Recovery Service Foundation

- [x] 1.1 Add a focused incomplete-campaign recovery module with safe result models, canonical durable milestone constants, stable reason codes (`flow_a_recovery_evidence_ambiguous` and related), and secret-safe response builders.
- [x] 1.2 Implement confined campaign load by `campaign_id` under `metadata/campaigns/`, rejecting non-`flow_a` campaigns, path escape, and missing/malformed documents with stable errors and no fabricated campaigns.
- [x] 1.3 Implement deterministic `last_valid_stage` derivation from `state`, `state_history`, and durable stage evidence markers for `ready` → `validated` → `blog_published` → `derivatives_generated` → `distribution_scheduled` → `flow_a_complete`, failing closed on ambiguity.
- [x] 1.4 Map effective `recovery_classification` using the existing five-value enum and surface `outcome`, `reason_code`, `next_stage`, and short `summary` for operator visibility.

## 2. Inspect, Resume, and Repair Behaviors

- [x] 2.1 Implement read-only inspect that returns recovery status without writing metadata, moving files, or calling external integrations.
- [x] 2.2 Implement resume eligibility gates: reject non-stale `processing` claims; block `location=error` with `requeue_required` (no silent requeue); reclaim stale claims via existing helpers; refuse ambiguous evidence with zero side effects.
- [x] 2.3 Implement resume stage advancement (publish → package → schedule → source lifecycle completion) reusing existing services and idempotent short-circuits; support `dry_run` and optional `stop_after_stage`; default-disable Git publication, live-site confirmation, and LinkedIn API publish.
- [x] 2.4 Implement allowlisted repair actions (`sync_location_from_filesystem`, `clear_stale_execution_claim`, `complete_partial_source_move`) with dry-run, before/after safe summaries, and fail-closed refusal for multi-match, identity conflict, invented success evidence, or unsafe `flow_a_complete` marking.
- [x] 2.5 Ensure mutating paths preserve confirmed durable evidence and never create a second campaign document or duplicate schedule/package/blog side effects.

## 3. HTTP Contract and Safety Boundary

- [x] 3.1 Wire `GET /flow-a/incomplete-campaign-recovery/{campaign_id}`, `POST /flow-a/incomplete-campaign-recovery/resume`, and `POST /flow-a/incomplete-campaign-recovery/repair` with `Depends(require_api_key)`, request validation, and no client-supplied absolute paths.
- [x] 3.2 Return HTTP 401 for auth failure, HTTP 422 for invalid bodies/`repair_action`/`stop_after_stage`, and structured JSON errors for not-found, blocked, and failed outcomes without secrets or content bodies.
- [x] 3.3 Keep route logging limited to safe identifiers/status fields; do not log absolute base paths, tokens, or Markdown/draft bodies.

## 4. Behavioral Tests

- [x] 4.1 Add derivation tests for each durable milestone, pending-state exclusion, ambiguous publish evidence, and consistent `flow_a_complete` terminal handling.
- [x] 4.2 Add inspect tests proving auth 401, not-found, secret/body exclusion, deterministic output, and byte-identical on-disk artifacts after repeated calls.
- [x] 4.3 Add resume tests for skip-already-published, skip-already-scheduled, dry-run zero mutation, non-stale claim block, error-folder requeue_required block, partial progress on mid-chain failure, and completed-campaign noop.
- [x] 4.4 Add repair tests for successful location sync, ambiguous multi-location refusal, invent-success refusal, unknown action 422, stale-claim clear, and partial-move completion where fixtureable.
- [x] 4.5 Add regression coverage that operational-status and operational-alerts contracts remain unchanged and LinkedIn publication recovery endpoints are not altered by this capability.

## 5. Documentation and Status

- [x] 5.1 Document the inspect/resume/repair contracts, last-valid-stage rules, repair allowlist, dry-run behavior, and non-goals (US-032, LinkedIn recovery, n8n activation) for operators.
- [x] 5.2 Update `docs/CURRENT-STATE.md` after implementation verification to record the capability as implemented/tested without claiming deployment, operational validation, US-032, or BL-012 closure.
- [x] 5.3 Update `docs/product/progress-checklist.md` and US-031 status only to the demonstrated business-validation level; leave US-032 and BL-012 open.

## 6. Verification and Business Validation

- [x] 6.1 Run targeted recovery service/HTTP tests plus affected Flow A lifecycle, operational queue, blog publish, package, schedule, and lifecycle-completion regression suites.
- [x] 6.2 Run the full pytest suite because executable worker code changes; resolve any new warnings attributable to this change; run strict OpenSpec validation.
- [x] 6.3 Run `git diff --check` and a secrets/content-body audit over modified files and representative recovery responses.
- [x] 6.4 Demonstrate US-031 against controlled fixtures: identify last-valid-stage; resume without repeating successful work; repair inconsistent metadata; show understandable outcomes; communicate blocks/failures; prove completed work is not duplicated or unintentionally changed.
- [ ] 6.5 Obtain business review of every US-031 acceptance criterion before marking the story accepted; keep US-032 and BL-012 open.
