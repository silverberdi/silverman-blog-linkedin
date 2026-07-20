## ADDED Requirements

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

This requirement is the BL-032 / US-083 control-center **foundation** for honest status. It MUST NOT implement publish-now (US-086), cancel for queued (US-085), or postpone/reschedule redesign (US-084). It MUST NOT reopen BL-015 as supervision-only product closure.

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

#### Scenario: US-083 does not ship later BL-032 mutations

- **WHEN** this US-083 capability is implemented
- **THEN** the console does not offer a working publish-now LinkedIn API path, does not implement cancel-for-queued as a completed mutation, and does not redesign postpone/reschedule beyond honest status and availability display

### Requirement: LinkedIn EventModal action availability matrix (US-083)

When an operator opens a LinkedIn calendar/event item in EventModal (or the equivalent item-detail control surface), the console MUST show which **control actions are available now** versus **unavailable**, with **plain-language reasons** when blocked or not yet shipped.

For actions the console already supports today, availability MUST reflect real eligibility (for example pending-supervision join + `actions` for edit/cancel; `schedule_editable` / block reason for reschedule/defer; `reopen_eligible` for reopen) and session mutation capability (`canMutate`).

For BL-032 controls not implemented in US-083, the matrix MUST still communicate honesty when an operator would reasonably expect them:

- **Cancel while waiting to send (`queued`)** — unavailable / not available yet (US-085), with plain language that queued is not live and cancel-from-console for that state is not shipped yet
- **Publish now** — unavailable / not available yet (US-086), and MUST NOT imply a LinkedIn API send occurred

Unavailable expected controls MUST NOT be silently omitted when the matrix is shown; hiding only truly irrelevant controls (for example reopen on a non-cancelled item) remains allowed.

Failures and blocked states (auth cannot mutate, schedule blocked, density/cadence block reasons already returned by the worker, integration failure context) MUST be communicated in plain language without claiming LinkedIn API published.

#### Scenario: Pending item lists available supervision controls

- **WHEN** an operator opens a LinkedIn item in the pending / Scheduled state with pending-supervision detail and mutation permission
- **THEN** the action matrix shows edit and cancel (pending) as available when worker `actions` allow them, and shows reschedule/defer according to schedule editability

#### Scenario: Queued item does not claim cancel-queued is done

- **WHEN** an operator opens a LinkedIn item in Waiting to send / `queued` state
- **THEN** the matrix does not present cancel-queued as an available completed control; it shows cancel for that state as unavailable with a plain-language not-available-yet (US-085) reason, and does not claim the item is live on LinkedIn

#### Scenario: Publish now shown as unavailable in US-083

- **WHEN** an operator opens an eligible-looking LinkedIn item that is not yet live
- **THEN** publish now appears as unavailable / not available yet (US-086) and no LinkedIn API publish is invoked from the console

#### Scenario: Blocked mutation explains why

- **WHEN** an action is blocked because the session cannot mutate, schedule is not editable, or reopen is ineligible
- **THEN** the console states the plain-language reason and does not present the blocked action as successfully completed

### Requirement: Preview versus real change is unmistakable for existing LinkedIn controls (US-083)

For existing LinkedIn console mutations (edit draft, defer/reschedule via ScheduleEditor, cancel-from-pending, reopen), the console MUST make **preview/dry-run** versus **real/committed** change unmistakable **before** the operator submits and **after** the outcome is shown.

Dry-run MUST remain the default unless the operator explicitly selects a real write. Preview outcomes MUST NOT use wording that implies the schedule was saved, the variant was cancelled for real, or content went live on LinkedIn.

Real outcomes MUST state that the change was committed/saved (as applicable) and MUST still NOT claim LinkedIn API published unless the mutation’s worker result actually establishes live publication evidence (US-083 mutations do not publish to LinkedIn).

#### Scenario: Dry-run default is explicit before submit

- **WHEN** an operator opens edit, cancel-pending, reopen, or schedule defer without changing the dry-run/preview control from its default
- **THEN** the UI indicates the attempt is preview/dry-run (no lasting change) before submit

#### Scenario: Preview outcome cannot be mistaken for real

- **WHEN** a dry-run mutation returns success
- **THEN** the console outcome/toast states that no lasting change was made (preview) and does not claim schedule saved, cancel completed for real, or live on LinkedIn

#### Scenario: Real outcome states committed without false LinkedIn live claim

- **WHEN** a real (`dry_run` false) edit, defer, cancel-pending, or reopen succeeds
- **THEN** the console outcome states the change was committed/saved as applicable and does not claim LinkedIn API published / live on LinkedIn solely because the mutation succeeded

## MODIFIED Requirements

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
