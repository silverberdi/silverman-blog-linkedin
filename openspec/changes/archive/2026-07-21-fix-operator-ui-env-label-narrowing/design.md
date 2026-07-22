## Context

US-093/US-094/US-095 are synced and archived on `feat/us-095-regress-separated-operator-ui` (HEAD `815826b`). Local Vitest passed; LAN `deploy-worker.sh` fails building `silverman-operator-ui` because `OperatorUiRuntimeConfig.envLabel` is `DeploymentEnvironment | ""` (empty for embedded mode). After the embedded early-return in `main.tsx`, TypeScript still types `config.envLabel` as including `""`, so `validateApiEnvironmentPairing` rejects the argument (`TS2345`).

Runtime behavior already rejects empty/invalid labels inside `resolveOperatorUiConfig` for separated mode; this is a type-narrowing + defensive fail-closed gap, not a pairing redesign.

## Goals / Non-Goals

**Goals:**

- Unblock production TypeScript build (`tsc -b` + `npm run build`).
- Call pairing only with a proven `DeploymentEnvironment`.
- Fail closed if label is empty after config ok (defensive).
- Keep US-093/094/095 / auth.session Vitest green.

**Non-Goals:**

- Redesign pairing, US-096, BL-035, publication flag changes.
- Discriminated-union refactor of the entire config type (optional follow-up; out of scope).
- Story-accepted claims from build/deploy alone.

## Decisions

1. **Narrow in `main.tsx` bootstrap (not change `validateApiEnvironmentPairing` signature)**  
   - After `deliveryMode === "embedded"` return, assign `const envLabel = config.envLabel` and reject unless `envLabel === "uat" || envLabel === "prod"` (or equivalent `normalizeDeploymentEnvironment`).  
   - Rationale: smallest fix at the call site; preserves shared config type used by embedded + separated; satisfies TS without casting.  
   - Alternatives considered: `as DeploymentEnvironment` (unsafe); discriminated union on `OperatorUiRuntimeConfig` (cleaner long-term, larger diff); change pairing to accept `""` (wrong).

2. **Fail-closed blocked screen for empty label**  
   - Reuse `ConfigBlockedScreen` / config-result shape with `reason: "invalid"` (or `"missing"`) naming `SILVERMAN_OPERATOR_UI_ENV_LABEL`.  
   - Rationale: matches existing US-093/094 fail-closed UX; no silent proceed.

3. **Tests**  
   - Prefer existing suites remaining green; add a focused unit/bootstrap test only if practical without heavy DOM bootstrap harness. Build + existing Vitest matrix is the primary gate.

## Risks / Trade-offs

- [Defensive branch never hit in normal config] → Acceptable; documents invariant and satisfies TypeScript control-flow.
- [Larger type refactor deferred] → Follow-up possible; not required to unblock deploy.

## Migration Plan

1. Implement narrowing + verify local `tsc`/`build`/Vitest.
2. Commit + push on same feature branch.
3. Redeploy on `192.168.0.194` with existing LAN prod pairing/CORS exports.
4. Confirm `/health` `deployment_environment` + `BUILD_REVISION`, UI `:8011`, pairing proceeds.
5. Update CURRENT-STATE / RUNTIME-STATE only for live evidence.

## Open Questions

- None for implementation. Operator Story acceptance for US-093–095 remains a separate gate after deploy evidence.
