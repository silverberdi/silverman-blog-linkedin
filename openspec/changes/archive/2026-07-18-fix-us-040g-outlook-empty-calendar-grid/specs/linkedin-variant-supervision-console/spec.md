## MODIFIED Requirements

### Requirement: Intentional empty Week and Month states

When a visible week or month has zero items after filters, the console MUST show a deliberate empty cue with short operator-facing copy and, when filters hid everything, a path to clear or reset filters.

Empty week/month presentations MUST use the dark theme and MUST NOT appear as an unexplained blank content void or system failure.

The Week day-column structure and the Month day grid MUST remain visible during empty and filter-zero periods (Outlook-like blank days). Empty messaging MUST NOT replace or remove the calendar day structure for the active week or month cursor. Day columns/cells with no items MUST remain blank (no fabricated events). Week/Month navigation (previous/next and Today/This-week where applicable) MUST remain usable while empty.

#### Scenario: Empty week keeps day columns

- **WHEN** the visible week has no items after filters
- **THEN** the Week view still renders the day-column calendar for that week and shows a calm empty cue (for example that there are no publications this week) without presenting a blank broken panel or a gridless substitute panel as the only content

#### Scenario: Empty month keeps day grid

- **WHEN** the visible month has no items after filters
- **THEN** the Month view still renders the month day grid for that month and shows a calm empty cue without presenting a blank broken panel or a gridless substitute panel as the only content

#### Scenario: Filters caused emptiness

- **WHEN** items exist in the shared model but active filters hide all items in the visible week or month
- **THEN** the empty cue offers a path to clear or reset filters while the Week or Month calendar day structure remains visible

#### Scenario: Empty period remains navigable

- **WHEN** the visible week or month has zero items after filters
- **THEN** the operator can still use previous/next (and Today/This-week where applicable) without the calendar chrome disappearing

### Requirement: Metric chips navigate within Week and Month only

Interactive operational metric chips MUST apply focus filters and MUST navigate or focus within Week or Month calendar cursors so matching work is visible on the calendar.

Metric chips MUST NOT reopen, switch to, or depend on a List view.

When no matching item exists for a metric focus, the console MUST keep the calendar surface — including the Week day-column structure or Month day grid — and show an intentional empty or zero-match cue rather than falling back to a list or replacing the calendar with a gridless panel.

#### Scenario: Blocked metric stays on calendar

- **WHEN** an operator activates the blocked metric while on Week or Month
- **THEN** the console applies the blocked focus filter and adjusts the Week or Month cursor toward matching work without opening a List view

#### Scenario: Zero matches do not restore List

- **WHEN** a metric focus matches zero items
- **THEN** the console remains on Week or Month with an intentional empty or zero-match presentation, keeps the calendar day structure visible, and does not open a List

### Requirement: US-040G Visual DoD and acceptance gates

US-040G MUST require desktop and mobile Visual DoD evidence (screenshots or equivalent browser-driven capture) covering at least:

- Week first paint
- empty week (calendar day columns still visible with empty cue)
- dense week
- Month switch
- empty month (month day grid still visible with empty cue)
- dense month
- Today / This-week control
- proof that List chrome is gone

Vitest or component assertions alone MUST NOT be treated as sufficient for Story accepted.

US-040G Story accepted and Acceptance criteria validated MUST NOT be marked until the content operator completes a live walkthrough on the deployed console or an explicitly agreed preview and confirms the UX meets calendar-first intent, including Outlook-like empty weeks/months.

Implementation commit and “business outcome demonstrated” MAY occur before that gate. BL-015 MUST remain open until the backlog completion outcome is operator-validated; shipping US-040G code or this empty-grid fix MUST NOT close BL-015 by itself.

If browser capture is unavailable in the implementation environment, status language MUST record that limitation and MUST leave Visual DoD / Story-accepted gates open.

#### Scenario: Visual DoD scenes are required

- **WHEN** US-040G claims visual validation complete for Story accepted
- **THEN** desktop and mobile evidence exists for Week first paint, empty week with persistent day columns, dense week, Month switch, empty month with persistent day grid, dense month, Today/This-week, and absence of List chrome

#### Scenario: Vitest alone does not accept the story

- **WHEN** only Vitest or component assertions have passed
- **THEN** status language does not mark US-040G Story accepted or Acceptance criteria validated

#### Scenario: Walkthrough gate blocks Story accepted

- **WHEN** implementation is complete but the operator walkthrough on deployed or agreed preview has not confirmed calendar-first UX including empty-grid persistence
- **THEN** US-040G remains not Story accepted and BL-015 remains open
