## Context

US-040G–K are Story accepted (operator-accepted 2026-07-19) on the deployed Flow A LinkedIn variant supervision console (`192.168.0.194:8010`): calendar-first Week/Month, EventModal + toasts, operator-local time, cancelled reopen, max-2 local-day density. US-040M (completed blogs as Published on blog) is a separate in-progress change that MUST NOT be redefined here; L MUST keep publication-state checkboxes including `completed` when that mapping is present.

Today the console still renders an always-visible FOCUS/Filters dock (`AppShell` → `filter-dock` → `Filters`) between metric chips (`StatusSummary`) and Week/Month. Operators experience that dock as a permanent second filter strip that duplicates chip focus and clutters the calendar-first chrome. US-040G already noted filters-dock removal was out of scope for the empty-grid fix; US-040L is the dedicated fix.

Filter capability and shared store state already exist (`FilterState` / `defaultFilters` / `setFilters` / `resetFilters` / hidden-critical banner). Empty Week/Month states already call `resetFilters`. Metric chips already write the same filter state. No new worker HTTP contracts are required for MVP.

**Constraints:** Console-only chrome delta; preserve ADR-0001 (worker HTTP only); no List restoration; no public URL / Google OIDC / BFF; no LinkedIn API publish from console; Visual DoD + operator walkthrough gate Story accepted; BL-015 stays open; do not unset US-038–US-040K/M Story accepted.

## Goals / Non-Goals

**Goals:**

- Remove the always-visible FOCUS/Filters dock from primary chrome.
- Header **Filters** control opens a modal with unchanged filter capability.
- Calm active cue on the header when filters diverge from `defaultFilters()`.
- Metric chips remain one-click focus; modal reflects resulting state when opened.
- Preserve empty-state Clear filters, hidden-critical discoverability, G–K baselines, session/`canMutate`, dry-run/confirm, ADR-0001, `*_utc`.
- Encode Visual DoD + walkthrough gates; honest CURRENT-STATE / product status.

**Non-Goals:**

- Flow B; public URL / Google OIDC / BFF / user-management.
- LinkedIn API publish from console; enablement bypass; n8n Execute Command; browser mount writes.
- Changing US-040M completed-blog mapping.
- New worker endpoints or filter-capability expansion.
- Closing BL-015 or accepting US-040L from Vitest alone.
- Unsetting US-038–US-040K/M Story accepted.

## Decisions

### D1 — Header label is Filters (not Search)

**Choice:** Label the header control **Filters**. Campaign/label text search remains a field inside the modal, not the primary header affordance.

**Rationale:** US-040L prefers Filters when the modal hosts the full filter set; Search only if search is primary with filters secondary. Current UX is full filter set.

**Not chosen:** Header labeled Search with filters buried as secondary tabs.

### D2 — Reuse existing Filters component inside a modal

**Choice:** Keep `Filters.tsx` as the capability surface (Channel, Campaign/label, Blocked only, Due soon, publication states including `completed` / Published on blog when present, Reset, hidden-critical banner). Host it in a new `FiltersModal` (or equivalent) opened from the header. Remove the permanent `filter-dock` section from `AppShell`.

**Rationale:** Smallest coherent delta; no filter-logic rewrite; same store state.

**Not chosen:** Rebuilding filter controls from scratch. Popover-only without modal a11y. Leaving the dock and adding a duplicate modal.

### D3 — Active-filter cue from defaultFilters divergence

**Choice:** Compute an active count (or equivalent) by comparing current `FilterState` to `defaultFilters()`:

| Field | Active when |
|-------|-------------|
| `channel` | ≠ `"all"` |
| `campaignQuery` | non-empty after trim |
| `blockedOnly` | `true` |
| `dueSoonOnly` | `true` |
| `publicationStates` | non-empty array |

Show a calm badge/count on the header control when any of the above is active. Exact badge copy (count vs “On”) fixed at apply; MUST be calm (not alarm-red failed styling).

**Rationale:** Matches AC “any non-default filter”; metric-chip focus that sets `blockedOnly` / publication states will light the cue without opening the modal.

**Not chosen:** Only counting text query. Silent filtered calendar with no header cue.

### D4 — Modal a11y aligned with EventModal patterns

**Choice:** Filters modal MUST use `role="dialog"`, `aria-modal="true"`, Escape and backdrop dismiss, keyboard focus trap while open, visible focus rings, and touch-friendly controls on ~375px. Prefer not stacking Filters modal over EventModal as the happy path (close or avoid opening Filters while EventModal owns the surface — exact stacking rule: if EventModal is open, Filters control MAY remain available but MUST NOT break EventModal focus trap; simplest apply rule: opening Filters while EventModal is open is allowed only if focus management remains correct, or disable Filters while EventModal open — prefer **allow sequential use**; do not require simultaneous dual modals).

**Rationale:** Reuse proven US-040H patterns; Story DoD includes mobile.

**Not chosen:** Non-modal always-expanded drawer that recreates the permanent strip.

### D5 — Metric chips stay outside the modal

**Choice:** Metric chips remain on the primary chrome as one-click focus shortcuts writing shared filter state. Opening Filters modal MUST show the resulting controls (checked boxes / toggles / query). Chips MUST NOT require the modal to apply focus.

**Rationale:** Explicit US-040L UX intent; preserves US-040F/G metric focus behavior.

### D6 — Empty-state Clear filters and hidden-critical stay

**Choice:** Week/Month empty-state Clear filters continue to call `resetFilters` without requiring the modal. Hidden-critical banner remains inside the Filters surface (modal) when filters hide critical failures; optionally a calm shell cue MAY remain if critical are hidden while modal is closed — prefer keeping the existing banner inside Filters (visible when modal open) AND ensuring the header active cue is on so operators know filters are active; the existing `hiddenCriticalCount` path MUST remain discoverable when the modal is open. If critical failures are hidden while the modal is closed, the active-filter cue on the header is the primary “calendar is filtered” signal; opening Filters reveals the show-critical affordance.

**Rationale:** Preserve AC for clear paths and discoverable critical failures without restoring the permanent dock.

### D7 — No worker contract changes

**Choice:** US-040L is console chrome only. No new endpoints, no mutation schema changes, no LinkedIn/DeepSeek/ComfyUI/Git calls.

**Rationale:** Filter state is already client-side on loaded snapshots.

### D8 — Honest status and acceptance gates

**Choice:** After apply: CURRENT-STATE / user-stories / progress-checklist reflect implementation evidence only; leave Acceptance criteria validated and Story accepted open until Visual DoD + walkthrough. Do not mark BL-015 closed. Do not unset US-038–US-040K/M Story accepted.

### D9 — Coexistence with US-040M

**Choice:** Do not change completed-blog mapping. Publication-state checkboxes in the modal MUST continue to include `completed` labeled Published on blog when that state exists in `PUBLICATION_STATES` / US-040M. If US-040M lands before or after L, L does not redefine it.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Filters feel “hidden” / undiscoverable | Clear header Filters control; active badge when filtered; Visual DoD + walkthrough gate |
| Dual modals (Event + Filters) confuse focus | Prefer sequential use; focus trap per modal; Vitest coverage |
| Hidden-critical only visible inside modal | Active cue when filtered; banner still in Filters when open; empty-state clear still works |
| Regressing filter capability | Reuse `Filters` component; Vitest asserts same controls present in modal |
| Claiming Story accepted from Vitest | Tasks gate Visual DoD + walkthrough |
| Accidental BL-015 close / Story unset | Explicit non-goals + doc task language |
| Drift vs US-040M | Preserve completed checkbox; no mapping rewrite |

## Migration Plan

1. Add Filters header control + FiltersModal; remove permanent filter-dock; active-filter helper; CSS.
2. Vitest (~1280/~375) for header, modal, badge, chip→modal state, empty clear, no dock; ensure prior suites pass.
3. Production `npm run build` into worker static path; secrets audit; `git diff --check`.
4. Honest CURRENT-STATE / product status (not Story accepted).
5. Deploy only after explicit approval; then Visual DoD + operator walkthrough before Story accepted.

**Rollback:** Revert console chrome to permanent filter-dock; no worker data migration.

## Open Questions

_(None blocking propose.)_

- Exact badge presentation (numeric count vs “Filtered”) — fix at apply; MUST be calm and visible when non-default.
- Whether to disable Filters while EventModal is open — prefer allow with correct focus; fix at apply if dual-modal proves brittle.
