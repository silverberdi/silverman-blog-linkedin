## ADDED Requirements

### Requirement: Deliberate publish now for eligible LinkedIn variants from the console (US-086)

The Silverman Authority Manager / LinkedIn console MUST provide a **deliberate publish now control** for LinkedIn-channel items that are **not Live on LinkedIn** and are eligible under product rules, including at least:

- **Waiting to send / `queued`** (primary happy path)
- **Scheduled / `pending`** when not excluded by supervision rules that `publish_now` must not bypass (including a deferred future `scheduled_at_utc`)

when session `canMutate` is true and campaign/variant identity is resolvable.

The control MUST:

- persist / send only through authenticated `POST /publish-linkedin-due-variants` (typed API client — no second publish pipeline, no browser filesystem writes, no n8n Execute Command)
- send a **targeted** request with `campaign_id`, `variant`, and `publish_now: true`
- for Waiting to send / `queued`, use `auto_queue_pending: false` (default)
- for Scheduled / `pending`, use `auto_queue_pending: true` so one deliberate action queues then publishes under existing worker semantics
- require **explicit confirmation** before a real (`dry_run` false) publish
- make **preview/dry-run** versus **real/committed** unmistakable before submit and after outcome (reuse US-083 honesty; dry-run remains default)
- present as an intentional control that **sends to the LinkedIn API on this action** (not a status re-label, not postpone/reschedule, not cancel/withdraw)

**Waiting to send / `queued`** and eligible **Scheduled / `pending`** MUST be **working** publish-now controls (not “unavailable / not available yet”). Publish-now MUST NOT require pending-supervision join when schedule-visibility (or equivalent) already provides `campaign_id` and `variant` identity.

**Live on LinkedIn** MUST NOT be a publish-now target. **Cancelled** continues via reopen (US-040J) before any future publish path. In-flight **publishing** MUST be unavailable with plain-language reason. Failed / critical publish-now recovery is not a primary US-086 acceptance target.

This requirement MUST respect `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` fail-closed for real publish, existing duplicate-publication / once-only safeguards, and publish-time sequence/cadence guards (`publish_now` bypasses timing gates only). It MUST NOT reopen BL-015 as supervision-only product closure. It MUST NOT regress US-084 postpone/reschedule or US-085 cancel. Publish now MUST be available without requiring SSH or deploy-script operation for the routine happy path.

#### Scenario: Operator publishes a Waiting-to-send LinkedIn variant now

- **WHEN** an authenticated mutating operator opens an eligible LinkedIn item in Waiting to send / `queued` state with campaign and variant identity and submits real publish now (`dry_run` false, `publish_now` true) with explicit confirmation
- **THEN** the console sends `POST /publish-linkedin-due-variants` with that identity and `publish_now` true, does not write editorial mounts from the browser, and does not invent a second mutation endpoint

#### Scenario: Operator publishes a Scheduled LinkedIn variant now

- **WHEN** an authenticated mutating operator opens an eligible LinkedIn item in Scheduled / `pending` state (not deferred-future-excluded) and submits real publish now with explicit confirmation
- **THEN** the console sends `POST /publish-linkedin-due-variants` with `auto_queue_pending` true and `publish_now` true for that identity

#### Scenario: Real publish now requires explicit confirmation

- **WHEN** an operator attempts a real (`dry_run` false) publish now
- **THEN** the console requires an explicit confirmation step before the request is sent

#### Scenario: Preview publish now cannot be mistaken for Live on LinkedIn

- **WHEN** the operator runs publish now with preview/dry-run default or explicitly selected
- **THEN** the outcome states that no LinkedIn API send was committed and the console does not claim the variant is Live on LinkedIn

#### Scenario: Live on LinkedIn cannot be publish-now target

- **WHEN** an operator opens a LinkedIn item that is Live on LinkedIn
- **THEN** publish now is unavailable with a plain-language reason and no publish-due mutation is invoked from the console as a successful new send

#### Scenario: Publish now is distinct from postpone and cancel

- **WHEN** an operator opens an eligible Scheduled or Waiting-to-send LinkedIn item
- **THEN** publish now is offered as send-to-LinkedIn-API-now, postpone/reschedule remains the US-084 time-change control, and cancel remains the US-085 withdraw control

#### Scenario: No second publish pipeline and no SSH for routine happy path

- **WHEN** US-086 publish now is exercised for an eligible variant
- **THEN** persistence uses only existing `POST /publish-linkedin-due-variants` over worker HTTP and does not require SSH or deploy-script operation for that routine happy path

### Requirement: After real publish now status is Live on LinkedIn with traceable identity (US-086)

After a **successful real** LinkedIn publish now (`POST /publish-linkedin-due-variants` with `dry_run` false and `publish_now` true) for the targeted eligible variant, the console MUST show operator-language status equivalent to **Live on LinkedIn**.

The console MUST refresh worker reads into the shared model after real success so the variant is no longer presented as Scheduled or Waiting to send for that identity.

The console MUST show a **traceable publication identity** suitable for operator verification (for example `linkedin_post_urn` from the publish-due response). Preview/dry-run success MUST NOT flip operator status to Live on LinkedIn for real and MUST NOT present a preview URN as committed live evidence.

After real Live success, publish-now MUST NOT remain offered as an available control for that Live item. Postpone and cancel remain unavailable for Live per US-084/US-085.

#### Scenario: Real publish now shows Live on LinkedIn with URN

- **WHEN** a real publish now succeeds for an eligible LinkedIn variant and the console refreshes schedule-visibility (and pending-supervision as applicable)
- **THEN** the primary operator status for that variant is equivalent to **Live on LinkedIn** and a traceable publication identity (e.g. URN) is shown for verification

#### Scenario: Preview does not claim Live

- **WHEN** a preview/dry-run publish now succeeds
- **THEN** the console does not claim Live on LinkedIn and does not treat the outcome as committed LinkedIn API publication

#### Scenario: Publish now withdrawn after Live

- **WHEN** a real publish now succeeds and the operator re-opens that Live variant
- **THEN** the action matrix does not offer publish now as available for that Live item

### Requirement: Publish now blocks and failures are plain-language (US-086)

When publish now is refused or fails (including publication not enabled, cadence, sequence, evidence invalid, configuration/credentials, content/platform failure, ineligible state, or session cannot mutate), the console MUST explain the refusal or failure in **plain language** with a **usable next step** and MUST NOT claim the variant is published / Live on LinkedIn.

Real publish MUST fail closed when LinkedIn publication enablement is off.

#### Scenario: Publication enablement off fails closed

- **WHEN** `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is off and the operator attempts real publish now
- **THEN** the console shows a plain-language not-enabled reason and does not claim Live on LinkedIn

#### Scenario: Cadence or sequence block is understandable

- **WHEN** publish-due reports a cadence or sequence block for the targeted variant
- **THEN** the console shows a plain-language reason with a usable next step and does not claim published

#### Scenario: Platform or content failure is understandable

- **WHEN** real publish now fails with a content or platform/API error
- **THEN** the console shows a plain-language failure reason and does not claim Live on LinkedIn

### Requirement: US-086 preserves US-083/US-084/US-085 honesty and BL-015 closure

US-086 MUST preserve US-083 operator-language status, queued ≠ LinkedIn API published, EventModal action availability honesty (except where this change correctly makes publish-now available), and preview-vs-real semantics.

US-086 MUST preserve US-084 deliberate postpone/reschedule and US-085 deliberate cancel for pending and queued and MUST NOT conflate publish-now with postpone or cancel.

US-086 MUST NOT mark US-086 or BL-032 Story accepted / closed by implementation alone, MUST NOT reopen BL-015, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or ADR-0001, and MUST keep committed console assets free of secrets and secret-like placeholders.

#### Scenario: US-083 status labels remain after publish-now ships

- **WHEN** the console renders Scheduled, Waiting to send, Live on LinkedIn, Failed, and Cancelled LinkedIn items after US-086 ships
- **THEN** primary operator-language labels and queued ≠ live semantics remain and blog Published on blog stays distinct from Live on LinkedIn

#### Scenario: Postpone and cancel remain available beside publish now

- **WHEN** an authenticated mutating operator opens an eligible Scheduled or Waiting-to-send LinkedIn item after US-086 ships
- **THEN** postpone/reschedule and cancel remain available as separate deliberate controls and publish now remains the send-to-API path

#### Scenario: Enablement and ADR-0001 hold

- **WHEN** US-086 publish now is implemented
- **THEN** real publish still fails closed when publication enablement is off and mutations still use worker HTTP only (no n8n Execute Command)

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

This requirement is the BL-032 / US-083 control-center **foundation** for honest status. Postpone/reschedule **control redesign** for not-Live variants including `pending` and `queued` is provided by US-084. Cancel for not-Live variants including `queued` is provided by US-085. Publish now for eligible not-Live variants is provided by US-086. This US-083 requirement itself MUST NOT reopen BL-015 as supervision-only product closure.

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

#### Scenario: US-083 foundation does not forbid later control-center mutations

- **WHEN** the US-083 honest-status foundation is considered alone
- **THEN** postpone/reschedule is owned by US-084, cancel for pending and queued is owned by US-085, and publish now is owned by US-086 rather than forbidden by US-083

### Requirement: LinkedIn EventModal action availability matrix (US-083)

When an operator opens a LinkedIn calendar/event item in EventModal (or the equivalent item-detail control surface), the console MUST show which **control actions are available now** versus **unavailable**, with **plain-language reasons** when blocked or not yet eligible.

For actions the console supports, availability MUST reflect real eligibility (for example pending-supervision join + `actions` for edit/cancel-pending; schedule-visibility campaign/variant identity for cancel-queued and publish-now; `schedule_editable` / block reason for postpone/reschedule of pending and queued; `reopen_eligible` for reopen; LinkedIn publication enablement and worker publish guards for publish-now) and session mutation capability (`canMutate`).

Postpone/reschedule availability MUST align with US-084: **available** as a deliberate control when schedule-editable for Scheduled (`pending`) or Waiting to send (`queued`) and `canMutate`; unavailable with plain-language reason for Live on LinkedIn, cancelled (use reopen), failed, in-flight publishing, or session/density blocks as applicable.

Cancel availability MUST align with US-085:

- **Cancel while scheduled (`pending`)** — **available** when eligible + `canMutate`
- **Cancel while waiting to send (`queued`)** — **available** when campaign/variant identity is present + `canMutate` (working control; not “not available yet”)
- Unavailable with plain-language reason for Live on LinkedIn, in-flight publishing, cancelled (use reopen), or session blocks as applicable

Publish now availability MUST align with US-086:

- **Publish now** — **available** when the item is eligible Waiting to send / `queued` or eligible Scheduled / `pending` (not deferred-future-excluded, not Live, not cancelled, not in-flight publishing), campaign/variant identity is present, and `canMutate`
- Unavailable with plain-language reason for Live on LinkedIn, cancelled (use reopen), in-flight publishing, deferred-future exclusion, failed/critical non-targets, missing identity, or session cannot mutate
- MUST NOT imply a LinkedIn API send occurred merely because the matrix row is shown

Unavailable expected controls MUST NOT be silently omitted when the matrix is shown; hiding only truly irrelevant controls (for example reopen on a non-cancelled item, or publish-now on Live) remains allowed.

Failures and blocked states (auth cannot mutate, schedule blocked, density/cadence block reasons already returned by the worker, publication not enabled, integration failure context) MUST be communicated in plain language without claiming LinkedIn API published.

#### Scenario: Pending item lists available supervision controls

- **WHEN** an operator opens a LinkedIn item in the pending / Scheduled state with pending-supervision detail and mutation permission
- **THEN** the action matrix shows edit and cancel (pending) as available when worker `actions` allow them, and shows postpone/reschedule as available when schedule-editable

#### Scenario: Queued item offers postpone and cancel-queued

- **WHEN** an operator opens a LinkedIn item in Waiting to send / `queued` state with mutation permission, schedule-editable true, and campaign/variant identity
- **THEN** the matrix shows postpone/reschedule as available, shows cancel-queued as available, and does not claim the item is live on LinkedIn

#### Scenario: Publish now available for eligible Waiting to send

- **WHEN** an operator opens an eligible LinkedIn item in Waiting to send / `queued` state with campaign/variant identity and mutation permission
- **THEN** publish now appears as available and points to send via existing publish-due with explicit confirmation / preview vs real behavior

#### Scenario: Publish now available for eligible Scheduled

- **WHEN** an operator opens an eligible LinkedIn item in Scheduled / `pending` state (not deferred-future-excluded) with campaign/variant identity and mutation permission
- **THEN** publish now appears as available with a reason that points to the deliberate auto-queue+publish_now path and explicit confirmation / preview vs real behavior

#### Scenario: Publish now unavailable for Live on LinkedIn

- **WHEN** an operator opens a LinkedIn item that is Live on LinkedIn
- **THEN** publish now is unavailable with a plain-language already-live reason and no LinkedIn API publish is invoked from the console as a new send

#### Scenario: Blocked mutation explains why

- **WHEN** an action is blocked because the session cannot mutate, schedule is not editable, reopen is ineligible, or publish now is refused
- **THEN** the console states the plain-language reason and does not present the blocked action as successfully completed

#### Scenario: Postpone row matches US-084 eligibility for pending and queued

- **WHEN** an operator opens a schedule-editable Scheduled or Waiting-to-send LinkedIn item with mutation permission
- **THEN** the action matrix shows postpone/reschedule as available with a reason that points to the deliberate control and explicit preview vs real behavior

#### Scenario: Cancel-queued row matches US-085 eligibility

- **WHEN** an operator opens a Waiting-to-send LinkedIn item with campaign/variant identity and mutation permission
- **THEN** the action matrix shows cancel (while waiting to send) as available with a reason that points to withdraw via the existing cancel endpoint and explicit confirmation / preview vs real behavior

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

Waiting to send / `queued` MUST be a **working** postpone/reschedule control (not “unavailable / not available yet”). Cancel-while-queued is provided by US-085 as a **separate** withdraw control and MUST NOT be implied by postpone. Publish now is provided by US-086 as a **separate** send control and MUST NOT be implied by postpone.

This requirement MUST NOT bypass ADR-0001 or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. It MUST NOT reopen BL-015 as supervision-only product closure. Cancel for not-Live pending and queued is owned by US-085 and MUST remain distinct from postpone. Publish now is owned by US-086 and MUST remain distinct from postpone.

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
- **THEN** persistence uses only existing `POST /defer-linkedin-variant` (plus existing reopen path when applicable) and does not add a LinkedIn API publish route or n8n Execute Command path as the postpone SoT

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

This requirement MUST NOT bypass ADR-0001 or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` for publication. It MUST NOT reopen BL-015 as supervision-only product closure. It MUST NOT regress US-084 postpone/reschedule for pending and queued. Publish now is owned by US-086 and MUST remain distinct from cancel.

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

#### Scenario: Cancel is distinct from postpone and publish now

- **WHEN** an operator opens an eligible Scheduled or Waiting-to-send LinkedIn item
- **THEN** cancel is offered as withdraw/will-not-send, postpone/reschedule remains the separate US-084 time-change control, and publish now remains the separate US-086 send control

#### Scenario: No second cancel pipeline

- **WHEN** US-085 cancel is exercised for pending or queued
- **THEN** persistence uses only existing `POST /cancel-linkedin-publication` and does not add a LinkedIn API publish/unpublish route or n8n Execute Command path

### Requirement: After real cancel status is Cancelled and publish actions are withdrawn (US-085)

After a **successful real** LinkedIn cancel (`POST /cancel-linkedin-publication` with `dry_run` false) for a not-yet-live variant, the console MUST show operator-language status equivalent to **Cancelled**.

The console MUST refresh worker reads into the shared model after real success so the variant is no longer presented as Scheduled or Waiting to send for that identity.

Publish actions for that variant MUST NOT be offered as available controls (including publish-now unavailable for cancelled — restore via reopen first — and cancel-pending/cancel-queued no longer offered as active withdraw controls for that now-cancelled item).

**Reopen & reschedule** MUST remain the approved restore path where product already allows it (`reopen_eligible` / US-040J).

Preview/dry-run success MUST NOT flip operator status to Cancelled for real.

#### Scenario: Real cancel shows Cancelled

- **WHEN** a real cancel succeeds for a pending or queued LinkedIn variant and the console refreshes schedule-visibility (and pending-supervision as applicable)
- **THEN** the primary operator status for that variant is equivalent to **Cancelled** and the item is not labeled live on LinkedIn

#### Scenario: Publish actions no longer offered after real cancel

- **WHEN** a real cancel succeeds and the operator re-opens that variant
- **THEN** the action matrix does not offer publish-now as available for the cancelled state and does not offer cancel-pending/cancel-queued as available withdraw controls for the cancelled state

#### Scenario: Reopen remains the restore path when eligible

- **WHEN** a real cancel succeeds for a reopen-eligible cancellation and the operator opens the item with mutation permission
- **THEN** reopen & reschedule is available per existing US-040J rules and is presented as the restore path

#### Scenario: Preview does not claim Cancelled

- **WHEN** a preview/dry-run cancel succeeds
- **THEN** the console does not present the variant as Cancelled for real
