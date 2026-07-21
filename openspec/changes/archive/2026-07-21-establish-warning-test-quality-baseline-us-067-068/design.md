## Context

P7 **BL-028** asks for a known baseline of test-suite warnings and code-quality signals so the team can identify whether a change introduces new quality problems. Stories **US-067** (run full suite, inventory, fix cheap root causes) and **US-068** (separate inherited vs new, document baseline, maintain zero new warnings) close together.

Audience is the **system owner / maintainer** (stories say “content operator” generically). This is engineering hygiene, not Flow A/B product work.

## Goals / Non-Goals

**Goals:**
- One operator SoT describing how to run suites and classify warnings.
- One dated baseline evidence file from a real full-suite run.
- Explicit vocabulary: inherited (documented baseline) vs new (must fix or justify before Story/CI gate).
- Close BL-028 when both stories accepted.

**Non-Goals:**
- Establishing GitHub Actions / CI (BL-029).
- Fixing every historical third-party warning if costly — document as inherited instead.
- Worker behavior, LinkedIn enablement, deploy, or secret rotation.
- Broad lint/ruff/mypy platform (unless already present and cheap to include in inventory).

## Decisions

1. **Suites in scope:** primary = `pytest` via `.venv`; secondary = frontend Vitest (`frontend/linkedin-variant-supervision-console`) when present — record both in baseline.
2. **SoT path:** `docs/operations/warning-and-test-quality-baseline.md`.
3. **Evidence:** dated file under `docs/operations/` (counts + warning categories; no secrets).
4. **Zero new warnings:** attributable to the change under review — inherited baseline entries are allowed until separately remediated.
5. **Filters:** prefer root-cause fixes; narrow `filterwarnings` only with inline comment tied to a specific inherited issue.

## Risks / Trade-offs

- Full suite runtime may be long; baseline is a snapshot, not continuous monitoring (CI is BL-029).
- Over-filtering hides real regressions — keep suppressions narrow.

## Migration Plan

N/A — docs + one-time baseline run. No runtime migration.

## Open Questions

None blocking — proceed with docs + suite inventory.
