## ADDED Requirements

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
