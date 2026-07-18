## 1. Operator recovery procedure artifact (US-037)

- [x] 1.1 Create `docs/operations/editorial-backup-restore-recovery.md` covering: purpose (BL-014 / US-037 only), integrity `pass` prerequisite (US-036), fixture/dry-run restore drills, fail-closed live restore gates with explicit confirmation, protected classes matching US-036 included scope, exclusions (secrets, public checkout as SoT, stack, backup packages as source content), restore `pass`/`fail`/`blocked` + reason codes, secret-safe reporting, operator visibility, and explicit statement that Git push / Pages deploy / LinkedIn publication are not part of restore.
- [x] 1.2 Cross-link from US-036 policy (`editorial-backup-scope-retention-integrity.md`) to the US-037 recovery procedure (additive pointer only — do not change US-036 scope/retention/integrity contracts).
- [x] 1.3 Ensure GLOSSARY US-037 restoration/recovery entry remains accurate; add a short pointer to the new runbook path if missing.
- [x] 1.4 Cross-link the recovery procedure from CURRENT-STATE (when status is updated) and product story US-037 references as needed; do not mark acceptance checkboxes done in this task.

## 2. Restore library and CLI

- [x] 2.1 Add `src/silverman_blog_linkedin/editorial_backup_restore.py` that reuses US-036 scope/integrity helpers, implements dry-run / restore-drill (explicit target) / live-restore (confirmation-gated), and returns structured `status` / `reason_codes` / secret-safe summaries.
- [x] 2.2 Enforce integrity `pass` prerequisite before any writes; map integrity not-pass / missing package / missing live confirmation / unsafe target to `blocked` with stable `restore_*` reason codes.
- [x] 2.3 Implement protected-class restore coverage for US-036 included classes (calendar, campaigns, runs, blog-posts/*, linkedin-posts/*, prompts, co-located binaries); refuse secrets and excluded paths; do not mutate packages under `metadata/backups/` as part of restore.
- [x] 2.4 Add post-restore (or post-drill) hash/size checks against the package manifest where files were written; report `fail` on mismatch.
- [x] 2.5 Extend `scripts/editorial_backup.py` with restore subcommands (`dry-run`, `restore-drill`, gated `restore`) — no new FastAPI routes; no n8n Execute Command.

## 3. Automated tests

- [x] 3.1 Add fixture-based tests for restore-drill `pass` into an explicit target tree covering campaigns, calendar, LinkedIn artifacts, and co-located images when present in the package.
- [x] 3.2 Add tests for integrity not-pass → restore `blocked` with no target writes; missing package → `blocked`; dry-run → no mutation; live without confirmation → `blocked`.
- [x] 3.3 Add tests for secret-path refusal and secret-safe result shape (no content bodies / tokens).
- [x] 3.4 Add a lightweight policy presence test that the recovery procedure doc exists and contains required restore/US-036-boundary/fail-closed phrases.
- [x] 3.5 Run targeted pytest for the new suite; do not weaken assertions; no real external API calls; do not break US-036 integrity tests.

## 4. US-036 additive alignment only

- [x] 4.1 Apply only the additive delta that US-037 owns restore (policy pointer + optional ADDED requirement); do not modify US-036 scope, retention, integrity verification, package layout, or integrity reason-code contracts.
- [x] 4.2 Confirm `verify_editorial_backup` remains read-only w.r.t. source editorial trees.

## 5. Status and product progress (after ACs demonstrated — leave open)

- [x] 5.1 Update `docs/CURRENT-STATE.md` to record US-037 as implemented/tested for restore drills + recovery procedure (qualified language); state live production restore remains operator-gated; do **not** claim BL-014 closed or US-037 operator-accepted from apply alone.
- [x] 5.2 Update `docs/product/progress-checklist.md` only for demonstrated in-progress items (e.g. work started / criteria demonstrated as accurate); **leave** US-037 Story accepted and BL-014 closed unchecked until later acceptance.
- [x] 5.3 Do not check off US-037 acceptance criteria in `docs/product/user-stories.md` as accepted from proposal or incomplete validation; update only when criteria are actually demonstrated and operator acceptance is appropriate later.
- [x] 5.4 Do not update `docs/RUNTIME-STATE.md` (no live flag changes).

## 6. Explicit non-touch / regression guardrails

- [x] 6.1 Verify git diff does not reopen or alter US-036 integrity contracts beyond the additive restore pointer; do not reopen BL-013 concurrency modules/tests.
- [x] 6.2 Verify no new primary worker HTTP endpoints, no n8n workflow changes, no deploy scripts, no Git push, and no unattended production restore mutation of editorial source trees.
- [x] 6.3 Confirm public GitHub Pages checkout is not treated as restore SoT; secrets are not restored into editorial trees.
- [x] 6.4 Run `git diff --check` on touched paths.

## 7. Business validation (US-037)

- [x] 7.1 Walk US-037 acceptance criteria against artifacts: (1) restoration tested via automated fixture drills, (2) recovery procedure documented, (3) calendar/campaigns/runs/posts/images/LinkedIn artifacts protected via restore coverage of US-036 scope, (4) outcome visible/understandable in runbook + report shape, (5) failures/blocked states clearly communicated, (6) existing completed work not duplicated or unintentionally changed.
- [x] 7.2 Confirm BL-014 remains open with US-037 Story accepted unchecked; confirm US-036 remains definition/verify only and is not rewritten by this change.
