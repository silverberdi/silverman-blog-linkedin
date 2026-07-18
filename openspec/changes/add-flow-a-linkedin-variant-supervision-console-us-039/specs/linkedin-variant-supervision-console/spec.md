## ADDED Requirements

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

The supervision console MUST allow a content operator to defer or reschedule a pending variant by submitting a future `new_scheduled_at_utc` relative to distribution strategy / US-017 defer rules.

The console MUST persist deferrals by calling the existing authenticated worker endpoint `POST /defer-linkedin-variant`. The console MUST NOT invent calendar write-back as part of defer success (calendar join remains read-only context and MAY appear stale until separately reconciled).

Dry-run default and pending-state language rules for edit also apply to defer.

#### Scenario: Defer control calls defer-linkedin-variant

- **WHEN** an authenticated operator submits a defer with a future UTC schedule for a pending variant from the supervision console
- **THEN** the console sends `POST /defer-linkedin-variant` with campaign id, variant id, and `new_scheduled_at_utc`

#### Scenario: Defer does not claim calendar auto-update

- **WHEN** a real defer succeeds
- **THEN** the console does not claim that the editorial calendar was automatically updated as part of the defer action

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

Story 2 MUST NOT expose cancel actions; MUST NOT add LinkedIn API publish paths; MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; MUST NOT introduce n8n Execute Command; MUST NOT change BL-007 auto-queue implementation; and MUST NOT mark BL-015 closed or US-039 Story accepted by implementation alone.

Committed console HTML MUST continue to pass the secrets/placeholder audit (no API keys, bearer tokens, or secret-like placeholders such as `CHANGE_ME`).

#### Scenario: No cancel control in Story 2 console

- **WHEN** an operator opens the Story 2 supervision console
- **THEN** the console does not expose a cancel action that calls `POST /cancel-linkedin-publication`

#### Scenario: No new mutation endpoint required

- **WHEN** Story 2 edit and defer are exercised from the console
- **THEN** persistence uses only `POST /correct-linkedin-variant` and `POST /defer-linkedin-variant` as the mutation endpoints

#### Scenario: Static HTML secrets audit still passes

- **WHEN** the committed console HTML asset is scanned for API keys, bearer tokens, and secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present in the asset

## MODIFIED Requirements

### Requirement: Worker HTTP is the source of truth for console data

The supervision console MUST obtain pending-variant and calendar-alignment data through authenticated worker HTTP. The browser or operator UI MUST NOT treat raw mount file paths as the source of truth.

The worker MUST expose the thin authenticated read-only aggregation endpoint `GET /flow-a/linkedin-variants/pending-supervision` that returns the required per-variant fields without mutating campaign metadata, calendar files, or LinkedIn publication state.

The worker MUST serve the operator console static page at `GET /flow-a/console/linkedin-variant-supervision`.

The pending-supervision GET MUST NOT call LinkedIn, DeepSeek, ComfyUI, or Git, and MUST NOT invoke US-017 mutation routes (`POST /correct-linkedin-variant`, `POST /defer-linkedin-variant`, `POST /cancel-linkedin-publication`) on the server.

The console page MAY call authenticated US-017 mutation routes for edit and defer only (US-039). Cancel remains out of scope for this capability until US-040.

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
- **THEN** the worker returns the static HTML console that consumes the pending-supervision read API and MAY offer edit/defer actions that call existing US-017 POSTs

### Requirement: Failures and blocked states are clearly communicated on the read path

The console and its read API MUST clearly communicate read/display failures and blocked-state context relevant to supervision, including at least:

- unreadable or invalid campaign metadata files (partial results allowed)
- missing or invalid editorial calendar (variants still listed when available)
- LinkedIn publication enablement off as display-only technical context (MUST NOT hide pending variants; MUST NOT bypass or change `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`)
- missing or unreadable draft artifacts for pending rows (`draft_content` null with issue)

The console MUST NOT invent new `publish_state` values and MUST NOT treat US-016 criteria failure as an automatic technical block.

Edit/defer mutation failure communication is specified under the Story 2 edit/defer failure requirement and does not replace read-path issue reporting.

#### Scenario: Partial campaign read failure is visible

- **WHEN** at least one campaign file is unreadable and at least one other campaign contributes a pending variant
- **THEN** the console or read API returns the successful pending rows and clearly reports the campaign read failure

#### Scenario: Enablement off is display context only

- **WHEN** LinkedIn publication enablement is false and pending variants exist
- **THEN** the console still lists those pending variants and communicates enablement-off as technical context without filtering them out of the supervision window list

### Requirement: Story 1 scope preserves existing supervision and publication contracts

This capability MUST reuse US-015 policy, US-016 criteria (guidance links only), and US-017 mechanics contracts without duplicating or changing their normative behavior for publication, auto-queue, or cancel.

Story 1 read-only listing remains available. Story 2 MAY expose edit and defer actions that call existing US-017 endpoints. This capability MUST NOT implement cancel actions (US-040); MUST NOT change BL-007 auto-queue behavior beyond consuming existing US-017 eligibility effects of edit/defer; MUST NOT add LinkedIn API publish paths; MUST NOT introduce n8n Execute Command; and MUST NOT mark BL-015 closed or stories accepted by implementation alone.

#### Scenario: Cancel remains out of scope on the console

- **WHEN** an operator opens the supervision console under Story 2
- **THEN** the console does not expose cancel actions that call `POST /cancel-linkedin-publication`

#### Scenario: Existing publication guards unchanged

- **WHEN** `GET /flow-a/linkedin-variants/pending-supervision` runs
- **THEN** it does not publish to LinkedIn and does not bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`
