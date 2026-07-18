## ADDED Requirements

### Requirement: Event modal as primary event surface (US-040H)

The Flow A LinkedIn variant supervision console MUST open a focused **event modal** when the operator activates an event chip on Week or Month.

The event modal MUST be the single primary surface for viewing the selected item and for edit, reschedule/defer, and cancel actions where those actions are already supported for that item.

The console MUST NOT use the US-040G interim detail panel (`InterimEventPanel` or equivalent) as the primary event surface after US-040H ships.

The modal MUST present operator-facing fields first: title/campaign, channel/audience, local datetime, publication state, and risk/blocked cues when applicable. Raw ids, endpoint names, and worker codes MUST be placed in an expandable diagnostics region (collapsed by default).

Desktop MUST present a centered or anchored modal with clear hierarchy (title → state → schedule → actions). Mobile MUST present a full-screen or near-full sheet with large touch targets.

#### Scenario: Event chip opens event modal

- **WHEN** an operator activates an event chip on Week or Month
- **THEN** the console opens the event modal for that item with view affordances and edit/reschedule/cancel actions appropriate to state and `canMutate`

#### Scenario: Operator-facing fields precede diagnostics

- **WHEN** the event modal is open
- **THEN** title/campaign, channel/audience, local datetime, publication state, and risk cues appear before raw ids, endpoint names, and worker codes, which remain behind expandable diagnostics

#### Scenario: Actions reachable without List

- **WHEN** the event modal is open for an item that supports edit, reschedule/defer, or cancel
- **THEN** those actions are reachable from the modal without restoring a List view

#### Scenario: Interim panel is not the primary surface

- **WHEN** US-040H is implemented
- **THEN** the console does not present `InterimEventPanel` (or equivalent interim drawer) as the primary event interaction surface

### Requirement: Empty day click must not open day-agenda dump

Clicking empty day space (day cell/header without activating an event chip) MUST NOT open a multi-item day-agenda dump that competes with the event modal.

Days MAY keep light hover or selected focus styling only. Month overflow cues such as “+N more” MUST NOT restore a multi-item agenda panel as the primary inspection path.

#### Scenario: Empty day click stays on calendar

- **WHEN** an operator clicks empty day space on Week or Month
- **THEN** the console does not open a multi-item day-agenda dump and does not open the event modal for multiple items

#### Scenario: Month day-focus chip list is absent

- **WHEN** a day is selected or focused on Month after US-040H
- **THEN** the console does not render a multi-item `month-day-focus` chip-list dump as an operator action surface

### Requirement: Ephemeral toast feedback (US-040H)

Success results, dry-run validation results, and non-blocking informational feedback MUST appear as ephemeral **toasts** (top-right or equivalent overlay), not as persistent full-width green success banners that permanently push the calendar down.

Toasts MUST auto-dismiss after approximately 4–6 seconds, MUST be manually dismissible, and MUST stack sensibly when multiple toasts are active.

Dry-run versus real commit MUST remain visually obvious in toast copy (and inside the modal controls). Destructive cancel MUST remain behind an explicit confirmation dialog and MUST NOT be toast-only; a success toast MAY follow after a confirmed cancel.

Failures and blocked states MUST be communicated via error toasts and/or in-modal errors and MUST NOT fail silently.

#### Scenario: Happy-path success uses toast

- **WHEN** an operator completes a successful edit, reschedule/defer, or cancel (dry-run or real) from the event modal
- **THEN** feedback appears as a toast overlay and does not permanently push the calendar layout down with a full-width green success banner

#### Scenario: Toast auto-dismiss and manual dismiss

- **WHEN** a success or info toast is shown
- **THEN** it auto-dismisses within approximately 4–6 seconds and can be dismissed manually before that

#### Scenario: Dry-run copy is distinct

- **WHEN** a dry-run action succeeds
- **THEN** toast copy (and modal mode affordances) clearly indicate dry-run / no mutation, distinct from real persisted write language

#### Scenario: Cancel confirmation is not toast-only

- **WHEN** an operator initiates destructive cancel
- **THEN** the console requires an explicit confirmation dialog before the cancel mutation, and toast success (if any) occurs only after confirmation

#### Scenario: Failures are not silent

- **WHEN** a mutation or load fails while the modal or toast path is in use
- **THEN** the operator sees an error toast and/or in-modal error message

### Requirement: Quiet app-bar context instead of green success banners

The primary scan path MUST NOT show persistent full-width green “everything is fine” success or enablement banners for happy-path status. LinkedIn publish-guard and session context MAY remain visible as a compact chip or quiet status in the app bar / session strip.

Structural warn/error context that is not happy-path success (for example filter-hidden critical notices or calendar issue warnings) MAY remain as non-green banners where already required.

#### Scenario: Publish-guard is quiet, not full-width green

- **WHEN** LinkedIn publication enablement context is shown on the primary scan path
- **THEN** it appears as a compact chip or quiet status and not as a persistent full-width green success banner

#### Scenario: Happy-path green success banners absent

- **WHEN** the operator is scanning Week or Month without an active error condition after a successful prior action
- **THEN** the primary scan path does not retain a persistent full-width green success banner from that action

### Requirement: Event modal keyboard and accessibility (US-040H)

While the event modal is open, keyboard focus MUST be trapped inside the modal (and any nested confirmation dialogs while those are open).

Escape, backdrop click, and the explicit close control MUST dismiss the modal. When unsaved edits or schedule drafts exist, the console MUST warn about draft loss and require confirmation before discarding.

Critical actions MUST be reachable via visible controls (not hover-only). Interactive controls MUST show visible focus rings under keyboard focus.

#### Scenario: Focus trap while modal open

- **WHEN** the event modal is open and the operator tabs through controls
- **THEN** focus remains within the modal until it is dismissed (or within a nested confirmation dialog while that dialog is open)

#### Scenario: Escape with unsaved draft warns

- **WHEN** the event modal has unsaved edits or schedule drafts and the operator presses Escape or activates close/backdrop dismiss
- **THEN** the console warns about draft loss and does not discard without confirmation

#### Scenario: Escape without draft closes

- **WHEN** the event modal has no unsaved drafts and the operator presses Escape or activates close/backdrop dismiss
- **THEN** the modal closes without a draft-loss warning

### Requirement: US-040H Visual DoD and acceptance gates

US-040H MUST require desktop and mobile Visual DoD evidence (screenshots or equivalent browser-driven capture) covering at least:

- event open
- modal hierarchy (operator fields before diagnostics)
- edit/reschedule in modal
- toast success + auto-dismiss
- toast stack
- cancel confirmation
- mobile sheet
- proof of no day-agenda dump
- proof of no persistent green success banner on happy path

Vitest or component assertions alone MUST NOT be treated as sufficient for Story accepted.

US-040H Story accepted and Acceptance criteria validated MUST NOT be marked until the content operator completes a live walkthrough on the deployed console or an explicitly agreed preview and confirms the modal + toast interaction feels focused and modern.

Implementation commit and “business outcome demonstrated” MAY occur before that gate. BL-015 MUST remain open until the backlog completion outcome is operator-validated; shipping US-040H code MUST NOT close BL-015 by itself.

If browser capture is unavailable in the implementation environment, status language MUST record that limitation and MUST leave Visual DoD / Story-accepted gates open.

#### Scenario: Visual DoD scenes are required

- **WHEN** US-040H claims visual validation complete for Story accepted
- **THEN** desktop and mobile evidence exists for event open, modal hierarchy, edit/reschedule in modal, toast success + auto-dismiss, toast stack, cancel confirmation, mobile sheet, absence of day-agenda dump, and absence of persistent green success banner on happy path

#### Scenario: Vitest alone does not accept the story

- **WHEN** only Vitest or component assertions have passed
- **THEN** status language does not mark US-040H Story accepted or Acceptance criteria validated

#### Scenario: Walkthrough gate blocks Story accepted

- **WHEN** implementation is complete but the operator walkthrough on deployed or agreed preview has not confirmed modal + toast UX
- **THEN** US-040H remains not Story accepted and BL-015 remains open

### Requirement: US-040H scope preserves baselines and defers I–K products

US-040H MUST NOT mark BL-015 closed or US-040H Story accepted by implementation alone.

US-040H MUST preserve:

- React + TypeScript + Vite same-origin static delivery
- typed injectable-auth API client
- shared normalized frontend model fed by worker HTTP reads
- ScheduleEditor mutation SoT (US-017 defer for LinkedIn; editorial-calendar schedule-update for blog) and existing correct/cancel contracts
- session states and `canMutate` gating
- Week (default) + Month calendar-first chrome without List restoration
- qualified publication language (`pending`, `queued`, `cancelled`, `flow_a_complete`, blog handoff ≠ LinkedIn API published)

US-040H MUST NOT implement US-040I local-day bucketing overhaul (existing local time display on chips/modal is allowed and MUST NOT be claimed as I complete), MUST NOT implement US-040J cancelled reopen worker path, and MUST NOT implement US-040K max-2-per-local-day enforcement.

US-040H MUST NOT activate public URL hosting, MUST NOT integrate live Google/OIDC, MUST NOT introduce a BFF/database/user-management product, MUST NOT call the LinkedIn publication API, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, MUST NOT read or write raw mount paths from the browser, and MUST NOT add new worker mutation routes unless a separate design amendment explicitly justifies them.

#### Scenario: Prior architecture baselines remain

- **WHEN** US-040H is implemented
- **THEN** worker HTTP remains the only console data/mutation path, ScheduleEditor / US-017 semantics remain the mutation surface inside the modal, session/`canMutate` gating remains, and List chrome is not restored

#### Scenario: I–K products remain out of apply scope

- **WHEN** US-040H implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records US-040I local-day bucketing, US-040J reopen, and US-040K density enforcement as not delivered by this change

#### Scenario: BL-015 remains open

- **WHEN** US-040H implementation lands
- **THEN** status language does not mark BL-015 closed or US-040H Story accepted by implementation alone

## MODIFIED Requirements

### Requirement: Interim calendar action entry points until event modal

After US-040H, clicking an event chip on Week or Month MUST open the focused event modal (see Requirement: Event modal as primary event surface (US-040H)), not an interim detail panel claimed as a temporary stand-in.

Edit, defer/reschedule, and cancel capabilities (where already supported) MUST remain reachable via the event modal using the typed API client and existing worker mutation contracts (ScheduleEditor / US-017 semantics).

Day selection MAY provide light focus affordance only; it MUST NOT restore a list-like multi-item diagnostic dump or day-agenda dump as the primary action surface.

Historical US-040G interim-panel language remains valid for that story’s demonstrated scope and MUST NOT be cited to keep the interim panel as the primary surface after H ships.

#### Scenario: Event chip opens event modal actions

- **WHEN** an operator activates an editable event chip on Week or Month after US-040H
- **THEN** the console opens the event modal for that item and preserves edit / defer/reschedule / cancel via existing worker HTTP mutations

#### Scenario: Capabilities remain reachable without List

- **WHEN** List chrome has been removed
- **THEN** pending LinkedIn edit, defer/reschedule, and cancel (where previously supported) remain reachable from calendar event entry points through the event modal

#### Scenario: Day click is not an agenda dump

- **WHEN** an operator selects or focuses a day without activating an event chip
- **THEN** the console does not open a multi-item day-agenda dump as the primary action surface
