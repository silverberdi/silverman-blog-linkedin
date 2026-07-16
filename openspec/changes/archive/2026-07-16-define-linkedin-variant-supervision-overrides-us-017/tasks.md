## 1. Operator supervision mechanics artifact (US-017)

- [x] 1.1 Create `docs/operations/linkedin-variant-supervision-mechanics.md` with sections covering: purpose/scope (US-017 only), relationship to US-015 optional supervision (not mandatory approval), relationship to US-016 criteria failure → persisted action, correction (edit) mechanics, rejection/cancel-from-pending vs post-queue `cancelled`, defer/delay mechanics, `operator_supervision` metadata contract summary, blocked/invalid actions table, BL-007 auto-queue eligibility exclusions (documentation only), and explicit out-of-scope (BL-007 implementation, BL-015 console, criteria automation, Flow B).
- [x] 1.2 Cross-link mechanics doc to `docs/operations/linkedin-variant-review-policy.md`, `docs/operations/linkedin-variant-quality-criteria.md`, `docs/GLOSSARY.md`, `docs/product/user-stories.md` US-017, and `content-strategy/silverman-editorial-system.md` anchors `#flow-a-vs-flow-b` and `#linkedin-distribution-strategy`.
- [x] 1.3 Update US-015 policy and US-016 criteria deferred/out-of-scope sections only: remove US-017 from deferred list; add pointer to mechanics doc; preserve all US-015/US-016 substance unchanged.

## 2. Glossary alignment

- [x] 2.1 Update `docs/GLOSSARY.md` with **operator supervision override** and **`auto_queue_eligible`** terms — cross-link mechanics doc; distinguish from `publish_state` and mandatory Flow B review.
- [x] 2.2 Ensure glossary entries do not equate supervision overrides with mandatory approval or contradict US-015/US-016 language.

## 3. Worker supervision implementation

- [x] 3.1 Add `src/silverman_blog_linkedin/linkedin_supervision_flow.py` with `correct_linkedin_variant()` and `defer_linkedin_variant()` per design D2/D4/D6 (atomic artifact write, hash update, `operator_supervision` history, idempotency, dry-run default).
- [x] 3.2 Extend `cancel_linkedin_publication()` in `linkedin_publication_flow.py` to accept `pending` in addition to `queued` per design D3/D7; record `operator_supervision.cancellation` with `phase` `pre_queue` or `post_queue`; set `auto_queue_eligible` false on cancel.
- [x] 3.3 Register `POST /correct-linkedin-variant` and `POST /defer-linkedin-variant` in `main.py` with API key auth, Pydantic request models, and structured JSON responses.
- [x] 3.4 Add stable error codes: `linkedin_supervision_variant_not_pending`, `linkedin_supervision_action_not_allowed`, `linkedin_supervision_defer_time_invalid`, `linkedin_supervision_edit_unchanged`, `linkedin_supervision_idempotency_conflict`.
- [x] 3.5 Verify supervision endpoints do **not** require `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` (pre-API actions).

## 4. Presence / contract checks

- [x] 4.1 Add `tests/test_linkedin_variant_supervision_mechanics.py` mirroring US-015/US-016 policy test style: file exists, required headings/phrases (edit, defer, cancel, pre_queue, auto_queue_eligible, BL-007 eligibility, US-015/US-016 cross-links, criteria_failure reason, blocked states).
- [x] 4.2 Add `tests/test_linkedin_supervision_flow.py` with behavioral tests: correct pending variant (artifact + hash + edit_history), defer pending variant (scheduled_at_utc + deferral_history + auto_queue_eligible false), cancel pending variant (cancelled + phase pre_queue), cancel queued variant unchanged semantics (phase post_queue), reject edit/defer on queued, reject cancel on published, dry-run no mutation, idempotent replay — no real LinkedIn API calls.
- [x] 4.3 Extend existing cancel publication tests to cover `pending` acceptance without regressing `queued` → `cancelled` behavior.
- [x] 4.4 Run targeted tests only (`test_linkedin_variant_supervision_mechanics.py`, `test_linkedin_supervision_flow.py`, touched cancel tests).

## 5. Status and product progress (after ACs demonstrated)

- [x] 5.1 Update `docs/CURRENT-STATE.md` to record US-017 / BL-006 story 3 as supervision mechanics implemented (worker + docs); qualify implemented vs operationally validated; close BL-006 only when all three stories demonstrated.
- [x] 5.2 Update `docs/product/user-stories.md` US-017 acceptance criteria and status only when demonstrated; add mechanics artifact link.
- [x] 5.3 Update `docs/product/progress-checklist.md` for US-017 demonstrated items; mark BL-006 closed only when US-015, US-016, and US-017 are all accepted.
- [x] 5.4 Update `docs/product/backlog.md` BL-006 status to closed only when all three stories validated.
- [x] 5.5 Do not update `docs/RUNTIME-STATE.md` (no live flag changes unless enablement touched — must not be).

## 6. Explicit non-touch / regression guardrails

- [x] 6.1 Verify git diff does **not** include BL-007 WIP paths: `auto_queue_pending` behavior changes, `n8n/workflows/silverman-blog-linkedin-publish-pending.json`, `deploy/server/finish-pending-linkedin-publication.sh`, `deploy/server/run-publish-pending-linkedin-variants.sh`, or unapproved `bl-007-auto-queue-pending-handoff.md` implementation.
- [x] 6.2 Verify no change to `POST /publish-linkedin-due-variants` queue eligibility logic beyond reading documented `auto_queue_eligible` (no BL-007 auto-queue implementation).
- [x] 6.3 Verify US-011 publication-guard semantics unchanged: Flow A schedule ≠ LinkedIn enablement; `distribution_scheduled` ≠ LinkedIn API published; fail-closed `linkedin_publish_not_enabled` on real publish only.
- [x] 6.4 Verify Flow A ready-path completion (`POST /complete-flow-a-ready-path`), package generation, and schedule lifecycle transitions are unchanged by supervision routes.
- [x] 6.5 Verify US-015 policy and US-016 criteria substance unchanged (cross-link edits only).
- [x] 6.6 Verify no n8n Execute Command and no new n8n LinkedIn publish workflows.
- [x] 6.7 Run `git diff --check` on touched paths.

## 7. Business validation (US-017 / BL-006 closure)

- [x] 7.1 Walk US-017 acceptance criteria: (1) correction and rejection before queueing via worker routes, (2) outcome visible in campaign JSON and HTTP responses, (3) blocked/invalid states return stable error codes and mechanics doc table, (4) no unintended change to US-015/US-016/Flow A/US-011/post-queue cancel.
- [x] 7.2 Confirm a reviewer can answer without reading code: what the operator does in supervision, what persists in metadata, what blocks BL-007 auto-queue, and why BL-006 may close after US-017.
- [x] 7.3 Confirm BL-006 closure criteria: US-015 policy defined, US-016 criteria defined, US-017 mechanics demonstrated — then mark backlog item closed.
