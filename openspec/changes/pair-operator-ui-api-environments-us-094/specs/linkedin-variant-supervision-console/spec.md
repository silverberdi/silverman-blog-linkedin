## ADDED Requirements

### Requirement: Separated console shows environment identity and pairing blocks

When the console runs as the separated operator UI, it MUST display the active paired environment (`uat` or `prod`) after successful UI↔API environment pairing.

When environment label configuration is missing/invalid or UI↔API pairing fails (including mismatched or unreadable API `deployment_environment`), the console MUST show a clear operator-visible blocked state and MUST NOT proceed with authenticated supervision reads or mutations. Messages MUST name relevant configuration keys without including API keys, bearer tokens, or other secrets.

Embedded compatibility mode is not required to enforce pairing.

#### Scenario: Paired console shows environment badge

- **WHEN** the separated UI successfully pairs with the worker API
- **THEN** the operator can see the active environment identity (`uat` or `prod`) in the console chrome or equivalent visible surface

#### Scenario: Pairing mismatch blocks authenticated use

- **WHEN** the separated UI env label does not match the API `deployment_environment`
- **THEN** the console shows a blocked/pairing error and does not call authenticated supervision or mutation endpoints

## MODIFIED Requirements

### Requirement: Separated console surfaces configuration and API blocked states

When the separated operator UI cannot proceed because API base URL configuration is missing/invalid, because UI↔API environment pairing fails or required environment label config is missing/invalid, or because worker HTTP calls fail due to network/CORS/unauthorized conditions already modeled by the client error vocabulary, the console MUST communicate a clear operator-visible blocked or error state. Messages MUST NOT include API keys, bearer tokens, or other secrets.

#### Scenario: Configuration block is operator-visible

- **WHEN** separated-UI API base URL configuration is missing or invalid
- **THEN** the operator sees a clear blocked/configuration message naming the required config key(s) without secret values

#### Scenario: Environment pairing block is operator-visible

- **WHEN** separated-UI environment pairing fails or the required env label is missing/invalid
- **THEN** the operator sees a clear blocked/pairing message naming the required config key(s) without secret values

#### Scenario: Unauthorized API call remains understandable

- **WHEN** the separated UI calls the worker without valid credentials
- **THEN** the console presents the existing unauthorized / sign-in blocked semantics without exposing secrets
