## ADDED Requirements

### Requirement: Deliberate cancel for not-yet-live LinkedIn variants from the console (US-085)

The Silverman Authority Manager / LinkedIn console MUST provide a **deliberate cancel control** for LinkedIn-channel items that are **not Live on LinkedIn**, including at least:

- **Scheduled / `pending`** (and pending-like supervision-window states already eligible for cancel-pending)
- **Waiting to send / `queued`**

when session `canMutate` is true and campaign/variant identity is resolvable.

The control MUST:

- persist only through authenticated `POST /cancel-linkedin-publication` (typed API client — no second cancel pipeline, no browser filesystem writes)
- require **explicit confirmation** before a real (`dry_run` false) cancel
- make **preview/dry-run** versus **real/committed** unmistakable before submit and after outcome (reuse US-083 honesty; dry-run remains default)
- present as an intentional control action with clear framing that cancel **withdraws** the variant (will not send) and is **not** postpone/reschedule and **not** LinkedIn API unpublish of a live post

**Waiting to send / `queued`** MUST be a **working** cancel control (not “unavailable / not available yet”). Queued cancel MUST NOT require pending-supervision join when schedule-visibility (or equivalent) already provides `campaign_id` and `variant` identity.

**Live on LinkedIn** MUST NOT be cancellable via this control. **Cancelled** continues via the approved reopen path (US-040J), not re-cancel. In-flight **publishing** MUST be unavailable with plain-language reason and usable next step. Failed recovery cancel is not a primary US-085 acceptance target; existing worker recovery cancel MAY remain if already reachable without inventing a second pipeline.

This requirement MUST NOT implement publish-now / LinkedIn API publish (US-086), ADR-0001 bypass, or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` bypass for publication. It MUST NOT reopen BL-015 as supervision-only product closure. It MUST NOT regress US-084 postpone/reschedule for pending and queued.

#### Scenario: Operator cancels a Scheduled LinkedIn variant

- **WHEN** an authenticated mutating operator opens an eligible LinkedIn item in Scheduled / `pending` state and submits real cancel (`dry_run` false) with explicit confirmation
- **THEN** the console sends `POST /cancel-linkedin-publication` with campaign id and variant id and does not write editorial mounts from the browser

#### Scenario: Operator cancels a Waiting-to-send LinkedIn variant

- **WHEN** an authenticated mutating operator opens a LinkedIn item in Waiting to send / `queued` state with campaign and variant identity (even without pending-supervision join) and submits real cancel with explicit confirmation
- **THEN** the console sends `POST /cancel-linkedin-publication` with that identity, does not claim LinkedIn API published or unpublished, and does not invent a second mutation endpoint

#### Scenario: Real cancel requires explicit confirmation

- **WHEN** an operator attempts a real (`dry_run` false) cancel
- **THEN** the console requires an explicit confirmation step before the request is sent

#### Scenario: Preview cancel cannot be mistaken for completed cancel

- **WHEN** the operator runs cancel with preview/dry-run default or explicitly selected
- **THEN** the outcome states that no lasting cancel was made and the console does not claim the variant is Cancelled for real or live on LinkedIn

#### Scenario: Live on LinkedIn cannot be cancelled from this control

- **WHEN** an operator opens a LinkedIn item that is Live on LinkedIn
- **THEN** cancel is unavailable with a plain-language reason and no cancel mutation is invoked from the console as a successful withdraw

#### Scenario: Cancel is distinct from postpone

- **WHEN** an operator opens an eligible Scheduled or Waiting-to-send LinkedIn item
- **THEN** cancel is offered as withdraw/will-not-send and postpone/reschedule remains the separate US-084 time-change control

#### Scenario: No second cancel pipeline

- **WHEN** US-085 cancel is exercised for pending or queued
- **THEN** persistence uses only existing `POST /cancel-linkedin-publication` and does not add a LinkedIn API publish/unpublish route or n8n Execute Command path

### Requirement: After real cancel status is Cancelled and publish actions are withdrawn (US-085)

After a **successful real** LinkedIn cancel (`POST /cancel-linkedin-publication` with `dry_run` false) for a not-yet-live variant, the console MUST show operator-language status equivalent to **Cancelled**.

The console MUST refresh worker reads into the shared model after real success so the variant is no longer presented as Scheduled or Waiting to send for that identity.

Publish actions for that variant MUST NOT be offered as available controls (including publish-now remaining unavailable per US-086, and cancel-pending/cancel-queued no longer offered as active withdraw controls for that now-cancelled item).

**Reopen & reschedule** MUST remain the approved restore path where product already allows it (`reopen_eligible` / US-040J).

Preview/dry-run success MUST NOT flip operator status to Cancelled for real.

#### Scenario: Real cancel shows Cancelled

- **WHEN** a real cancel succeeds for a pending or queued LinkedIn variant and the console refreshes schedule-visibility (and pending-supervision as applicable)
- **THEN** the primary operator status for that variant is equivalent to **Cancelled** and the item is not labeled live on LinkedIn

#### Scenario: Publish actions no longer offered after real cancel

- **WHEN** a real cancel succeeds and the operator re-opens that variant
- **THEN** the action matrix does not offer publish-now as available and does not offer cancel-pending/cancel-queued as available withdraw controls for the cancelled state

#### Scenario: Reopen remains the restore path when eligible

- **WHEN** a real cancel succeeds for a reopen-eligible cancellation and the operator opens the item with mutation permission
- **THEN** reopen & reschedule is available per existing US-040J rules and is presented as the restore path

#### Scenario: Preview does not claim Cancelled

- **WHEN** a preview/dry-run cancel succeeds
- **THEN** the console does not present the variant as Cancelled for real

### Requirement: Cancel failures and blocks are plain language with a next step (US-085)

When cancel is refused or fails (session cannot mutate, Live / in-flight / ineligible state, `linkedin_publish_cancel_not_allowed`, action-not-allowed, idempotency conflict, HTTP 401/422, or equivalent), the console MUST explain the outcome in **plain language** with a **usable next step**.

Primary UI MUST NOT rely only on raw machine codes. Expandable diagnostics MAY still show stable worker codes.

The console MUST NOT claim LinkedIn API published, unpublished, or Cancelled for real on a failed or preview cancel.

#### Scenario: Cancel-not-allowed is understandable

- **WHEN** `POST /cancel-linkedin-publication` fails with `linkedin_publish_cancel_not_allowed`
- **THEN** the console states in plain language that cancel is not allowed for this state (for example already live) with a usable next step and does not claim the variant was cancelled

#### Scenario: Session cannot mutate blocks cancel clearly

- **WHEN** cancel is unavailable or blocked because the session cannot mutate
- **THEN** the console states that mutation permission is required and does not present cancel as completed

#### Scenario: Auth or validation failure does not silently succeed

- **WHEN** cancel returns unauthorized or validation failure
- **THEN** the console shows a clear failure state and does not present the variant as Cancelled

### Requirement: US-085 preserves US-083/US-084 honesty and BL-015 closure

US-085 MUST preserve US-083 operator-language status, queued ≠ LinkedIn API published, EventModal action availability honesty (except where this change correctly makes cancel-queued available), and preview-vs-real semantics.

US-085 MUST preserve US-084 deliberate postpone/reschedule for pending and queued and MUST NOT conflate postpone with cancel.

US-085 MUST NOT mark US-085 or BL-032 Story accepted / closed by implementation alone, MUST NOT reopen BL-015, MUST NOT implement US-086 mutations, and MUST keep committed console assets free of secrets and secret-like placeholders.

#### Scenario: US-083 status labels remain after cancel control ships

- **WHEN** the console renders Scheduled, Waiting to send, Live on LinkedIn, Failed, and Cancelled LinkedIn items after US-085 ships
- **THEN** primary operator-language labels and queued ≠ live semantics remain and blog Published on blog stays distinct from Live on LinkedIn

#### Scenario: US-084 postpone remains available beside cancel

- **WHEN** an authenticated mutating operator opens a schedule-editable Scheduled or Waiting-to-send LinkedIn item after US-085 ships
- **THEN** postpone/reschedule remains available as a separate deliberate control and cancel remains the withdraw path

#### Scenario: Publish-now stays out of US-085

- **WHEN** US-085 cancel is implemented
- **THEN** the console does not offer a working publish-now LinkedIn API path

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

This requirement is the BL-032 / US-083 control-center **foundation** for honest status. Postpone/reschedule **control redesign** for not-Live variants including `pending` and `queued` is provided by US-084. Cancel for not-Live variants including `queued` is provided by US-085. This US-083 requirement itself MUST NOT implement publish-now (US-086). It MUST NOT reopen BL-015 as supervision-only product closure.

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

#### Scenario: US-083 foundation does not ship publish-now

- **WHEN** the US-083 honest-status foundation is considered alone
- **THEN** it does not require a working publish-now LinkedIn API path; postpone/reschedule control redesign for pending and queued is owned by US-084; cancel for pending and queued is owned by US-085 rather than forbidden by US-083

### Requirement: LinkedIn EventModal action availability matrix (US-083)

When an operator opens a LinkedIn calendar/event item in EventModal (or the equivalent item-detail control surface), the console MUST show which **control actions are available now** versus **unavailable**, with **plain-language reasons** when blocked or not yet shipped.

For actions the console supports, availability MUST reflect real eligibility (for example pending-supervision join + `actions` for edit/cancel-pending; schedule-visibility campaign/variant identity for cancel-queued; `schedule_editable` / block reason for postpone/reschedule of pending and queued; `reopen_eligible` for reopen) and session mutation capability (`canMutate`).

Postpone/reschedule availability MUST align with US-084: **available** as a deliberate control when schedule-editable for Scheduled (`pending`) or Waiting to send (`queued`) and `canMutate`; unavailable with plain-language reason for Live on LinkedIn, cancelled (use reopen), failed, in-flight publishing, or session/density blocks as applicable.

Cancel availability MUST align with US-085:

- **Cancel while scheduled (`pending`)** — **available** when eligible + `canMutate`
- **Cancel while waiting to send (`queued`)** — **available** when campaign/variant identity is present + `canMutate` (working control; not “not available yet”)
- Unavailable with plain-language reason for Live on LinkedIn, in-flight publishing, cancelled (use reopen), or session blocks as applicable

For BL-032 controls not implemented yet, the matrix MUST still communicate honesty when an operator would reasonably expect them:

- **Publish now** — unavailable / not available yet (US-086), and MUST NOT imply a LinkedIn API send occurred

Unavailable expected controls MUST NOT be silently omitted when the matrix is shown; hiding only truly irrelevant controls (for example reopen on a non-cancelled item) remains allowed.

Failures and blocked states (auth cannot mutate, schedule blocked, density/cadence block reasons already returned by the worker, integration failure context) MUST be communicated in plain language without claiming LinkedIn API published.

#### Scenario: Pending item lists available supervision controls

- **WHEN** an operator opens a LinkedIn item in the pending / Scheduled state with pending-supervision detail and mutation permission
- **THEN** the action matrix shows edit and cancel (pending) as available when worker `actions` allow them, and shows postpone/reschedule as available when schedule-editable

#### Scenario: Queued item offers postpone and cancel-queued

- **WHEN** an operator opens a LinkedIn item in Waiting to send / `queued` state with mutation permission, schedule-editable true, and campaign/variant identity
- **THEN** the matrix shows postpone/reschedule as available, shows cancel-queued as available, and does not claim the item is live on LinkedIn

#### Scenario: Publish now shown as unavailable until US-086

- **WHEN** an operator opens an eligible-looking LinkedIn item that is not yet live
- **THEN** publish now appears as unavailable / not available yet (US-086) and no LinkedIn API publish is invoked from the console

#### Scenario: Blocked mutation explains why

- **WHEN** an action is blocked because the session cannot mutate, schedule is not editable, or reopen is ineligible
- **THEN** the console states the plain-language reason and does not present the blocked action as successfully completed

#### Scenario: Postpone row matches US-084 eligibility for pending and queued

- **WHEN** an operator opens a schedule-editable Scheduled or Waiting-to-send LinkedIn item with mutation permission
- **THEN** the action matrix shows postpone/reschedule as available with a reason that points to the deliberate control and explicit preview vs real behavior

#### Scenario: Cancel-queued row matches US-085 eligibility

- **WHEN** an operator opens a Waiting-to-send LinkedIn item with campaign/variant identity and mutation permission
- **THEN** the action matrix shows cancel (while waiting to send) as available with a reason that points to withdraw via the existing cancel endpoint and explicit confirmation / preview vs real behavior

### Requirement: Preview versus real change is unmistakable for existing LinkedIn controls (US-083)

For existing LinkedIn console mutations (edit draft, defer/reschedule via ScheduleEditor, cancel-from-pending, cancel-from-queued, reopen), the console MUST make **preview/dry-run** versus **real/committed** change unmistakable **before** the operator submits and **after** the outcome is shown.

Dry-run MUST remain the default unless the operator explicitly selects a real write. Preview outcomes MUST NOT use wording that implies the schedule was saved, the variant was cancelled for real, or content went live on LinkedIn.

Real outcomes MUST state that the change was committed/saved (as applicable) and MUST still NOT claim LinkedIn API published unless the mutation’s worker result actually establishes live publication evidence (US-083/US-084/US-085 mutations do not publish to LinkedIn).

#### Scenario: Dry-run default is explicit before submit

- **WHEN** an operator opens edit, cancel-pending, cancel-queued, reopen, or schedule defer without changing the dry-run/preview control from its default
- **THEN** the UI indicates the attempt is preview/dry-run (no lasting change) before submit

#### Scenario: Preview outcome cannot be mistaken for real

- **WHEN** a dry-run mutation returns success
- **THEN** the console outcome/toast states that no lasting change was made (preview) and does not claim schedule saved, cancel completed for real, or live on LinkedIn

#### Scenario: Real outcome states committed without false LinkedIn live claim

- **WHEN** a real (`dry_run` false) edit, defer, cancel-pending, cancel-queued, or reopen succeeds
- **THEN** the console outcome states the change was committed/saved as applicable and does not claim LinkedIn API published / live on LinkedIn solely because the mutation succeeded

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

Waiting to send / `queued` MUST be a **working** postpone/reschedule control (not “unavailable / not available yet”). Cancel-while-queued is provided by US-085 as a **separate** withdraw control and MUST NOT be implied by postpone.

This requirement MUST NOT implement publish-now / LinkedIn API publish (US-086), ADR-0001 bypass, or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` bypass. It MUST NOT reopen BL-015 as supervision-only product closure. Cancel for not-Live pending and queued is owned by US-085 and MUST remain distinct from postpone.

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

### Requirement: US-084 preserves US-083 honesty and BL-015 closure

US-084 MUST preserve US-083 operator-language status, queued ≠ LinkedIn API published, EventModal action availability honesty (except where postpone is correctly available for queued), and preview-vs-real semantics for existing non-postpone mutations.

US-084 MUST NOT mark US-084 or BL-032 Story accepted / closed by implementation alone, MUST NOT reopen BL-015, MUST NOT implement US-086 mutations, and MUST keep committed console assets free of secrets and secret-like placeholders.

Cancel for not-Live pending and queued is owned by US-085 (separate from US-084 postpone). US-084 MUST NOT be interpreted to forbid US-085 cancel-queued.

#### Scenario: US-083 status labels remain after postpone redesign

- **WHEN** the console renders Scheduled, Waiting to send, Live on LinkedIn, Failed, and Cancelled LinkedIn items after US-084 ships
- **THEN** primary operator-language labels and queued ≠ live semantics remain and blog Published on blog stays distinct from Live on LinkedIn

#### Scenario: Publish-now stays out of US-084

- **WHEN** US-084 postpone/reschedule is implemented
- **THEN** the console does not offer a working publish-now LinkedIn API path as part of US-084

### Requirement: Operator can cancel pending variants from the supervision console

The supervision console at `GET /flow-a/console/linkedin-variant-supervision` MUST allow a content operator to cancel a Flow A LinkedIn variant while that variant appears in the optional supervision window (`publish_state` is `pending`), per the LinkedIn variant review policy and US-017 cancel mechanics.

US-085 extends cancel as a deliberate control-center action for not-yet-live variants including Waiting to send / `queued` (see Requirement: Deliberate cancel for not-yet-live LinkedIn variants from the console (US-085)). This pending-window requirement remains the Story 3 / pending-supervision cancel path and MUST continue to work; it MUST NOT be interpreted to forbid cancel-queued via schedule-visibility identity.

The console MUST persist cancellations by calling the existing authenticated worker endpoint `POST /cancel-linkedin-publication` with `campaign_id` and `variant` (plus optional `reason` / `idempotency_key`). The console MUST NOT introduce a parallel mutation endpoint or treat raw mount paths as the persistence source of truth.

The console MUST default cancel attempts to dry-run (`dry_run` true, matching US-017) unless the operator explicitly selects a real write. Successful real cancel MUST move the variant out of the pending supervision window (`publish_state` `cancelled` per worker contract), MUST set operator-visible eligibility context such that strategy-driven auto-queue will not select it, and MUST NOT claim LinkedIn API published.

Defer controls delivered by Story 2 / US-084 remain available; cancel MUST NOT re-implement defer through a second endpoint.

#### Scenario: Cancel control calls cancel-linkedin-publication

- **WHEN** an authenticated operator submits a cancel for a pending variant from the supervision console
- **THEN** the console sends `POST /cancel-linkedin-publication` with the selected campaign id and variant id and does not write campaign files from the browser filesystem

#### Scenario: Cancel dry-run default is explicit

- **WHEN** an operator opens the cancel action without changing the dry-run control from its default
- **THEN** the request uses `dry_run` true and a successful response is presented as validation without mutation

#### Scenario: Real cancel removes variant from pending supervision window

- **WHEN** a real (`dry_run` false) cancel succeeds for a pending variant and the console refreshes pending-supervision data
- **THEN** the cancelled variant is no longer listed as `pending` and the console does not label the outcome as LinkedIn API published

#### Scenario: Pending cancel remains available beside US-085 queued cancel

- **WHEN** US-085 cancel-queued ships
- **THEN** cancel for pending supervision-window variants continues to call the same `POST /cancel-linkedin-publication` endpoint without a second pipeline
