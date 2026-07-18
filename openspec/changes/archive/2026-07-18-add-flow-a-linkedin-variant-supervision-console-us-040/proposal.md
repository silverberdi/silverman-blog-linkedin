## Why

US-038 and US-039 delivered a Flow A LinkedIn variant supervision console that lists `pending` variants and supports edit/defer via existing US-017 POSTs, but operators still cannot cancel from that surface, and blocked-state context (publication enablement, deferred auto-queue eligibility, integration failures) is only partially visible. US-040 closes BL-015 Story 3 by wiring cancel through `POST /cancel-linkedin-publication`, clarifying defer/cancel outcomes that constrain BL-007 eligibility, and surfacing blocked reasons without inventing a parallel mutation SoT or LinkedIn API publish path.

## Goals

- From the existing supervision console, allow operators to **cancel** pending variants before queue per the LinkedIn variant review policy (US-015 / US-017), using authenticated `POST /cancel-linkedin-publication`.
- Preserve and clarify **defer** already delivered in US-039 so cancel-or-defer before queue is complete on the console (no second defer SoT).
- Surface **blocked states** relevant to supervision: publication enablement (display-only), deferred / `auto_queue_eligible` context, and integration-failure context operators need to understand why publication will not proceed under strategy-driven defaults.
- Invoke worker capabilities over HTTP only (ADR-0001); fail closed on `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` for real publish (do not bypass guards; cancel/defer remain pre-API).
- Make cancel/defer outcomes and eligibility effects visible and understandable (`pending` ≠ LinkedIn API published; cancel → not auto-queue eligible; defer → eligibility per US-017 due-time rule).
- Communicate failures and blocked mutation attempts clearly using existing US-017 / cancel stable error codes.
- Keep session API-key pattern and secrets audit on the static console HTML.

## Non-Goals

- Claiming **US-040 Story accepted** or **BL-015 closed** from this proposal or from apply alone.
- New mutation endpoints or parallel persistence paths (reuse `POST /cancel-linkedin-publication` and existing defer POST only).
- Changing **BL-007** auto-queue implementation beyond consuming existing US-017 eligibility effects of cancel/defer.
- Adding LinkedIn API publish paths; permanent enablement; bypassing publication guards.
- Rewriting US-015 policy, US-016 criteria, or US-017 normative HTTP contracts.
- Reopening closed BL-006–BL-014 work, or Flow B review console.
- Replacing US-038/US-039 read/edit/defer surfaces (extend in place).
- n8n Execute Command (ADR-0001).
- Treating US-016 criteria failure as an automatic technical block (guidance only).

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (Story 3 only) | Leave backlog open until Story accepted; do not close from apply |
| **US-040** | Yes | All six acceptance criteria |
| **US-039** | Consume | Defer UI already present; do not re-implement |
| **US-038** | Consume / minimal extend | Pending list + console; extend only for cancel + blocked-state visibility |
| **US-017** | Consume only | Cancel/defer POSTs and `operator_supervision` as SoT |
| **US-015 / US-016** | Consume only | Policy/criteria guidance; no rewrite |
| **BL-007** | Consume eligibility only | No auto-queue implementation changes |

**US-040 acceptance criteria addressed:**

1. Cancel or defer variants before queue per the LinkedIn variant review policy (cancel UI primary new work; defer retained from US-039; policy-aligned gaps only).
2. Surface blocked states (publication enablement, integration failures, deferred capabilities).
3. Invoke worker capabilities over HTTP only (ADR-0001); do not bypass publication guards.
4. The outcome is visible and understandable to the intended user.
5. Failures or blocked states are clearly communicated.
6. Existing completed work is not duplicated or unintentionally changed.

**Intentionally excluded:** Story accepted / BL-015 closed checkboxes; new mutation SoT; LinkedIn API publish; BL-007 code changes; US-015 default change.

## What Changes

- Extend capability `linkedin-variant-supervision-console` from Story 2 (edit/defer) to Story 3 cancel + blocked-state surfacing on the same console (`GET /flow-a/console/linkedin-variant-supervision`).
- Wire the console to call existing authenticated `POST /cancel-linkedin-publication` for pending pre-queue cancel (dry-run default on; explicit real confirm).
- Minimally extend `GET /flow-a/linkedin-variants/pending-supervision` only as needed so blocked-state / deferred / enablement / integration-failure **display context** is operator-visible without mount scraping (reuse existing row fields where sufficient; add fields only when required for US-040 AC2).
- After real cancel, refresh the pending list so the cancelled variant leaves the supervision window and outcome copy explains BL-007 eligibility exclusion without claiming LinkedIn API published.
- Surface cancel failures with existing stable codes (e.g. not allowed / not pending / auth / validation) alongside retained defer failure communication.
- Behavioral tests for cancel wiring, blocked-state display, dry-run, secrets audit; no real LinkedIn API calls.
- Update CURRENT-STATE and progress-checklist for **in-progress / demonstrated** US-040 items only — leave Story accepted and BL-015 closed unchecked.

## Capabilities

### New Capabilities

_None — Story 3 extends the existing console capability rather than introducing a separate capability name._

### Modified Capabilities

- `linkedin-variant-supervision-console`: Add operator-facing cancel actions via US-017 `POST /cancel-linkedin-publication`; supersede Story 2 “cancel remains out of scope” for console UI; strengthen blocked-state surfacing (enablement, deferred/`auto_queue_eligible`, integration-failure context); preserve edit/defer and read contracts from US-038/US-039.

## Impact

- **Product:** Advances BL-015 / US-040 (Story 3); BL-015 remains open until operator acceptance of all stories.
- **Worker / UI:** Extend static HTML at `GET /flow-a/console/linkedin-variant-supervision` with Cancel control + blocked-state presentation; optional thin pending-supervision field/context extension — no new mutation routes.
- **APIs:** Consume `POST /cancel-linkedin-publication` (and existing defer) as-is (auth, dry-run default, idempotency, stable codes).
- **Docs:** CURRENT-STATE (US-040 cancel + blocked context in progress/demonstrated); progress-checklist US-040 in-progress marks only; mechanics cross-link that Story 3 console exercises cancel (no US-017 contract rewrite).
- **Tests:** Console/action contract tests; secrets/placeholder audit still passes; mock worker responses — no LinkedIn/DeepSeek/ComfyUI.
- **Preserved:** ADR-0001; US-011 enablement fail-closed; US-015 strategy default; US-016 guidance-only; US-017 mechanics; BL-007 auto-queue implementation; Flow A lifecycle language; Flow B deferred.
