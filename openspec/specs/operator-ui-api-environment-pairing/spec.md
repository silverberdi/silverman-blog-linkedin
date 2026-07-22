# operator-ui-api-environment-pairing

## Purpose

Closed-vocabulary UAT/prod pairing between the separated operator UI and the worker API (BL-034 / US-094): non-secret environment identity on both sides, health advertisement, fail-closed agreement checks, per-environment deploy defaults, and operator-visible pairing status—without claiming full BL-029 CI/UAT stand-up or mutating publication guards.

## Requirements

### Requirement: Closed deployment environment vocabulary

The system SHALL use a closed set of non-secret deployment environment identifiers for operator UI↔API pairing: exactly `uat` and `prod` (normalized case-insensitively to lowercase). Free-form or alternate labels MUST NOT satisfy pairing requirements.

Documentation and env examples MUST use these tokens by name and MUST NOT embed API keys, bearer tokens, or secret-like placeholders.

#### Scenario: Only uat and prod are valid pairing labels

- **WHEN** an operator configures UI or worker deployment environment for separated-UI pairing
- **THEN** accepted values are `uat` and `prod` only (after lowercase normalization)

### Requirement: Worker declares deployment environment

The worker SHALL read a non-secret environment variable `SILVERMAN_DEPLOYMENT_ENVIRONMENT` whose value MUST be `uat` or `prod` when the deployment is intended to pair with the separated operator UI.

Invalid values (missing when required by deploy profile, empty, or outside the closed set) MUST be rejected at configuration load for pairing-capable server profiles, or otherwise fail closed such that the worker does not advertise a false environment identity.

Docs and examples MUST name the variable and use placeholders only—no secrets.

#### Scenario: Valid worker environment loads

- **WHEN** `SILVERMAN_DEPLOYMENT_ENVIRONMENT` is set to `uat` or `prod`
- **THEN** the worker configuration exposes that normalized value for health advertisement and pairing

#### Scenario: Invalid worker environment is rejected

- **WHEN** `SILVERMAN_DEPLOYMENT_ENVIRONMENT` is set to a value outside `uat`/`prod`
- **THEN** configuration validation fails closed with an actionable error that names the variable and does not include secret values

### Requirement: Separated UI declares intended environment label

In separated-UI mode, the operator UI SHALL require `SILVERMAN_OPERATOR_UI_ENV_LABEL` (injected via the existing runtime non-secret config path) to be `uat` or `prod`. Missing, empty, or invalid labels MUST fail closed with an operator-visible blocked state that names the required configuration key(s) without revealing secrets.

After US-096 there is no supported worker-embedded console compatibility mode that skips this label requirement.

#### Scenario: Valid UI env label accepted

- **WHEN** separated UI runtime config provides `envLabel` `uat` or `prod` with a valid API base URL
- **THEN** the UI proceeds to the API environment pairing check

#### Scenario: Missing UI env label blocks separated mode

- **WHEN** separated UI runtime config omits or leaves empty `SILVERMAN_OPERATOR_UI_ENV_LABEL`
- **THEN** the UI presents a clear blocked/configuration error and does not call authenticated supervision or mutation APIs

### Requirement: Separated bootstrap narrows env label before pairing

After separated-UI runtime configuration resolves successfully (`ok: true` with `deliveryMode` `separated`), the UI bootstrap MUST treat `envLabel` as a closed `uat`|`prod` value before invoking API environment pairing validation.

If `envLabel` is empty or otherwise not a proven deployment environment at that point, the UI MUST fail closed with an operator-visible blocked state that names `SILVERMAN_OPERATOR_UI_ENV_LABEL` (no secrets) and MUST NOT call `validateApiEnvironmentPairing` or proceed with authenticated supervision.

This requirement does not redesign pairing agreement checks; it ensures the pairing entrypoint is only invoked with a proven `DeploymentEnvironment` (including TypeScript build safety).

#### Scenario: Proven env label reaches pairing

- **WHEN** separated config resolves with `envLabel` `uat` or `prod`
- **THEN** the UI invokes API environment pairing with that label and does not treat the empty-label type as callable

#### Scenario: Empty env label after config ok fails closed

- **WHEN** separated bootstrap somehow observes an empty `envLabel` after config resolution reported success
- **THEN** the UI shows an operator-visible blocked state naming `SILVERMAN_OPERATOR_UI_ENV_LABEL` and does not call pairing or authenticated APIs

### Requirement: UI validates agreement with API deployment environment

After US-093 API base URL validation succeeds, the separated UI MUST obtain the worker’s advertised `deployment_environment` from `GET {apiBaseUrl}/health` (or the documented equivalent non-secret read on that origin) and MUST compare it to the UI env label.

If the values are equal (`uat`/`uat` or `prod`/`prod`), pairing succeeds and the console MAY proceed with authenticated HTTP as today.

If they differ, or the health response is unreachable/unreadable/missing a valid `deployment_environment`, the UI MUST fail closed with an operator-visible blocked state and MUST NOT perform authenticated supervision reads or mutations against that API base URL (no silent cross-environment writes). Relative same-origin fallback MUST remain disabled in separated mode.

#### Scenario: Matching UAT pair allows proceed

- **WHEN** UI env label is `uat` and `GET {apiBaseUrl}/health` returns `deployment_environment` `uat`
- **THEN** the separated UI treats pairing as successful and may proceed with authenticated worker HTTP

#### Scenario: Matching prod pair allows proceed

- **WHEN** UI env label is `prod` and `GET {apiBaseUrl}/health` returns `deployment_environment` `prod`
- **THEN** the separated UI treats pairing as successful and may proceed with authenticated worker HTTP

#### Scenario: Mismatched environments block the console

- **WHEN** UI env label is `uat` and the API advertises `deployment_environment` `prod` (or the reverse)
- **THEN** the UI presents a clear pairing-blocked error naming the relevant configuration keys and does not issue authenticated supervision or mutation requests

#### Scenario: Unreadable API environment blocks the console

- **WHEN** the separated UI cannot read a valid `deployment_environment` from the configured API health response
- **THEN** the UI fails closed with an operator-visible error and does not proceed with authenticated API use

### Requirement: Per-environment deploy defaults pair UI to matching API

The repository SHALL provide non-secret deploy configuration examples (or clearly separated overlays) such that:

- A **UAT** profile defaults the UI env label to `uat` and the UI API base URL to the UAT worker origin placeholder (not the prod worker placeholder).
- A **prod** profile defaults the UI env label to `prod` and the UI API base URL to the prod worker origin placeholder (not the UAT worker placeholder).

Corresponding worker examples for each profile MUST default `SILVERMAN_DEPLOYMENT_ENVIRONMENT` to the same token. Examples MUST NOT embed secrets.

Presence of these defaults documents intended pairing; it MUST NOT claim that a live second UAT stack or full BL-029 CI/UAT stand-up is complete.

#### Scenario: UAT example points UI at UAT API

- **WHEN** an operator reads the UAT pairing env example overlay
- **THEN** `SILVERMAN_OPERATOR_UI_ENV_LABEL` is `uat` and `SILVERMAN_OPERATOR_UI_API_BASE_URL` uses a UAT worker placeholder distinct from the prod placeholder

#### Scenario: Prod example points UI at prod API

- **WHEN** an operator reads the prod pairing env example overlay
- **THEN** `SILVERMAN_OPERATOR_UI_ENV_LABEL` is `prod` and `SILVERMAN_OPERATOR_UI_API_BASE_URL` uses a prod worker placeholder distinct from the UAT placeholder

### Requirement: Operator can see active environment and pairing failures

When pairing succeeds, the separated UI MUST surface the active environment (`uat` or `prod`) in an operator-visible way (for example a chrome badge or equivalent). When pairing or required pairing config fails, the blocked state MUST be understandable and MUST NOT expose secrets.

#### Scenario: Successful pair shows environment

- **WHEN** an operator opens a successfully paired separated UI
- **THEN** the console displays the active environment identity without secret values

#### Scenario: Pairing failure is understandable

- **WHEN** pairing fails closed
- **THEN** the operator sees a clear blocked message that distinguishes configuration/pairing failure from routine auth failure and does not include secret values

### Requirement: Pairing preserves ADR-0001 and existing publication guards

Environment pairing MUST NOT introduce n8n Execute Command, MUST NOT make the UI an n8n orchestration target, MUST NOT rewrite Flow A/B or LinkedIn business contracts, and MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` as part of this change.

#### Scenario: n8n still targets worker HTTP only

- **WHEN** an operator reviews orchestration after US-094 pairing work
- **THEN** n8n continues to call the worker API over HTTP only and does not gain Execute Command for worker file I/O as a result of this change

### Requirement: Pairing remains enforced during separated-UI capability regression

During US-095 capability regression on the separated operator UI, UI↔API environment pairing semantics from US-094 MUST remain in force: matching `uat`/`prod` labels allow proceed; mismatch, missing/invalid UI env label, or unreadable API `deployment_environment` MUST fail closed with an operator-visible blocked state and MUST NOT permit authenticated supervision or mutation traffic.

US-095 MUST verify this hold as part of regression evidence and MUST NOT redesign the pairing vocabulary, health advertisement field, deploy overlays, or badge/blocked UX.

#### Scenario: Regression keeps matching pair operable

- **WHEN** US-095 regression exercises the separated UI with matching UI env label and API `deployment_environment`
- **THEN** pairing still succeeds and authenticated supervision reads may proceed under existing rules

#### Scenario: Regression keeps mismatch blocked

- **WHEN** US-095 regression exercises a mismatched or unreadable pairing condition
- **THEN** the console remains fail-closed with an operator-visible pairing/configuration block and does not issue authenticated supervision or mutation requests

#### Scenario: Pairing not redesigned by US-095

- **WHEN** US-095 changes are reviewed against US-094 pairing design
- **THEN** closed vocabulary (`uat`|`prod`), `GET /health.deployment_environment`, and per-environment overlay approach are preserved without a pairing redesign
