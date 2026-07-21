## Context

BL-028 / US-067+068 established a warning and test quality baseline that recorded **11 pytest failures** and **1 inherited** `StarletteDeprecationWarning`. **US-090 / BL-033** clears that debt before BL-029 CI.

## Goals / Non-Goals

**Goals:**
- Green full pytest: 0 failed, 0 warnings (unrestricted runner).
- Clear inherited Starlette TestClient/`httpx` deprecation via root-cause path (`httpx2` or equivalent).
- Refresh baseline evidence; close US-090 / BL-033.
- Vitest remains green.

**Non-Goals:**
- Establishing CI (BL-029).
- Broad `filterwarnings` as the sole “fix” for W1.
- Weakening assertions to hide real regressions.
- LinkedIn enablement mutation.

## Decisions

1. **Markdown-only connector tests:** Stale calendar seed (JSON-only). Fix `_write_calendar` to use `write_and_seed_calendar` (same as sibling Flow A execute tests). No production connector change required for that class.
2. **Compose tests:** Update expected editorial mount to current durable worker data path; tighten `postgres:` forbidden marker so commented calendar URL hostnames do not false-positive.
3. **Editorial canon:** Restore/encode the normative phrase that Flow B content MUST NOT enter Flow A automatic publish paths (align `#flow-a-vs-flow-b` with editorial-canon spec).
4. **Console static contract:** Update assertions to current US-083 preview/real copy baked into Vite static assets (not obsolete “validated (dry-run, no mutation)” strings).
5. **Starlette warning:** Add `httpx2` to dev dependencies and install so FastAPI/Starlette TestClient stops emitting the deprecation.

## Risks / Trade-offs

- `httpx2` is a new package; pin a known version and verify TestClient still works across the suite.
- Canon phrase restore must not contradict simplified Flow B policy (unapproved pending-approval guardrail remains).

## Migration Plan

N/A for runtime. Update baseline evidence after green suite.

## Open Questions

None blocking.
