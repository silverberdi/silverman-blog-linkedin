## ADDED Requirements

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
