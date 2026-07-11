## Why

`scripts/flow_a_readiness.py` still defaults Phase 0 `expected_commits` to the Flow A slice-7 trio (`79f5345`, `962ba2f`, `53708eb`). That baseline predates post-slice-7 operational validation (calendar completion, guarded Git publication, live-site confirmation) and is recorded as a known divergence in `docs/CURRENT-STATE.md`. Operators and docs therefore reference obsolete revision assumptions while the repository has moved on — last verified baseline `615091c` at `2026-07-11T07:45:00Z` per `docs/CURRENT-STATE.md` (point-in-time snapshot, not a permanent runtime requirement). The readiness defaults are a separate concern from `last_verified_baseline`; they must gate the operational capability floor, not mirror every docs-only archive commit. Stale defaults create misleading readiness signals and maintenance debt (BL-026, US-061–US-063).

## What Changes

- Replace stale `DEFAULT_EXPECTED_COMMITS` in `scripts/flow_a_readiness.py` with a current operational readiness floor anchored to documented milestones (not the slice-7-only trio).
- Update automated tests for the new defaults and preserve `--expected-commit` CLI override behavior.
- Sync canonical spec default-commit scenario in `flow-a-deployment-readiness-and-smoke-test`.
- Update operator documentation (`README.md`, `docs/deployment/ubuntu-server-worker-deployment.md`) to describe the new baseline and override path.
- Remove the known-divergence row from `docs/CURRENT-STATE.md` once defaults align.
- Adjust `repository-context-governance` delta so the prior “do not change readiness defaults” guard is superseded by this dedicated follow-up change.

## Goals

- Readiness defaults reflect the current operational capability floor without requiring operators to pass `--expected-commit` on every run.
- Phase 0 file manifest, OpenAPI, workflow, and worker checks remain unchanged.
- Milestone commit meanings are documented for future maintainers.
- Documentation distinguishes `last_verified_baseline` (`615091c`, timestamped in CURRENT-STATE) from `DEFAULT_EXPECTED_COMMITS` (capability milestones — not the same as “permanent expected commit” language in README).

## Non-Goals

- Changing Phase 0–4 gating logic, OpenAPI path requirements, or worker smoke scripts.
- Activating n8n, deploying workers, or live operational validation on the Ubuntu server.
- Eliminating commit ancestry checks entirely (override remains for forks and bisect).
- Updating `docs/product/progress-checklist.md` or user-story checkboxes (deferred until post-apply demonstration).

## Capabilities

### New Capabilities

_None — this change corrects defaults within an existing capability._

### Modified Capabilities

- `flow-a-deployment-readiness-and-smoke-test`: Update the default expected-commit ancestry scenario and document the new baseline milestones.
- `repository-context-governance`: Supersede the interim rule that froze `scripts/flow_a_readiness.py` executable defaults; record that stale defaults are resolved by this change.

## Impact

| Area | Effect |
|------|--------|
| `scripts/flow_a_readiness.py` | `DEFAULT_EXPECTED_COMMITS` and inline documentation |
| `tests/test_flow_a_readiness.py` | Assertions on default commit list |
| `openspec/specs/flow-a-deployment-readiness-and-smoke-test/spec.md` | Default commit scenario (via sync after apply) |
| `openspec/specs/repository-context-governance/spec.md` | Divergence/freeze scenario (via sync after apply) |
| `docs/CURRENT-STATE.md` | Remove known divergence row |
| `docs/deployment/ubuntu-server-worker-deployment.md` | Phase 0 expected-commit documentation |
| `README.md` | Remove “defaults may lag” caveat where superseded |

**Backlog:** BL-026 (P7). **User stories:** US-061 (identify/replace stale revisions), US-062 (avoid false failures, preserve checks), US-063 (document new baseline). **Excluded until validation:** progress-checklist and user-story checkbox updates.
