## 1. Operator policy artifact (US-015)

- [x] 1.1 Create `docs/operations/linkedin-variant-review-policy.md` with sections covering: purpose/scope (US-015 only), strategy-driven publication default (all scheduled variants expected to publish unless operator cancels/defers), optional supervision window while `pending` (edit/delay/cancel — mechanics US-017), Flow A vs Flow B mandatory review table (Flow A: not mandatory; Flow B: mandatory, deferred), relationship to `publish_state` and publication enablement, blocked/deferred states table, future BL-007 eligibility (scheduled non-overridden `pending` variants; no mandatory review gate), future supervision console note, and out-of-scope (US-016/US-017/BL-007 WIP).
- [x] 1.2 Cross-link the policy to `docs/GLOSSARY.md`, `docs/product/user-stories.md` (US-015), `docs/product/bl-007-auto-queue-pending-handoff.md` (as future consumer only), and `content-strategy/silverman-editorial-system.md` `#flow-a-vs-flow-b`.
- [x] 1.3 Confirm the policy does not instruct operators to merge or run BL-007 `auto_queue_pending` WIP, publish-pending n8n, or permanent LinkedIn enablement.

## 2. Glossary and editorial canon alignment

- [x] 2.1 Update `docs/GLOSSARY.md` to define **LinkedIn variant supervision window** (Flow A `pending` before API send) and **mandatory review** (Flow B) as distinct from technical `publish_state`; clarify that `distribution_scheduled` / `flow_a_complete` ≠ LinkedIn API published.
- [x] 2.2 Update `content-strategy/silverman-editorial-system.md` `#flow-a-vs-flow-b` so Flow A core remains automatic after validation; Flow A LinkedIn API publish follows distribution strategy with optional supervision (not mandatory per-variant approval); Flow B keeps mandatory review before publish.
- [x] 2.3 Keep Flow B guardrails intact; do not route Flow B into Flow A paths.

## 3. Presence / contract checks

- [x] 3.1 Add or extend a lightweight test that `docs/operations/linkedin-variant-review-policy.md` exists and contains required headings/phrases for strategy-driven publication, optional supervision window, Flow A vs Flow B mandatory review distinction, and blocked/deferred states.
- [x] 3.2 If editorial-canon section tests assert `#flow-a-vs-flow-b` phrasing, update those assertions to match strategy-driven + optional supervision wording.
- [x] 3.3 Run targeted test(s) only; do not add LinkedIn API integration tests.

## 4. Status and product progress (after ACs demonstrated)

- [x] 4.1 Update `docs/CURRENT-STATE.md` to record US-015 / BL-006 story 1 as policy defined (docs/spec); state enforcement, console, and US-016/US-017 remain open; do not claim BL-006 closed or BL-007 started.
- [x] 4.2 Update `docs/product/user-stories.md` US-015 acceptance criteria and status only when demonstrated; leave US-016 and US-017 unchecked.
- [x] 4.3 Update `docs/product/progress-checklist.md` for US-015 demonstrated items only; keep BL-006 open until US-016/US-017 complete.
- [x] 4.4 Do not update `docs/RUNTIME-STATE.md` (no live flag changes in this change).

## 5. Explicit non-touch / regression guardrails

- [x] 5.1 Verify git diff does not include BL-007 WIP paths (`linkedin_publication_flow.py` auto_queue changes, publish-pending n8n, deploy publish-pending scripts) unless unrelated and left untouched.
- [x] 5.2 Verify no new worker routes, no n8n LinkedIn publish workflow changes, and no change to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` defaults or US-011 guard semantics.
- [x] 5.3 Run `git diff --check` on touched paths.

## 6. Business validation (US-015)

- [x] 6.1 Walk US-015 acceptance criteria against the policy doc: (1) strategy-driven publish expectation defined, (2) mandatory review defined for Flow B and optional supervision for Flow A, (3) outcome visible to operator, (4) blocked/deferred states clear, (5) no unintended change to completed Flow A / publication guard work.
- [x] 6.2 Confirm BL-006 remains open with US-016/US-017 still pending; confirm BL-007 handoff can reference scheduled non-overridden variants without a mandatory review gate from US-015.
