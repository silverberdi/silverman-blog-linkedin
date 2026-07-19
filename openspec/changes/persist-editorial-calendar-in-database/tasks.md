## 1. Product + ADR scaffolding

- [x] 1.1 Add proposed **BL-031** / **US-041** entries to `docs/product/backlog.md`, `docs/product/user-stories.md`, and `docs/product/progress-checklist.md` (open / not validated).
- [x] 1.2 Draft ADR accepting Postgres database **`silverman_linkedin_db`** as master editorial calendar SoT (assign next ADR number; link from CURRENT-STATE when implemented).

## 2. Dependencies and configuration

- [x] 2.1 Add Postgres driver + migration tooling to project dependencies (`pyproject.toml` / lock as applicable).
- [x] 2.2 Add settings for calendar DB URL (env-only) targeting **`silverman_linkedin_db`**; document variable names in deploy docs without secrets.
- [x] 2.3 On stack Postgres: create database **`silverman_linkedin_db`** (+ dedicated role/grants); wire compose/env so the worker reaches it on `local-ai-stack_backend`.

## 3. Schema and persistence adapter

- [x] 3.1 Create migration **inside `silverman_linkedin_db`** for `editorial_calendar` + `editorial_calendar_items` (or approved equivalent from design).
- [x] 3.2 Implement DB-backed `load_calendar` / `save_calendar_atomic` with validation + `row_version` concurrency.
- [x] 3.3 Remove filesystem `calendar.json` as authoritative path from calendar callers after adapter cutover.
- [x] 3.4 Implement operator-gated import-from-`calendar.json` (CLI/module; refuse clobber when DB non-empty).

## 4. HTTP and health integration

- [x] 4.1 Ensure plan-due, status, update-item-schedule, schedule-visibility, pending-supervision, and calendar execute paths use DB loader/saver only.
- [x] 4.2 Add secret-safe calendar store readiness signal (`calendar_store_ready` or status fields); fail closed on DB errors without file fallback.
- [x] 4.3 Keep `editorial-calendar/` directory compatibility for folder health if still required; do not require `calendar.json` for SoT.

## 5. Backup policy alignment

- [x] 5.1 Update `docs/operations/editorial-backup-scope-retention-integrity.md` so calendar SoT is DB/stack backup, not `calendar.json` in filesystem packages.
- [x] 5.2 Adjust backup verifier expectations/tests if they asserted `editorial-calendar/` as required SoT content.

## 6. Tests

- [x] 6.1 Unit/integration tests: save/load round-trip, validation reject, concurrent-update, import empty/non-empty, DB-down fail-closed.
- [x] 6.2 Update existing calendar/plan/schedule-update/schedule-visibility tests to use DB fixture (no reliance on authoritative `calendar.json`).
- [x] 6.3 Run targeted pytest for touched modules; fix warnings introduced by this change.

## 7. Docs honesty and business validation gate

- [x] 7.1 Update `docs/CURRENT-STATE.md` (and `RUNTIME-STATE.md` if live DB flags/URL shape change) — implemented ≠ operator-validated.
- [x] 7.2 Operator checklist: create/migrate **`silverman_linkedin_db`** on server, configure URL, import if a JSON copy exists, verify status/plan/console schedule-visibility.
- [ ] 7.3 Mark US-041 / checklist only after acceptance criteria are demonstrated; do not claim wiped historical rows restored.
