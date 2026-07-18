## 1. Claim Atomicity Foundation

- [x] 1.1 Inspect existing `claim_flow_a_execution`, `write_campaign_metadata`, and calendar fingerprint CAS patterns; add a campaign-metadata content fingerprint helper (or reuse an equivalent) without changing unrelated writers.
- [x] 1.2 Implement compare-and-swap (or equivalent) persistence for claim transitions to `execution_state=processing`, with a small bounded retry and fail-closed `flow_a_execution_already_claimed` / `manual_intervention_required` on non-stale peer contention.
- [x] 1.3 Preserve sequential claim rejection, attempt metadata fields, and dry-run no-claim behavior; do not expand stale reclaim semantics (US-034).

## 2. Post-Processing Visibility on Existing Paths

- [x] 2.1 Ensure calendar Flow A connector claim failures continue to surface `flow_a_execution_already_claimed` in item `errors` and do not invoke publish or ComfyUI for the losing attempt.
- [x] 2.2 Confirm incomplete-campaign recovery resume still rejects non-stale `processing` claims with zero second-claim side effects (regression only; no recovery contract redesign).
- [x] 2.3 Verify same-identity queue acceptance remains idempotent (`skipped_already_queued` / completed) without creating a second campaign document under repeated accepts.

## 3. Image and Blog Duplicate Protection Hardening

- [x] 3.1 Add or tighten pre-ComfyUI reusable-asset re-check so concurrent/repeated image paths skip generation and do not overwrite an existing readable public asset.
- [x] 3.2 Preserve `already_published` short-circuit ordering and fail-closed `blog_publish_target_exists` behavior under concurrent/repeated `publish_blog_post` attempts; ensure losers cannot create a second distinct public artifact set for the same identity.
- [x] 3.3 Keep Git push, live-site confirmation, LinkedIn API publish, schedule, and reclaim paths out of mutating US-033 changes.

## 4. Behavioral Tests

- [x] 4.1 Add concurrent overlapping-claim tests proving one winner, one `flow_a_execution_already_claimed` loser, and a single active `execution_attempt_id`.
- [x] 4.2 Add repeated/concurrent image tests proving ComfyUI skip/reuse when public or active-folder assets exist, and connector claim-loser does not call ComfyUI.
- [x] 4.3 Add repeated/concurrent blog publish tests for `already_published`, unproven target collision fail-closed, and single public artifact set under first-publish race fixtures.
- [x] 4.4 Add regression coverage that sequential claim/idempotency tests still pass and BL-012 recovery / BL-008 LinkedIn publication recovery modules are not behaviorally altered.

## 5. Documentation and Status

- [x] 5.1 Document US-033 operator-visible outcomes (already-claimed, already-queued, already-published, image skip/reuse, target-exists) and explicit non-goals (US-034 / US-035) in operator docs as needed.
- [x] 5.2 Update `docs/CURRENT-STATE.md` after implementation verification to record US-033 concurrency protection as implemented/tested without claiming deployment, operational validation, US-034/US-035, or BL-013 closure.
- [x] 5.3 Update `docs/product/progress-checklist.md` and US-033 status only to the demonstrated business-validation level; leave US-034, US-035, and BL-013 open; do not mark US-033 accepted from code alone.

## 6. Verification and Business Validation

- [x] 6.1 Run targeted tests for operational queue claim CAS, blog publish idempotency, image handoff skip, calendar connector claim failure surfacing, and incomplete-campaign recovery claim rejection regression.
- [x] 6.2 Run the full pytest suite because executable worker code changes; resolve any new warnings attributable to this change; run strict OpenSpec validation.
- [x] 6.3 Run `git diff --check` and a secrets/content-body audit over modified files and representative contention/idempotent responses.
- [x] 6.4 Demonstrate US-033 against controlled fixtures: prevent duplicate post processing; prevent duplicate image generation; prevent duplicate blog publication; show understandable outcomes; communicate blocks/failures; prove completed work is not duplicated or unintentionally changed.
- [x] 6.5 Obtain business review of every US-033 acceptance criterion before marking the story accepted; keep US-034, US-035, and BL-013 open.
