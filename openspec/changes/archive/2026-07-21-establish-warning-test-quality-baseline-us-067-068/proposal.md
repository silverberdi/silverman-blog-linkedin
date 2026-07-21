## Why

P7 **BL-028 / US-067 + US-068** still lack a known baseline for test-suite warnings and code-quality signals. Without an inventory and a written “inherited vs new” contract, operators cannot tell whether a change introduces new quality problems — and BL-029 CI would only automate an undefined bar.

## What Changes

- Publish an operator-facing **warning and test quality baseline** SoT under `docs/operations/` covering: how to run the full suite(s), how to inventory warnings, how to separate inherited vs new warnings, and the rule **zero new warnings attributable to a change**.
- Run the full suite once as part of this change, capture a dated inventory, correct cheap root causes where safe, and document remaining inherited warnings (if any) as the baseline.
- Introduce capability `warning-and-test-quality-baseline` as documentation/contract (plus evidence of the baseline run).
- Close US-067 + US-068 and **BL-028** when Story accepted after the baseline is documented.
- Does **not** establish CI (BL-029), mutate Flow A/B behavior, or mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

## Capabilities

### New Capabilities
- `warning-and-test-quality-baseline`: Normative procedure + dated baseline inventory for suite warnings and the zero-new-warnings rule (US-067 + US-068).

### Modified Capabilities
- *(none)*

## Impact

- Docs: `docs/operations/` SoT + dated evidence; GLOSSARY / CURRENT-STATE / product pointers.
- Tooling: may add narrow pytest warning filters only with inline justification for inherited third-party noise; prefer root-cause fixes.
- No worker route/Docker/n8n behavior changes required for Story acceptance.
- BL-029 remains open (CI consumes this baseline later).
