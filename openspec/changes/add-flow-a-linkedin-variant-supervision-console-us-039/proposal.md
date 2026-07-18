## Why

US-038 delivered a read-only Flow A LinkedIn variant supervision console, but operators still cannot correct draft text or reschedule timing from that surface during the optional `pending` window. US-017 already exposes authenticated `POST /correct-linkedin-variant` and `POST /defer-linkedin-variant`; BL-015 / US-039 closes the gap by wiring those mechanics into the existing console so edits and deferrals persist traceably without raw mount inspection or parallel mutation sources of truth.

## Goals

- From the existing supervision console, allow operators to edit variant content before queue authorization while `publish_state` remains `pending`.
- Allow defer/reschedule relative to distribution strategy rules (future `new_scheduled_at_utc`, US-017 defer eligibility) while `publish_state` remains `pending`.
- Persist operator changes traceably via existing US-017 worker HTTP contracts only (same `operator_supervision` metadata and artifact writes).
- Make successful and failed outcomes visible and understandable on the console (extend the US-038 static HTML surface).
- Communicate failures and blocked states clearly using existing US-017 stable error codes (non-pending, invalid schedule, unchanged edit, auth, dry-run vs real, idempotency conflict, etc.).
- Keep API key via runtime prompt / session-only storage; committed HTML/docs MUST NOT embed secrets or secret-like placeholders (extend the US-038 secrets audit).
- Preserve precise language: `pending` ≠ LinkedIn API published; `flow_a_complete` ≠ LinkedIn API published.

## Non-Goals

- **US-040** — cancel UI and cancel-driven auto-queue eligibility surfaces as the primary story; full blocked/integration failure action console beyond what edit/defer needs.
- Claiming **Story accepted** or **BL-015 closed** from this proposal or from apply alone.
- New LinkedIn API publish paths; bypassing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Reopening **BL-007** auto-queue behavior (consume existing eligibility effects of edit/defer only).
- Reopening **BL-008–BL-014** closed work.
- Reopening **US-038** read contracts beyond the minimal extension needed to populate edit forms and refresh outcomes.
- Inventing parallel mutation endpoints or browser scraping of mounts as source of truth.
- Flow B review console or mandatory-review UI.
- Changing US-015 strategy-driven default (absence of operator action still means expected to publish when due).
- Changing US-016 criteria into automatic technical blocks (guidance links only).
- n8n Execute Command (ADR-0001).

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (Story 2 only) | Leave backlog open; do not close |
| **US-039** | Yes | All six acceptance criteria |
| **US-038** | Consume / minimal extend | Read-only SoT preserved; only necessary draft/outcome fields for edit UI |
| **US-040** | No | Cancel / full blocked-action console deferred |
| **US-015 / US-016 / US-017** | Consume only | No policy/mechanics rewrite; console calls existing POSTs |
| **BL-007** | No | Do not change auto-queue; edit/defer already affect eligibility per US-017 |

**US-039 acceptance criteria addressed:**

1. Edit variant content before queue authorization.
2. Defer or reschedule relative to distribution strategy rules.
3. Persist operator changes traceably (aligned with US-017).
4. The outcome is visible and understandable to the intended user.
5. Failures or blocked states are clearly communicated.
6. Existing completed work is not duplicated or unintentionally changed.

**Intentionally excluded:** US-040 cancel UI and broader blocked-state action console; Story accepted / BL-015 closed checkboxes; new mutation SoT; LinkedIn API publish; US-015 default change.

## What Changes

- Extend capability `linkedin-variant-supervision-console` from Story 1 read-only to Story 2 operator edit and defer/reschedule actions on the same console surface (`GET /flow-a/console/linkedin-variant-supervision`).
- Wire the console to call existing authenticated US-017 routes `POST /correct-linkedin-variant` and `POST /defer-linkedin-variant` (no duplicate mutation endpoints).
- Minimally extend the US-038 read aggregation only as needed so the edit form can load current draft text and the console can refresh to show post-action schedule / `operator_supervision` outcome without mount scraping.
- Preserve dry-run default semantics (`dry_run` defaults `true` per US-017); console MUST make dry-run vs real mutation explicit to the operator.
- Surface US-017 stable error codes and auth failures clearly on the console after failed edit/defer attempts.
- Behavioral tests for console/API wiring (edit success, defer success, dry-run no mutation, error-code display, secrets audit extended); no real LinkedIn API calls.
- Update CURRENT-STATE and progress-checklist for **in-progress / demonstrated** US-039 items only — leave Story accepted and BL-015 closed unchecked.

## Capabilities

### New Capabilities

_None — Story 2 extends the existing console capability rather than introducing a separate capability name._

### Modified Capabilities

- `linkedin-variant-supervision-console`: Add operator-facing edit and defer/reschedule action surfaces that persist via US-017 POSTs; clarify that Story 1 “no mutation controls” is superseded for edit/defer only (cancel remains US-040); allow minimal read-path field extension for draft content needed by the edit form.

## Impact

- **Product:** Advances BL-015 / US-039 (Story 2); BL-015 remains open until US-040 and acceptance.
- **Worker / UI:** Extend static HTML at `GET /flow-a/console/linkedin-variant-supervision` to invoke US-017 POSTs; optional thin extension of `GET /flow-a/linkedin-variants/pending-supervision` response fields for draft content / outcome refresh — no new mutation routes.
- **APIs:** Consume `POST /correct-linkedin-variant` and `POST /defer-linkedin-variant` as-is (auth, dry-run default, idempotency, stable codes).
- **Docs:** CURRENT-STATE (US-039 console actions in progress/demonstrated); progress-checklist US-039 in-progress marks only; optional mechanics cross-link that BL-015 Story 2 console now exercises edit/defer (no US-017 contract rewrite).
- **Tests:** Console/action contract tests; secrets/placeholder audit still passes; mock worker responses — no LinkedIn/DeepSeek/ComfyUI.
- **Preserved:** ADR-0001; US-011 enablement fail-closed; US-015 strategy default; US-016 guidance-only; US-017 mechanics; BL-007 auto-queue implementation; Flow A lifecycle; Flow B deferred; US-040 cancel out of scope.
