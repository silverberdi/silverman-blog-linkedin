## ADDED Requirements

### Requirement: Deliberate postpone and reschedule control from the console (US-084)

The Silverman Authority Manager / LinkedIn console MUST provide a **deliberate postpone / reschedule control** for LinkedIn-channel items that are **not Live on LinkedIn** and are schedule-mutable under worker truth, including at least:

- **Scheduled / `pending`**
- **Waiting to send / `queued`**

when session `canMutate` is true and schedule-visibility (or equivalent) marks the item schedule-editable.

The control MUST:

- let the operator choose a **new future local** datetime (operator-local picker; wire `new_scheduled_at_utc` via the typed API client)
- persist only through authenticated `POST /defer-linkedin-variant` (shared ScheduleEditor / EventModal — no second publication or schedule pipeline)
- make **preview/dry-run** versus **real/committed** unmistakable before submit and after outcome (reuse US-083 preview honesty; dry-run remains default)
- present as an intentional control action (clear primary affordance and framing), not an accidental-looking always-on single lever

**Live on LinkedIn** MUST NOT be postpone/reschedule targets. **Cancelled** continues via the approved reopen path (not this postpone control). **Failed** and in-flight **publishing** MUST be unavailable with plain-language reason and usable next step unless a later approved change makes them schedule-mutable. Blog schedule-update remains the blog mutation path and MUST NOT be used as LinkedIn defer SoT.

Waiting to send / `queued` MUST be a **working** postpone/reschedule control (not “unavailable / not available yet”). Cancel-while-queued remains US-085 and MUST NOT be implied by postpone.

This requirement MUST NOT implement cancel-for-queued (US-085), publish-now / LinkedIn API publish (US-086), ADR-0001 bypass, or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` bypass. It MUST NOT reopen BL-015 as supervision-only product closure.

#### Scenario: Operator postpones a Scheduled LinkedIn variant

- **WHEN** an authenticated mutating operator opens a schedule-editable LinkedIn item in Scheduled / `pending` state and submits a future local time through the postpone/reschedule control with dry-run false
- **THEN** the console sends `POST /defer-linkedin-variant` with campaign id, variant id, and `new_scheduled_at_utc` and does not write editorial mounts from the browser

#### Scenario: Operator postpones a Waiting-to-send LinkedIn variant

- **WHEN** an authenticated mutating operator opens a schedule-editable LinkedIn item in Waiting to send / `queued` state and submits a future local time through the postpone/reschedule control with dry-run false
- **THEN** the console sends `POST /defer-linkedin-variant` with campaign id, variant id, and `new_scheduled_at_utc` and does not claim LinkedIn API published or invent a second mutation endpoint

#### Scenario: Preview postpone does not claim schedule changed

- **WHEN** the operator runs postpone/reschedule with preview/dry-run default or explicitly selected
- **THEN** the outcome states that no lasting schedule change was made and the console does not claim the new time was saved or that the item went live on LinkedIn

#### Scenario: Live on LinkedIn cannot be postponed

- **WHEN** an operator opens a LinkedIn item that is Live on LinkedIn
- **THEN** postpone/reschedule is unavailable with a plain-language reason and no defer mutation is invoked

#### Scenario: Control is deliberate, not spectator misuse

- **WHEN** an operator opens an eligible Scheduled or Waiting-to-send LinkedIn item in EventModal
- **THEN** postpone/reschedule is offered as a clear intentional control with preview vs real framing, not only an unlabeled accidental-looking single lever

#### Scenario: No second publication pipeline

- **WHEN** US-084 postpone/reschedule is exercised for pending or queued
- **THEN** persistence uses only existing `POST /defer-linkedin-variant` (plus existing reopen path when applicable) and does not add a LinkedIn API publish route or n8n Execute Command path

### Requirement: Calendar and authoritative schedule agree after real reschedule (US-084)

After a **successful real** LinkedIn postpone/reschedule (`POST /defer-linkedin-variant` with `dry_run` false) for `pending` or `queued`, the console Week and Month calendars and the variant’s **authoritative** schedule (`scheduled_at_utc` from worker schedule-visibility / pending-supervision reads) MUST **agree on the new time**.

The console MUST refresh worker reads into the shared model after real success so the variant identity is placed on the **new** operator-local day/time and the previous slot is **not** left as operator truth for that item.

Preview/dry-run success MUST NOT move calendar placement to the proposed time.

The console MUST NOT claim that the editorial calendar file/store was automatically written as LinkedIn SoT. Secondary calendar-join context MUST NOT override or visually present a stale old LinkedIn due time as authoritative after a real defer when campaign `scheduled_at_utc` has changed.

#### Scenario: Real reschedule moves Week and Month to the new local slot

- **WHEN** a real postpone/reschedule succeeds for a LinkedIn variant (pending or queued) and the console refreshes schedule-visibility (and pending-supervision as applicable)
- **THEN** Week and Month show that variant at the new operator-local day/time matching the authoritative `scheduled_at_utc`, and the old slot is not presented as that variant’s current schedule

#### Scenario: Preview leaves calendar placement unchanged

- **WHEN** a preview/dry-run postpone/reschedule succeeds
- **THEN** Week and Month placement for that variant remains at the prior authoritative schedule

#### Scenario: Stale secondary join cannot override new schedule

- **WHEN** a real defer updates campaign `scheduled_at_utc` and any secondary calendar-join context still reflects an older due time
- **THEN** the operator-facing calendar truth follows the refreshed authoritative schedule, not the stale join as the current slot

### Requirement: Density and cadence refusals explain next steps (US-084)

When postpone/reschedule is refused by product rules (including US-040K max-2 publications per operator-local day, interim defer cadence/saturation checks, non-future time, ineligible state, or session cannot mutate), the console MUST explain the refusal in **plain language** with a **usable next step**.

Primary UI MUST NOT rely only on raw machine codes. Expandable diagnostics MAY still show stable worker codes.

US-040K max-2/local-day MUST remain enforced (client pre-check and worker) for pending and queued defer. The console MUST NOT claim LinkedIn API published on refusal or on defer success.

#### Scenario: Full local day refusal includes a next step

- **WHEN** postpone/reschedule targets a local day that already has 2 density members (excluding the item being moved) and the attempt is blocked client-side or by the worker
- **THEN** the console states in plain language that the day already has 2 publications (or equivalent) and directs the operator to choose another local day with capacity (or equivalent usable next step)

#### Scenario: Invalid future time refusal is understandable

- **WHEN** `POST /defer-linkedin-variant` fails with `linkedin_supervision_defer_time_invalid` (or equivalent client pre-check)
- **THEN** the console states that the new time must be strictly in the future and does not claim the schedule changed

#### Scenario: Cadence or other defer product-rule refusal is plain language

- **WHEN** defer fails with an interim cadence/saturation or related schedule product-rule code
- **THEN** the primary outcome explains the block in plain language with a usable next step and MAY expose the raw code in diagnostics

### Requirement: US-084 preserves US-083 honesty and BL-015 closure

US-084 MUST preserve US-083 operator-language status, queued ≠ LinkedIn API published, EventModal action availability honesty (except where this change correctly makes postpone available for queued), and preview-vs-real semantics for existing non-postpone mutations.

US-084 MUST NOT mark US-084 or BL-032 Story accepted / closed by implementation alone, MUST NOT reopen BL-015, MUST NOT implement US-085 or US-086 mutations, and MUST keep committed console assets free of secrets and secret-like placeholders.

#### Scenario: US-083 status labels remain after postpone redesign

- **WHEN** the console renders Scheduled, Waiting to send, Live on LinkedIn, Failed, and Cancelled LinkedIn items after US-084 ships
- **THEN** primary operator-language labels and queued ≠ live semantics remain and blog Published on blog stays distinct from Live on LinkedIn

#### Scenario: Later BL-032 mutations stay out of US-084

- **WHEN** US-084 postpone/reschedule is implemented
- **THEN** the console does not offer a working publish-now LinkedIn API path and does not implement cancel-for-queued as a completed mutation

## MODIFIED Requirements

### Requirement: Operator-language LinkedIn publication status (US-083)

For LinkedIn-channel items on the Silverman Authority Manager / LinkedIn console (Week, Month, EventModal, and related status chips/filters that surface publication labels), the console MUST present **operator-language primary status** that distinguishes at least:

- **Scheduled** — not yet authorized to send (maps from `pending` / equivalent pre-send supervision window)
- **Waiting to send** — authorized to send but not yet on LinkedIn (maps from `queued`, and from in-flight `publishing` when shown)
- **Live on LinkedIn** — confirmed LinkedIn API publication evidence (maps from `published` and/or `linkedin_api_published === true`)
- **Failed** — publication failed (maps from `failed`)
- **Cancelled** — will not send unless restored via approved reopen (maps from `cancelled`)

Technical `publish_state` / `publication_state` MAY remain visible as secondary diagnostics. The console MUST NOT invent new campaign `publish_state` wire values solely for this labeling.

The console MUST make clear that **Waiting to send** / `queued` is **not** LinkedIn API published.

Blog-channel **Published on blog** (`publication_state: completed`) MUST remain visually and verbally distinct from **Live on LinkedIn**. The console MUST NOT label blog completed items as live on LinkedIn.

This requirement is the BL-032 / US-083 control-center **foundation** for honest status. Postpone/reschedule **control redesign** for not-Live variants including `pending` and `queued` is provided by US-084. This US-083 requirement itself MUST NOT implement publish-now (US-086) or cancel for queued (US-085). It MUST NOT reopen BL-015 as supervision-only product closure.

#### Scenario: Pending shows as Scheduled, not live

- **WHEN** the console renders a LinkedIn item whose display/publication state is `pending`
- **THEN** the primary operator label is equivalent to **Scheduled** (not “live on LinkedIn”) and the presentation does not claim LinkedIn API published

#### Scenario: Queued shows as Waiting to send, not live

- **WHEN** the console renders a LinkedIn item whose display/publication state is `queued`
- **THEN** the primary operator label is equivalent to **Waiting to send** and the presentation makes clear the item is not yet on LinkedIn / not LinkedIn API published

#### Scenario: Published evidence shows Live on LinkedIn

- **WHEN** the console renders a LinkedIn item with `publication_state` `published` or `linkedin_api_published` true
- **THEN** the primary operator label is equivalent to **Live on LinkedIn**

#### Scenario: Failed and cancelled use operator language

- **WHEN** the console renders LinkedIn items with display states `failed` and `cancelled`
- **THEN** primary labels are equivalent to **Failed** and **Cancelled** respectively and neither is labeled live on LinkedIn

#### Scenario: Blog published-on-site stays distinct from LinkedIn live

- **WHEN** the console renders a blog item labeled Published on blog beside a LinkedIn item labeled Live on LinkedIn
- **THEN** the two labels remain distinct and the blog item MUST NOT claim LinkedIn API published / live on LinkedIn

#### Scenario: US-083 foundation does not ship publish-now or cancel-queued

- **WHEN** the US-083 honest-status foundation is considered alone
- **THEN** it does not require a working publish-now LinkedIn API path or cancel-for-queued as a completed mutation; postpone/reschedule control redesign for pending and queued is owned by US-084 rather than forbidden by US-083

### Requirement: LinkedIn EventModal action availability matrix (US-083)

When an operator opens a LinkedIn calendar/event item in EventModal (or the equivalent item-detail control surface), the console MUST show which **control actions are available now** versus **unavailable**, with **plain-language reasons** when blocked or not yet shipped.

For actions the console supports, availability MUST reflect real eligibility (for example pending-supervision join + `actions` for edit/cancel-pending; `schedule_editable` / block reason for postpone/reschedule of pending and queued; `reopen_eligible` for reopen) and session mutation capability (`canMutate`).

Postpone/reschedule availability MUST align with US-084: **available** as a deliberate control when schedule-editable for Scheduled (`pending`) or Waiting to send (`queued`) and `canMutate`; unavailable with plain-language reason for Live on LinkedIn, cancelled (use reopen), failed, in-flight publishing, or session/density blocks as applicable.

For BL-032 controls not implemented yet, the matrix MUST still communicate honesty when an operator would reasonably expect them:

- **Cancel while waiting to send (`queued`)** — unavailable / not available yet (US-085), with plain language that queued is not live and cancel-from-console for that state is not shipped yet
- **Publish now** — unavailable / not available yet (US-086), and MUST NOT imply a LinkedIn API send occurred

Unavailable expected controls MUST NOT be silently omitted when the matrix is shown; hiding only truly irrelevant controls (for example reopen on a non-cancelled item) remains allowed.

Failures and blocked states (auth cannot mutate, schedule blocked, density/cadence block reasons already returned by the worker, integration failure context) MUST be communicated in plain language without claiming LinkedIn API published.

#### Scenario: Pending item lists available supervision controls

- **WHEN** an operator opens a LinkedIn item in the pending / Scheduled state with pending-supervision detail and mutation permission
- **THEN** the action matrix shows edit and cancel (pending) as available when worker `actions` allow them, and shows postpone/reschedule as available when schedule-editable

#### Scenario: Queued item offers postpone but not cancel-queued

- **WHEN** an operator opens a LinkedIn item in Waiting to send / `queued` state with mutation permission and schedule-editable true
- **THEN** the matrix shows postpone/reschedule as available, does not present cancel-queued as an available completed control (US-085 not shipped), and does not claim the item is live on LinkedIn

#### Scenario: Publish now shown as unavailable until US-086

- **WHEN** an operator opens an eligible-looking LinkedIn item that is not yet live
- **THEN** publish now appears as unavailable / not available yet (US-086) and no LinkedIn API publish is invoked from the console

#### Scenario: Blocked mutation explains why

- **WHEN** an action is blocked because the session cannot mutate, schedule is not editable, or reopen is ineligible
- **THEN** the console states the plain-language reason and does not present the blocked action as successfully completed

#### Scenario: Postpone row matches US-084 eligibility for pending and queued

- **WHEN** an operator opens a schedule-editable Scheduled or Waiting-to-send LinkedIn item with mutation permission
- **THEN** the action matrix shows postpone/reschedule as available with a reason that points to the deliberate control and explicit preview vs real behavior

### Requirement: Operator can defer or reschedule pending variants from the supervision console

The supervision console MUST allow a content operator to defer or reschedule a not-yet-live LinkedIn variant (`pending` or `queued`, when schedule-editable) by submitting a future `new_scheduled_at_utc` relative to distribution strategy / extended US-017 defer rules.

The console MUST persist deferrals by calling the existing authenticated worker endpoint `POST /defer-linkedin-variant`. The console MUST NOT invent editorial-calendar write-back as LinkedIn schedule SoT as part of defer success.

After a successful **real** defer, Week/Month calendar placement MUST agree with the authoritative refreshed `scheduled_at_utc` (see US-084 calendar agreement requirement). Secondary calendar-join context MUST NOT remain the operator’s believed current slot when it disagrees with that authoritative schedule.

Dry-run default and pending-state language rules for edit also apply to defer. US-084 deliberate postpone framing and preview-vs-real honesty apply to this path for both pending and queued.

#### Scenario: Defer control calls defer-linkedin-variant for pending

- **WHEN** an authenticated operator submits a defer with a future UTC schedule for a pending variant from the supervision console
- **THEN** the console sends `POST /defer-linkedin-variant` with campaign id, variant id, and `new_scheduled_at_utc`

#### Scenario: Defer control calls defer-linkedin-variant for queued

- **WHEN** an authenticated operator submits a defer with a future UTC schedule for a queued variant from the supervision console
- **THEN** the console sends `POST /defer-linkedin-variant` with campaign id, variant id, and `new_scheduled_at_utc`

#### Scenario: Defer does not claim editorial calendar auto-write as SoT

- **WHEN** a real defer succeeds
- **THEN** the console does not claim that the editorial calendar was automatically updated as LinkedIn SoT, and Week/Month truth follows refreshed authoritative schedule-visibility data

### Requirement: Calendar schedule actions reuse existing worker semantics

Calendar and agenda schedule-modification actions MUST reuse the same business rules and worker mutation semantics used by LinkedIn defer/reschedule for schedule-editable not-yet-live LinkedIn variants (`pending` and `queued`), and MUST use the authenticated editorial-calendar schedule-update API for blog calendar items.

The console MUST NOT introduce a second LinkedIn schedule mutation source of truth and MUST NOT write `editorial-calendar/calendar.json` (or any mount path) from the browser.

Existing edit, defer/reschedule, and cancel affordances for pending LinkedIn variants MUST remain available where already supported. Queued postpone/reschedule MUST use the same defer endpoint.

#### Scenario: LinkedIn schedule edit from calendar calls defer endpoint

- **WHEN** an authenticated operator commits a schedule change for a pending or queued LinkedIn variant from Month or Week
- **THEN** the console sends `POST /defer-linkedin-variant` (via the typed API client) and does not write campaign files from the browser

#### Scenario: Blog schedule edit calls editorial calendar API

- **WHEN** an authenticated operator commits a schedule change for an editable blog calendar item
- **THEN** the console sends the authenticated worker calendar schedule-update endpoint and does not write `calendar.json` from the browser

#### Scenario: Pending edit and cancel remain available

- **WHEN** an operator uses EventModal for a pending LinkedIn variant after US-084
- **THEN** existing edit and cancel-pending affordances remain available alongside postpone/reschedule
