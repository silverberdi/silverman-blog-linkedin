# linkedin-variant-supervision-console

## Purpose

Operator-facing console for Flow A LinkedIn variants (BL-015 / US-038–US-040 Stories 1–3 + US-040A–US-040F historical context; BL-032 / US-083 control-center foundation for honest status and action availability): authenticated `GET /flow-a/linkedin-variants/pending-supervision` for pending-supervision detail; authenticated `GET /flow-a/schedule-visibility` for blog + LinkedIn calendar placement; shared ScheduleEditor mutations (US-017 defer + editorial-calendar schedule-update); same-origin React + TypeScript + Vite console at `GET /flow-a/console/linkedin-variant-supervision` with calendar-first Week (default) and Month (secondary) operator views, EventModal + toasts (US-040H), operator-local primary clock and local-day Week/Month placement (US-040I), shared filters, dark responsive UX, typed injectable-auth API client with explicit session states and `canMutate` gating, shared normalized frontend model, and secrets-safe frontend source and built assets. US-040G supersedes list-as-first-class operator chrome for future UX while preserving US-040A–US-040F historical requirements except where explicitly superseded. Public URL hosting and live Google/OIDC activation remain deferred pending a separate security change; LinkedIn API publish-now from the console (US-086), cancel-queued (US-085), and postpone/reschedule redesign (US-084) remain out of scope for US-083. BL-015 is closed as pre-send supervision; successor control-center work continues under BL-032.

## Requirements

### Requirement: Operator-facing pending LinkedIn variant supervision view

The system SHALL provide an operator-facing console surface for Flow A LinkedIn variants that are in the optional supervision window (`publish_state` is `pending`) so a content operator can supervise scheduled publication without inspecting raw mount files.

The console MUST present each pending variant with at least:

- campaign id
- variant id
- audience
- `scheduled_at_utc`
- `publish_state`

The console MUST be understandable to a content operator without requiring inspection of worker source code or raw campaign JSON files.

The console MUST NOT claim that `pending`, `distribution_scheduled`, or `flow_a_complete` means LinkedIn API published.

#### Scenario: Pending variants listed with required fields

- **WHEN** one or more Flow A campaign variants have `publish_state` `pending` with audience and `scheduled_at_utc` present in campaign metadata
- **THEN** the supervision console presents each such variant with campaign id, variant id, audience, `scheduled_at_utc`, and `publish_state` equal to `pending`

#### Scenario: Empty supervision window is understandable

- **WHEN** no campaign variants have `publish_state` `pending`
- **THEN** the console communicates that there are no pending variants in the supervision window and does not present this as a system failure

#### Scenario: Pending is not claimed as LinkedIn API published

- **WHEN** the console displays a variant with `publish_state` `pending`
- **THEN** the presentation does not label that variant as LinkedIn API published and does not equate campaign `flow_a_complete` with LinkedIn API published

### Requirement: Editorial calendar alignment for pending variants

Where an editorial calendar item includes a `campaign_id` that matches a pending variant’s campaign, the console MUST align the pending-variant view with that calendar item by exposing calendar context available from the existing calendar contract (at least calendar item id and due time or title when present).

When the calendar is missing or invalid, the console MUST still present pending variants from campaign metadata and MUST communicate that calendar alignment is unavailable.

The console MUST NOT write or reconcile calendar files as part of this read-only view.

#### Scenario: Pending variant aligned to calendar item

- **WHEN** a pending variant’s `campaign_id` matches a calendar item’s `campaign_id` and the calendar loads successfully
- **THEN** the console presents that pending variant with calendar alignment context from the matched item

#### Scenario: Calendar unavailable does not hide pending variants

- **WHEN** pending variants exist in campaign metadata and `editorial-calendar/calendar.json` is missing or invalid
- **THEN** the console still lists the pending variants and clearly communicates that calendar alignment could not be applied

### Requirement: Worker HTTP is the source of truth for console data

The supervision console MUST obtain pending-variant, calendar-alignment, and blocked-state display data through authenticated worker HTTP. The browser or operator UI MUST NOT treat raw mount file paths as the source of truth.

The worker MUST expose the thin authenticated read-only aggregation endpoint `GET /flow-a/linkedin-variants/pending-supervision` that returns the required per-variant fields without mutating campaign metadata, calendar files, or LinkedIn publication state.

The worker MUST serve the operator console at `GET /flow-a/console/linkedin-variant-supervision` as static build artifacts produced by the approved frontend toolchain (React + TypeScript + Vite), or MUST serve a documented compatible replacement route that preserves understandable operator access. The console MAY be an SPA shell plus hashed static assets; it MUST NOT require a separate production frontend server.

The pending-supervision GET MUST NOT call LinkedIn, DeepSeek, ComfyUI, or Git, and MUST NOT invoke US-017 mutation routes (`POST /correct-linkedin-variant`, `POST /defer-linkedin-variant`, `POST /cancel-linkedin-publication`) on the server.

The console page MAY call authenticated US-017 mutation routes for edit, defer, and cancel (US-039 + US-040).

#### Scenario: Authenticated read returns pending rows

- **WHEN** an authenticated client requests `GET /flow-a/linkedin-variants/pending-supervision` while pending variants exist
- **THEN** the response includes the required per-variant fields and performs no campaign or calendar file mutation

#### Scenario: Unauthenticated read is rejected

- **WHEN** a client requests `GET /flow-a/linkedin-variants/pending-supervision` without a valid API key
- **THEN** the worker rejects the request with the existing unauthorized semantics and does not return variant payloads

#### Scenario: Read path does not mutate

- **WHEN** `GET /flow-a/linkedin-variants/pending-supervision` is called repeatedly against the same editorial base
- **THEN** campaign metadata and calendar files remain byte-identical aside from unrelated concurrent operators

#### Scenario: Console page is served at the fixed path

- **WHEN** an operator requests `GET /flow-a/console/linkedin-variant-supervision`
- **THEN** the worker returns the built static console (SPA shell and associated assets) that consumes the pending-supervision read API and MAY offer edit, defer, and cancel actions that call existing US-017 POSTs

### Requirement: Static console HTML MUST NOT embed secrets or secret-like placeholders

Frontend source for the supervision console and the built static assets served for `GET /flow-a/console/linkedin-variant-supervision` (including `index.html` and bundled JavaScript/CSS) MUST NOT contain API keys, bearer tokens, OAuth tokens, or placeholders that look like real secrets (including but not limited to `CHANGE_ME`, `sk-` prefixed samples, `Bearer ` token samples, or hardcoded `X-API-Key` values).

Operators MUST supply credentials at runtime through the typed API-client auth boundary (browser prompt or local-only in-memory configuration). Credentials MUST NOT be persisted in browser storage as part of US-040A. Documentation examples MUST use clearly non-secret wording (for example “your API key”) without embedding fake credential strings that resemble production secrets.

#### Scenario: Static HTML secrets audit passes

- **WHEN** the committed or built console assets served for the supervision console route are scanned for API keys, bearer tokens, and secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present in those assets

#### Scenario: Frontend source secrets audit passes

- **WHEN** the React + TypeScript frontend source for the supervision console is scanned for API keys, bearer tokens, and secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present in the source

### Requirement: Console uses an approved modern frontend stack

The Flow A LinkedIn variant supervision console MUST be implemented with the approved modern frontend stack **React + TypeScript + Vite** (or an equivalent stack only if a superseding approved OpenSpec change explicitly replaces this decision).

The stack change MUST be treated as console-layer modernization only. It MUST NOT rewrite worker business logic, n8n workflows, Python utilities beyond static-asset serving, file contracts, publication guards, or existing US-017 HTTP mutation semantics as part of US-040A.

#### Scenario: Stack identity is React TypeScript Vite

- **WHEN** an implementer inspects the supervision console frontend package for US-040A
- **THEN** the package is a React + TypeScript application built with Vite (or documents an approved equivalent replacement change)

#### Scenario: Worker mutation contracts remain unchanged by stack migration

- **WHEN** the modernized console performs edit, defer, or cancel
- **THEN** those actions call the existing authenticated US-017 endpoints without introducing a parallel mutation source of truth

### Requirement: Console is delivered as static build artifacts from the worker

The modernized console MUST produce static build artifacts (`index.html` and associated assets) that the existing worker serves in production.

Production deployment MUST NOT require a separate frontend application server process for the supervision console.

The worker MUST continue to expose the operator console at `GET /flow-a/console/linkedin-variant-supervision`, or MUST provide a documented compatible replacement route that preserves understandable operator access during migration.

#### Scenario: Console route serves built SPA shell

- **WHEN** an operator requests `GET /flow-a/console/linkedin-variant-supervision` (or the documented compatible replacement)
- **THEN** the worker returns the Vite-built console shell HTML that loads same-origin static assets and consumes worker HTTP APIs

#### Scenario: No separate frontend server required

- **WHEN** the worker is deployed with the US-040A console assets included
- **THEN** the console is reachable through the worker HTTP process alone without a second production frontend server


### Requirement: Console UI is componentized with operational screen scaffolding

The modernized console MUST structure the UI as componentized operational screens and MUST include implemented boundaries for at least:

- week view (US-040G: default first-class)
- month calendar view (density secondary first-class)
- item detail (reachable from calendar event entry points; interim until US-040H modal)
- schedule editor (shared mutation surface from Week, Month, and mobile day/agenda equivalents)
- status summary (at-a-glance operational counts)
- filters
- confirmation flows
- shared API and error handling

List view MUST NOT remain a first-class operator chrome boundary after US-040G.

Full public URL hosting and live Google/OIDC activation remain out of scope (separate security change required).

#### Scenario: Required component boundaries exist in the frontend package

- **WHEN** the frontend package is inspected after US-040G
- **THEN** distinct component (or module) boundaries exist for week, month calendar, item detail, schedule editor, status summary, filters, confirmation flows, and shared API/error handling, and List is not a first-class operator chrome boundary

#### Scenario: Schedule editor remains shared

- **WHEN** an operator opens schedule modification from Week, Month, or mobile day/agenda for an editable item
- **THEN** the shared schedule editor supports dry-run, confirmation, and worker-backed commit

#### Scenario: Public URL activation remains deferred

- **WHEN** US-040G calendar-first UX is present in the console
- **THEN** the console does not activate public URL hosting or live Google/OIDC authentication


### Requirement: Browser API access uses a typed client with injectable auth

All browser calls to worker supervision APIs MUST go through a typed API client (or equivalent centralized boundary).

The client MUST centralize request construction, response typing, and error mapping for at least:

- `GET /flow-a/linkedin-variants/pending-supervision`
- `GET /flow-a/schedule-visibility`
- `POST /correct-linkedin-variant`
- `POST /defer-linkedin-variant`
- `POST /cancel-linkedin-publication`
- `POST /editorial-calendar/update-item-schedule`

Auth credentials MUST be injectable at the API-client boundary (for example via an `AuthProvider` headers/credentials provider) so a later Google/OIDC bearer token or secure session cookie can replace the current worker API-key header mechanism without changing list, month calendar, or schedule-editor business components.

The auth/client boundary MUST expose operator session and capability signals sufficient for UI gating, including at least whether a credential is held and whether mutations are allowed (`canMutate`), without requiring calendar components to parse raw HTTP status codes for auth policy.

Frontend source, rendered HTML, logs, and browser storage MUST NOT embed API keys, bearer tokens, OAuth tokens, operational secrets, mount paths, LAN-only host assumptions, or secret-like placeholders.

Until a separate approved security change activates public URL hosting and Google/OIDC authentication, local operations MAY continue to use the existing worker API-key auth mechanism through the same injectable provider.

#### Scenario: Business components do not call fetch directly for worker APIs

- **WHEN** list, calendar, or schedule-editor components load pending supervision or schedule-visibility data or submit edit/defer/cancel/calendar schedule-update
- **THEN** those components use the typed API client rather than ad-hoc `fetch`/`XMLHttpRequest` calls scattered across view code

#### Scenario: Auth provider can be swapped without editing calendar components

- **WHEN** the auth provider implementation is replaced at the API-client boundary with a Google/OIDC bearer or secure session-cookie strategy
- **THEN** list, month calendar, and schedule-editor business components do not require changes to continue calling the same client methods

#### Scenario: Secrets and local-only assumptions are absent from frontend artifacts

- **WHEN** frontend source and built console assets are scanned for API keys, bearer tokens, secret-like placeholders such as `CHANGE_ME`, hardcoded mount paths, or embedded operational secrets
- **THEN** no such values are present

#### Scenario: Local API-key auth still flows through the injectable boundary

- **WHEN** an operator authenticates for local operations using the worker API-key mechanism
- **THEN** credentials are supplied only through the injectable auth provider at runtime and are not hardcoded in source, rendered HTML, or browser storage


### Requirement: List and calendar share one normalized frontend model

Week view and Month calendar view MUST be backed by the same worker read models or by one shared normalized frontend model derived from those read models so the views cannot disagree about item identity, state, schedule, or available actions.

The shared model MUST incorporate pending-supervision rows for pending operational detail and schedule-visibility rows for Week/Month placement (blog and LinkedIn), normalizing overlapping LinkedIn pending rows to one identity.

#### Scenario: Shared model identity is stable across views

- **WHEN** a pending LinkedIn variant exists in the normalized frontend model
- **THEN** Week and Month views that render that item use the same campaign id, variant id, schedule, and action availability derived from that model

#### Scenario: Refresh updates the shared model

- **WHEN** pending-supervision and schedule-visibility data are refreshed after a successful real mutation
- **THEN** the shared model updates and both Week and Month presentations reflect the new state without a separate divergent calendar cache


### Requirement: Frontend validation covers build and key UX contracts

US-040A build and list validation requirements remain in force. After US-040B, frontend validation MUST also cover month calendar visibility UX, filter consistency across views, dual-view shared-model identity, and desktop plus mobile viewports for both List and Month calendar (including mobile agenda-style day expansion or equivalent).

US-040B MUST include frontend validation appropriate to the React + TypeScript + Vite stack covering at least:

- production build success
- key component behavior for the list-oriented supervision experience
- month calendar visibility behavior and filters
- API error mapping for auth/validation and known supervision failure codes
- desktop viewport usability of the list and calendar console
- mobile viewport usability of the list and calendar console

#### Scenario: Production build succeeds

- **WHEN** the frontend production build command is run for the supervision console
- **THEN** the build completes successfully and emits static artifacts consumable by the worker

#### Scenario: API error mapping is tested

- **WHEN** the typed client receives unauthorized or known US-017 supervision failure responses
- **THEN** automated tests assert those responses map to clear operator-facing error states without silent success

#### Scenario: Desktop and mobile viewports are covered

- **WHEN** frontend validation for US-040B runs
- **THEN** evidence covers both a desktop-width and a mobile-width presentation of the list and month calendar visibility console


### Requirement: Persistent view switcher preserves operator context

The console MUST provide a clear, persistent view switcher suitable for desktop and mobile viewports with labels `Week` and `Month`.

Switching between Week and Month MUST NOT clear filters, selected campaign context, dry-run mode, or unsaved schedule-edit drafts without an explicit warning and operator confirmation.

#### Scenario: Filters survive view switch

- **WHEN** an operator applies filters and then switches from Week to Month (or the reverse)
- **THEN** the same filter selection remains active in the destination view

#### Scenario: Unsaved schedule draft warns before discard on switch

- **WHEN** an unsaved schedule-edit draft exists and the operator attempts to switch views in a way that would discard that draft
- **THEN** the console warns and requires confirmation before discarding the draft

### Requirement: Month calendar visibility UX

The Month calendar view MUST present a full month grid for the current month with previous/next month navigation, a today marker, selected-day state, and clear empty-day states.

The calendar MUST use a dark visual theme with readable contrast, stable spacing, clear hierarchy, and touch targets suitable for mobile operation.

On phone viewports, the calendar MUST provide an agenda-style day expansion (or equivalent) for the selected day instead of forcing horizontal table scrolling as the only way to inspect that day’s items.

#### Scenario: Navigate months and see today

- **WHEN** an operator opens Month calendar
- **THEN** the current month is shown with a today marker and the operator can navigate to previous and next months

#### Scenario: Empty day is understandable

- **WHEN** a day in the visible month has no schedule items after filters
- **THEN** the day presents a clear empty state and is not shown as a system failure

#### Scenario: Mobile uses agenda expansion

- **WHEN** the console is viewed at a mobile width and the operator selects a day with items
- **THEN** those items are inspectable via an agenda-style expansion (or equivalent) without requiring horizontal scrolling of the month table

### Requirement: Schedule items appear on the correct calendar day

The Month calendar MUST show each included Flow A blog post and LinkedIn variant on the correct **operator-local** calendar day according to the local calendar date of the stored UTC timestamp (`scheduled_at_utc` for LinkedIn; mapped `due_at_utc` for blog) in the browser’s timezone.

Week day columns MUST use the same local-day bucketing rule so Week and Month cannot disagree about which local day an item occupies.

UTC day-of-month derived solely from the `Z` timestamp MUST NOT be the primary placement rule after US-040I.

Each calendar item presentation MUST include at least:

- title or campaign label
- campaign id where available
- variant id where available
- audience where available
- channel (`blog` or `linkedin`)
- publication state (operator-facing display state)
- scheduled time (operator-local interpretation with timezone cue on Week chips and in EventModal; Month chips MAY omit clock time when density requires it, with full local datetime available in the EventModal)

#### Scenario: LinkedIn pending variant lands on local calendar day

- **WHEN** a LinkedIn variant has `scheduled_at_utc` whose operator-local calendar date falls on a day in the visible local month
- **THEN** the Month calendar places that item on that local day with channel `linkedin` and the required identity/state/time fields

#### Scenario: Blog calendar item lands on local due day

- **WHEN** an editorial calendar blog item has `due_at_utc` whose operator-local calendar date falls on a day in the visible local month and is included by the schedule-visibility read
- **THEN** the Month calendar places that item on that local day with channel `blog` and the required identity/state/time fields

#### Scenario: Near-midnight item is not placed on the wrong local day

- **WHEN** a stored UTC instant falls on a different UTC calendar date than the operator’s local calendar date
- **THEN** Week and Month place the item on the operator-local calendar date, not the UTC calendar date

### Requirement: Publication states are distinguished without false LinkedIn published claims

The console MUST distinguish operator-facing display states covering at least: planned, pending, queued, published, completed, deferred, cancelled, blocked, and failed.

For **LinkedIn-channel** items, primary operator-facing labels MUST follow US-083 operator language for the publication lifecycle states that map to scheduled / waiting to send / live on LinkedIn / failed / cancelled (see Requirement: Operator-language LinkedIn publication status (US-083)). Technical wire values MAY remain secondary.

The console MUST NOT imply that `pending` or `queued` content has already been published to the LinkedIn API.

The console MUST NOT equate campaign `flow_a_complete`, blog handoff, editorial calendar `completed` / Published on blog, or Waiting to send / `queued` with LinkedIn API published / Live on LinkedIn.

#### Scenario: Pending is not labeled LinkedIn API published

- **WHEN** a LinkedIn item has display state `pending`
- **THEN** the presentation does not label it as LinkedIn API published or Live on LinkedIn

#### Scenario: Queued is not labeled LinkedIn API published

- **WHEN** a LinkedIn item has display state `queued`
- **THEN** the presentation does not label it as LinkedIn API published or Live on LinkedIn and communicates waiting-to-send / not yet on LinkedIn

#### Scenario: Blog completed is not labeled Live on LinkedIn

- **WHEN** a blog item has display state `completed` (Published on blog)
- **THEN** the presentation does not label it as Live on LinkedIn or LinkedIn API published

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

US-084 MUST NOT mark US-084 or BL-032 Story accepted / closed by implementation alone, MUST NOT reopen BL-015, MUST NOT implement US-086 mutations, and MUST keep committed console assets free of secrets and secret-like placeholders.

Cancel for not-Live pending and queued is owned by US-085 (separate from US-084 postpone). US-084 MUST NOT be interpreted to forbid US-085 cancel-queued.

#### Scenario: US-083 status labels remain after postpone redesign

- **WHEN** the console renders Scheduled, Waiting to send, Live on LinkedIn, Failed, and Cancelled LinkedIn items after US-084 ships
- **THEN** primary operator-language labels and queued ≠ live semantics remain and blog Published on blog stays distinct from Live on LinkedIn

#### Scenario: Publish-now stays out of US-084

- **WHEN** US-084 postpone/reschedule is implemented
- **THEN** the console does not offer a working publish-now LinkedIn API path as part of US-084

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

### Requirement: Schedule-visibility cadence-conflict projection fields (US-087)

Authenticated `GET /flow-a/schedule-visibility` LinkedIn-channel items that are **not Live on LinkedIn** and carry a usable `scheduled_at_utc` MUST include additive cadence-conflict projection fields so the console can warn without browser filesystem SoT and without inventing a second cadence engine.

For each such LinkedIn item the worker MUST evaluate whether, at that item’s `scheduled_at_utc`, a real publish-due / auto-queue path would refuse or skip **for cadence** under the US-051 / US-020 meaning (same gate as live `linkedin_publish_blocked_cadence` / related cadence skip): same-campaign successful `published` evidence separated by a minimum real interval of **72 hours**, using the same interval constant as the publish-time guard.

Additive fields MUST include at least:

- `cadence_conflict` (boolean) — `true` only for the cadence refuse/skip condition at `scheduled_at_utc`
- `cadence_conflict_code` (`string` or null) — `linkedin_publish_blocked_cadence` when `cadence_conflict` is true; otherwise null
- `cadence_earliest_feasible_at_utc` (`string` or null) — earliest UTC instant at which same-campaign cadence would clear (`max(published_at) + 72h` among valid same-campaign `published` evidence) when computable; otherwise null

`cadence_conflict` MUST be **false** (and the warning fields MUST NOT claim conflict) when the slot is cadence-feasible, when the item is Live on LinkedIn, when the item is Cancelled, when the item is Failed (Failed remains a distinct status story), when the channel is blog, or when the condition is density-full alone, OAuth missing, publication enablement off, sequence block alone, or evidence-invalid alone.

The schedule-visibility read MUST remain **read-only** (no campaign metadata mutation, no LinkedIn API call, no change to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`). The browser MUST obtain these fields through authenticated worker HTTP (typed client); MUST NOT read raw mounts.

#### Scenario: Cadence-infeasible Scheduled LinkedIn item is projected

- **WHEN** an authenticated client requests schedule-visibility for a range containing a not-yet-Live LinkedIn variant whose `scheduled_at_utc` would hit the US-020 cadence refuse/skip gate against same-campaign `published_at` evidence
- **THEN** that item’s `cadence_conflict` is true and `cadence_conflict_code` is `linkedin_publish_blocked_cadence`

#### Scenario: Cadence-feasible LinkedIn item is not projected as conflicted

- **WHEN** an authenticated client requests schedule-visibility for a not-yet-Live LinkedIn variant whose `scheduled_at_utc` satisfies same-campaign 72h cadence
- **THEN** that item’s `cadence_conflict` is false and `cadence_conflict_code` is null

#### Scenario: Live on LinkedIn is not cadence-conflict warned

- **WHEN** schedule-visibility returns a LinkedIn variant that is Live on LinkedIn
- **THEN** `cadence_conflict` is false for that item

#### Scenario: Density-full alone is not cadence conflict

- **WHEN** a LinkedIn item’s local day is at US-040K density capacity but the slot is cadence-feasible under US-020
- **THEN** `cadence_conflict` is false for that item

#### Scenario: Earliest feasible time is exposed when computable

- **WHEN** `cadence_conflict` is true and same-campaign published evidence yields a clear `published_at + 72h` instant
- **THEN** `cadence_earliest_feasible_at_utc` is that instant (UTC)

#### Scenario: Schedule-visibility cadence projection does not mutate or publish

- **WHEN** schedule-visibility evaluates cadence-conflict fields
- **THEN** no campaign metadata write, no LinkedIn API call, and no enablement bypass occurs

### Requirement: Week and Month cadence-conflict visual warning (US-087)

Silverman Authority Manager Week and Month views MUST show a **red or equivalent warning indicator** on LinkedIn-channel calendar items whose schedule-visibility (or shared model) `cadence_conflict` is true.

The indicator MUST:

- remain visible alongside the US-083 primary operator status (Scheduled / Waiting to send remain Scheduled / Waiting to send)
- MUST NOT imply Live on LinkedIn
- MUST NOT imply density-full alone
- MUST remain visually distinct from Failed, Cancelled, and Waiting to send primary status presentation
- MUST NOT appear on items with `cadence_conflict` false

Outcome MUST be readable on desktop and mobile calendar chips (or equivalent dense-month affordances).

#### Scenario: Week shows warning on cadence-conflicted Scheduled item

- **WHEN** Week view renders a LinkedIn item with `cadence_conflict` true and primary status Scheduled
- **THEN** a red or equivalent cadence-conflict warning indicator is visible on that chip and the primary status is not replaced by Live / Failed / Cancelled

#### Scenario: Month shows warning on cadence-conflicted item

- **WHEN** Month view renders a LinkedIn item with `cadence_conflict` true
- **THEN** a red or equivalent cadence-conflict warning indicator is visible for that item

#### Scenario: Feasible item has no cadence-conflict warning

- **WHEN** Week or Month renders a LinkedIn item with `cadence_conflict` false
- **THEN** the cadence-conflict warning indicator is not shown for that item

#### Scenario: Warning is distinct from Failed and density cues

- **WHEN** the console shows a Failed LinkedIn chip or a US-040K density-full day cue in the same view as a cadence-conflicted Scheduled item
- **THEN** the cadence-conflict indicator remains distinguishable from Failed status styling and from the density-full day cue

### Requirement: EventModal cadence-conflict explanation and next step (US-087)

When an operator opens a LinkedIn calendar/event item in EventModal (or equivalent detail) and `cadence_conflict` is true, the console MUST explain the conflict in **plain language** and provide a **usable next step**.

Plain language MUST convey that the current slot would be blocked for **same-campaign LinkedIn cadence** (72h since last successful publication in the campaign) — not that the item is Live on LinkedIn, not density-full alone, and not Failed/Cancelled as the conflict class.

Usable next step MUST include at least one actionable path such as:

- showing the **earliest feasible** time (operator-local interpretation of `cadence_earliest_feasible_at_utc` with timezone cue) and pointing to existing **Postpone / reschedule** (US-084), and/or
- offering or pointing to **Replan cadence conflicts** (US-089) via the authenticated worker path / console control when available — without claiming LinkedIn API published and without implying replan is still an unshipped future-only promise when the control/endpoint is present

Blocked/conflict states MUST be clearly communicated. Cadence-feasible opens MUST NOT show the cadence-conflict explanation as if conflicted.

#### Scenario: EventModal explains cadence conflict with next step

- **WHEN** an operator opens a LinkedIn item with `cadence_conflict` true in EventModal
- **THEN** the modal shows plain-language cadence-conflict copy and a usable next step (earliest feasible and/or postpone and/or replan)

#### Scenario: EventModal does not claim Live or density-full for cadence conflict

- **WHEN** EventModal shows a cadence-conflict explanation
- **THEN** the copy does not claim Live on LinkedIn and does not describe the condition as density-full alone

#### Scenario: Feasible item has no false cadence-conflict explanation

- **WHEN** an operator opens a LinkedIn item with `cadence_conflict` false
- **THEN** the EventModal does not present the cadence-conflict warning explanation as active for that item

#### Scenario: EventModal does not claim US-089 unshipped when replan exists

- **WHEN** US-089 replan HTTP (and optional console control) is available
- **THEN** EventModal next-step copy MUST NOT state that operators must only “wait for a later replan” as if US-089 were still unimplemented

### Requirement: Console replan of cadence conflicts via worker HTTP (US-089)

When Silverman Authority Manager exposes a deliberate **Replan cadence conflicts** control (EventModal when `cadence_conflict` is true, and/or a bulk ops entry), it MUST call authenticated `POST /replan-linkedin-cadence-conflicts` through the typed injectable-auth client. Browser filesystem SoT and n8n Execute Command MUST NOT be used (ADR-0001). The console control is optional relative to HTTP: documented one-shot ops/curl against the same worker endpoint remains a valid operator path when the control is deferred; the HTTP contract remains the mutation SoT.

When the control is present:

- Preview / dry-run MUST be available and MUST default to non-mutating behavior consistent with US-083 (preview ≠ Live on LinkedIn; preview ≠ LinkedIn API published).
- Real replan MUST require explicit confirmation before `dry_run` false.
- After a **successful real** replan, the console MUST refresh schedule-visibility (and pending-supervision as applicable) so Week/Month placement and authoritative `scheduled_at_utc` agree on the new times.
- US-087 cadence-conflict indicators MUST clear for items whose new slot is cadence-feasible; the warning chrome itself MUST NOT be redesigned beyond clear-after-success and next-step honesty.

#### Scenario: Console replan uses worker HTTP only

- **WHEN** an operator runs Replan cadence conflicts from the console (preview or real)
- **THEN** the console calls `POST /replan-linkedin-cadence-conflicts` with injectable auth
- **AND** the browser does not write editorial mounts as schedule SoT

#### Scenario: Preview does not move calendar chips

- **WHEN** an operator runs replan preview / dry-run from the console
- **THEN** Week/Month placement for affected items does not change solely due to the preview
- **AND** the UI does not claim Live on LinkedIn

#### Scenario: After real replan calendar and warnings agree

- **WHEN** a real replan succeeds and the console refreshes schedule-visibility
- **THEN** affected items appear at their new local slots
- **AND** items that are cadence-feasible at the new slot do not show the US-087 cadence-conflict warning

### Requirement: US-089 preserves US-087 honesty and non-goals

US-089 MUST preserve US-083 preview-vs-real honesty, US-087 cadence-conflict meaning (projection fields unchanged except reflecting new `scheduled_at_utc` after replan), and BL-032 control-center labels. It MUST NOT mark US-089 / US-087 / US-088 / BL-021 Story accepted by implementation alone, MUST NOT change publish-time US-020 cadence math, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT expand into BL-022 metrics, and MUST NOT redesign US-087 warning chrome beyond clear-after-success / next-step honesty.

#### Scenario: Non-goals hold

- **WHEN** US-089 console or HTTP replan is implemented
- **THEN** LinkedIn publication enablement is not bypassed
- **AND** US-087 warning meaning is not redefined to density/sequence/OAuth/enablement
- **AND** Story accepted / BL-021 closure are not claimed by code alone

### Requirement: US-087 Visual DoD and non-duplication

US-087 Story accepted MUST be supported by **desktop + mobile** visual evidence (screenshots or equivalent browser-driven capture) for at least: Week conflicted chip; Month conflicted item; EventModal conflict explanation + next step; feasible item without warning; distinctness from Failed and density-full cues; mobile-readable EventModal conflict copy — unless the operator explicitly waives the formal screenshot pack as with prior console stories. Vitest alone is insufficient for Story accepted.

This change MUST NOT duplicate or weaken completed work: BL-032 control-center labels remain; no second publish pipeline; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` untouched; US-020 publish-time cadence guard remains authoritative at send. This change MUST NOT implement US-088 schedule-time shift-forward or US-089 replan.

#### Scenario: Visual DoD scenes are required for Story accepted

- **WHEN** operators evaluate US-087 for Story accepted
- **THEN** desktop and mobile evidence for the listed conflict-warning scenes is available unless explicitly waived by the operator

#### Scenario: Non-goals hold — no shift-forward or enablement bypass

- **WHEN** US-087 implementation is complete
- **THEN** schedule-time shift-forward (US-088) and replan (US-089) are not shipped by this change, and LinkedIn publication enablement is not bypassed

### Requirement: Same item recognizable across Week and Month

Week and Month MUST render from the same shared normalized frontend model (fed by worker HTTP reads) so the same logical item is recognizable across views via stable ids, labels, status colors, and detail fields.

The console MUST NOT maintain divergent per-view caches that can disagree about item identity, schedule, or publication state.

#### Scenario: Shared identity across views

- **WHEN** a LinkedIn pending variant exists in the shared model
- **THEN** Week and Month presentations for that item use the same campaign id, variant id, schedule, and display publication state derived from that model

#### Scenario: Refresh updates both views from shared store

- **WHEN** schedule or pending data is refreshed after a successful real mutation
- **THEN** both views reflect the updated shared model without a separate divergent calendar-only cache

### Requirement: Filters apply consistently with discoverable critical failures

The console MUST provide filters or toggles for channel, campaign, publication state, blocked items, and due-soon items.

After US-040L, those filter controls MUST be hosted in the header Filters modal rather than an always-visible FOCUS/Filters dock, without reducing filter capability.

Filters MUST apply consistently to both Week and Month views via shared filter state whether the modal is open or closed.

When filters hide critical failure indicators (failed/blocked/integration-critical items), the console MUST keep those hidden critical failures discoverable through a count, warning, or reset / show-critical affordance (at minimum inside the Filters modal when open, with the header active-filter cue indicating that the calendar is filtered while the modal is closed). Critical failures MUST NOT be hidden silently with no signal.

#### Scenario: Filter applies to both views

- **WHEN** an operator filters to channel `linkedin` and switches between Week and Month
- **THEN** both views show only items that satisfy the linkedin channel filter within schedule-visibility (and pending detail) scope

#### Scenario: Hidden critical failures remain discoverable

- **WHEN** active filters exclude one or more critical failure items
- **THEN** the console surfaces a count, warning, or affordance that makes those hidden critical failures discoverable

#### Scenario: Filters are reached from the header modal

- **WHEN** an operator needs the full filter set after US-040L
- **THEN** the operator opens the header Filters control and finds Channel, Campaign/label, Blocked only, Due soon, publication states, and Reset in the modal

### Requirement: Filters live in a header modal (US-040L)

The Flow A LinkedIn variant supervision console MUST NOT render an always-visible FOCUS/Filters dock as permanent primary chrome between the metric summary and the Week/Month calendar surfaces.

The console MUST provide a clear header control labeled **Filters** that opens a focused filters modal.

The filters modal MUST contain the existing filter controls without reducing capability:

- Channel
- Campaign / label
- Blocked only
- Due soon (48h)
- Publication state checkboxes (including `completed` / Published on blog when that publication state is present in the console model)
- Reset

Filters MUST continue to apply consistently to both Week and Month via the shared filter state. Closing the modal MUST NOT clear filters.

#### Scenario: Permanent filters dock is absent

- **WHEN** the console shell is rendered after US-040L
- **THEN** Week/Month are not permanently preceded by a full FOCUS/Filters strip in the primary chrome

#### Scenario: Header Filters opens the modal

- **WHEN** an operator activates the header Filters control
- **THEN** a modal opens containing Channel, Campaign/label, Blocked only, Due soon, publication state checkboxes, and Reset

#### Scenario: Closing the modal keeps filter state

- **WHEN** an operator sets a non-default filter in the modal and then dismisses the modal
- **THEN** Week and Month continue to reflect that filter selection

### Requirement: Active-filter cue on the header Filters control

When any non-default filter is active relative to the console default filter state (channel not `all`, non-empty campaign/label query, blocked-only, due-soon-only, or any selected publication states), the header Filters control MUST surface a calm active cue (badge, count, or equivalent).

The active cue MUST NOT use failed/blocked alarm styling as its only signal. When all filters match defaults, the cue MUST be absent or clearly inactive.

#### Scenario: Badge appears when filtered

- **WHEN** an operator enables blocked-only or selects one or more publication states
- **THEN** the header Filters control shows a calm active cue without requiring the modal to stay open

#### Scenario: Cue clears after reset

- **WHEN** filters return to defaults via Reset or Clear filters
- **THEN** the header active cue is absent or inactive

### Requirement: Metric chip focus remains outside the modal and is reflected inside it

Interactive metric chips MUST remain usable one-click focus shortcuts that write the same shared filter state without requiring the filters modal to apply focus.

When the operator opens the filters modal after a metric-chip focus, the modal MUST reflect the resulting filter controls (toggles, checkboxes, and query fields consistent with that focus).

#### Scenario: Chip focus does not require the modal

- **WHEN** an operator activates a blocked (or equivalent) metric chip
- **THEN** the blocked focus filter applies on Week/Month without opening the filters modal

#### Scenario: Modal reflects chip-applied filters

- **WHEN** an operator applies a metric-chip focus and then opens the Filters modal
- **THEN** the modal controls show the resulting filter state

### Requirement: US-040L Visual DoD and operator walkthrough gates

Automated tests (including Vitest) are necessary but MUST NOT be treated as sufficient for US-040L Story accepted.

US-040L MUST capture Visual DoD evidence (desktop ≈1280 and mobile ≈375, or equivalent) for at least:

- header Filters control visible
- modal opens with the full filter set
- active-filter badge when filtered
- Week/Month uncluttered without a permanent filters dock
- metric chip focus still works
- Reset / clear paths remain obvious

**Story accepted** / Acceptance criteria validated MUST NOT be marked until the content operator completes a live walkthrough on the deployed or explicitly agreed preview console and confirms the calendar feels cleaner and filters remain discoverable.

Vitest/checkbox completion alone MUST NOT imply Story accepted. BL-015 MUST remain open until the backlog completion outcome is operator-validated. US-038–US-040K Story accepted MUST NOT be unset as a side effect of US-040L implementation. US-040M completed-blog mapping MUST NOT be redefined by this requirement.

#### Scenario: Vitest alone does not accept the story

- **WHEN** US-040L implementation and Vitest suites pass without Visual DoD evidence and operator walkthrough
- **THEN** product status MUST NOT mark US-040L Story accepted or Acceptance criteria validated

#### Scenario: Walkthrough required before Story accepted

- **WHEN** Visual DoD evidence exists and the operator completes a walkthrough confirming filters-in-modal UX intent
- **THEN** Story accepted MAY be recorded; otherwise it remains open

### Requirement: US-040L console scope preserves G–K baselines

US-040L MUST preserve:

- Week default + Month secondary calendar-first chrome (no List restoration as primary)
- EventModal + toast feedback
- operator-local primary clock and `*_utc` wire fields (US-040I)
- cancelled reopen path (US-040J)
- local-day density cues and enforcement UX (US-040K)
- session states and `canMutate` gating
- dry-run default + confirm for real
- worker HTTP-only SoT (ADR-0001)
- Week/Month empty-state Clear filters paths
- discoverable hidden-critical failures when filters hide them (via Filters modal surface and/or active-filter cue)
- qualified publication language

US-040L MUST NOT activate public URL / Google OIDC / BFF / user-management, MUST NOT call LinkedIn API publish from the console, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, MUST NOT write editorial mounts from the browser, MUST NOT change US-040M completed-blog mapping semantics, and MUST NOT close BL-015 by implementation alone.

#### Scenario: Prior console baselines remain

- **WHEN** US-040L is implemented
- **THEN** Week remains default, EventModal remains the event surface, local-time helpers remain authoritative for display/placement, density cues remain, reopen remains available for eligible cancelled items, and empty-state Clear filters still clears shared filter state

#### Scenario: No LinkedIn API publish from filters UX

- **WHEN** the Filters modal or active-filter cue is exercised in the console
- **THEN** the console does not invoke LinkedIn publication and only uses worker HTTP read/mutation endpoints already in scope

### Requirement: Explicit timezone handling for schedules

The console MUST use **operator-local** date and time as the primary visible clock for routine Week, Month, and EventModal schedule displays, with a visible timezone cue (for example a short timezone name such as `CST`).

UTC MAY remain the storage and worker wire format (`*_utc` fields). Raw UTC ISO values and UTC day keys MAY appear only in expandable diagnostics or secondary technical detail — they MUST NOT be the primary routine clock.

Calendar day placement for Week and Month MUST follow the operator-local day-bucketing rule based on stored UTC timestamps interpreted in the browser timezone.

Routine empty, error, and help copy MUST NOT instruct the operator to “think in UTC” or enter UTC wall-clock digits for normal schedule work.

#### Scenario: Primary displays use local time with timezone cue

- **WHEN** an item with `scheduled_at_utc` is shown on a Week chip, in Month-driven EventModal detail, or in the EventModal schedule line
- **THEN** the primary presentation uses operator-local date and/or time with a visible timezone cue

#### Scenario: UTC is diagnostic-only for routine work

- **WHEN** an operator views an event without expanding diagnostics
- **THEN** the primary surface does not require reading or entering UTC as the routine clock

#### Scenario: Routine copy does not coach UTC thinking

- **WHEN** the operator reads ScheduleEditor help, empty-state guidance, or mapped `*_time_invalid` error copy
- **THEN** the copy does not instruct the operator to think in UTC for routine edits

### Requirement: Worker schedule-visibility read aggregation

The worker MUST expose an authenticated read-only schedule-visibility aggregation HTTP endpoint for the console (path fixed at implementation and documented; recommended `GET /flow-a/schedule-visibility`) that returns Flow A blog and LinkedIn schedule items for month visibility without mutating campaign metadata, calendar files, or LinkedIn publication state.

The endpoint MUST support constraining results to a month (or equivalent UTC range) suitable for month navigation.

The endpoint MUST NOT call LinkedIn, DeepSeek, ComfyUI, or Git, and MUST NOT invoke US-017 mutation routes on the server.

The browser MUST obtain schedule-visibility data through this worker HTTP capability (or the typed client wrapping it). The browser MUST NOT read raw mounted files or infer schedule state from filesystem paths.

`GET /flow-a/linkedin-variants/pending-supervision` MUST remain available as the pending-window read for list operational detail and MUST NOT be removed by this capability.

#### Scenario: Authenticated schedule-visibility read returns items

- **WHEN** an authenticated client requests the schedule-visibility endpoint for a month that contains blog and LinkedIn schedule facts
- **THEN** the response includes items with channel, identity fields, `scheduled_at_utc`, and publication display state, and performs no campaign or calendar file mutation

#### Scenario: Unauthenticated schedule-visibility read is rejected

- **WHEN** a client requests the schedule-visibility endpoint without a valid API key
- **THEN** the worker rejects the request with existing unauthorized semantics and does not return schedule payloads

#### Scenario: Browser does not read mount paths

- **WHEN** the Month calendar loads schedule data
- **THEN** it uses the typed API client against worker HTTP only and does not read editorial mount paths from the browser

### Requirement: Partial and blocked schedule reads are communicated

The schedule-visibility read and console MUST clearly communicate partial-data and blocked-state context when campaign, calendar, variant, or integration state cannot be read completely, including secret-safe issues and integration-failure context where applicable.

LinkedIn publication enablement off MUST remain display-only technical context: it MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, and MUST NOT be used as a reason to invent LinkedIn API published success.

#### Scenario: Calendar missing still allows LinkedIn schedule rows when available

- **WHEN** `editorial-calendar/calendar.json` is missing or invalid and LinkedIn campaign variants with schedules exist
- **THEN** the console or schedule-visibility response still returns available LinkedIn items and clearly reports calendar read failure

#### Scenario: Enablement off does not claim published

- **WHEN** LinkedIn publication enablement is false
- **THEN** schedule visibility still presents pending/queued items without labeling them LinkedIn API published

### Requirement: Frontend validation covers calendar visibility contracts

US-040B MUST include frontend validation covering at least:

- month calendar UX behavior (navigation, day placement, empty states)
- filter application consistency across List and Month calendar
- dual-view shared-model identity consistency
- desktop viewport and mobile viewport (including agenda-style day expansion or equivalent)

Production build success for the existing React + TypeScript + Vite console MUST continue to hold.

#### Scenario: Dual-view consistency is tested

- **WHEN** frontend validation for US-040B runs
- **THEN** automated tests assert the same logical item identity/state appears consistently for List and Month calendar from the shared model

#### Scenario: Desktop and mobile calendar viewports are covered

- **WHEN** frontend validation for US-040B runs
- **THEN** evidence covers desktop-width and mobile-width presentations including calendar agenda/day expansion behavior

### Requirement: US-040B scope preserves prior console work and defers later variants

US-040B MUST NOT mark BL-015 closed or US-040B Story accepted by implementation alone.

US-040B MUST NOT implement US-040C calendar schedule mutation / new calendar mutation SoT, US-040D public URL and Google auth activation, or US-040E polish beyond what visibility UX requires.

US-040B MUST NOT introduce a backend-for-frontend, database, user-management system, or public hosting change.

US-040B MUST NOT call the LinkedIn publication API, bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, use n8n Execute Command, or read raw mount paths from the browser.

US-040B MUST preserve the React + TypeScript + Vite static-asset delivery and Stories 1–3 list mutation behavior delivered by prior console work.

#### Scenario: Later variants remain out of scope

- **WHEN** US-040B implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records US-040C–US-040E as not implemented (except visibility surfaces delivered by US-040B)

#### Scenario: No calendar mutation SoT introduced

- **WHEN** an operator uses the Month calendar in the US-040B console
- **THEN** the console does not persist schedule changes through a new calendar mutation source of truth and does not write calendar files from the browser

### Requirement: US-040A scope preserves Stories 1–3 and defers later variants

US-040A MUST NOT mark BL-015 closed or US-040A Story accepted by implementation alone.

US-040A MUST NOT implement US-040C calendar schedule mutation / new calendar mutation SoT, US-040D public URL and Google auth activation, or US-040E polish beyond stack-migration needs. (US-040B list + month schedule visibility is delivered by the US-040B capability slice.)

US-040A MUST NOT introduce a backend-for-frontend, database, user-management system, or public hosting change.

US-040A MUST NOT call the LinkedIn publication API, bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, use n8n Execute Command, or read raw mount paths from the browser.

#### Scenario: Later variants remain out of scope

- **WHEN** US-040A implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records US-040B–US-040E as not implemented (except scaffolding/readiness boundaries delivered by US-040A)

#### Scenario: No BFF or public hosting introduced

- **WHEN** US-040A lands
- **THEN** the architecture still uses browser → worker HTTP for console data and mutations without a new BFF, database, or public hosting topology

### Requirement: Failures and blocked states are clearly communicated on the read path

The console and its read API MUST clearly communicate read/display failures and blocked-state context relevant to supervision, including at least:

- unreadable or invalid campaign metadata files (partial results allowed)
- missing or invalid editorial calendar (variants still listed when available)
- LinkedIn publication enablement off as display-only technical context (MUST NOT hide pending variants; MUST NOT bypass or change `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`)
- missing or unreadable draft artifacts for pending rows (`draft_content` null with issue)
- deferred / `auto_queue_eligible` context on pending rows when present
- integration-failure context for failed sibling variants discovered during the pending aggregation scan (secret-safe fields only)

The console MUST NOT invent new `publish_state` values and MUST NOT treat US-016 criteria failure as an automatic technical block.

Edit/defer/cancel mutation failure communication is specified under Story 2 and Story 3 mutation failure requirements and does not replace read-path issue reporting.

#### Scenario: Partial campaign read failure is visible

- **WHEN** at least one campaign file is unreadable and at least one other campaign contributes a pending variant
- **THEN** the console or read API returns the successful pending rows and clearly reports the campaign read failure

#### Scenario: Enablement off is display context only

- **WHEN** LinkedIn publication enablement is false and pending variants exist
- **THEN** the console still lists those pending variants and communicates enablement-off as technical context without filtering them out of the supervision window list

### Requirement: Story 1 scope preserves existing supervision and publication contracts

This capability MUST reuse US-015 policy, US-016 criteria (guidance links only), and US-017 mechanics contracts without duplicating or changing their normative behavior for publication or auto-queue implementation.

Story 1 read-only listing remains available. Story 2 MAY expose edit and defer actions that call existing US-017 endpoints. Story 3 MAY expose cancel actions that call existing `POST /cancel-linkedin-publication`. This capability MUST NOT change BL-007 auto-queue behavior beyond consuming existing US-017 eligibility effects of edit/defer/cancel; MUST NOT add LinkedIn API publish paths; MUST NOT introduce n8n Execute Command; and MUST NOT mark BL-015 closed or stories accepted by implementation alone.

#### Scenario: Existing publication guards unchanged

- **WHEN** `GET /flow-a/linkedin-variants/pending-supervision` runs
- **THEN** it does not publish to LinkedIn and does not bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`

#### Scenario: Console actions use worker HTTP only

- **WHEN** an operator uses edit, defer, or cancel from the supervision console
- **THEN** those actions invoke existing authenticated worker HTTP endpoints and do not use n8n Execute Command

### Requirement: Operator can edit pending variant content from the supervision console

The supervision console at `GET /flow-a/console/linkedin-variant-supervision` MUST allow a content operator to edit draft content for a Flow A LinkedIn variant while that variant appears in the optional supervision window (`publish_state` is `pending`).

The console MUST persist edits by calling the existing authenticated worker endpoint `POST /correct-linkedin-variant` with `campaign_id`, `variant`, and `draft_content` (plus optional `reason` / `idempotency_key`). The console MUST NOT introduce a parallel mutation endpoint or treat raw mount paths as the persistence source of truth.

The console MUST default mutation attempts to dry-run (`dry_run` true, matching US-017) unless the operator explicitly selects a real write. Successful real edits MUST leave `publish_state` as `pending` and MUST NOT claim LinkedIn API published.

#### Scenario: Edit control calls correct-linkedin-variant

- **WHEN** an authenticated operator submits an edit for a pending variant from the supervision console
- **THEN** the console sends `POST /correct-linkedin-variant` with the selected campaign id, variant id, and draft content and does not write campaign or draft files from the browser filesystem

#### Scenario: Edit dry-run default is explicit

- **WHEN** an operator opens the edit action without changing the dry-run control from its default
- **THEN** the request uses `dry_run` true and a successful response is presented as validation without mutation

#### Scenario: Real edit outcome remains pending supervision

- **WHEN** a real (`dry_run` false) edit succeeds for a pending variant
- **THEN** the console communicates success without labeling the variant as LinkedIn API published and `publish_state` remains in the supervision window (`pending`)

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

### Requirement: Mutation outcomes are visible on the console after edit or defer

After a successful edit or defer (dry-run or real), the console MUST present an understandable outcome to the operator (action, campaign/variant identity, dry-run vs real).

After a successful real mutation, the console MUST refresh pending-supervision data so updated `scheduled_at_utc` and available `operator_supervision` display fields (such as last action / `auto_queue_eligible` when present) are visible without requiring the operator to inspect raw campaign JSON.

#### Scenario: Real defer refreshes schedule on the console

- **WHEN** a real defer succeeds and the operator view refreshes pending supervision data
- **THEN** the listed variant shows the new `scheduled_at_utc` from the read API

#### Scenario: Failed mutation does not silently succeed

- **WHEN** edit or defer returns a failed supervision status or HTTP auth/validation error
- **THEN** the console shows a clear failure state and does not present the action as persisted

### Requirement: Console communicates edit and defer failures using US-017 codes

The console MUST clearly communicate blocked or invalid edit/defer attempts, including at least:

- unauthorized / invalid API key
- request validation failures (HTTP 422)
- `linkedin_supervision_variant_not_pending`
- `linkedin_supervision_defer_time_invalid`
- `linkedin_supervision_edit_unchanged`
- `linkedin_supervision_idempotency_conflict`
- `linkedin_supervision_action_not_allowed`

The console MUST NOT invent new worker error codes for Story 2. US-016 criteria failure MUST NOT be presented as an automatic technical block (guidance only).

#### Scenario: Non-pending edit failure is visible

- **WHEN** `POST /correct-linkedin-variant` fails with `linkedin_supervision_variant_not_pending`
- **THEN** the console displays that code (or equivalent operator-facing text tied to that code) and does not claim the draft was updated

#### Scenario: Invalid defer time is visible

- **WHEN** `POST /defer-linkedin-variant` fails with `linkedin_supervision_defer_time_invalid`
- **THEN** the console displays that the new schedule must be strictly in the future and does not claim the schedule changed

### Requirement: Pending-supervision read includes draft content for edit forms

`GET /flow-a/linkedin-variants/pending-supervision` MUST include a nullable `draft_content` field on each pending variant row, populated from the existing generated LinkedIn draft artifact for that campaign/variant when readable.

When the draft artifact is missing or unreadable, `draft_content` MUST be `null` and the response MUST record a structured issue; the pending row MUST still be returned so defer remains available.

The pending-supervision GET MUST remain free of filesystem mutation and MUST NOT invoke US-017 mutation routes on the server.

#### Scenario: Readable draft is returned for edit population

- **WHEN** a pending variant has a readable generated draft artifact
- **THEN** the pending-supervision response includes that variant’s `draft_content` text for console edit population

#### Scenario: Missing draft still lists the pending row

- **WHEN** a pending variant’s draft artifact is missing
- **THEN** the response still includes the pending row with `draft_content` null and an issue describing the draft read failure

### Requirement: Story 2 preserves existing mutation and publication contracts

Story 2 MUST reuse US-015 policy, US-016 criteria (guidance links only), and US-017 edit/defer mechanics without duplicating or changing their normative HTTP contracts.

Story 2 delivered edit and defer console actions. Story 3 MAY additionally expose cancel. Story 2-era requirements MUST NOT be interpreted to forbid Story 3 cancel. This capability MUST NOT add LinkedIn API publish paths; MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; MUST NOT introduce n8n Execute Command; MUST NOT change BL-007 auto-queue implementation; and MUST NOT mark BL-015 closed or stories accepted by implementation alone.

Committed console HTML MUST continue to pass the secrets/placeholder audit (no API keys, bearer tokens, or secret-like placeholders such as `CHANGE_ME`).

#### Scenario: Edit and defer remain available alongside cancel

- **WHEN** an operator opens the Story 3 supervision console
- **THEN** the console still exposes edit and defer actions that call `POST /correct-linkedin-variant` and `POST /defer-linkedin-variant`

#### Scenario: No new mutation endpoint required for edit or defer

- **WHEN** Story 2 edit and defer are exercised from the console
- **THEN** persistence uses only `POST /correct-linkedin-variant` and `POST /defer-linkedin-variant` as the mutation endpoints for those actions

#### Scenario: Static HTML secrets audit still passes for Story 2 assets

- **WHEN** the committed console HTML asset is scanned for API keys, bearer tokens, and secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present in the asset

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

### Requirement: Console surfaces blocked and deferred publication context

The supervision console and `GET /flow-a/linkedin-variants/pending-supervision` MUST surface blocked and deferred context relevant to optional supervision, including at least:

- LinkedIn publication enablement as display-only technical context (MUST NOT hide pending variants; MUST NOT bypass or change `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`)
- deferred / operator-supervision eligibility context on pending rows (`operator_supervision_last_action`, `auto_queue_eligible`, and reason when available)
- integration-failure context for failed sibling variants discovered while scanning campaign metadata for the pending aggregation (secret-safe fields only; at least campaign id, variant id, and `publish_state` `failed`)

The console MUST present this context so an operator can understand why strategy-driven publication or auto-queue may not proceed, without requiring raw mount inspection.

The console MUST NOT invent new `publish_state` values and MUST NOT treat US-016 criteria failure as an automatic technical block.

#### Scenario: Enablement off remains visible without filtering pending rows

- **WHEN** LinkedIn publication enablement is false and pending variants exist
- **THEN** the console still lists those pending variants and communicates enablement-off as blocked technical context for real API publish

#### Scenario: Deferred eligibility is visible on a pending row

- **WHEN** a pending variant has `operator_supervision` indicating a defer (`auto_queue_eligible` false and/or last action defer)
- **THEN** the console presents deferred / not-auto-queue-eligible context for that row without removing it from the pending list

#### Scenario: Failed sibling integration context is visible

- **WHEN** a campaign that contributes a pending variant also contains a sibling variant with `publish_state` `failed`
- **THEN** the pending-supervision response or console presents that failed sibling as integration-failure context without offering Story 3 cancel/edit/defer actions on the failed sibling

### Requirement: Cancel outcomes are visible on the console

After a successful cancel (dry-run or real), the console MUST present an understandable outcome to the operator (action, campaign/variant identity, dry-run vs real).

After a successful real cancel, the console MUST refresh pending-supervision data and MUST communicate that the override constrains future BL-007 auto-queue eligibility without claiming LinkedIn API published or equating `flow_a_complete` with LinkedIn API published.

#### Scenario: Real cancel outcome explains eligibility constraint

- **WHEN** a real cancel succeeds
- **THEN** the console shows a success state that states the variant is cancelled for strategy-driven auto-queue eligibility and does not claim LinkedIn API published

#### Scenario: Failed cancel does not silently succeed

- **WHEN** cancel returns a failed status or HTTP auth/validation error
- **THEN** the console shows a clear failure state and does not present the variant as cancelled

### Requirement: Console communicates cancel failures using existing worker codes

The console MUST clearly communicate blocked or invalid cancel attempts, including at least:

- unauthorized / invalid API key
- request validation failures (HTTP 422)
- `linkedin_supervision_variant_not_pending` (when returned)
- `linkedin_supervision_action_not_allowed` (when returned)
- `linkedin_publish_cancel_not_allowed`
- `linkedin_supervision_idempotency_conflict` (when returned)

The console MUST NOT invent new worker error codes for Story 3. Existing Story 2 edit/defer failure communication MUST remain available.

#### Scenario: Cancel-not-allowed failure is visible

- **WHEN** `POST /cancel-linkedin-publication` fails with `linkedin_publish_cancel_not_allowed`
- **THEN** the console displays that code (or equivalent operator-facing text tied to that code) and does not claim the variant was cancelled

#### Scenario: Auth failure on cancel is visible

- **WHEN** cancel is attempted without a valid API key
- **THEN** the console shows an unauthorized failure and does not claim the cancel persisted

### Requirement: Story 3 preserves existing mutation and publication contracts

Story 3 MUST reuse US-015 policy, US-016 criteria (guidance links only), and US-017 cancel/defer/edit mechanics without duplicating or changing their normative HTTP contracts.

Story 3 MUST persist cancel only via `POST /cancel-linkedin-publication` and MUST continue to persist defer only via `POST /defer-linkedin-variant`. Story 3 MUST NOT add LinkedIn API publish paths; MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; MUST NOT introduce n8n Execute Command; MUST NOT change BL-007 auto-queue implementation beyond consuming existing US-017 eligibility effects of cancel/defer; and MUST NOT mark BL-015 closed or US-040 Story accepted by implementation alone.

Committed console HTML MUST continue to pass the secrets/placeholder audit (no API keys, bearer tokens, or secret-like placeholders such as `CHANGE_ME`).

#### Scenario: Cancel uses only the existing cancel endpoint

- **WHEN** Story 3 cancel is exercised from the console
- **THEN** persistence uses `POST /cancel-linkedin-publication` and does not introduce a parallel cancel mutation endpoint

#### Scenario: Publication guards unchanged by console cancel

- **WHEN** an operator cancels a pending variant from the console
- **THEN** the worker does not call LinkedIn as part of cancel and does not bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`

#### Scenario: Static HTML secrets audit still passes

- **WHEN** the committed console HTML asset is scanned for API keys, bearer tokens, and secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present in the asset

### Requirement: Shared schedule editor from calendar entry points

The Flow A LinkedIn variant supervision console MUST allow an operator to select a future unpublished schedule item from the Week view, the Month calendar view, or mobile day/agenda equivalents and open the **same** schedule editor component (embedded in the EventModal after US-040H).

The schedule editor MUST collect a new schedule value in **operator-local** wall time (with timezone cue), convert to the existing worker `*_utc` wire fields only at the typed API client boundary, accept an optional reason, present dry-run vs real mode, and require explicit confirmation before a committed (`dry_run` false) schedule change.

Client-side and operator-facing validation MUST enforce that the new schedule is strictly after now in absolute time, explained in local terms. Moving an event earlier than its previous schedule MUST be allowed when the new absolute time is still after now. The worker remains authoritative for absolute-time rejection codes.

Published or historical items MUST open as read-only (or refuse schedule mutation) and MUST NOT offer a commit path that would rewrite their schedule.

#### Scenario: Week opens shared schedule editor for editable item

- **WHEN** an operator selects a future unpublished editable item from the Week view
- **THEN** the console opens the same schedule editor used by Month and mobile day/agenda equivalents for that item

#### Scenario: Month opens the same schedule editor

- **WHEN** an operator selects a future unpublished editable item from the Month calendar
- **THEN** the console opens the same schedule editor instance/path as Week

#### Scenario: Published historical item is read-only for schedule

- **WHEN** an operator selects a published or otherwise historical non-editable item
- **THEN** the console does not allow a committed schedule change for that item

#### Scenario: Schedule editor is local-first at the API boundary

- **WHEN** an operator submits a new schedule from ScheduleEditor
- **THEN** the picker value is interpreted as operator-local wall time and the typed client sends the existing `new_scheduled_at_utc` or `new_due_at_utc` field as UTC ISO without requiring the operator to enter UTC digits

#### Scenario: Earlier-than-previous future move is allowed

- **WHEN** an operator chooses a new local time that is still strictly after now but earlier than the item’s previous schedule
- **THEN** the console does not block the change solely because it is earlier than the previous schedule

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

### Requirement: Schedule mutation dry-run and confirmation

Schedule mutations from the shared schedule editor MUST default to dry-run (`dry_run` true) and MUST make dry-run vs real mode visible before any real mutation.

Committed schedule changes (`dry_run` false) MUST require explicit operator confirmation.

#### Scenario: Dry-run schedule change is visible as non-mutating

- **WHEN** an operator submits the schedule editor with dry-run default
- **THEN** a successful response is presented as validation without claiming the schedule was persisted

#### Scenario: Real schedule change requires confirmation

- **WHEN** an operator selects real (non-dry-run) mode and attempts to commit
- **THEN** the console requires explicit confirmation before sending `dry_run` false

### Requirement: Dual-view refresh and schedule-change outcome messaging

After a successful real schedule change, the console MUST refresh Week and Month presentations from the shared model (schedule-visibility and pending-supervision reads as applicable) so both views remain consistent.

The success presentation MUST show at least: the affected item identity, previous schedule, new schedule, and whether related LinkedIn variants were changed or remained separate overrides.

The console MUST NOT claim LinkedIn API published, MUST NOT equate `flow_a_complete` or blog handoff with LinkedIn API published, and MUST NOT claim that schedule edit published blog content.

#### Scenario: Real success refreshes week and month

- **WHEN** a real schedule change succeeds
- **THEN** the shared model refreshes from worker HTTP reads and both Week and Month reflect the new schedule

#### Scenario: Outcome reports previous and new schedule

- **WHEN** a real schedule change succeeds
- **THEN** the console shows previous schedule, new schedule, and affected item identity

#### Scenario: Blog reschedule reports LinkedIn variants as separate overrides by default

- **WHEN** a real blog calendar schedule change succeeds without a separate LinkedIn defer in the same operator action
- **THEN** the console reports that related LinkedIn variants remained separate overrides (unchanged by the blog calendar write)

### Requirement: Schedule editor validation and failure communication

The console MUST clearly communicate blocked or invalid schedule attempts, including at least:

- unauthorized / invalid API key
- request validation failures (HTTP 422)
- past or invalid time failures
- saturation and duplicate-slot failures when returned by the worker
- unsupported publication/calendar state failures
- existing US-017 defer failure codes when the LinkedIn path is used (`linkedin_supervision_variant_not_pending`, `linkedin_supervision_defer_time_invalid`, `linkedin_supervision_idempotency_conflict`, and related)

Failed attempts MUST NOT be presented as persisted schedule changes.

#### Scenario: Invalid future time failure is visible

- **WHEN** the worker rejects a schedule change for a past or invalid timestamp
- **THEN** the console displays a clear failure and does not claim the schedule changed

#### Scenario: Unsupported state failure is visible

- **WHEN** the worker rejects a schedule change because the item is not eligible (published/historical/unsupported state)
- **THEN** the console displays that failure and does not claim the schedule changed

### Requirement: Schedule mutation does not publish

Schedule edit actions from the supervision console MUST NOT call the LinkedIn publication API and MUST NOT publish blog content, commit/push Git, or bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

#### Scenario: Schedule edit does not invoke LinkedIn publish

- **WHEN** an operator completes a schedule edit (dry-run or real) from the console
- **THEN** the worker path used does not call LinkedIn publication APIs as part of that edit

### Requirement: US-040C scope preserves visibility baseline and defers later variants

US-040C MUST NOT mark BL-015 closed or US-040C Story accepted by implementation alone.

US-040C MUST preserve the US-040B list + month schedule visibility baseline (dual first-class views, schedule-visibility read, filters, CSS-grid month, mobile agenda) and MUST NOT rewrite that visibility contract except where additive fields are required for schedule editability.

US-040C MUST NOT implement US-040D public URL and Google auth activation, or US-040E polish beyond what schedule-mutation UX requires.

US-040C MUST NOT introduce a backend-for-frontend, database, user-management system, or public hosting change.

US-040C MUST NOT use n8n Execute Command or read/write raw mount paths from the browser.

#### Scenario: Later variants remain out of scope

- **WHEN** US-040C implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records US-040D–US-040E as not implemented (except mutation UX delivered by US-040C) and does not claim BL-015 closed

#### Scenario: US-040B visibility remains first-class

- **WHEN** US-040C schedule mutation is available
- **THEN** List and Month calendar visibility remain dual first-class views and schedule-visibility reads continue to power month placement

### Requirement: Typed client covers schedule-update APIs

The typed API client MUST centralize calls for:

- existing `GET /flow-a/linkedin-variants/pending-supervision`
- existing `GET /flow-a/schedule-visibility`
- existing US-017 `POST /correct-linkedin-variant`, `POST /defer-linkedin-variant`, `POST /cancel-linkedin-publication`
- the authenticated editorial-calendar schedule-update endpoint introduced for US-040C

Auth MUST remain injectable at the client boundary. Schedule editor and calendar components MUST NOT scatter ad-hoc `fetch` calls for these mutations.

#### Scenario: Schedule editor uses typed client

- **WHEN** the schedule editor submits a LinkedIn or blog schedule change
- **THEN** it uses the typed API client rather than ad-hoc browser filesystem or direct mount writes

### Requirement: Console represents explicit auth session states

The supervision console MUST represent the following operator-facing session states in the UI, even while the current local implementation uses the existing worker API-key auth mechanism:

- anonymous (no credential held)
- authenticated (credential held and session usable)
- expired-session (prior credential invalidated; re-auth required)
- forbidden (credential present but not authorized)
- service-unavailable (worker/API unreachable or HTTP 5xx)

Session-state presentation MUST be understandable without implying LinkedIn API published, and MUST NOT equate `pending`, `queued`, `cancelled`, `flow_a_complete`, or blog handoff with LinkedIn API published.

#### Scenario: Anonymous state is visible

- **WHEN** the console has no credential held
- **THEN** the UI presents an anonymous/not-authenticated state and does not claim the operator is signed in

#### Scenario: Authenticated state is visible

- **WHEN** a credential is held and the session is usable for worker calls
- **THEN** the UI presents an authenticated state distinct from anonymous and expired-session

#### Scenario: Expired session is visible after unauthorized response

- **WHEN** the typed client receives HTTP 401 and clears the held credential
- **THEN** the UI presents an expired-session state with guidance to re-authenticate

#### Scenario: Forbidden state is visible

- **WHEN** the typed client receives HTTP 403
- **THEN** the UI presents a forbidden/not-authorized state distinct from expired-session

#### Scenario: Service unavailable state is visible

- **WHEN** the typed client encounters a network failure or HTTP 5xx response
- **THEN** the UI presents a service-unavailable state and does not claim the request succeeded

### Requirement: Unauthenticated and read-only sessions cannot mutate schedules

The console MUST prevent unauthenticated sessions and read-only sessions (`canMutate` false) from executing schedule mutations, including:

- LinkedIn variant edit (`POST /correct-linkedin-variant`)
- LinkedIn variant defer/reschedule (`POST /defer-linkedin-variant`)
- LinkedIn variant cancel (`POST /cancel-linkedin-publication`)
- Editorial calendar schedule update (`POST /editorial-calendar/update-item-schedule`)

Mutation commit controls MUST be disabled or otherwise non-executable while `canMutate` is false. The worker remains the authoritative rejector for unauthenticated requests; the UI MUST NOT present a successful mutation when auth is missing or read-only.

#### Scenario: Anonymous session cannot commit schedule mutations

- **WHEN** the session is anonymous
- **THEN** the console does not execute edit/defer/cancel/calendar schedule-update commits and communicates that authentication is required

#### Scenario: Read-only session cannot commit schedule mutations

- **WHEN** the auth provider reports an authenticated but read-only session (`canMutate` false)
- **THEN** the console does not execute schedule mutation commits and communicates that mutation is not allowed

#### Scenario: Authenticated mutable session may attempt mutations via typed client

- **WHEN** the session is authenticated with `canMutate` true
- **THEN** the console may submit schedule mutations through the typed API client subject to existing dry-run and confirmation rules

### Requirement: Mobile session expiry preserves context and unsaved schedule drafts

When a session expires (including on mobile viewports), the console MUST preserve visible list/calendar context and MUST NOT silently discard an unsaved schedule-editor draft.

The console MUST guide the operator back to authentication and, after successful re-auth, MUST allow the operator to resume the preserved schedule draft without forcing a blank editor solely because auth was refreshed.

#### Scenario: Expiry mid-edit keeps schedule draft

- **WHEN** an operator has unsaved schedule-editor fields and the session transitions to expired-session
- **THEN** the unsaved draft remains available in the editor and is not silently cleared by auth expiry alone

#### Scenario: Re-auth guidance after expiry

- **WHEN** the session is expired-session
- **THEN** the UI guides the operator to re-authenticate without claiming mutation success

#### Scenario: Visible context survives expiry

- **WHEN** list or calendar data was already loaded and the session expires
- **THEN** the previously visible context remains on screen (with expired-session messaging) rather than being wiped without explanation

### Requirement: Same-origin default and documented CORS readiness

Browser calls from the supervision console to worker APIs MUST use same-origin relative paths by default while the console is served by the worker.

If a future architecture serves the console from a distinct origin, the project MUST document an explicit CORS allowlist strategy that can be restricted for public exposure (allowed origins, methods, and headers; no wildcard-with-credentials). US-040D MUST NOT enable permissive public CORS as part of readiness.

#### Scenario: Console API calls are same-origin by default

- **WHEN** the built console calls pending-supervision, schedule-visibility, or mutation endpoints
- **THEN** those calls use same-origin relative URLs under the worker host that serves the console

#### Scenario: Public CORS activation is not implied by readiness

- **WHEN** US-040D auth readiness is implemented
- **THEN** documentation states that any cross-origin CORS policy for public exposure requires a separate security change and is not activated by this slice

### Requirement: Public URL and Google authentication activation remain deferred

US-040D MUST document that public deployment (internet exposure of the console URL) and Google/OIDC authentication activation are out of scope for this backlog slice and require a separate approved security OpenSpec change before internet exposure.

US-040D MUST NOT activate public URL hosting, MUST NOT integrate a live Google OAuth/OIDC identity provider, MUST NOT introduce a backend-for-frontend, database, or user-management product, and MUST NOT use n8n Execute Command or browser filesystem writes.

#### Scenario: Activation deferred is recorded

- **WHEN** US-040D implementation is complete
- **THEN** CURRENT-STATE or equivalent operator documentation records that public URL hosting and Google authentication are not activated and require a separate security change before internet exposure

#### Scenario: No live IdP integration in this slice

- **WHEN** an implementer inspects the US-040D change scope
- **THEN** there is no live Google OAuth/OIDC login flow required for local API-key operations through the injectable auth boundary

### Requirement: US-040D scope preserves A–C baselines and defers US-040E

US-040D MUST NOT mark BL-015 closed or US-040D Story accepted by implementation alone.

US-040D MUST preserve the US-040A stack, US-040B list + month schedule visibility baseline, and US-040C shared schedule-editor mutation SoT (US-017 defer for LinkedIn; editorial-calendar schedule-update for blog). It MUST NOT rewrite those baselines except where additive auth-session and capability gating is required.

US-040D MUST NOT implement US-040E polish beyond what auth-readiness UX requires.

US-040D MUST NOT call the LinkedIn publication API, publish blog content, or bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` as part of auth-readiness work.

#### Scenario: Later polish remains out of scope for the US-040D slice

- **WHEN** US-040D implementation is complete
- **THEN** CURRENT-STATE or equivalent status language does not claim US-040D delivered US-040E polish and does not claim BL-015 closed from US-040D alone

#### Scenario: Prior console baselines remain first-class

- **WHEN** US-040D auth-readiness surfaces are available
- **THEN** List and Month calendar remain dual first-class views, shared ScheduleEditor remains the schedule mutation surface, and worker HTTP remains the only authz path for console data and mutations

### Requirement: Auth-readiness failures are clearly communicated

Auth and availability failures MUST be clearly communicated to the operator, including at least:

- missing credential / anonymous
- unauthorized / expired-session (HTTP 401)
- forbidden (HTTP 403)
- service unavailable (network or HTTP 5xx)
- validation failures (HTTP 422) that remain distinct from auth failures

Failed auth or blocked mutation attempts MUST NOT be presented as successful schedule or content changes.

#### Scenario: Auth failure is not shown as mutation success

- **WHEN** a mutation attempt fails because the session is anonymous, expired, or forbidden
- **THEN** the console shows a clear failure or blocked state and does not claim the schedule or variant was updated

#### Scenario: Service unavailable is distinct from auth missing

- **WHEN** the worker is unreachable or returns HTTP 5xx
- **THEN** the console communicates service unavailability distinctly from anonymous or expired-session messaging

### Requirement: At-a-glance operational counts

The supervision console MUST provide at-a-glance counts visible from the operational shell for at least:

- upcoming
- pending
- due soon
- deferred
- blocked
- failed
- recently published

Counts MUST be derived from the shared normalized frontend model fed by existing worker HTTP reads (`GET /flow-a/linkedin-variants/pending-supervision` and `GET /flow-a/schedule-visibility`) unless an approved thin additive read-only field is required and documented in the same change.

Count semantics MUST use qualified publication language:

- `pending` and `queued` MUST NOT be counted or labeled as LinkedIn API published
- `cancelled` MUST NOT be labeled as LinkedIn API published
- campaign `flow_a_complete` and blog handoff MUST NOT be treated as LinkedIn API published
- recently published MUST reflect display state `published` and/or `linkedinApiPublished` evidence within the documented recent window — not inferred from lifecycle metadata alone

Due soon MUST reuse the console’s existing due-soon window (48 hours) unless a superseding approved change replaces it.

#### Scenario: Counts appear after data load

- **WHEN** an authenticated operator has loaded pending-supervision and/or schedule-visibility data
- **THEN** the status summary presents counts for upcoming, pending, due soon, deferred, blocked, failed, and recently published

#### Scenario: Pending is not counted as LinkedIn API published

- **WHEN** items exist with display state `pending`
- **THEN** those items contribute to the pending count and are not labeled or counted as LinkedIn API published in the recently published count solely because they are pending

#### Scenario: Empty zero counts are understandable

- **WHEN** no items match a count category
- **THEN** that count shows zero (or equivalent empty) without presenting the zero as a system failure

### Requirement: Actionable states have visual priority without alarm fatigue

The console MUST prioritize actionable states visually so blocked or failed (and other critical) items are noticeable in Week and Month presentations without overwhelming normal scheduled content (planned / pending / queued / routine published).

Week MUST remain optimized for “this week’s plan” comprehension with scannable event chips. Month calendar MUST remain optimized for schedule density comprehension (day placement and compact status), not full diagnostic walls inside every day cell.

#### Scenario: Blocked or failed items are noticeable in Week

- **WHEN** the Week contains blocked or failed items among routine scheduled items
- **THEN** those actionable items are visually distinct from routine chips without making every chip appear critical

#### Scenario: Month keeps schedule comprehension

- **WHEN** the Month calendar shows a day with both routine and blocked/failed items
- **THEN** the day remains schedule-comprehensible (time/placement readable) and does not force full diagnostic chrome into every cell

### Requirement: Concise operator-facing labels with expandable diagnostics

The console MUST present concise operator-facing labels for technical publication display states (at least planned, pending, queued, published, deferred, cancelled, blocked, failed).

Detailed diagnostic codes and issue text (including known US-017 / calendar schedule-update codes and HTTP auth/validation failures already mapped by the typed client) MUST remain available in expandable details, detail panels, or equivalent disclosure UI when needed.

Primary chrome MUST prefer the concise label. The console MUST NOT remove operator access to diagnostic codes for failed or blocked outcomes.

#### Scenario: Concise label is shown for pending

- **WHEN** an item has display state `pending`
- **THEN** the primary presentation uses a concise operator-facing label and does not claim LinkedIn API published

#### Scenario: Diagnostic code remains available on failure

- **WHEN** a mutation or read failure includes a known worker diagnostic code
- **THEN** the operator can reveal that code (or equivalent tied text) via expandable details or an equivalent disclosure without treating the failure as success

### Requirement: Clear operational affordances

The console MUST provide clear affordances for:

- switching view (Week / Month)
- filtering
- inspecting item detail from calendar event entry points
- rescheduling / deferring where supported
- cancelling where supported
- refreshing data
- dry-run vs commit mode
- Today / This week (and equivalent month today navigation where applicable)

Destructive or irreversible actions (including real cancel) MUST remain protected by confirmation and MUST NOT be placed as peer controls immediately adjacent to routine navigation controls (view switcher and refresh) in a way that invites accidental activation.

Unauthenticated and read-only sessions (`canMutate` false) MUST continue to be prevented from executing mutations (US-040D).

#### Scenario: View switch and refresh are distinct from cancel

- **WHEN** the operator views the operational toolbar
- **THEN** view switching and refresh are clearly available and cancel is not presented as an adjacent peer of those routine navigation controls without confirmation protection

#### Scenario: Dry-run mode remains visible

- **WHEN** the operator uses the console shell
- **THEN** dry-run vs commit mode is clearly visible before real mutations

#### Scenario: Inspect and schedule actions remain reachable from calendar

- **WHEN** an editable future item is selected from a Week or Month event chip (interim entry path)
- **THEN** the operator can inspect detail and open the shared schedule editor where schedule edit is supported

### Requirement: Keyboard and touch accessibility for operational controls

The console MUST preserve keyboard accessibility for laptop use and touch accessibility for mobile use on primary operational controls (view switch, filters, refresh, dry-run toggle, list/calendar interaction, detail, schedule editor, confirmation).

Interactive controls MUST expose a visible focus indication for keyboard users. Primary touch targets on mobile MUST remain suitable for finger activation (MUST NOT regress below the mobile usability baseline delivered by US-040B).

Critical actions MUST NOT rely on hover-only disclosure.

#### Scenario: Keyboard can reach primary shell controls

- **WHEN** an operator uses keyboard focus on a desktop-width console
- **THEN** primary shell controls (including view switch and refresh) are reachable and show a visible focus indication

#### Scenario: Mobile touch targets remain usable

- **WHEN** the console is shown at a mobile width
- **THEN** primary actions in the shell and active view remain touch-operable without requiring hover

### Requirement: Dark theme consistency across console states

The console MUST keep the dark visual theme consistent across loading, empty, error, detail, confirmation, and success states, with readable contrast and stable spacing aligned to the existing dark console baseline.

#### Scenario: Empty state uses dark theme

- **WHEN** the List or Month presents an empty operational state
- **THEN** the empty presentation uses the dark theme and is not shown as a light marketing surface

#### Scenario: Error and success states use dark theme

- **WHEN** the console shows an error banner or a success outcome banner
- **THEN** those states use dark-theme-consistent chrome distinct from a light marketing page

#### Scenario: Confirmation and detail use dark theme

- **WHEN** the operator opens item detail or a confirmation flow
- **THEN** those surfaces use dark-theme-consistent presentation

### Requirement: Operational first screen without marketing landing

The first screen of `GET /flow-a/console/linkedin-variant-supervision` MUST be the usable operational console experience (shell with Week/Month view switcher, status path, header Filters control, and Week content area by default).

The console MUST NOT introduce a marketing-style landing page, promotional hero, or brand splash that replaces or delays the operational console as the first screen.

Auth session banners (anonymous / sign-in guidance) MAY appear inside the operational shell and MUST NOT constitute a separate marketing landing.

After US-040L, the first screen MUST NOT permanently show a full FOCUS/Filters dock ahead of Week/Month.

#### Scenario: First paint is the operational Week console

- **WHEN** an operator opens the supervision console route
- **THEN** the first screen is the operational console shell with Week as the default content area rather than a marketing-style landing page or List home

#### Scenario: First paint has Filters in the header not a permanent dock

- **WHEN** an operator opens the supervision console route after US-040L
- **THEN** the header Filters control is available and a permanent FOCUS/Filters strip does not precede the Week calendar

### Requirement: Desktop and mobile visual validation for US-040E

US-040E MUST include desktop and mobile visual validation evidence via screenshots or equivalent UI checks covering at least:

- dense lists
- empty lists
- dense months
- empty months
- blocked items
- long titles
- switching views
- schedule editing

Production build success for the existing React + TypeScript + Vite console MUST continue to hold. Secrets audits for frontend source and built assets MUST continue to pass.

#### Scenario: Visual validation matrix is covered

- **WHEN** US-040E frontend validation runs
- **THEN** evidence covers desktop-width and mobile-width presentations for dense/empty list, dense/empty month, blocked items, long titles, view switching, and schedule editing

#### Scenario: Production build still succeeds

- **WHEN** the frontend production build command is run after US-040E polish
- **THEN** the build completes successfully and emits static artifacts consumable by the worker

### Requirement: US-040E scope preserves A–D baselines and does not close BL-015 alone

US-040E MUST NOT mark BL-015 closed or US-040E Story accepted by implementation or propose alone.

US-040E MUST preserve:

- US-040A React + TypeScript + Vite static-asset delivery
- US-040B dual first-class List + Month visibility, filters, and shared model
- US-040C shared ScheduleEditor mutation SoT (US-017 defer for LinkedIn; editorial-calendar schedule-update for blog)
- US-040D session states and `canMutate` gating (public URL hosting and Google/OIDC activation remain deferred)

US-040E MUST prefer frontend UX polish on existing worker HTTP APIs and MUST NOT introduce a new mutation source of truth unless strictly required and approved within this change’s apply scope as a thin additive contract.

US-040E MUST NOT activate public URL hosting, MUST NOT integrate a live Google OAuth/OIDC identity provider, MUST NOT introduce a BFF/database/user-management product, MUST NOT call the LinkedIn publication API, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, and MUST NOT read or write raw mount paths from the browser.

#### Scenario: Prior baselines remain first-class after polish

- **WHEN** US-040E polish is implemented
- **THEN** List and Month remain dual first-class views, shared ScheduleEditor remains the schedule mutation surface, typed injectable auth with session/`canMutate` gating remains, and worker HTTP remains the only path for console data and mutations

#### Scenario: Public URL and Google remain not activated

- **WHEN** US-040E implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records that public URL hosting and Google/OIDC authentication are not activated and still require a separate security change before internet exposure

#### Scenario: BL-015 remains open until acceptance

- **WHEN** US-040E implementation lands
- **THEN** status language does not mark BL-015 closed or US-040E Story accepted by implementation alone

### Requirement: US-040E failures and outcomes are clearly communicated

US-040E polish MUST keep failures and blocked states clearly communicated and outcomes understandable to the content operator, including loading/empty/error/success/confirmation presentations and existing auth, validation, and supervision failure mappings.

Failed or blocked attempts MUST NOT be presented as successful schedule, cancel, or content changes. The console MUST NOT equate `pending`, `queued`, `cancelled`, `flow_a_complete`, or blog handoff with LinkedIn API published.

#### Scenario: Blocked state remains understandable after polish

- **WHEN** blocked or failed items are present
- **THEN** the console communicates that actionable state clearly without claiming LinkedIn API published

#### Scenario: Failed mutation is not shown as success

- **WHEN** a supervised mutation fails after polish
- **THEN** the console shows a clear failure or blocked outcome and does not present the action as persisted

### Requirement: Modern operational UX redesign for US-040F

US-040F MUST redesign the existing React + TypeScript + Vite console as a modern dark operational web app rather than a text-heavy technical status page.

The redesign MUST preserve US-040A–US-040E architecture and worker contracts: same static asset delivery, same typed API client/auth boundary, same shared normalized model, same first-class List and Month views, same shared ScheduleEditor mutation surface, same session states and `canMutate` gating, and no new mutation source of truth.

The shell MUST use available desktop width effectively and provide a structured workspace with concise top app controls, visible session state, refresh, dry-run/commit mode, view navigation, interactive operational metrics, primary content, and contextual detail/action areas.

Visible primary chrome SHOULD minimize endpoint names, worker codes, raw mount/path wording, and policy prose. Technical details MUST remain available through diagnostics/details or documentation references when needed, especially for failures or blocked states.

#### Scenario: Console renders as an app workspace

- **WHEN** the console first renders after US-040F
- **THEN** the first screen includes a modern app shell with top controls, session state, metric summary, filters path, and List or Month content area rather than a centered documentation-like page

#### Scenario: Metrics can focus the operator

- **WHEN** an operator activates an actionable metric such as blocked, failed, due soon, pending, deferred, or recently published
- **THEN** the console applies the relevant filter or navigation state without requiring the operator to configure filters manually

#### Scenario: Technical prose is not the primary interface

- **WHEN** an operator scans the primary shell, List, or Month view
- **THEN** endpoint paths, raw source-state codes, and long publication semantics are not the dominant visible content, while diagnostics remain available in details for troubleshooting

### Requirement: US-040F Calendar UX

The Month calendar MUST remain first-class and MUST communicate schedule density, channel/state, selected day, today, blocked/failed risk, and overflow at a glance.

The Month view MUST NOT turn day cells into full diagnostic forms. Full diagnostics and schedule actions SHOULD remain in selected-day agenda, item detail, or schedule editor surfaces.

Mobile calendar behavior MUST provide a usable month overview plus agenda-style day detail with touch-friendly schedule actions.

#### Scenario: Month communicates schedule and risk

- **WHEN** a month contains routine, blocked, and failed items
- **THEN** the calendar day cells show compact schedule/risk indicators while selected-day agenda exposes item detail and actions

#### Scenario: Mobile calendar remains usable

- **WHEN** the console is viewed at a mobile width
- **THEN** the month overview and selected-day agenda remain usable without horizontal table scrolling

### Requirement: US-040F validation and scope

US-040F MUST include frontend validation covering modern app shell structure, interactive metric filtering/navigation, card/list triage, master-detail or drawer behavior, responsive mobile layout, preservation of List/Month switching, destructive-action separation, and production build success.

Browser screenshots or equivalent browser-driven visual evidence SHOULD be captured when a browser runner is available. If the local environment cannot provide browser capture, implementation notes MUST explicitly state that limitation and keep automated viewport/component evidence in place.

US-040F MUST NOT activate public URL hosting, MUST NOT integrate a live Google/OIDC identity provider, MUST NOT introduce a BFF/database/user-management product, MUST NOT call the LinkedIn publication API, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, and MUST NOT read or write raw mount paths from the browser.

US-040F MUST NOT mark BL-015 closed or US-040F Story accepted by implementation alone. Further operator-directed UX iteration MAY follow in a subsequent approved change.

#### Scenario: Prior baselines remain intact

- **WHEN** US-040F is implemented
- **THEN** US-040A–US-040E behavior remains available and worker HTTP remains the only path for console data and mutations

#### Scenario: UX evidence exists

- **WHEN** frontend validation runs after US-040F
- **THEN** tests or documented evidence cover the modern shell, metric focus, list cards/master-detail, calendar/agenda, responsive layout, schedule editor, destructive confirmation, and blocked/failed states

#### Scenario: Story acceptance remains gated

- **WHEN** US-040F implementation and OpenSpec alignment land
- **THEN** status language does not mark BL-015 closed or US-040F Story accepted while further UX direction remains open

### Requirement: Calendar-first Week and Month operator chrome (US-040G)

The Flow A LinkedIn variant supervision console MUST be calendar-first. The operator-facing view switcher MUST offer exactly two first-class views labeled `Week` and `Month`.

`Week` MUST be the default view on first load and after hard refresh (unless a documented deep-link explicitly selects Month).

The console MUST NOT present a List tab, list-first landing, or empty list as the default workspace.

#### Scenario: Week is default first paint

- **WHEN** an operator opens `GET /flow-a/console/linkedin-variant-supervision` with no deep-link overriding the view
- **THEN** the first operational content area is the Week calendar view with the view switcher showing Week selected

#### Scenario: View switcher is Week and Month only

- **WHEN** the operator inspects the persistent view switcher
- **THEN** the switcher exposes Week and Month controls and does not expose a List control

#### Scenario: List chrome is absent

- **WHEN** the console shell is rendered after US-040G
- **THEN** no List tab, list landing route, or empty-list home workspace is presented as an operator chrome surface

### Requirement: Week calendar visibility UX

The Week view MUST present a readable local-week layout using day columns (or equivalent day sections on mobile), with day headers, today emphasis, previous/next week navigation, and a one-click Today / This week affordance.

Events MUST render as scannable chips or cards showing at least title or campaign label, channel, local time interpretation, and concise publication state. Raw ids MUST NOT be the primary visible label.

Week MUST NOT use an hour-by-hour time grid as the primary layout for this product density.

On phone viewports, week navigation and event chips MUST remain thumb-friendly and readable without requiring horizontal table scrolling as the only inspection path.

#### Scenario: Week shows day columns and today

- **WHEN** an operator opens Week for the current week
- **THEN** day headers are visible, today is emphasized, and the operator can navigate to previous and next weeks

#### Scenario: Event chips are scannable

- **WHEN** one or more schedule items fall in the visible week
- **THEN** each item appears as a chip or card with title or campaign label, channel, local time, and concise state (not raw id as the primary label)

#### Scenario: Today / This week control

- **WHEN** the operator activates the Today / This week control from Week
- **THEN** the Week cursor returns to the current week with today emphasized

#### Scenario: Mobile week remains usable

- **WHEN** the console is viewed at a mobile width on Week
- **THEN** week navigation and event chips remain usable without horizontal table scrolling as the only layout

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

Metric chips MUST NOT require the Filters modal to apply focus. Opening the Filters modal after a chip focus MUST reflect the resulting shared filter state.

When no matching item exists for a metric focus, the console MUST keep the calendar surface — including the Week day-column structure or Month day grid — and show an intentional empty or zero-match cue rather than falling back to a list or replacing the calendar with a gridless panel.

#### Scenario: Blocked metric stays on calendar

- **WHEN** an operator activates the blocked metric while on Week or Month
- **THEN** the console applies the blocked focus filter and adjusts the Week or Month cursor toward matching work without opening a List view

#### Scenario: Zero matches do not restore List

- **WHEN** a metric focus matches zero items
- **THEN** the console remains on Week or Month with an intentional empty or zero-match presentation, keeps the calendar day structure visible, and does not open a List

#### Scenario: Chip focus lights the Filters cue

- **WHEN** a metric chip applies a non-default filter
- **THEN** the header Filters control shows its calm active cue and the Filters modal, when opened, reflects that filter state

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

### Requirement: US-040G scope preserves baselines and defers H–K products

US-040G MUST NOT mark BL-015 closed or US-040G Story accepted by implementation alone.

US-040G MUST preserve:

- React + TypeScript + Vite same-origin static delivery
- typed injectable-auth API client
- shared normalized frontend model fed by worker HTTP reads
- ScheduleEditor mutation SoT (US-017 defer for LinkedIn; editorial-calendar schedule-update for blog)
- session states and `canMutate` gating
- qualified publication language (`pending`, `queued`, `cancelled`, `flow_a_complete`, blog handoff ≠ LinkedIn API published)

US-040G MUST NOT implement the US-040H event modal + toast product (interim entry points only), MUST NOT implement US-040I local-day bucketing overhaul (interim UTC day placement with local time display is allowed and MUST be documented as debt), MUST NOT implement US-040J cancelled reopen worker path, and MUST NOT implement US-040K max-2-per-local-day enforcement.

US-040G MUST NOT activate public URL hosting, MUST NOT integrate live Google/OIDC, MUST NOT introduce a BFF/database/user-management product, MUST NOT call the LinkedIn publication API, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, and MUST NOT read or write raw mount paths from the browser.

#### Scenario: Prior architecture baselines remain

- **WHEN** US-040G is implemented
- **THEN** worker HTTP remains the only console data/mutation path, ScheduleEditor remains the schedule mutation surface, and session/`canMutate` gating remains

#### Scenario: H–K products remain out of apply scope

- **WHEN** US-040G implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records US-040H modal/toasts, US-040I local-day bucketing, US-040J reopen, and US-040K density enforcement as not delivered by this change (aside from G interim action entry points and documented I debt)

#### Scenario: BL-015 remains open

- **WHEN** US-040G implementation lands
- **THEN** status language does not mark BL-015 closed or US-040G Story accepted by implementation alone

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

### Requirement: Operator-local Week and Month navigation (US-040I)

Week and Month navigation cursors (Today / This week, previous/next week, previous/next month, week and month labels) MUST be based on the operator’s **local** calendar, not UTC calendar weeks or months as the primary chrome.

Week labels and Month labels MUST NOT present `(UTC)` as the primary clock identity after US-040I.

#### Scenario: Today uses local calendar

- **WHEN** an operator activates Today / This week from Week
- **THEN** the Week cursor returns to the local week containing the operator’s local today

#### Scenario: Month label is local

- **WHEN** an operator views Month
- **THEN** the month label reflects the operator-local month without a primary `(UTC)` clock label

### Requirement: US-040I Visual DoD and acceptance gates

US-040I MUST require desktop and mobile Visual DoD evidence (screenshots or equivalent browser-driven capture) covering at least:

- local times on Week with timezone cue
- local times on Month / EventModal with timezone cue
- near-midnight day placement (item on correct local day)
- reschedule earlier-but-still-future
- proof that routine UI does not force UTC thinking (ScheduleEditor labels/help and primary surfaces)

Vitest or component assertions alone MUST NOT be treated as sufficient for Story accepted.

US-040I Story accepted and Acceptance criteria validated MUST NOT be marked until the content operator completes a live walkthrough on the deployed console or an explicitly agreed preview and confirms the local-time UX feels coherent in the operator’s timezone.

Implementation commit and “business outcome demonstrated” MAY occur before that gate. BL-015 MUST remain open until the backlog completion outcome is operator-validated; shipping US-040I code MUST NOT close BL-015 by itself.

US-040I MUST NOT mark US-040G or US-040H Story accepted as a side effect of this change.

If browser capture is unavailable in the implementation environment, status language MUST record that limitation and MUST leave Visual DoD / Story-accepted gates open.

#### Scenario: Visual DoD scenes are required

- **WHEN** US-040I claims visual validation complete for Story accepted
- **THEN** desktop and mobile evidence exists for local times with timezone cue on Week/Month/modal, near-midnight local-day placement, earlier-but-still-future reschedule, and absence of routine UTC coaching

#### Scenario: Vitest alone does not accept the story

- **WHEN** only Vitest or component assertions have passed
- **THEN** status language does not mark US-040I Story accepted or Acceptance criteria validated

#### Scenario: Walkthrough gate blocks Story accepted

- **WHEN** implementation is complete but the operator walkthrough on deployed or agreed preview has not confirmed local-time UX
- **THEN** US-040I remains not Story accepted and BL-015 remains open

### Requirement: US-040I scope preserves baselines and defers J–K products

US-040I MUST NOT mark BL-015 closed or US-040I Story accepted by implementation alone.

US-040I MUST preserve:

- React + TypeScript + Vite same-origin static delivery
- typed injectable-auth API client
- shared normalized frontend model fed by worker HTTP reads
- ScheduleEditor mutation SoT (US-017 defer for LinkedIn; editorial-calendar schedule-update for blog) and existing correct/cancel contracts with `*_utc` wire fields
- session states and `canMutate` gating
- Week (default) + Month calendar-first chrome without List restoration
- EventModal + toast feedback interaction model from US-040H
- Postgres editorial calendar SoT separation from LinkedIn variant campaign-metadata schedules
- qualified publication language (`pending`, `queued`, `cancelled`, `flow_a_complete`, blog handoff ≠ LinkedIn API published; dry-run ≠ real mutation)

US-040I MUST NOT implement US-040J cancelled reopen worker path, and MUST NOT implement US-040K max-2-per-local-day density enforcement (local day helpers MAY exist for reuse; K product rules MUST NOT ship here).

US-040I MUST NOT activate public URL hosting, MUST NOT integrate live Google/OIDC, MUST NOT introduce a BFF/database/user-management product, MUST NOT call the LinkedIn publication API, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, MUST NOT read or write raw mount paths from the browser, MUST NOT migrate campaign metadata schedules into Postgres, and MUST NOT add new worker mutation routes or non-`*_utc` schedule wire fields unless a separate design amendment explicitly justifies them.

#### Scenario: Prior architecture baselines remain

- **WHEN** US-040I is implemented
- **THEN** worker HTTP remains the only console data/mutation path, ScheduleEditor / US-017 semantics remain the mutation surface inside the EventModal, session/`canMutate` gating remains, List chrome is not restored, and `*_utc` wire fields remain

#### Scenario: J–K products remain out of apply scope

- **WHEN** US-040I implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records US-040J reopen and US-040K density enforcement as not delivered by this change

#### Scenario: BL-015 remains open

- **WHEN** US-040I implementation lands
- **THEN** status language does not mark BL-015 closed or US-040I Story accepted by implementation alone

### Requirement: Cancelled events remain visible with calm distinct styling

The Flow A LinkedIn variant supervision console MUST keep cancelled LinkedIn schedule items visible on Week and Month when they fall in the visible local range and pass active filters.

Cancelled chips MUST use a distinct but calm visual treatment and an operator-facing Cancelled label. Styling MUST NOT use the alarming failed/blocked treatment.

Cancelled MUST NOT be labeled or implied as LinkedIn API published. Campaign `flow_a_complete` and blog handoff MUST NOT be equated with LinkedIn API published.

A dedicated Cancelled metric chip is NOT required by this requirement (filters MAY already include publication state `cancelled`).

#### Scenario: Cancelled chip visible on Week

- **WHEN** a LinkedIn variant with display state `cancelled` has a schedule on a local day in the visible Week
- **THEN** Week shows a calm cancelled chip with a Cancelled label for that item

#### Scenario: Cancelled chip visible on Month

- **WHEN** a LinkedIn variant with display state `cancelled` has a schedule on a local day in the visible Month
- **THEN** Month shows a calm cancelled chip with a Cancelled label for that item

#### Scenario: Cancelled is not styled as failed

- **WHEN** a cancelled item and a failed item are both visible
- **THEN** the cancelled treatment is visually distinct from failed/blocked alarm styling

### Requirement: Cancelled EventModal answers what, why, and what next

Opening a cancelled calendar item MUST open the EventModal (not a day-agenda dump and not a restored List) and MUST answer three questions in plain operator language:

1. **What is this?** — identity (campaign/variant/audience/channel) and that the item is a cancelled planned LinkedIn publication (not LinkedIn API published).
2. **Why is it cancelled?** — reason, source/phase, and cancelled timestamp when available from schedule-visibility (or equivalent worker fields); when absent, an honest fallback such as “Cancelled by operator” without inventing facts; raw machine codes only in expandable diagnostics.
3. **What can I do now?** — when reopen is available and the session `canMutate`, present Reopen & reschedule (or equivalent); when reopen is unavailable or the variant is not reopen-eligible, state that explicitly and MUST NOT show fake Edit/reschedule controls that imply mutation.

#### Scenario: Cancelled modal explains identity and non-published meaning

- **WHEN** an operator opens a cancelled LinkedIn chip
- **THEN** the EventModal states the item is cancelled and does not claim LinkedIn API published

#### Scenario: Cancelled modal explains why when fields exist

- **WHEN** schedule-visibility provides cancellation reason and/or cancelled_at_utc for the item
- **THEN** the EventModal presents that information in operator language

#### Scenario: Non-reopenable cancelled item has explicit next-step copy

- **WHEN** an operator opens a cancelled item that is not reopen-eligible (or reopen is temporarily deferred inside the same change)
- **THEN** the modal states what the operator can or cannot do next and does not offer fake Edit controls

### Requirement: Operator can reopen and reschedule from a cancelled EventModal

When the approved worker reopen path is shipped, the console MUST allow an authenticated mutating session (`canMutate`) to reopen an eligible cancelled LinkedIn variant from the EventModal.

The happy path MUST:

1. require explicit confirmation before a real reopen
2. collect a new schedule in operator-local wall time (US-040I ScheduleEditor local-first rules; convert to `new_scheduled_at_utc` only at the typed API boundary)
3. default to dry-run and require explicit confirmation for real (`dry_run` false) commit
4. call the authenticated worker reopen endpoint over HTTP only (ADR-0001)
5. on success, show a toast (not a persistent green success banner), refresh schedule-visibility (and pending-supervision as applicable), and present the item as an editable pending/planned supervision target on the calendar at the new local day/time

Anonymous or read-only sessions MUST NOT execute reopen. Failures MUST surface as a failure toast with plain-language mapping of stable worker codes; the console MUST NOT claim success.

US-040K max-2-per-local-day density product rules MUST be enforced on reopen schedule pick and commit (client-side prevention + worker refusal mapping with plain-language density errors). Existing interim defer saturation/duplicate-slot worker refusals MUST remain mapped to plain language when returned.

If reopen must be temporarily deferred inside the same change, this requirement’s mutation scenarios remain unimplemented and the explicit read-only cancelled modal requirement above MUST still hold — mystery cancelled UX is forbidden either way.

#### Scenario: Reopen success toast and pending return

- **WHEN** a real reopen/reschedule succeeds from the cancelled EventModal
- **THEN** the console shows a success toast, refreshes calendar data, and the variant appears as editable pending (not cancelled) at the new local schedule

#### Scenario: Dry-run reopen does not claim committed restore

- **WHEN** a dry-run reopen succeeds
- **THEN** the toast/outcome indicates dry-run validation and the calendar does not treat the variant as restored until a real reopen succeeds

#### Scenario: Reopen failure toast

- **WHEN** reopen fails (not allowed, time invalid, auth, validation, saturation/duplicate-slot, or local-day density)
- **THEN** the console shows a failure toast with understandable copy and does not present the variant as pending

#### Scenario: Read-only session cannot reopen

- **WHEN** the session cannot mutate
- **THEN** the cancelled modal does not offer a commitable reopen path

#### Scenario: Reopen onto a full local day is blocked in plain language

- **WHEN** the operator attempts reopen onto a local day that already has 2 density members
- **THEN** the console blocks or fails with plain language that the day already has 2 publications and does not claim success

### Requirement: Schedule-visibility exposes cancellation context for console honesty

Authenticated `GET /flow-a/schedule-visibility` LinkedIn items MUST include additive nullable cancellation context sufficient for the cancelled EventModal when `publication_state` / source state is cancelled, including at least:

- `cancelled_at_utc` when known
- `cancellation_phase` when known (`pre_queue` / `post_queue` or equivalent)
- `cancellation_reason` when an operator reason was recorded (secret-safe)
- `reopen_eligible` boolean computed by the worker from reopen eligibility rules

These fields MUST NOT include secrets, tokens, or raw LinkedIn API bodies. Absent optional fields MUST be null/omitted rather than invented.

#### Scenario: Cancelled item includes reopen_eligible

- **WHEN** schedule-visibility returns a cancelled LinkedIn variant
- **THEN** the item includes `reopen_eligible` reflecting whether `POST /reopen-linkedin-variant` would be allowed for that provenance

#### Scenario: Cancellation reason is secret-safe

- **WHEN** a cancellation reason is present on campaign supervision metadata
- **THEN** schedule-visibility may expose that reason string without secrets or raw API payloads

### Requirement: Active cancel remains destructive and reopen-gated

Cancel from an active editable pending event in the EventModal MUST remain behind explicit confirmation, MUST call existing `POST /cancel-linkedin-publication`, and MUST remain irreversible except through the approved reopen path.

After cancel success, the console MUST refresh calendar data so the item shows as cancelled (calm chip) rather than silently disappearing without explanation when still in range.

#### Scenario: Cancel confirmation remains required

- **WHEN** an operator initiates cancel from an active pending EventModal
- **THEN** the console requires explicit confirmation before a real cancel mutation

#### Scenario: Cancel outcome is not LinkedIn API published

- **WHEN** a real cancel succeeds
- **THEN** outcome copy does not claim LinkedIn API published and describes cancelled / auto-queue exclusion in qualified language

### Requirement: US-040J Visual DoD and acceptance gates

US-040J MUST require desktop and mobile Visual DoD evidence (screenshots or equivalent browser-driven capture) covering at least:

- cancelled chip on Week
- cancelled chip on Month
- cancelled modal answering what / why / what next
- reopen/reschedule happy path (or explicit interim read-only cancelled copy if reopen deferred inside the same change)
- failure toast for a blocked/failed reopen (or equivalent failure communication if only read-only shipped)
- mobile cancelled modal

Vitest alone MUST NOT mark US-040J Story accepted.

Operator walkthrough on deployed or explicitly agreed preview MUST confirm cancelled items are understandable and the approved next action is obvious before Story accepted.

US-040J implementation MUST NOT mark BL-015 closed, MUST NOT mark US-040G/H/I Story accepted as a side effect, MUST NOT implement US-040K density product rules unless a hard dependency is recorded, MUST NOT activate public URL / Google OIDC / BFF / user-management, MUST NOT call LinkedIn API publish from the console, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, and MUST NOT read/write raw mount paths from the browser.

#### Scenario: Visual DoD required before Story accepted

- **WHEN** US-040J implementation and Vitest evidence exist
- **THEN** status language still leaves Story accepted open until Visual DoD + operator walkthrough complete

#### Scenario: BL-015 and prior UX stories remain open

- **WHEN** US-040J implementation lands
- **THEN** status language does not close BL-015 and does not mark US-040G/H/I Story accepted solely because US-040J shipped

#### Scenario: US-040K remains a follow-up

- **WHEN** US-040J implementation is complete
- **THEN** CURRENT-STATE or equivalent records max-2-per-local-day density enforcement as not delivered by this change

### Requirement: Week and Month surface local-day density (US-040K)

The Flow A LinkedIn variant supervision console MUST surface operator-local day density on Week and Month so that:

- a local day with **2** density members looks **full** (calm visual cue — not failed/blocked alarm styling)
- a local day with **3+** density members remains **visible** with a distinct over-capacity cue and no hidden chips
- a conflict attempt (placing a third member) is understandable **before** commit when using ScheduleEditor / reopen schedule pick

Density membership MUST follow the same inclusion set as the worker US-040K rule (live planned LinkedIn pending/queued including deferred pending, published items still shown, blog items shown; cancelled and failed excluded).

Day bucketing MUST use US-040I `localDayKey` (operator-local), not UTC day.

#### Scenario: Full day cue at two publications

- **WHEN** a local day has exactly 2 density members on Week or Month
- **THEN** the console presents a calm full-day density cue for that day

#### Scenario: Over-full day remains visible

- **WHEN** a local day has 3 or more density members
- **THEN** all events remain visible on Week/Month with an over-capacity cue and chips are not removed to satisfy the cap

#### Scenario: Local midnight boundary matches US-040I

- **WHEN** an item’s UTC timestamp falls near local midnight
- **THEN** density occupancy for that item uses the same local day as Week/Month placement

### Requirement: Client-side density validation on reschedule defer and reopen

Reschedule/defer (ScheduleEditor) and cancelled reopen schedule flows MUST validate the max-2 operator-local-day cap **client-side** using the current schedule-visibility snapshot before commit, and MUST still rely on worker enforcement.

Prefer prevention in the picker (disable or warn saturated local days where `others_on_day >= 2` excluding the item being edited) over cryptic post-submit codes alone.

Anonymous or read-only sessions (`canMutate` false) MUST NOT commit schedule changes. Dry-run default and confirm-for-real semantics MUST remain.

#### Scenario: Picker blocks or warns a third placement

- **WHEN** an authenticated mutating operator selects a target local day that already has 2 density members (excluding the item being moved)
- **THEN** the console blocks or clearly warns before commit with plain language that the day already has 2 publications

#### Scenario: Client and server both refuse over-capacity

- **WHEN** a commit is attempted that would exceed 2 density members on the target local day
- **THEN** the console does not claim success and surfaces a failure outcome if the worker refuses

### Requirement: Plain-language density and timezone errors

The console MUST map US-040K density and timezone worker codes to plain-language toast/modal copy. Density messaging MUST be human (e.g. “This day already has 2 publications”) and MUST NOT rely only on raw `*_saturation` or machine codes in the primary UI.

Expandable diagnostics MAY still show raw codes.

#### Scenario: Density refusal is plain language

- **WHEN** defer or reopen fails with the LinkedIn local-day density code
- **THEN** the operator-facing toast/modal states that the day already has 2 publications (or equivalent plain language)

#### Scenario: Timezone failure is understandable

- **WHEN** a mutation fails because operator timezone is missing or invalid
- **THEN** the console communicates a clear blocked state without claiming schedule success

### Requirement: Fix path for grandfathered over-capacity days

For local days that already have 3+ density members, the console MUST offer a clear path to fix density by moving events through the EventModal / ScheduleEditor (reschedule/defer or reopen flows as applicable). The console MUST NOT silently delete or auto-redistribute events.

#### Scenario: Operator can open and move an event off an over-full day

- **WHEN** an operator opens an event on an over-full local day and reschedules it to an under-capacity local day
- **THEN** the happy path remains EventModal → schedule edit → toast → calendar refresh, and the source day density decreases after a successful real mutation

### Requirement: US-040K Visual DoD and operator walkthrough gates

Automated tests (including Vitest) are necessary but MUST NOT be treated as sufficient for US-040K Story accepted.

US-040K MUST capture Visual DoD evidence (desktop ≈1280 and mobile ≈375, or equivalent) for at least:

- local day at 2 publications (full cue)
- attempt to place a 3rd (plain-language block)
- Month density cue
- existing 3+ day still visible with fix path
- local-midnight boundary occupancy

**Story accepted** / Acceptance criteria validated MUST NOT be marked until the content operator completes a live walkthrough on the deployed or explicitly agreed preview console and confirms the density rule is obvious and prevents a spammy plan.

Vitest/checkbox completion alone MUST NOT imply Story accepted. BL-015 MUST remain open until the backlog completion outcome is operator-validated. US-040G/H/I/J Story accepted MUST NOT be closed as a side effect of US-040K implementation.

#### Scenario: Vitest alone does not accept the story

- **WHEN** US-040K implementation and Vitest suites pass without Visual DoD evidence and operator walkthrough
- **THEN** product status MUST NOT mark US-040K Story accepted or Acceptance criteria validated

#### Scenario: Walkthrough required before Story accepted

- **WHEN** Visual DoD evidence exists and the operator completes a walkthrough confirming max-2 density UX intent
- **THEN** Story accepted MAY be recorded; otherwise it remains open

### Requirement: US-040K console scope preserves G–J baselines

US-040K MUST preserve:

- Week default + Month secondary calendar-first chrome (no List restoration as primary)
- EventModal + toast feedback
- operator-local primary clock and `*_utc` wire fields (US-040I)
- cancelled reopen path (US-040J)
- session states and `canMutate` gating
- dry-run default + confirm for real
- worker HTTP-only SoT (ADR-0001)
- qualified publication language

US-040K MUST NOT activate public URL / Google OIDC / BFF / user-management, MUST NOT call LinkedIn API publish from the console, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, and MUST NOT write editorial mounts from the browser.

#### Scenario: Prior console baselines remain

- **WHEN** US-040K is implemented
- **THEN** Week remains default, EventModal remains the event surface, local-time helpers remain authoritative for display/placement, and reopen remains available for eligible cancelled items

#### Scenario: No LinkedIn API publish from density UX

- **WHEN** density cues or density refusals are exercised in the console
- **THEN** the console does not invoke LinkedIn publication and only uses worker HTTP read/mutation endpoints

### Requirement: Completed blog calendar items display as published-on-blog

Authenticated `GET /flow-a/schedule-visibility` MUST map editorial-calendar blog items whose calendar `status` is `completed` to display `publication_state` **`completed`** (not `planned`).

For those blog-channel items the worker MUST:

- set `linkedin_api_published` to **`false`**
- set `source_state` to the calendar status (`completed`)
- preserve schedule non-editability for completed calendar status
- MUST NOT append the legacy title suffix `(blog handoff completed — not LinkedIn API published)` to `title`

The console MUST present `publication_state: completed` with an operator-facing label equivalent to **“Published on blog”**, distinct from LinkedIn `published` (“Published (API evidence)”).

The console MUST include `completed` in publication-state filters and status coloring without treating it as LinkedIn API published.

This requirement MUST NOT mark blog items as LinkedIn API published, MUST NOT mutate calendar Postgres status as part of the display fix, and MUST NOT implement Flow B or US-040L.

#### Scenario: Completed blog maps to completed display state

- **WHEN** schedule-visibility includes an editorial-calendar blog item with calendar `status: completed`
- **THEN** the item’s `channel` is `blog`, `publication_state` is `completed`, `linkedin_api_published` is `false`, and `title` does not include the legacy handoff suffix

#### Scenario: Planned blog remains planned

- **WHEN** schedule-visibility includes an editorial-calendar blog item with calendar status in the planned-like set (`planned`, `scheduled`, `due`, `in_progress`, or equivalent non-terminal states used today)
- **THEN** the item’s `publication_state` remains `planned` (or the existing non-completed mapping) and is not labeled “Published on blog”

#### Scenario: Console label distinguishes blog completed from LinkedIn published

- **WHEN** the console renders a blog item with `publication_state: completed` and a LinkedIn item with `publication_state: published`
- **THEN** the blog item shows a “Published on blog” (or equivalent) label and the LinkedIn item continues to show the LinkedIn API evidence published label; the blog item MUST NOT claim LinkedIn API published

#### Scenario: Completed blogs remain filterable and non-editable

- **WHEN** an operator filters by the completed / published-on-blog publication state
- **THEN** completed blog items are included by that filter and remain schedule-read-only (not schedule-editable)

#### Scenario: Scope excludes Flow B and filters-modal redesign

- **WHEN** this capability is implemented
- **THEN** Flow B (BL-016+) and US-040L Search/Filters header modal remain out of scope, and no calendar status backfill is required for items already `completed` in the store

### Requirement: Flow B gap operator settings surface in Authority Manager

Silverman Authority Manager (the existing LinkedIn supervision console product surface) SHALL provide an authenticated UI for operators to view and update Flow B gap operator settings defined by capability `flow-b-gap-operator-settings`. The UI MUST use the worker HTTP settings API as its source of truth, MUST validate or surface worker validation for IANA timezone, time-of-day, non-negative integers, and enums, and MUST clearly communicate failures or blocked states (including auth/session failures).

The console MUST NOT become a separate Flow B-only application. The settings surface MUST NOT expose secrets, MUST NOT claim that saving settings publishes to LinkedIn, and MUST NOT implement gap detect, draft generation, or blog approve/promote flows in this requirement’s scope.

#### Scenario: Authenticated operator can view and save settings

- **WHEN** an authenticated operator opens the Authority Manager settings surface and saves valid gap operator settings
- **THEN** the console persists them via the worker settings API and shows the updated values
- **AND** validation or worker errors are shown in plain language without secret material

#### Scenario: Unauthenticated operator cannot mutate settings

- **WHEN** the console session is anonymous, expired, or forbidden
- **THEN** settings mutation controls remain unavailable or fail closed with a clear re-auth cue

#### Scenario: Settings UI does not enable LinkedIn publish by implication

- **WHEN** an operator saves settings with any gap knobs including `gap_trigger_enabled`
- **THEN** the UI does not present saving settings as enabling LinkedIn API publish
- **AND** auto-trigger remains described as fail-closed while `gap_trigger_enabled` is false

### Requirement: Editorial content backlog surface in Authority Manager

Silverman Authority Manager (the existing LinkedIn supervision console product surface) SHALL provide an authenticated UI for operators to list, create, and edit editorial content backlog items defined by capability `editorial-content-backlog`. The UI MUST use the worker HTTP backlog API as its source of truth, MUST present the US-049 capture fields (topic, audience, objective, format, priority, status, target date) and LinkedIn derivative planning notes in operator-understandable language, and MUST clearly communicate failures or blocked states (including auth/session and validation failures).

The console MUST NOT become a separate Flow B-only application. The backlog surface MUST NOT expose secrets, MUST NOT claim that saving a backlog item publishes to LinkedIn or starts Flow B discovery/gap trigger, MUST NOT implement US-050 dependency/reprioritization UX, and MUST NOT redesign the console chrome or introduce a new UI component kit.

#### Scenario: Authenticated operator can list and create backlog items

- **WHEN** an authenticated operator opens the Authority Manager backlog surface and creates a valid backlog item
- **THEN** the console persists it via the worker backlog API and shows the item in the list with capture fields visible
- **AND** validation or worker errors are shown in plain language without secret material

#### Scenario: Authenticated operator can edit an existing item

- **WHEN** an authenticated operator edits an existing backlog item’s capture fields or LinkedIn derivative notes and saves
- **THEN** the console updates the item via the worker backlog API and shows the updated values

#### Scenario: Unauthenticated operator cannot mutate backlog

- **WHEN** the console session is anonymous, expired, or forbidden
- **THEN** backlog mutation controls remain unavailable or fail closed with a clear re-auth cue

#### Scenario: Empty backlog is understandable and not a failure

- **WHEN** an authenticated operator opens the backlog surface and the worker returns an empty list
- **THEN** the UI communicates that no backlog items exist yet
- **AND** does not present emptiness as a system failure or as a blocker for Flow B
