## ADDED Requirements

### Requirement: Separated production path includes capability-regression evidence

The supported production path for Silverman Authority Manager as a separated UI artifact MUST be backed by focused capability-regression evidence (US-095) showing that schedule visibility, BL-032 control-center reads, at least one representative gated/dry-run mutation, and US-040D auth session gating remain available when the UI calls the worker via the configured absolute `SILVERMAN_OPERATOR_UI_API_BASE_URL` (with pairing labels applied where required).

US-093 packaging (distinct UI artifact, runtime base URL injection, CORS allowlist) and US-094 pairing enforcement remain in force; this requirement does not redesign them. Evidence MAY be automated tests and/or controlled local/LAN smoke and MUST NOT claim public console exposure beyond BL-026.

#### Scenario: Regression evidence required for separated path claim

- **WHEN** docs or checklists claim day-to-day supervision remains available on the separated UI production path after US-095
- **THEN** they cite focused regression evidence covering absolute-base reads, a representative gated/dry-run mutation, auth session gating, and existing config/pairing fail-closed holds

#### Scenario: No relative fallback in separated mode during regression

- **WHEN** separated-UI mode has a valid absolute API base URL under regression
- **THEN** typed client calls continue to use that absolute origin and do not silently fall back to UI same-origin relative API paths

#### Scenario: US-093 packaging not redesigned by US-095

- **WHEN** US-095 regression work is applied
- **THEN** the distinct UI artifact/service model and runtime API base URL injection from US-093 remain the packaging approach (verify hold; no packaging redesign required)
