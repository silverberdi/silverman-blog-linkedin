## Context

`scripts/flow_a_readiness.py` Phase 0 verifies repository ancestry against `DEFAULT_EXPECTED_COMMITS` before worker OpenAPI and file-manifest checks. The script was introduced with slice-7 milestones (`79f5345`, `962ba2f`, `53708eb`). Context alignment change `align-project-context-and-current-state` intentionally froze executable defaults and recorded the mismatch in `docs/CURRENT-STATE.md` pending BL-026.

The repository has since validated Flow A core through calendar completion (`88cd5bc`), guarded Git publication (`96519c3`), and live-site confirmation (`9dba064`). `docs/CURRENT-STATE.md` now records last verified baseline `615091c` at `2026-07-11T07:45:00Z` — a docs/archive snapshot **after** `9dba064`, not a fourth readiness milestone. HEAD is ahead of all legacy defaults, so the old trio does not currently fail on `main`, but it no longer represents the operational floor operators expect and misleads documentation.

**Terminology guardrail:** `last_verified_baseline` (CURRENT-STATE, RUNTIME-STATE) and `DEFAULT_EXPECTED_COMMITS` (readiness script) serve different purposes. README correctly warns against treating any SHA as a permanent runtime requirement; readiness defaults instead assert “this checkout includes validated capability X” via ancestry checks.

Constraints:

- Preserve `--expected-commit` CLI override (non-breaking for operators using custom SHAs).
- Do not change Phase 0 gating, OpenAPI path list, file manifest, or worker/n8n probes.
- No live deploy or server mutation during apply.

## Goals / Non-Goals

**Goals:**

- Align `DEFAULT_EXPECTED_COMMITS` with documented post-slice-7 operational milestones.
- Keep ancestry semantics (`merge-base --is-ancestor`) unchanged.
- Document milestone meanings in script, deployment docs, and spec.
- Remove the CURRENT-STATE known-divergence entry after apply.

**Non-Goals:**

- Auto-reading baseline SHAs from `docs/CURRENT-STATE.md` at runtime (adds fragility).
- Replacing commit checks with tags or `BUILD_REVISION` comparison (different concern: deployed image vs checkout).
- Broad refactors of readiness reporting or new phases.

## Decisions

### D1: Replace slice-7 trio with three operational milestones

**Decision:** Set `DEFAULT_EXPECTED_COMMITS = ("88cd5bc", "96519c3", "9dba064")`.

| SHA | Rationale |
|-----|-----------|
| `88cd5bc` | Flow A calendar completion archived — operational validation floor for core lifecycle |
| `96519c3` | Guarded blog Git publication automation (US-001) |
| `9dba064` | Live-site confirmation and reconciliation (US-002) |

**Rationale:** These commits subsume slice-7 implementation (all are descendants of `53708eb` / `962ba2f`) while gating checkouts that predate validated post-Flow-A-core capabilities. Dropping `79f5345` removes a docs-only anchor with no behavioral signal. **`615091c` is intentionally excluded** — it is a post-validation OpenSpec archive/docs commit after `9dba064`; ancestry through `9dba064` already implies it on linear `main`, and adding docs-only SHAs would reintroduce brittle maintenance.

**Not included:** `615091c` (current `last_verified_baseline` in CURRENT-STATE) — tracked separately with timestamp; readiness defaults gate **capabilities**, not every subsequent docs sync.

**Alternatives considered:**

- **Keep old trio** — fails BL-026; perpetuates known divergence.
- **Single SHA (`88cd5bc` only)** — simpler but weaker signal for Git publication and live-site gates added after that baseline.
- **Runtime parse of CURRENT-STATE** — brittle regex maintenance; rejected.

### D2: Inline milestone documentation in script constant

**Decision:** Add a module-level comment block above `DEFAULT_EXPECTED_COMMITS` listing each SHA and meaning (mirrors archived deployment-readiness design table style).

**Rationale:** Future maintainers see why each SHA exists without opening OpenSpec archive.

### D3: Test updates only where defaults are asserted

**Decision:** Update `tests/test_flow_a_readiness.py` references to `DEFAULT_EXPECTED_COMMITS`; add one test that documents the three SHAs match spec milestones (constant equality or explicit tuple).

**Rationale:** Existing ancestry, OpenAPI, and stale-worker tests remain valid.

### D4: Documentation sync scope

**Decision:** Update `docs/deployment/ubuntu-server-worker-deployment.md` Phase 0 bullet for expected commits; trim README caveat that "defaults may lag" once aligned; remove CURRENT-STATE divergence row.

**Rationale:** Operators should not need CURRENT-STATE to discover correct defaults.

## Risks / Trade-offs

- **[Risk] Defaults drift again as new milestones land** → Mitigation: document in spec that dedicated readiness changes update defaults; CURRENT-STATE records `last_verified_baseline` with timestamp separately — do not conflate with `DEFAULT_EXPECTED_COMMITS`.
- **[Risk] Operators confuse readiness defaults with `last_verified_baseline`** → Mitigation: CURRENT-STATE note (task 4.2) and README wording clarify the distinction.
- **[Risk] Fork or old branch fails new defaults** → Mitigation: expected behavior — use `--expected-commit` override; failure message already lists missing SHAs.
- **[Risk] Cherry-picked partial history** → Mitigation: unchanged; ancestry check is intentionally strict; file manifest still catches missing modules.

## Migration Plan

1. Apply code change to `DEFAULT_EXPECTED_COMMITS` and comment block.
2. Update tests; run `pytest tests/test_flow_a_readiness.py`.
3. Update operator docs and `docs/CURRENT-STATE.md`.
4. Sync specs via `/opsx-sync` after implementation commit.
5. No server deploy required; operators on old checkouts see fail until pull or override.

**Rollback:** Revert commit restoring old trio; no data migration.

## Open Questions

_None — milestone set is anchored to CURRENT-STATE validated capabilities at proposal time._
