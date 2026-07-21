## Context

BL-030 asks the system owner to keep business/technical/operational documentation aligned with reality. Stories US-071 (update CURRENT/RUNTIME), US-072 (detect contradictions; historical ≠ current), US-073 (Cursor ↔ repo guidance) close together. Operator chose depth-C audit + live RUNTIME-STATE refresh; BL-029 stays open.

## Goals / Non-Goals

**Goals:**
- Normative maintenance SoT.
- Depth-C audit evidence + remediation of high/medium drifts.
- Live RUNTIME-STATE snapshot (secret-safe).
- Close BL-030.

**Non-Goals:**
- BL-029 CI / GitFlow / branch protection.
- Full rewrite of every historical ops evidence file.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or redeploying the worker.

## Decisions

1. **SoT path:** `docs/operations/project-runtime-context-maintenance.md`.
2. **RUNTIME-STATE:** Keep volatile and lean; refresh `verified_at_utc` + live facts; move long narrative of closed BLs to CURRENT-STATE / evidence — do not grow RUNTIME into a second CURRENT-STATE.
3. **Historical:** All `docs/context/*` get Historical bootstrap banners where missing; bodies softened when they still sound current.
4. **Ops status headers:** Patch clear “not accepted / remains open” lines that contradict Story accepted — not every paragraph of old evidence.
5. **Cursor rules:** Verify they link CONTEXT-AUTHORITY / CURRENT-STATE / GLOSSARY and do not embed volatile inventories; edit only if misaligned.

## Risks / Trade-offs

- Depth-C remediations touch many files; keep diffs factual/status-only.
- Live snapshot can go stale again the next day — SoT must define refresh triggers.

## Migration Plan

N/A runtime. Docs-only apply.

## Open Questions

None — proceed.
