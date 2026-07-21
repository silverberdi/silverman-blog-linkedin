# Warning and test quality baseline (US-067 / US-068 / BL-028)

**Scope:** Operator-facing **warning and test quality baseline** — run full suite(s), inventory warnings, separate inherited vs new, maintain zero new warnings attributable to a change (**BL-028 / US-067 + US-068**).
**Status:** Procedure **published**; baseline evidence: [us-067-us-068-warning-test-quality-baseline-2026-07-21.md](us-067-us-068-warning-test-quality-baseline-2026-07-21.md).
**Authority:** Complements engineering “zero new warnings” rule, [CURRENT-STATE.md](../CURRENT-STATE.md), [GLOSSARY.md](../GLOSSARY.md).
**OpenSpec:** capability `warning-and-test-quality-baseline` (change `establish-warning-test-quality-baseline-us-067-068`).

Does **not** establish CI (**BL-029**), mutate Flow A/B behavior, or mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

Audience: **system owner / maintainer** (stories use generic “content operator”).

---

## 1. Suites in scope

| Suite | How to run | Role |
|-------|------------|------|
| **pytest** (primary) | From repo root: `.venv/bin/python -m pytest -q -W default` | Worker / contract tests |
| **Vitest** (secondary) | `cd frontend/linkedin-variant-supervision-console && npm test` | Console UI |

Use a project `.venv` with `dev` extras (`pytest`). Do not invent alternate runners for the baseline.

---

## 2. Outcome vocabulary

| Term | Meaning |
|------|---------|
| **Inherited warning** | Documented in the dated baseline evidence; allowed until separately remediated |
| **New warning** | Appears in a change’s suite output and is **not** in the baseline (or is a new occurrence of a different message class) — **must fix or explicitly justify** before accepting the change |
| **Suite failure** | Test assertion/error (not a Python/pytest warning). Tracked separately from the warning baseline; green suite is preferred but failures are quality debt, not “warnings” |
| **Environment noise** | Warnings caused only by restricted runners (e.g. sandbox `PermissionError` on temp `.git` cleanup) — re-run unrestricted before updating the baseline |

---

## 3. US-067 — Run suite, inventory, fix cheap causes

1. Run full pytest with warnings visible (`-W default`).
2. Inventory: warning category, library/module, short message class (no secrets).
3. Correct root causes where **safe and cheap** (project code). Prefer fix over suppress.
4. Narrow `filterwarnings` only with an inline comment tied to a specific inherited third-party issue.
5. Record pass/fail/warning counts in dated evidence under `docs/operations/`.

---

## 4. US-068 — Inherited vs new; zero new warnings

**Standing rule:** A change MUST NOT introduce **new** warnings attributable to that change.

- Compare suite warning summary to the latest baseline evidence.
- Inherited entries may remain until a dedicated remediation (or dependency upgrade).
- New warnings block “done” for implementation quality (and later BL-029 CI).
- Updating the baseline requires an explicit operator/docs decision (usually after intentional remediation or dependency change), not silent expansion.

---

## 5. Current baseline (pointer)

See [us-067-us-068-warning-test-quality-baseline-2026-07-21.md](us-067-us-068-warning-test-quality-baseline-2026-07-21.md) for the 2026-07-21 snapshot (git `6bb4a90` at measurement; counts may move as HEAD advances).

**Inherited warnings (pytest):** one `StarletteDeprecationWarning` from FastAPI/Starlette `TestClient` / `httpx` (third-party).

**Known suite debt (not warnings):** pytest had **11 failed** tests at baseline time — listed in evidence as follow-ups; do not confuse with the warning inventory. Vitest was green (173 passed).

---

## 6. Related

- CI automation → **BL-029** (consumes this baseline).
- Engineering standards: zero new warnings attributable to your change.
