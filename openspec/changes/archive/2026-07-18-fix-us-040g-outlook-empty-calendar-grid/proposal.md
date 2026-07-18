## Why

US-040G shipped calendar-first Week + Month and was deployed for operator walkthrough. When a week or month has zero scheduled items (or filters hide all items), the console **replaces** the day grid with a standalone empty panel. Operators expect an Outlook-like calendar: **blank days remain visible**; emptiness is communicated without dissolving the calendar structure. Until that holds, US-040G cannot clear the shared Visual DoD / “outcome understandable” gate or Story accepted.

## What Changes

- Keep the **Week day-column grid** and **Month day grid** rendered whenever Week or Month is active — including zero-item periods.
- Treat “no publications” as a **calm banner / overlay / inline empty cue on top of the persistent grid**, not a substitute for the calendar chrome.
- Empty day cells/columns stay blank (no fake events); today emphasis and prev/next / Today navigation remain usable so operators can page into future weeks/months that still look like a calendar.
- When filters hid everything, keep a clear path to clear/reset filters **without** collapsing the grid.
- Update Vitest + Visual DoD scenes so empty week/month evidence shows the **grid still present**.
- Honest product docs: US-040G remains not Story accepted until redeploy + walkthrough; BL-015 stays open.

## Goals

- Restore Outlook-like empty calendar comprehension for US-040G Week and Month.
- Unblock operator acceptance of the empty-state Visual DoD scenes for US-040G.
- Preserve Week default, Month secondary, List removed, metric chip calendar navigation, interim event-chip actions, and worker HTTP contracts.

## Non-goals

- Removing the Filters dock / channel-campaign filter panel (separate follow-up US after operator request).
- Adding a Cancelled metric chip or cancelled reopen UX (**US-040J**).
- Event modal + toasts (**US-040H**), local-day bucketing overhaul (**US-040I**), max-2/day density (**US-040K**).
- Public URL / Google auth, LinkedIn API publish, Flow B, n8n Execute Command, BFF/DB/user-management.
- Closing BL-015 or marking US-040G Story accepted from implementation alone (Visual DoD + walkthrough still required after deploy).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `linkedin-variant-supervision-console`: Clarify intentional empty Week/Month requirements so the calendar day structure MUST remain visible (Outlook-like); empty messaging MUST NOT replace the grid.

## Impact

- **Product:** BL-015 / **US-040G** empty-state acceptance criteria and Visual DoD scenes (empty week / empty month desktop + mobile).
- **Frontend:** `WeekView`, `MonthCalendarView`, related CSS, Vitest empty-state assertions; rebuild static assets under `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`.
- **Docs:** CURRENT-STATE / user-stories / progress-checklist honesty after apply; no worker API or mutation SoT changes.
- **Deploy:** Explicit approval required before Visual DoD / Story accepted.

## Acceptance criteria addressed (US-040G)

- Empty week/month must remain a **calendar product** surface (day structure visible; calm empty copy; clear-filters when filters hid everything).
- Visual DoD empty week / empty month scenes must show grid + empty cue, not a gridless void panel.
- Operator walkthrough gate for empty comprehension (does not by itself accept modal/toasts/cancelled/density stories).

## Acceptance criteria intentionally excluded

- Filters dock removal; Cancelled chip; US-040H/I/J/K product outcomes; BL-015 closure.
