# linkedin-variant-supervision-console

## Purpose

Operator-facing console for Flow A LinkedIn variants in the optional `pending` supervision window (BL-015 / US-038 Story 1 + US-039 Story 2 + US-040 Story 3 + US-040A stack migration): authenticated `GET /flow-a/linkedin-variants/pending-supervision` aggregation over campaign metadata and editorial calendar (including nullable `draft_content`, deferred eligibility, and secret-safe `integration_failures[]`), same-origin React + TypeScript + Vite console served as static build artifacts at `GET /flow-a/console/linkedin-variant-supervision`, edit/defer/cancel actions via existing US-017 POSTs through a typed injectable-auth API client, shared normalized frontend model for list/calendar scaffolds, blocked-state display context (enablement, deferred capabilities, integration failures), and secrets-safe frontend source and built assets. LinkedIn API publish paths, BL-007 auto-queue implementation changes, and US-040B–US-040E full delivery remain out of scope for this capability slice.

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

### Requirement: List-oriented pending supervision remains a first-class view

The modernized console MUST preserve the existing list-oriented pending-variant supervision experience as a first-class view, including presentation of pending rows and operator edit, defer, and cancel actions via existing US-017 POSTs with dry-run default and confirmation for real cancel.

The list view MUST NOT be removed, permanently hidden, or degraded to a secondary-only surface by the introduction of calendar scaffolding.

#### Scenario: List view remains primary operational surface

- **WHEN** an operator opens the modernized supervision console
- **THEN** a list-oriented pending-variant supervision view is available as a first-class view and supports the Stories 1–3 supervision actions already delivered

#### Scenario: Calendar scaffold does not replace list

- **WHEN** month calendar view scaffolding is present in the console
- **THEN** the list view remains reachable and continues to present pending supervision rows without requiring calendar interaction

### Requirement: Console UI is componentized with operational screen scaffolding

The modernized console MUST structure the UI as componentized operational screens and MUST include scaffolding (implemented shells and clear extension boundaries) for at least:

- list view
- month calendar view
- item detail
- schedule editor
- status summary
- filters
- confirmation flows
- shared API and error handling

Full month calendar visibility UX and schedule mutation behavior from the calendar remain out of scope for US-040A and MUST NOT be required for US-040A acceptance beyond scaffolding and shared-model readiness.

#### Scenario: Required scaffolds exist in the frontend package

- **WHEN** the US-040A frontend package is inspected
- **THEN** distinct component (or module) boundaries exist for list, month calendar, item detail, schedule editor, status summary, filters, confirmation flows, and shared API/error handling

#### Scenario: Calendar and schedule scaffolds do not imply US-040B or US-040C complete

- **WHEN** the month calendar or schedule editor scaffold is shown without full US-040B/US-040C behavior
- **THEN** the console does not claim those later stories are complete and does not invent a new calendar mutation source of truth

### Requirement: Browser API access uses a typed client with injectable auth

All browser calls to worker supervision APIs MUST go through a typed API client (or equivalent centralized boundary).

The client MUST centralize request construction, response typing, and error mapping for at least:

- `GET /flow-a/linkedin-variants/pending-supervision`
- `POST /correct-linkedin-variant`
- `POST /defer-linkedin-variant`
- `POST /cancel-linkedin-publication`

Auth credentials MUST be injectable at the API-client boundary (for example via a headers provider) so a future Google/OIDC bearer token or secure session cookie (US-040D) can replace the current API-key header mechanism without changing list or calendar business components.

Frontend source, rendered HTML, logs, and browser storage MUST NOT embed API keys, bearer tokens, OAuth tokens, operational secrets, or secret-like placeholders.

#### Scenario: Business components do not call fetch directly for worker APIs

- **WHEN** list or calendar components load pending supervision data or submit edit/defer/cancel
- **THEN** those components use the typed API client rather than ad-hoc `fetch`/`XMLHttpRequest` calls scattered across view code

#### Scenario: Auth provider can be swapped without editing list components

- **WHEN** the auth header provider implementation is replaced at the API-client boundary
- **THEN** list and calendar business components do not require changes to continue calling the same client methods

#### Scenario: Secrets are absent from frontend artifacts

- **WHEN** frontend source and built console assets are scanned for API keys, bearer tokens, and secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present

### Requirement: List and calendar share one normalized frontend model

List view and month calendar view MUST be backed by the same worker read models or by one shared normalized frontend model derived from those read models so the views cannot disagree about item identity, state, schedule, or available actions.

US-040A MUST implement the shared model and wire the list view to it. The calendar scaffold MUST consume the same model (even if calendar presentation remains placeholder-level).

#### Scenario: Shared model identity is stable across views

- **WHEN** a pending variant exists in the normalized frontend model
- **THEN** list and calendar scaffolds that render that item use the same campaign id, variant id, schedule, and action availability derived from that model

#### Scenario: List refresh updates the shared model

- **WHEN** pending-supervision data is refreshed after a successful real mutation
- **THEN** the shared model updates and list presentation reflects the new state without a separate divergent calendar cache

### Requirement: Frontend validation covers build and key UX contracts

US-040A MUST include frontend validation appropriate to the React + TypeScript + Vite stack covering at least:

- production build success
- key component behavior for the list-oriented supervision experience
- API error mapping for auth/validation and known supervision failure codes
- desktop viewport usability of the list-oriented console
- mobile viewport usability of the list-oriented console

#### Scenario: Production build succeeds

- **WHEN** the frontend production build command is run for the supervision console
- **THEN** the build completes successfully and emits static artifacts consumable by the worker

#### Scenario: API error mapping is tested

- **WHEN** the typed client receives unauthorized or known US-017 supervision failure responses
- **THEN** automated tests assert those responses map to clear operator-facing error states without silent success

#### Scenario: Desktop and mobile viewports are covered

- **WHEN** frontend validation for US-040A runs
- **THEN** evidence covers both a desktop-width and a mobile-width presentation of the list-oriented console

### Requirement: US-040A scope preserves Stories 1–3 and defers later variants

US-040A MUST NOT mark BL-015 closed or US-040A Story accepted by implementation alone.

US-040A MUST NOT implement US-040B full calendar UX, US-040C calendar schedule mutation / new calendar mutation SoT, US-040D public URL and Google auth activation, or US-040E polish beyond stack-migration needs.

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

The console MUST persist cancellations by calling the existing authenticated worker endpoint `POST /cancel-linkedin-publication` with `campaign_id` and `variant` (plus optional `reason` / `idempotency_key`). The console MUST NOT introduce a parallel mutation endpoint or treat raw mount paths as the persistence source of truth.

The console MUST default cancel attempts to dry-run (`dry_run` true, matching US-017) unless the operator explicitly selects a real write. Successful real cancel MUST move the variant out of the pending supervision window (`publish_state` `cancelled` per worker contract), MUST set operator-visible eligibility context such that strategy-driven auto-queue will not select it, and MUST NOT claim LinkedIn API published.

Defer controls delivered by Story 2 remain available; Story 3 MUST NOT re-implement defer through a second endpoint.

#### Scenario: Cancel control calls cancel-linkedin-publication

- **WHEN** an authenticated operator submits a cancel for a pending variant from the supervision console
- **THEN** the console sends `POST /cancel-linkedin-publication` with the selected campaign id and variant id and does not write campaign files from the browser filesystem

#### Scenario: Cancel dry-run default is explicit

- **WHEN** an operator opens the cancel action without changing the dry-run control from its default
- **THEN** the request uses `dry_run` true and a successful response is presented as validation without mutation

#### Scenario: Real cancel removes variant from pending supervision window

- **WHEN** a real (`dry_run` false) cancel succeeds for a pending variant and the console refreshes pending-supervision data
- **THEN** the cancelled variant is no longer listed as `pending` and the console does not label the outcome as LinkedIn API published

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
