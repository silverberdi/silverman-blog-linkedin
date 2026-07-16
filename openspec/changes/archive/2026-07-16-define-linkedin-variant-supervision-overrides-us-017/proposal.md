## Why

US-015 defined the optional Flow A supervision window while `publish_state` is `pending`, and US-016 defined quality/differentiation criteria that guide operator action on criteria failure — but neither story provides **persisted mechanics** or a **worker contract** to correct, reject, or defer a variant before LinkedIn API queueing. Today the operator cannot edit a `pending` variant with metadata traceability, cancel a variant still `pending` (existing cancel requires `queued`), or defer with evidence that future BL-007 auto-queue can respect. US-017 closes BL-006 by answering: *“How do I persist correction or rejection before queueing during the supervision window?”*

## Goals

- Define operator-facing supervision **mechanics** (edit, reject/cancel, defer) for variants while `publish_state` is `pending`.
- Persist auditable operator decisions in campaign `variants[]` metadata (actor, timestamps, optional reason, eligibility flags).
- Expose minimal worker HTTP endpoints (ADR-0001) with idempotency and dry-run defaults.
- Document BL-007 auto-queue eligibility exclusions from supervision metadata — **documentation and metadata only**, no BL-007 implementation.
- Make outcomes visible in campaign JSON and structured HTTP responses without requiring source-code inspection.
- Preserve US-015 strategy-driven defaults (supervision remains optional, not an approval gate).
- Preserve US-016 criteria as guidance that maps to persisted actions — not automated queue gates.

## Non-Goals

- **BL-007** — `auto_queue_pending`, publish-pending n8n workflow, deploy publish-pending scripts, or any change to `POST /publish-linkedin-due-variants` queue behavior.
- **BL-015** — supervision console UI (US-038–US-040).
- **Flow B** mandatory review implementation.
- Converting supervision into a mandatory approval gate (contradicts US-015).
- US-016 criteria as automatic queue/publish gates.
- Permanent LinkedIn enablement changes or US-011 guard weakening.
- n8n Execute Command.
- Rewriting US-015 policy or US-016 criteria substance (cross-links only).
- New `publish_state` enum values (`deferred`, `rejected`) — use parallel `operator_supervision` metadata.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-006** | Partial (story 3 — closes backlog when demonstrated) | US-015 and US-016 already validated; BL-006 closes only after US-017 ACs demonstrated |
| **US-017** | Yes | All four acceptance criteria |
| **US-015 / US-016** | No | Cross-link updates only; substance unchanged |
| **BL-007 / BL-015** | No | Document future consumer eligibility only |
| **US-038–US-040** | No | Console consumes US-017 metadata later |

**US-017 acceptance criteria addressed:**

1. Support correction or rejection before queueing → edit + cancel-from-pending endpoints, defer endpoint, mechanics doc, metadata contract.
2. Outcome visible and understandable → `operator_supervision` on `variants[]`, HTTP response fields, mechanics doc, cross-links from user-stories.
3. Failures or blocked states clearly communicated → stable error codes for invalid state (already `queued`/`published`/`failed`), enablement off, hash mismatch, invalid defer time; blocked-actions table in mechanics doc.
4. Existing completed work not duplicated or unintentionally changed → no Flow A lifecycle, US-011, or US-015/US-016 rewrite; post-queue cancel semantics preserved; idempotent replays.

**Intentionally excluded:** BL-007 auto-queue, console UI, criteria automation, Flow B, new `publish_state` values.

## What Changes

- Add operator-facing mechanics artifact at `docs/operations/linkedin-variant-supervision-mechanics.md` defining edit, reject/cancel-from-pending, defer, blocked states, US-015/US-016 relationships, and BL-007 eligibility documentation.
- Extend `linkedin-variant-review-process` capability with normative US-017 requirements (mechanics artifact, metadata contract, worker supervision endpoints).
- Extend `linkedin-publication-integration` to allow `POST /cancel-linkedin-publication` from `pending` (pre-queue) with distinct `operator_supervision` audit trail; preserve existing `queued` → `cancelled` behavior.
- Add `POST /correct-linkedin-variant` — atomically update `linkedin-posts/generated/<campaign>/<variant>.md` and `derivative_content_sha256` with edit history.
- Add `POST /defer-linkedin-variant` — update `scheduled_at_utc` with deferral history and `auto_queue_eligible` flag.
- Extend `linkedin-distribution-scheduling-model` for supervised reschedule semantics (pending-only, history, idempotency).
- Add behavioral tests for supervision endpoints (mock filesystem; no LinkedIn API).
- Add presence/contract test for mechanics doc mirroring US-015/US-016 test style.
- Update `docs/GLOSSARY.md` with supervision override terms; cross-link policy, criteria, mechanics, user-stories.
- After demonstrated ACs only: update CURRENT-STATE, user-stories US-017, progress-checklist, and **close BL-006** when all three stories are demonstrated.

## Capabilities

### New Capabilities

_None — extends existing capabilities rather than introducing a separate capability._

### Modified Capabilities

- `linkedin-variant-review-process`: Add US-017 supervision mechanics artifact, `operator_supervision` metadata contract, blocked/invalid action communication, and BL-007 eligibility documentation.
- `linkedin-publication-integration`: Extend cancel to accept `pending` pre-queue cancellation; document pre-queue vs post-queue `cancelled` audit distinction via `operator_supervision.phase`; add `POST /correct-linkedin-variant` and `POST /defer-linkedin-variant` requirements.
- `linkedin-distribution-scheduling-model`: Supervised defer/reschedule of `scheduled_at_utc` while `pending` with history and idempotency constraints.
- `flow-a-automatic-publishing`: Clarify `variants[]` traceability fields for `operator_supervision` (additive metadata; no lifecycle regression).

## Impact

- **Product:** Completes BL-006 / US-017; enables BL-015 console and BL-007 auto-queue to consume persisted overrides later.
- **Docs:** New mechanics artifact; policy/criteria cross-links; GLOSSARY/CURRENT-STATE/progress updates after validation.
- **OpenSpec:** Delta specs for four modified capabilities.
- **Worker:** New module functions + three HTTP routes (two new, one extended cancel); `linkedin_publication_flow.py` and new `linkedin_supervision_flow.py` (or equivalent); atomic artifact writes.
- **Tests:** Mechanics doc presence test; behavioral tests for edit/defer/cancel-from-pending with idempotency and dry-run.
- **Preserved:** US-015 defaults; US-016 criteria; ADR-0001; US-011; existing `publish_state` enum; post-queue cancel; Flow A lifecycle; BL-007 WIP untouched.
