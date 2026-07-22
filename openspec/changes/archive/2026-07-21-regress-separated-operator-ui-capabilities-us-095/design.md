## Context

US-093 ships Silverman Authority Manager as a separated compose service on LAN `:8011` with runtime-injected `SILVERMAN_OPERATOR_UI_API_BASE_URL`, typed `SupervisionApiClient` absolute-base prefixing, CORS allowlist, and fail-closed config UX. US-094 adds bilateral UAT/prod pairing (`SILVERMAN_OPERATOR_UI_ENV_LABEL` ↔ worker `SILVERMAN_DEPLOYMENT_ENVIRONMENT` via `GET /health.deployment_environment`) with fail-closed mismatch blocks and env badge.

BL-032 control-center capabilities (schedule visibility, pending-supervision, postpone/reschedule, cancel, publish-now) and US-040D auth (injectable Bearer paste, session states, `canMutate`) were Story accepted on the historical embedded/same-origin path. **US-095** must prove those capabilities remain reachable on the **supported production path**: separated UI → worker HTTP—without rewriting screens, implementing Google login, or decommissioning the embedded console (US-096).

Stakeholders: content operator (day-to-day supervision still works), system owner (split did not regress the production console path). Constraints: build on US-093/US-094 hooks; prefer reuse of Vitest/pytest/smoke patterns; no new endpoints; no secrets in docs/tests; ADR-0001 unchanged; branch `feat/us-095-regress-separated-operator-ui` (or equivalent)—not `main`.

## Goals / Non-Goals

**Goals:**

- Define and satisfy a minimal credible **regression matrix** for separated-UI → worker via absolute `SILVERMAN_OPERATOR_UI_API_BASE_URL` (+ paired env labels when required).
- Prove schedule visibility (read) and BL-032 pending-supervision / control-center reads remain reachable via the typed client in separated mode.
- Prove at least one representative authenticated mutation path already Story accepted (prefer `dry_run: true` postpone/defer or equivalent gated action) uses the absolute base URL and respects `canMutate`.
- Prove US-040D session gating (sign-in / `canMutate` / clear session) still works without Google.
- Reaffirm US-093/US-094 fail-closed blocked UX remains operator-visible.
- Document evidence collection; update CURRENT-STATE / product docs only for demonstrated ACs.

**Non-Goals:**

- US-096 hard independence / removing embedded console routes.
- BL-035 Google/OIDC implementation.
- BL-029 full CI/UAT stand-up beyond regression needs.
- n8n Execute Command or workflow rewrites.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Re-packaging US-093 or redesigning US-094 pairing.
- Broad UI redesign or new business capabilities.
- Claiming public console exposure beyond BL-026.
- Mandatory re-execution of every historical Vitest file as a US-095 gate.

## Decisions

### D1 — Regression-first change (prove, don’t rebuild)

**Choice:** US-095 is an evidence and light harness change. Prefer extending/adding focused Vitest coverage and a short documented smoke checklist over application feature work. Fix only defects found by the matrix that block US-095 ACs; do not expand into US-096 or BL-035.

**Why:** Product intent is “day-to-day supervision is not regressed after the split,” not a capability rewrite.

**Alternatives considered:** Full UI E2E rewrite (out of scope); treat US-093/US-094 smoke alone as sufficient (does not cover BL-032 control-center + auth handoff ACs).

### D2 — Concrete regression matrix (normative for this change)

**Choice:** The following rows are the minimum credible matrix. Each row names evidence type. Automated Vitest is the default primary evidence; controlled local or LAN smoke is optional supplement where browser CORS/topology matters.

| # | Capability under test | Separated-mode expectation | Primary evidence | Notes |
|---|----------------------|----------------------------|------------------|-------|
| R1 | Absolute base URL join | `SupervisionApiClient` / `joinApiUrl` prefixes worker paths with configured absolute origin; **no** relative same-origin fallback when separated config is valid | Vitest (extend `us093.operator-ui-config` or focused `us095.*`) | Already partially covered by US-093; US-095 must keep coverage green and cite it |
| R2 | Schedule visibility (read) | Authenticated `getScheduleVisibility` issues `GET {apiBaseUrl}/flow-a/schedule-visibility?...` | Vitest client mock asserting absolute URL | BL-032 / US-040 visibility baseline |
| R3 | Pending-supervision / control-center read | Authenticated `getPendingSupervision` issues `GET {apiBaseUrl}/flow-a/linkedin-variants/pending-supervision` | Vitest client mock asserting absolute URL | BL-032 control-center data path |
| R4 | Representative mutation (dry-run-safe) | With `canMutate` true, `deferVariant` (postpone/reschedule) with `dry_run: true` posts to `{apiBaseUrl}` + existing defer path (no new endpoint) | Vitest client mock asserting absolute URL + dry_run body | Prefer dry-run; do **not** require live LinkedIn publish; do **not** flip publication enablement |
| R5 | Auth session gating (US-040D) | Sign-in sets credential; `canMutate` true when authenticated for mutations; clear session returns to non-mutating / anonymous (or equivalent) without Google | Vitest (`auth.session` +/or focused `us095` shell/client) | Preserve injectable `AuthProvider` boundary for BL-035 |
| R6 | Config fail-closed (US-093) | Missing/invalid API base URL → `ConfigBlockedScreen` (or equivalent); no relative API traffic | Vitest (existing `us093` suite remains green) | Verify hold |
| R7 | Pairing fail-closed (US-094) | Mismatch / missing label / unreadable health → blocked; no authenticated supervision/mutation | Vitest (existing `us094` suite remains green) | Verify hold; no redesign |
| R8 | Operator-visible outcome | Successful paired separated path can load console chrome (env badge when paired) and surface schedule/control-center data or empty states understandably; blocked states remain clear | Vitest render assertions and/or controlled local/LAN smoke checklist | Smoke optional if Vitest covers visibility; document either way |
| R9 | Non-regression invariants | No n8n Execute Command introduced; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` not mutated by this change; no Flow/LinkedIn business rewrites | Diff review + checklist in tasks | Document in CURRENT-STATE / product updates |

**Optional LAN smoke (documented, not a public-exposure claim):** With UI `:8011` paired to worker `:8010`, operator pastes Bearer, opens schedule/pending views, runs one dry-run postpone if safe fixtures exist. Record pass/fail in apply notes; do not claim BL-026 public exposure or Story accepted without operator gate.

**Why:** Maps 1:1 to US-095 ACs while staying smaller than “run the entire console suite.”

**Alternatives considered:** Only document manual smoke (weaker CI signal); require real publish-now against live LinkedIn (unsafe / enablement-coupled); invent new regression HTTP endpoints (unnecessary).

### D3 — Prefer client-level absolute-URL proofs for reads/mutations

**Choice:** Primary automated proofs for R2–R4 mock `fetch` and assert the **full absolute URL** (and dry_run body for R4) when `apiBaseUrl` is set to a worker origin (e.g. `http://192.168.0.194:8010`). Component-level BL-032 suites remain valuable regression signal but are not all mandatory US-095 gates if client absolute-URL + auth gating coverage is solid.

**Why:** Separated-mode risk is wrong origin / relative fallback—not re-proving every EventModal eligibility rule already Story accepted under BL-032.

**Alternatives considered:** Mandate full Playwright against LAN (heavier; optional smoke only); duplicate all `us084`/`us085`/`us086` suites under `us095` (scope creep).

### D4 — Auth handoff = preserve injectable boundary, not implement Google

**Choice:** Demonstrate that `MemoryBearerAuthProvider` (or current paste provider) + `SupervisionApiClient.canMutate()` + clear-session still gate mutations on the separated bootstrap path. Do **not** add OIDC, Google buttons, cookies, or BFF. Spec language: “compatible with future Google login (BL-035)” means the auth provider remains swappable without rewriting business screens—same US-040D contract.

**Why:** Matches US-095 AC literally and keeps BL-035 out of scope.

### D5 — Evidence collection and honesty gates

**Choice:**

| Evidence | When it counts |
|----------|----------------|
| Targeted Vitest for R1–R7 (and R8 where render-assertable) | Required for implementation-complete local demonstration |
| Optional controlled local/LAN smoke checklist | Encouraged when CORS/topology doubt remains; record results without claiming public exposure |
| CURRENT-STATE | Update to note US-095 regression evidence (local and/or LAN) without claiming Story accepted or live deploy unless true |
| Product docs (`user-stories` / `progress-checklist` / backlog status line) | Check ACs only when demonstrated; leave Story accepted unchecked until operator gate |
| RUNTIME-STATE | Update only if live flags/topology change during optional LAN smoke apply |

**Why:** Aligns with project “demonstrated ≠ Story accepted” discipline.

### D6 — Unchanged boundaries

**Choice:** n8n → `:8010` HTTP only; UI never an n8n target; no mutation of `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; no Flow/LinkedIn business rewrites; embedded console retained until US-096; US-093 packaging and US-094 pairing semantics verified, not redesigned.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Matrix too thin → false confidence | Require R1–R9 explicitly in specs/tasks; include both read classes + one mutation + auth + fail-closed holds |
| Matrix too fat → delays US-096 | Cap mandatory suites; optional smoke; do not re-gate every BL-032 Vitest file |
| Dry-run mutation still mutates unexpected state | Assert `dry_run: true` in client test; prefer mock fetch; LAN smoke only with operator awareness |
| Claiming LAN smoke as public readiness | Specs/docs forbid public-exposure claims beyond BL-026 |
| US-094 not yet synced to canonical specs | US-095 pairing delta ADDs “verify hold” language; apply assumes US-094 local implementation present |
| Fixing unrelated console bugs mid-regression | Only fix blockers for matrix rows; park neighbors as follow-ups |

## Migration Plan

1. Branch `feat/us-095-regress-separated-operator-ui` from integration base that includes US-093 + US-094 (not `main`).
2. Add focused Vitest (`us095.*` and/or targeted extensions) for matrix R1–R5; keep `us093`/`us094`/`auth.session` green for R5–R7.
3. Optionally run documented local/LAN smoke for R8 topology confidence.
4. Confirm R9 invariants via diff review.
5. Update CURRENT-STATE + product docs for demonstrated ACs only.
6. Rollback: remove US-095 test harness / doc notes; no deploy topology change required if smoke was local-only.

## Open Questions

1. Whether optional LAN smoke is required for operator Story acceptance vs local Vitest-only demonstration — leave Story-accepted gate to the operator; implementation can complete on Vitest + checklist.
2. Exact dry-run mutation fixture identity for optional LAN smoke — choose a non-live pending/queued variant at apply time; skip real publish-now.
