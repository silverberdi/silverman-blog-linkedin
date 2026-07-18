# BL-012 / US-031 + US-032 — operator acceptance (2026-07-18)

Operator acceptance of **Consolidate Recovery for Incomplete Campaigns**
against automated fixture evidence, with worker endpoints deployed.

## Status

- **US-031** and **US-032** acceptance criteria **validated** and stories
  **accepted** 2026-07-18 (fixture evidence + operator review of recovery
  contract).
- **BL-012 closed 2026-07-18.**
- Worker deployed on `192.168.0.194` at `BUILD_REVISION=018aa36` (2026-07-18)
  with OpenAPI paths for inspect/resume/repair/cancel present; auth fail-closed
  (401 without Bearer).
- Live mutation of production incomplete campaigns was **not** required for
  this acceptance (fixtures cover resume short-circuits, repair allowlist,
  cancel gating, attempt ledger). Controlled live recovery remains operator-driven.

## Evidence

| Artifact | Role |
|----------|------|
| [flow-a-incomplete-campaign-recovery.md](flow-a-incomplete-campaign-recovery.md) | Operator contract |
| `tests/test_flow_a_incomplete_campaign_recovery.py` | Automated fixtures |
| Canonical specs | `openspec/specs/` incomplete-campaign recovery capability |
| Deploy | `192.168.0.194:8010`, `BUILD_REVISION=018aa36d041d20d9ca2ae9fa42c4b8cc87f7e8c9` |

**Pytest (acceptance re-run):** suite included in 2026-07-18T14:45Z batch —
`test_flow_a_incomplete_campaign_recovery` passed within 75-test BL-012/013/014
batch.

**Live deploy probes (non-mutating):**

- `GET /health` → HTTP 200
- OpenAPI exposes all four recovery paths
- Unauthenticated inspect → HTTP 401
- Backup restore/integrity modules importable in the deployed worker image
- Container `BUILD_REVISION=018aa36d041d20d9ca2ae9fa42c4b8cc87f7e8c9` (from deploy)

## US-031 acceptance walkthrough

| Criterion | Evidence |
|-----------|----------|
| Identify last valid stage | Inspect derives `last_valid_stage` from durable milestones |
| Resume without repeating successful work | Resume short-circuits / stage catch-up fixtures |
| Repair inconsistent metadata | Allowlisted repair paths + fail-closed non-allowlist |
| Outcome visible/understandable | Contract + structured JSON outcomes |
| Failures/blocked clearly communicated | Stable reason codes / classifications |
| Existing work not duplicated/changed | Inspect read-only; dry-run; no invented stage success |

## US-032 acceptance walkthrough

| Criterion | Evidence |
|-----------|----------|
| Classify recovery actions | `recommended_recovery_action` taxonomy |
| Preserve attempt history | Durable `flow_a_recovery.attempts` ledger fixtures |
| Safe cancellation | Cancel + post-cancel resume/repair gating |
| Outcome visible/understandable | Contract + secret-safe reports |
| Failures/blocked clearly communicated | Cancel/history reason codes |
| Existing work not duplicated/changed | Cancel does not rewrite confirmed stage evidence |

## Explicit non-claims

- Not LinkedIn API publication recovery (BL-008).
- Not Git push / Pages deploy / production n8n activation changes.
- Not a claim that every historical incomplete campaign was live-resumed.
