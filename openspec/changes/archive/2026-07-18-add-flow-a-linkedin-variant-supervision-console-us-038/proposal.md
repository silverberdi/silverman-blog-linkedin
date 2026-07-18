## Why

Flow A LinkedIn variants enter an optional supervision window while `publish_state` is `pending` (US-015), with quality guidance (US-016) and persisted edit/defer/cancel mechanics already on worker HTTP (US-017). Operators still must open raw campaign JSON and calendar files to see what is pending. BL-015 / US-038 delivers the first console story: a read-only, operator-facing view of pending variants so supervision does not require inspecting mount files.

## Goals

- Present Flow A variants in the optional supervision window (`publish_state=pending`) on a calendar and/or campaign-aligned operator view.
- For each pending variant, show at least: campaign id, variant id, audience, `scheduled_at_utc`, and `publish_state`.
- Align the view with the editorial calendar where applicable (join on existing `campaign_id` / calendar contracts).
- Make the outcome visible and understandable to a content operator without reading worker source or raw mount files.
- Communicate read/display failures and blocked states clearly (missing calendar, unreadable campaign metadata, enablement-off as display context) without inventing new publication semantics.
- Reuse US-015 / US-016 / US-017 contracts; consume worker HTTP only (ADR-0001).

## Non-Goals

- **US-039** — edit variant content, defer/reschedule UI, or persist operator mutations beyond reading existing US-017 state for display.
- **US-040** — cancel/defer action surfaces that constrain auto-queue eligibility; full blocked/integration failure action consoles beyond Story 1 read-only visibility.
- Claiming **Story accepted** or **BL-015 closed** from this proposal or from apply alone.
- New LinkedIn API publish paths; bypassing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Reopening **BL-007** publication automation or changing auto-queue behavior.
- Reopening **BL-008–BL-014** closed work.
- Flow B review console or mandatory-review UI.
- Changing US-015 strategy-driven default (absence of operator action still means expected to publish when automation/manual queue runs).
- n8n Execute Command; embedding secrets in UI, docs, or responses.
- Browser scraping of raw mount files as source of truth.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (Story 1 only) | Leave backlog open; do not close |
| **US-038** | Yes | All five acceptance criteria |
| **US-039 / US-040** | No | Deferred to later stories |
| **US-015 / US-016 / US-017** | Consume only | Cross-links; no policy/mechanics rewrite |
| **BL-007** | No | Auto-queue already implemented elsewhere; this change is the view |

**US-038 acceptance criteria addressed:**

1. Present `pending` variants with campaign id, variant id, audience, `scheduled_at_utc`, and `publish_state`.
2. Align the view with the editorial calendar where applicable.
3. The outcome is visible and understandable to the intended user.
4. Failures or blocked states are clearly communicated.
5. Existing completed work is not duplicated or unintentionally changed.

**Intentionally excluded:** US-039 edit/defer UI and persistence; US-040 cancel/block action surfaces; Story accepted / BL-015 closed checkboxes.

## What Changes

- Add a new capability `linkedin-variant-supervision-console` defining the operator-facing **read-only** supervision view for Flow A `pending` LinkedIn variants (US-038).
- Add a thin authenticated worker **read** API at the fixed path `GET /flow-a/linkedin-variants/pending-supervision` that aggregates campaign `variants[]` + editorial calendar join fields (existing GETs `/flow-a/operational-status` and `/editorial-calendar/status` do not return per-variant rows with audience / `scheduled_at_utc`).
- Add a minimal same-origin operator UI at the fixed path `GET /flow-a/console/linkedin-variant-supervision` (static HTML served by the worker) that renders the pending list in campaign and/or calendar-aligned grouping; API key via browser prompt or local-only config — never embedded in committed HTML/docs.
- Document how the console consumes US-015 policy, US-016 criteria (guidance links only), and US-017 mechanics (display of existing `operator_supervision` when present — no mutation in Story 1).
- Behavioral tests for the read path (happy path, empty pending set, calendar missing/invalid, campaign read failures) plus an explicit static-HTML secrets audit (no real keys/tokens; no `CHANGE_ME` or similar placeholders that look like secrets); no LinkedIn API calls.
- Update CURRENT-STATE and progress-checklist for **in-progress / demonstrated** US-038 items only — leave Story accepted and BL-015 closed unchecked.

## Capabilities

### New Capabilities

- `linkedin-variant-supervision-console`: Operator-facing read-only console for Flow A LinkedIn variants in the optional `pending` supervision window — per-variant fields, calendar alignment, failure communication, and ADR-0001 worker-HTTP data access.

### Modified Capabilities

_None — US-038 introduces the console surface; it does not change US-015/US-016/US-017 normative requirements, publication integration, or editorial calendar orchestration contracts. Cross-link and CURRENT-STATE wording updates are documentation tasks, not requirement deltas._

## Impact

- **Product:** Starts BL-015 / US-038 (Story 1); BL-015 remains open until US-039/US-040.
- **Worker:** Authenticated `GET /flow-a/linkedin-variants/pending-supervision` + static page at `GET /flow-a/console/linkedin-variant-supervision`; read-only aggregation over `metadata/campaigns/` and `editorial-calendar/calendar.json`.
- **APIs:** Fixed Flow A read paths above; no mutation of US-017 POST routes; no new publish/queue paths.
- **Docs:** CURRENT-STATE (console Story 1 in progress/demonstrated); progress-checklist US-038 in-progress marks only; optional cross-links from policy/mechanics “future console” language to the new surface without rewriting policy substance.
- **Tests:** Read-path unit/contract tests; static HTML secrets/placeholder audit; no real LinkedIn/DeepSeek/ComfyUI.
- **Preserved:** ADR-0001; US-011 enablement fail-closed; US-015 strategy default; US-017 mechanics; BL-007 auto-queue; Flow A lifecycle; Flow B deferred.
