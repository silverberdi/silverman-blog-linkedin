## Why

After US-040K, the calendar-first console still shows an always-visible FOCUS/Filters dock under the metric chips. Operators experience that strip as a permanent second filter surface that duplicates chip focus and clutters Week/Month. US-040L (BL-015) collapses those controls into a header Filters control + modal so the calendar stays primary while filter capability and discoverability remain.

## Goals

- Remove the always-visible FOCUS/Filters dock from primary console chrome.
- Add a clear header control labeled **Filters** (prefer over **Search** because the modal hosts the full filter set; campaign/label search stays one control inside the modal, not the primary header affordance).
- On click, open a modal containing the **current** filter controls unchanged in capability: Channel, Campaign/label, Blocked only, Due soon (48h), Publication state checkboxes (including completed / Published on blog from US-040M when that mapping is present), Reset.
- When any non-default filter is active, the header control MUST show a calm active cue (badge/count or equivalent).
- Metric chips MAY remain one-click focus shortcuts on the same filter state; opening the modal MUST reflect the resulting filter state.
- Preserve Week/Month empty-state Clear filters paths.
- Preserve session/`canMutate`, dry-run/confirm, EventModal, local-time, density cues (US-040K), cancelled reopen (US-040J), ADR-0001, `*_utc` wire fields.
- Do not restore List as primary chrome.
- Encode Shared UX DoD: Visual DoD (desktop + mobile) + operator walkthrough before Story accepted; Vitest alone insufficient.
- Leave BL-015 open; do not unset US-038–US-040K/M Story accepted (or their gates) as a side effect; do not change US-040M completed-blog mapping.

## Non-Goals

- Flow B (BL-016+ / US-074–081).
- Public URL hosting / Google OIDC / BFF / user-management.
- LinkedIn API publish from the console; bypassing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; n8n Execute Command; browser mount writes.
- Changing US-040M completed-blog display/mapping semantics.
- Closing **BL-015** or marking **US-040L Story accepted** / Acceptance criteria validated from implementation or Vitest alone.
- Unsetting or reopening **US-038–US-040K** (or US-040M) Story accepted / Acceptance criteria validated as a side effect.
- Restoring List as primary operator chrome.
- New worker endpoints, schema changes, or filter-capability expansion beyond relocating existing controls.
- Push / deploy without explicit approval after apply/verify.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (US-040L only) | Remains open until operator-validated completion outcome |
| **US-040L** | Yes | Search/Filters header modal; collapse always-visible filters dock |
| **US-038–US-040K** | Preserve | Do not regress; do not unset Story accepted |
| **US-040M** | Preserve mapping | Include completed / Published on blog in publication-state checkboxes when present; do not redefine mapping |
| **BL-016+ / Flow B** | Out | Explicit non-goal |

US-040L acceptance criteria addressed by this change (implementation + evidence gates; Story accepted only after walkthrough):

- Remove always-visible FOCUS/Filters dock from primary chrome.
- Header Filters (or Search) button opens modal with existing filter controls without reducing capability.
- Calm active cue on header when any non-default filter is active.
- Metric chips remain one-click focus shortcuts; modal reflects chip-applied state.
- Week/Month empty-state Clear filters continue to work.
- Preserve Week default + Month secondary, EventModal + toasts, local-time, cancelled reopen, density cues, session/`canMutate`, dry-run/confirm, worker HTTP-only (ADR-0001), `*_utc` wire fields.
- No List restoration; no public URL / Google OIDC / BFF / user-management; no LinkedIn API publish from console.
- Visual DoD evidence (desktop + mobile); Vitest alone insufficient for Story accepted.
- Operator walkthrough on deployed or agreed preview before Story accepted.
- Failures / blocked states clearly communicated.
- Existing completed work not duplicated or unintentionally changed.

Intentionally excluded: BL-015 closed, US-040L Story accepted from code alone, US-040M mapping changes, Flow B, deploy/push, Google/OIDC, LinkedIn API publish from console.

## What Changes

- Remove the always-visible `filter-dock` / FOCUS/Filters panel from the primary scan path between metric chips and Week/Month.
- Add a header **Filters** control that opens a focused filters modal hosting the existing `Filters` controls (same store state and capability).
- Show a calm active-filter cue (badge/count or equivalent) on the header control when filters diverge from defaults.
- Keep metric-chip focus writing the same shared filter state; modal open MUST show that state.
- Preserve empty-state Clear filters, hidden-critical discoverability, Week/Month baselines, EventModal a11y patterns (focus trap, Escape, backdrop).
- Update `linkedin-variant-supervision-console` requirements; Vitest (~1280/~375); rebuild static assets into worker static path.
- Honest CURRENT-STATE / US-040L product status (implemented ≠ Story accepted; Visual DoD + walkthrough gated; BL-015 open).

## Capabilities

### New Capabilities

_(none — filters-modal is a chrome relocation on the existing supervision console capability)_

### Modified Capabilities

- `linkedin-variant-supervision-console`: Collapse always-visible FOCUS/Filters dock into header Filters control + modal; active-filter cue; preserve filter capability, metric-chip focus, empty-state clear paths, G–K baselines, session/`canMutate`, dry-run/confirm, worker HTTP SoT, local-time, density, cancelled reopen, `*_utc` wire fields; US-040L Visual DoD / walkthrough gates.

## Impact

- **Product:** Advances BL-015 / US-040L toward calendar-first chrome without permanent filter strip duplication; BL-015 stays open; US-040L Story accepted only after Visual DoD + operator walkthrough.
- **Worker:** No new endpoints or mutation contracts required for MVP (console-only chrome change). Static rebuild of console assets under `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`.
- **Frontend:** `frontend/linkedin-variant-supervision-console/` — AppShell header control, FiltersModal (or equivalent), remove permanent filter-dock, active-filter badge helper, Vitest (~1280/~375), CSS polish consistent with existing dark console.
- **Ops/docs:** CURRENT-STATE + product status honesty; do not claim Story accepted or BL-015 closed from Vitest alone.
- **Specs:** Delta under this change; sync later updates main.
- **Lifecycle (approval-gated):** apply → verify → implementation commit → sync → archive → explicit push → explicit deploy → Visual DoD / operator walkthrough → only then Story accepted. No apply until explicit approval of this proposal.

## Lifecycle gates (normative for this change)

1. Explicit user approval of this proposal (and design/specs/tasks) before `/opsx-apply`.
2. `/opsx-verify` after implementation; re-run if post-verify edits.
3. Explicit approval before implementation commit; separate sync and archive commits.
4. Explicit approval before push and before deploy to `192.168.0.194`.
5. Visual DoD (desktop + mobile) + operator walkthrough required before marking US-040L Acceptance criteria validated / Story accepted.
6. Do not mark BL-015 closed; do not unset US-038–US-040K/M Story accepted (or their open gates) from this change alone.
