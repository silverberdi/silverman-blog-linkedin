## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Worker HTTP is the source of truth for console data

The supervision console MUST obtain pending-variant, calendar-alignment, and blocked-state display data through authenticated worker HTTP. The browser or operator UI MUST NOT treat raw mount file paths as the source of truth.

The worker MUST expose the thin authenticated read-only aggregation endpoint `GET /flow-a/linkedin-variants/pending-supervision` that returns the required per-variant fields without mutating campaign metadata, calendar files, or LinkedIn publication state.

The worker MUST serve the operator console static page at `GET /flow-a/console/linkedin-variant-supervision`.

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
- **THEN** the worker returns the static HTML console that consumes the pending-supervision read API and MAY offer edit, defer, and cancel actions that call existing US-017 POSTs

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
