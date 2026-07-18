## ADDED Requirements

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

The supervision console MUST obtain pending-variant and calendar-alignment data through authenticated worker HTTP. The browser or operator UI MUST NOT treat raw mount file paths as the source of truth.

The worker MUST expose the thin authenticated read-only aggregation endpoint `GET /flow-a/linkedin-variants/pending-supervision` that returns the required per-variant fields without mutating campaign metadata, calendar files, or LinkedIn publication state.

The worker MUST serve the operator console static page at `GET /flow-a/console/linkedin-variant-supervision`.

The read path MUST NOT call LinkedIn, DeepSeek, ComfyUI, or Git, and MUST NOT invoke US-017 mutation routes (`POST /correct-linkedin-variant`, `POST /defer-linkedin-variant`, `POST /cancel-linkedin-publication`).

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
- **THEN** the worker returns the Story 1 static HTML console that is intended to consume the pending-supervision read API

### Requirement: Static console HTML MUST NOT embed secrets or secret-like placeholders

The committed static HTML for `GET /flow-a/console/linkedin-variant-supervision` MUST NOT contain API keys, bearer tokens, OAuth tokens, or placeholders that look like real secrets (including but not limited to `CHANGE_ME`, `sk-` prefixed samples, `Bearer ` token samples, or hardcoded `X-API-Key` values).

Operators MUST supply credentials at runtime (browser prompt or local-only configuration). Documentation examples MUST use clearly non-secret wording (for example “your API key”) without embedding fake credential strings that resemble production secrets.

#### Scenario: Static HTML secrets audit passes

- **WHEN** the committed console HTML asset is scanned for API keys, bearer tokens, and secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present in the asset

### Requirement: Failures and blocked states are clearly communicated on the read path

The console and its read API MUST clearly communicate read/display failures and blocked-state context relevant to Story 1, including at least:

- unreadable or invalid campaign metadata files (partial results allowed)
- missing or invalid editorial calendar (variants still listed when available)
- LinkedIn publication enablement off as display-only technical context (MUST NOT hide pending variants; MUST NOT bypass or change `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`)

The console MUST NOT invent new `publish_state` values, MUST NOT treat US-016 criteria failure as an automatic technical block, and MUST NOT present US-039/US-040 mutation action surfaces as implemented in this capability.

#### Scenario: Partial campaign read failure is visible

- **WHEN** at least one campaign file is unreadable and at least one other campaign contributes a pending variant
- **THEN** the console or read API returns the successful pending rows and clearly reports the campaign read failure

#### Scenario: Enablement off is display context only

- **WHEN** LinkedIn publication enablement is false and pending variants exist
- **THEN** the console still lists those pending variants and communicates enablement-off as technical context without filtering them out of the supervision window list

### Requirement: Story 1 scope preserves existing supervision and publication contracts

This capability MUST reuse US-015 policy, US-016 criteria (guidance links only), and US-017 mechanics contracts without duplicating or changing their normative behavior.

This capability MUST NOT implement edit, defer, or cancel actions; MUST NOT change BL-007 auto-queue behavior; MUST NOT add LinkedIn API publish paths; MUST NOT introduce n8n Execute Command; and MUST NOT mark BL-015 closed or US-038 Story accepted by implementation alone.

#### Scenario: No mutation controls in Story 1 console

- **WHEN** an operator opens the Story 1 supervision console
- **THEN** the console does not expose edit, defer, or cancel actions that call US-017 mutation endpoints

#### Scenario: Existing publication guards unchanged

- **WHEN** `GET /flow-a/linkedin-variants/pending-supervision` runs
- **THEN** it does not publish to LinkedIn and does not bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`
