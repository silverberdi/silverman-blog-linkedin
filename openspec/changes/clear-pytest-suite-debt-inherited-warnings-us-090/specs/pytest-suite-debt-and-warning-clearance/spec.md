# pytest-suite-debt-and-warning-clearance

## Purpose

Clear the BL-028-recorded pytest suite debt and inherited Starlette TestClient warning for **BL-033 / US-090**, refreshing the warning/test quality baseline to a clean green bar before continuous integration (BL-029).

## ADDED Requirements

### Requirement: Clear known pytest failures

The repository SHALL resolve the pytest failures recorded in the BL-028 baseline evidence (editorial canon Flow A vs Flow B phrase, compose editorial mount and shared-stack marker checks, console static dry-run contract copy, and Flow A markdown-only connector calendar-seed / claim-release tests) such that a full unrestricted pytest run reports **0 failed**. Fixes MUST realign tests to intentional current behavior or restore missing normative wording — they MUST NOT weaken assertions solely to hide regressions.

#### Scenario: Full pytest has zero failures

- **WHEN** an operator runs full pytest via the project `.venv` on an unrestricted runner
- **THEN** the suite reports 0 failed tests for the previously listed BL-028 debt nodes and overall

### Requirement: Eliminate inherited Starlette TestClient warning

The repository SHALL eliminate the inherited `StarletteDeprecationWarning` about using `httpx` with Starlette/`fastapi.testclient.TestClient` by root-cause remediation (installing/using the supported `httpx2` path or an equivalent supported upgrade). Broad global warning filters MUST NOT be the sole remediation.

#### Scenario: Full pytest reports zero warnings

- **WHEN** an operator runs full pytest with warnings visible (`-W default`) on an unrestricted runner
- **THEN** the suite reports 0 warnings attributable to TestClient/`httpx` deprecation
- **AND** no broad global filter is the only remediation for that warning

### Requirement: Baseline refresh and independence

Normative docs SHALL refresh the warning/test quality baseline evidence after clearance, mark US-090 / BL-033 Story accepted when criteria are met, and MUST NOT establish CI (BL-029 remains separate) or mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. Frontend Vitest MUST remain green.

#### Scenario: Baseline evidence updated without establishing CI

- **WHEN** US-090 is Story accepted
- **THEN** baseline evidence no longer lists the cleared failures and W1 as open inherited debt
- **AND** BL-029 is not required for acceptance
