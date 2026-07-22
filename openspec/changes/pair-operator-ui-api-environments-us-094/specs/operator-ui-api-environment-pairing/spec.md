## ADDED Requirements

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

Embedded worker-console compatibility mode MUST NOT require this label for same-origin operation.

#### Scenario: Valid UI env label accepted

- **WHEN** separated UI runtime config provides `envLabel` `uat` or `prod` with a valid API base URL
- **THEN** the UI proceeds to the API environment pairing check

#### Scenario: Missing UI env label blocks separated mode

- **WHEN** separated UI runtime config omits or leaves empty `SILVERMAN_OPERATOR_UI_ENV_LABEL`
- **THEN** the UI presents a clear blocked/configuration error and does not call authenticated supervision or mutation APIs

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
