## Why

BL-028 recorded **11 failing pytest nodes** and **1 inherited** `StarletteDeprecationWarning` (FastAPI/Starlette TestClient + `httpx`). BL-033 / **US-090** must clear that suite debt and eliminate the warning so continuous integration (BL-029) can start from a clean, measurable green bar — not a red suite with a known third-party warning treated as permanent.

## What Changes

- Fix or correctly realign the known failing pytest expectations (editorial canon phrase, compose mount/`postgres:` checks, console static dry-run copy, Flow A markdown-only connector claim/release/reconcile tests) without weakening assertions to hide real regressions.
- Eliminate the inherited `StarletteDeprecationWarning` via root-cause remediation (supported TestClient / `httpx2` or compatible upgrade path) — not a broad global warning filter as the sole fix.
- Re-run full pytest with warnings visible; achieve **0 failed** and **0 warnings**.
- Confirm Vitest remains green; refresh BL-028 baseline evidence / SoT pointers; close **US-090** and **BL-033**.
- Does **not** establish CI (BL-029), mutate LinkedIn publication enablement, or reopen BL-028 as incomplete.

## Capabilities

### New Capabilities
- `pytest-suite-debt-and-warning-clearance`: Normative clearance of BL-028-recorded pytest failures and the inherited Starlette TestClient warning for US-090 / BL-033.

### Modified Capabilities
- *(none required for product runtime specs; optional thin pointer updates in warning-and-test-quality-baseline docs only)*

## Impact

- Tests, possibly small docs (editorial canon / compose expectations), possibly dependency pins for TestClient/`httpx2`, and baseline evidence under `docs/operations/`.
- Product pointers for BL-033 / US-090 closure.
- No intentional Flow A/B behavior change unless a failing connector test reveals a true regression that must be restored.
