## 1. Operator policy artifact (US-036)

- [x] 1.1 Create `docs/operations/editorial-backup-scope-retention-integrity.md` covering: purpose (BL-014 / US-036 only), included scope inventory, exclusions (secrets, public checkout, stack, recursive backups), package layout under `metadata/backups/<backup_id>/`, retention (7 most recent; never auto-delete fail/blocked), integrity verification (`pass`/`fail`/`blocked`, reason codes), secret-safe reporting rules, operator visibility of outcomes, and explicit US-037 boundary (restore drills + recovery procedure out of scope).
- [x] 1.2 Add a short GLOSSARY pointer distinguishing **editorial backup integrity (US-036)** from **restoration / recovery procedure (US-037)** without claiming BL-014 complete.
- [x] 1.3 Cross-link the policy from CURRENT-STATE (when status is updated) and product story US-036 references as needed; do not mark acceptance checkboxes done in this task.

## 2. Integrity verifier module and CLI

- [x] 2.1 Add a Python module under `src/silverman_blog_linkedin/` (e.g. `editorial_backup_integrity.py`) implementing manifest schema constants, scope include/exclude lists, path-safety checks, and `verify_editorial_backup(...)` returning structured `status` / `reason_codes` / secret-safe summaries.
- [x] 2.2 Implement optional copy-out package builder that writes only under `metadata/backups/<backup_id>/` (manifest + content), excludes excluded classes, and does not mutate source editorial trees.
- [x] 2.3 Implement retention prune helper that only removes eligible packages under `metadata/backups/`, keeps fail/blocked packages, and never touches source editorial trees.
- [x] 2.4 Add a `scripts/` CLI (or `python -m` entry) for `verify` (required) and optionally `create` / `prune` — no new FastAPI routes; no n8n Execute Command.

## 3. Automated tests

- [x] 3.1 Add fixture-based tests for integrity `pass`, hash mismatch `fail`, missing package `blocked`, path-traversal `fail`, and secret-safe result shape (no content bodies / tokens).
- [x] 3.2 Add tests that optional builder (if present) writes only under `metadata/backups/` and leaves source fixture trees unchanged; retention prune does not delete fail/blocked packages or paths outside backups.
- [x] 3.3 Add a lightweight policy presence test that the operator doc exists and contains required scope/retention/integrity/US-037-boundary phrases.
- [x] 3.4 Run targeted pytest for the new suite; do not weaken assertions; no real external API calls.

## 4. worker-foundation clarification (docs/spec alignment only)

- [x] 4.1 Ensure implementation/docs align with the delta that `metadata/backups` is the editorial backup package root without changing `GET /health` into backup create/verify/prune/restore behavior.
- [x] 4.2 Do not expand this change into unrelated folder-list drift fixes unless a compile/test break forces a minimal comment-only clarification.

## 5. Status and product progress (after ACs demonstrated — leave open)

- [x] 5.1 Update `docs/CURRENT-STATE.md` to record US-036 as implemented/tested for scope+retention+integrity definition (qualified language); state US-037 restore remains open; do **not** claim BL-014 closed or US-036 operator-accepted from apply alone.
- [x] 5.2 Update `docs/product/progress-checklist.md` only for demonstrated in-progress items (e.g. work started / criteria demonstrated as accurate); **leave** US-036 Story accepted and BL-014 closed unchecked until later acceptance.
- [x] 5.3 Do not check off US-036 acceptance criteria in `docs/product/user-stories.md` as accepted from proposal or incomplete validation; update only when criteria are actually demonstrated and operator acceptance is appropriate later.
- [x] 5.4 Do not update `docs/RUNTIME-STATE.md` (no live flag changes).

## 6. Explicit non-touch / regression guardrails

- [x] 6.1 Verify git diff does not reopen or modify BL-013 concurrency modules/tests (`flow_a` concurrency claim/CAS paths) except an unavoidable neutral shared import — default: zero BL-013 churn.
- [x] 6.2 Verify no new primary worker HTTP endpoints, no n8n workflow changes, no deploy scripts, no Git push, and no production restore mutation of editorial source trees.
- [x] 6.3 Confirm US-037 deliverables (restore test procedure, live restore drills) are not absorbed into this change.
- [x] 6.4 Run `git diff --check` on touched paths.

## 7. Business validation (US-036)

- [x] 7.1 Walk US-036 acceptance criteria against artifacts: (1) backup scope defined, (2) retention defined, (3) integrity verification automated and demonstrated on fixtures, (4) outcome visible/understandable in policy + report shape, (5) failures/blocked states clearly communicated, (6) existing completed work not duplicated or unintentionally changed.
- [x] 7.2 Confirm BL-014 remains open with US-037 still pending; confirm product status leaves US-036 unaccepted until explicit later acceptance.
