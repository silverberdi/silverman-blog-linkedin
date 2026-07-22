## Why

Production Docker build of `silverman-operator-ui` fails on branch `feat/us-095-regress-separated-operator-ui` with `TS2345` in `main.tsx`: `config.envLabel` is typed `"" | "uat" | "prod"` and cannot be passed to `validateApiEnvironmentPairing(..., envLabel: DeploymentEnvironment)`. This blocks LAN deploy of already-synced US-093/US-094/US-095 work (BL-034).

## What Changes

- Narrow the separated-mode bootstrap path so pairing is only invoked with a proven `DeploymentEnvironment`.
- Fail closed with an operator-visible blocked state if `envLabel` is somehow empty after config resolution succeeded (defensive; should not occur after `resolveOperatorUiConfig` ok in separated mode).
- No pairing redesign, no US-096, no BL-035, no LinkedIn publication flag mutation.

## Goals

1. `npx tsc -b` and `npm run build` succeed for `frontend/linkedin-variant-supervision-console`.
2. Existing US-093 / US-094 / US-095 / `auth.session` Vitest suites remain green.
3. Separated UI can be redeployed on LAN prod (`:8011` ↔ API `:8010`) without changing pairing semantics.

## Non-goals / intentionally excluded

- Reopening or redesigning US-094 pairing, US-095 regression matrix, or US-096 embedded-console removal.
- Google/OIDC (BL-035).
- Claiming Story accepted solely because build/deploy succeeded.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- n8n Execute Command or Flow business rewrites.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `operator-ui-api-environment-pairing`: Clarify that after separated config resolves successfully, the bootstrap MUST narrow `envLabel` to `uat`|`prod` before the health pairing call, and MUST fail closed if the label is empty (TypeScript + runtime guard; no pairing redesign).

## Impact

- Code: `frontend/linkedin-variant-supervision-console/src/main.tsx` (and tests only if needed for the fail-closed empty-label guard).
- Product: BL-034 / US-093–US-095 deploy unblock; no new user story.
- Ops: Enables `deploy-worker.sh` operator-UI image build; CURRENT-STATE / RUNTIME-STATE update only after live redeploy evidence.
- Related backlog: **BL-034** (in progress); does not close BL-034 or mark US-093–US-095 Story accepted.
