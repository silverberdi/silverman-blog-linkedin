## Context

US-093 (archived) shipped Silverman Authority Manager as a separated compose service on LAN `:8011` with runtime-injected `SILVERMAN_OPERATOR_UI_API_BASE_URL`, reserved `SILVERMAN_OPERATOR_UI_ENV_LABEL`, worker CORS allowlist, and fail-closed UI when the base URL is missing/invalid. Pairing enforcement was explicitly deferred.

Today a single LAN stack at `192.168.0.194` is the live topology. BL-029 has not stood up a second physical UAT stack, but US-094 still requires **declared** UAT vs prod pairing defaults and **fail-closed** disagreement—so a mis-set base URL cannot silently drive writes at the wrong environment once (or if) both stacks exist.

Stakeholders: system owner (environment separation), content operator (visible env + clear blocks). Constraints: build on US-093 hooks; prefer deploy-time/runtime non-secret config; no secrets in docs/assets/responses; ADR-0001 unchanged; no Google login; no LinkedIn/Flow rewrites; branch `feat/us-094-pair-operator-ui-api-environments` (or equivalent)—not `main`.

## Goals / Non-Goals

**Goals:**

- Declare a closed set of deployment environments (`uat` | `prod`) on both UI and worker via non-secret env config.
- Provide UAT and prod deploy defaults so each UI profile points at the matching API by default.
- Validate agreement at separated-UI startup (UI label ↔ API-advertised environment) and fail closed on mismatch/missing/unreadable pairing identity.
- Show the active environment to the operator; keep blocked states clear (env var names only).
- Document pairing topology in CURRENT-STATE / RUNTIME-STATE / ubuntu deploy docs when live.

**Non-Goals:**

- Standing up a full second UAT host, CI gates, or BL-029 automation beyond pairing config/docs.
- US-095 full regression program.
- BL-035 Google/OIDC; mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Baking environment hosts into hashed JS; public console exposure beyond BL-026.
- n8n Execute Command or workflow rewrites.

## Decisions

### D1 — Closed environment vocabulary: `uat` | `prod`

**Choice:** Canonical non-secret tokens are exactly `uat` and `prod` (case-normalized to lowercase). No third `lan` token in the pairing contract—current single LAN stack MUST still declare one of `uat` or `prod` consistently on UI and API until a second stack exists.

**Why:** Matches US-094 ACs literally; avoids a soft “lan” escape that weakens cross-environment fail-closed semantics.

**Alternatives considered:** Optional `lan` / `dev` labels (weaker AC alignment); free-form strings (harder to validate and document).

### D2 — Bilateral identity: UI label + worker `SILVERMAN_DEPLOYMENT_ENVIRONMENT`

**Choice:**

| Side | Env var | Values |
|------|---------|--------|
| Worker | `SILVERMAN_DEPLOYMENT_ENVIRONMENT` | `uat` \| `prod` (required for pairing-capable separated-UI deploys) |
| UI | `SILVERMAN_OPERATOR_UI_ENV_LABEL` | same closed set (required in separated-UI mode) |

Worker advertises the value on existing **`GET /health`** as a non-secret JSON field `deployment_environment` (additive; n8n branching MUST remain compatible—extra field is fine). UI, after US-093 base-URL validation, performs an unauthenticated `GET {apiBaseUrl}/health`, reads `deployment_environment`, and compares to its env label.

**Fail closed when:**

- Separated mode and UI env label missing/empty/not in `{uat,prod}`
- Health unreachable, non-JSON, or missing/invalid `deployment_environment`
- UI label ≠ API `deployment_environment`

In any blocked pairing state the console MUST NOT proceed with authenticated supervision reads or mutations (no silent cross-environment writes). US-093 base-URL fail-closed remains first; pairing is the next gate.

**Why:** “Environments disagree” requires both sides to declare identity; health is already public/read-only and suitable for a non-secret label. Runtime config.js injection (US-093) keeps hosts and labels out of hashed bundles.

**Alternatives considered:**

| Alternative | Why not |
|-------------|---------|
| URL allowlist-only (no API identity) | Cannot detect “UI thinks UAT but pointed at prod host that still answers” without a host inventory; weaker |
| New dedicated `/operator-ui/environment` route | Extra surface; health already fits |
| Build-time `VITE_*` env baking | Couples image tags to environments; conflicts with “prefer runtime config” |
| Cookie/session env | Out of scope; Bearer paste auth unchanged |

### D3 — Per-environment deploy defaults (overlays), not a live second stack

**Choice:** Ship documented env example overlays (or clearly separated sections) in `deploy/server/`:

- **UAT profile defaults:** `SILVERMAN_DEPLOYMENT_ENVIRONMENT=uat`, `SILVERMAN_OPERATOR_UI_ENV_LABEL=uat`, `SILVERMAN_OPERATOR_UI_API_BASE_URL=<UAT worker placeholder>`, CORS origin for the UAT UI origin placeholder.
- **Prod profile defaults:** same pattern with `prod` and prod placeholders.

Compose continues to inject UI config at container start (existing `config.js` path). Operators select the profile for the stack they are deploying. US-094 does **not** require both stacks to be live on LAN for Story implementation evidence—unit/integration tests + documented defaults suffice; live RUNTIME-STATE update when an operator actually applies pairing on a deployed stack.

**Why:** Satisfies “configured to call … by default” without expanding into BL-029 stand-up.

### D4 — Operator visibility

**Choice:** When pairing succeeds, show a persistent non-secret environment indicator (e.g. “UAT” / “Prod”) in console chrome. When pairing fails, reuse/extend `ConfigBlockedScreen` (or equivalent) with clear copy naming the env var keys and that UI/API environments disagree—never secret values or full bearer tokens.

Embedded compatibility mode: pairing enforcement **not** required (same-origin worker); optional display may remain unset.

### D5 — Docs / CURRENT-STATE / RUNTIME-STATE

**Choice:** Update ubuntu deploy guide + CURRENT-STATE topology to describe UAT vs prod pairing model and env var names. Update RUNTIME-STATE only when live flags/topology for a deployed stack change (per project-runtime-context-maintenance). Do not claim public console exposure or that BL-029 UAT is fully stood up.

### D6 — Unchanged boundaries

**Choice:** n8n → `:8010` HTTP only; UI never an n8n target; no mutation of `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; no Flow/LinkedIn business rewrites; US-040D auth boundary preserved for BL-035 later.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Health field breaks naive clients that reject unknown keys | Additive JSON field; document; n8n typically ignores extras |
| Operator leaves worker env unset after upgrade → UI blocked | Fail closed intentionally; deploy docs + env examples make the var required beside UI label; migration notes in tasks |
| Single LAN host labeled `prod` while docs also mention UAT | Document that labels are stack identity, not “this machine is public prod”; second stack gets `uat` when BL-029 stands it up |
| Pairing GET /health fails due to CORS | Health must be included in CORS-allowed methods/headers for allowlisted UI origins (verify US-093 CORS covers GET /health; extend if needed) |
| False sense that UAT stack exists | Specs/docs state overlays ≠ live UAT stand-up (BL-029) |
| Silent relative fallback after pairing fail | Same as US-093: blocked state must not call API via relative paths |

## Migration Plan

1. Implement on `feat/us-094-pair-operator-ui-api-environments` from current integration base (not `main`).
2. Add worker `SILVERMAN_DEPLOYMENT_ENVIRONMENT` validation + `deployment_environment` on `GET /health`; pytest.
3. Require UI `SILVERMAN_OPERATOR_UI_ENV_LABEL` in separated mode; pairing check after base-URL OK; blocked UX + env badge; Vitest.
4. Add UAT/prod env example overlays; update compose/env docs; ensure CORS still allows health from UI origin.
5. Smoke: matching pair loads; forced mismatch blocks mutations; core HTTP path still works when paired.
6. Docs: CURRENT-STATE topology; RUNTIME-STATE when live deploy applies pairing.
7. Rollback: unset new worker field only if UI also rolled back; or set matching labels on both sides. Prior US-093 base-URL fail-closed remains.

## Open Questions

1. Which label to assign the current single LAN stack (`prod` recommended as the live authority stack; `uat` reserved for the future second stack)—confirm at apply/deploy time; does not block proposal.
2. Exact chrome placement for the env badge—implementer choice within existing Authority Manager header patterns.
