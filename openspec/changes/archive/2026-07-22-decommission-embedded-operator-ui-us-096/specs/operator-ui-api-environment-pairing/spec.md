## MODIFIED Requirements

### Requirement: Separated UI declares intended environment label

In separated-UI mode, the operator UI SHALL require `SILVERMAN_OPERATOR_UI_ENV_LABEL` (injected via the existing runtime non-secret config path) to be `uat` or `prod`. Missing, empty, or invalid labels MUST fail closed with an operator-visible blocked state that names the required configuration key(s) without revealing secrets.

After US-096 there is no supported worker-embedded console compatibility mode that skips this label requirement.

#### Scenario: Valid UI env label accepted

- **WHEN** separated UI runtime config provides `envLabel` `uat` or `prod` with a valid API base URL
- **THEN** the UI proceeds to the API environment pairing check

#### Scenario: Missing UI env label blocks separated mode

- **WHEN** separated UI runtime config omits or leaves empty `SILVERMAN_OPERATOR_UI_ENV_LABEL`
- **THEN** the UI presents a clear blocked/configuration error and does not call authenticated supervision or mutation APIs
