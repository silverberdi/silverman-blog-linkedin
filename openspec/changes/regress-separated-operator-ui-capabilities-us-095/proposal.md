## Why

US-093 separated Silverman Authority Manager onto `:8011` and US-094 paired UAT/prod UI↔API environments, but neither story proved that **day-to-day operator supervision** still works end-to-end on the supported production path (separated UI → worker HTTP). **BL-034 / US-095** (Story 3) closes that gap with a focused regression/smoke program—so operators keep schedule visibility and LinkedIn control-center actions after the split—without rewriting business screens, implementing Google login (BL-035), or hard-decommissioning the embedded console (US-096).

## What Changes

- Define and execute a **minimal but credible regression matrix** proving core supervision capabilities remain available through the separated UI calling the worker via `SILVERMAN_OPERATOR_UI_API_BASE_URL` (and paired env labels where required).
- Confirm **typed client absolute-base-URL behavior** in separated mode (no relative same-origin fallback) for schedule visibility, pending-supervision / control-center reads, and representative authenticated mutation path(s) already Story accepted under BL-032—prefer dry-run-safe or clearly gated actions; reuse existing Vitest/pytest/smoke patterns over new endpoints.
- Confirm **US-040D auth session gating** still works on the separated UI (sign-in / `canMutate` / clear session) without Google/OIDC, preserving the injectable auth boundary for BL-035.
- Reaffirm **fail-closed operator-visible UX** for existing US-093 config blocks and US-094 pairing blocks during the regression program.
- Document how **evidence is collected** (automated tests and/or controlled local/LAN smoke) without claiming public console exposure beyond BL-026.
- Update CURRENT-STATE / product docs **only** for ACs actually demonstrated; leave Story-accepted / deploy gates honest.
- Preserve ADR-0001 (n8n → worker HTTP only); do **not** mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or rewrite Flow/LinkedIn/n8n business logic; do **not** re-package US-093 or redesign US-094 pairing.

### Goals (US-095 acceptance criteria)

1. Core supervision capabilities remain available through the separated UI (schedule visibility and LinkedIn control-center actions already Story accepted under BL-032 remain reachable via API from the separated console on `:8011`).
2. Auth handoff remains compatible with a future Google login path (BL-035) without rewriting business screens (preserve US-040D Bearer paste / session boundary; no Google/OIDC implementation).
3. Outcome visible/understandable to the operator.
4. Failures or blocked states are clearly communicated (including existing config/pairing fail-closed UX from US-093/US-094).
5. Existing completed work is not duplicated or unintentionally changed.

### Non-goals / intentionally excluded

- **US-096** hard independence / removing embedded worker console assets and routes.
- **BL-035** Google/OIDC login implementation.
- **BL-029** full CI/UAT stand-up beyond what US-095 regression needs.
- Rewriting n8n workflows or introducing Execute Command.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Re-doing US-093 packaging or US-094 pairing enforcement (verify they still hold; do not redesign).
- Broad UI redesign or new business capabilities.
- Claiming public console exposure beyond BL-026 LAN acceptance.
- Full re-run of every historical Vitest suite as a mandatory gate (prefer a focused matrix + reuse of existing BL-032 / US-040D / US-093 / US-094 coverage).

## Capabilities

### New Capabilities

- `separated-operator-ui-capability-regression`: Normative focused regression/smoke program proving that after UI/API separation and environment pairing, day-to-day operator supervision (schedule visibility, BL-032 control-center reads, representative gated mutations, US-040D auth session gating, and US-093/US-094 fail-closed blocks) remains available on the separated UI → worker HTTP path (BL-034 / US-095).

### Modified Capabilities

- `linkedin-variant-supervision-console`: Require that BL-032 schedule visibility and control-center capabilities remain reachable from the separated console via the typed client absolute base URL; preserve injectable auth / `canMutate` session boundary for BL-035 without Google implementation; keep operator-visible success and blocked outcomes on the separated path.
- `operator-ui-deployment`: Tie supported production separated-UI path to US-095 capability-regression evidence expectations (absolute base URL, no relative fallback in separated mode) without changing US-093 packaging or US-094 pairing redesign.
- `operator-ui-api-environment-pairing`: Clarify that pairing remain in force during US-095 regression (verify hold; no redesign of labels, health field, or overlays).

## Impact

- **Frontend tests / light harness:** Focused Vitest (and optional documented local/LAN smoke) covering separated-mode absolute URL joins for schedule-visibility + pending-supervision, representative dry-run-safe or gated mutation client calls, auth session sign-in / `canMutate` / clear-session, and config/pairing blocked screens. Prefer extending existing suites (`us093`, `us094`, `auth.session`, BL-032 suites) over inventing new worker endpoints or business screens.
- **Worker / pytest:** Only if needed to support smoke evidence for CORS or existing read/mutation contracts from a separated origin—no Flow/LinkedIn business rewrites; no publication-enablement mutation.
- **Docs:** CURRENT-STATE topology note that US-095 regression evidence exists (local and/or controlled LAN); product story/checklist updates only for demonstrated ACs; do not claim Story accepted or public exposure without operator gate.
- **n8n / publication / Flow A–B:** unchanged contracts; n8n still targets worker HTTP only (ADR-0001).
- **Auth:** US-040D Bearer paste / injectable provider preserved; BL-035 out of scope.
- **Branch:** implement later on `feat/us-095-regress-separated-operator-ui` (or equivalent); do not implement on `main`. Preconditions: US-093 and US-094 local implementations (or merged equivalent).

## Backlog / story mapping

| ID | Role in this change |
|----|---------------------|
| **BL-034** | Parent epic — UI/API separation |
| **US-093** | Precondition — packaging/CORS/base URL (verify hold; do not re-implement) |
| **US-094** | Precondition — UAT/prod pairing (verify hold; do not redesign) |
| **US-095** | **In scope** — Story 3 (this change) |
| **US-096** | Out of scope — hard decommission of embedded console |
| **BL-032** | Capability baseline — schedule + control-center actions already Story accepted; prove still reachable via separated UI |
| **US-040D** | Auth boundary baseline — preserve Bearer paste / session / `canMutate` for BL-035 |
| **BL-035** | Out of scope — Google/OIDC |
| **BL-029** | Out of scope beyond regression needs |
| **BL-026** | Exposure ceiling — no public console claim |
