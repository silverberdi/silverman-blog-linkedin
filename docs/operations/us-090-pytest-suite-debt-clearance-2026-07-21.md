# US-090 / BL-033 pytest suite debt and inherited warning clearance — evidence 2026-07-21

**BANNER — no secrets in this file.**

**Normative procedure (baseline rules):** [warning-and-test-quality-baseline.md](warning-and-test-quality-baseline.md).
**Prior baseline (historical debt):** [us-067-us-068-warning-test-quality-baseline-2026-07-21.md](us-067-us-068-warning-test-quality-baseline-2026-07-21.md).

| Field | Value |
|-------|-------|
| Clearance date (UTC) | `2026-07-21` |
| Scope | BL-033 / US-090 |
| Overall outcome | **cleared** — full pytest **1415 passed**, **0 failed**, **0 warnings**; Vitest **173 passed** |
| Story accepted | operator-accepted 2026-07-21; **BL-033 closed** |

## Remediation summary

| Debt | Fix |
|------|-----|
| 7× markdown-only connector tests | Seed calendar via `write_and_seed_calendar` (store-backed) |
| Compose editorial mount | Expect durable worker data path |
| Compose `postgres:` false positive | Forbid service-definition shapes, not JDBC hostname substrings |
| Editorial `#flow-a-vs-flow-b` phrase | Restored normative “Flow B content MUST NOT enter Flow A automatic publish paths” |
| Console static dry-run copy | Assert current US-083 “Preview only (dry-run)” / Saved / Make real change copy |
| Inherited W1 StarletteDeprecationWarning | Added `httpx2` to `pyproject.toml` `[project.optional-dependencies] dev` |

## Commands (post-fix)

```text
.venv/bin/python -m pytest -q -W default   # 1415 passed, 0 warnings
cd frontend/linkedin-variant-supervision-console && npm test   # 173 passed
```

## Operator attestation

| Statement | Yes / No |
|-----------|----------|
| Zero failed pytest | Yes |
| Zero pytest warnings (unrestricted) | Yes |
| Vitest green | Yes |
| No broad global filterwarnings as sole W1 fix | Yes |
| BL-029 CI not established by this change | Yes |
