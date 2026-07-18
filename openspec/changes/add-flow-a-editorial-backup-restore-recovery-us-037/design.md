## Context

BL-014 protects the files and metadata required to recover the editorial system. Story 1 (**US-036**) is implemented and synced: scope, retention, and integrity verification live under `metadata/backups/` via `editorial_backup_integrity.py` + `scripts/editorial_backup.py`, with operator policy at `docs/operations/editorial-backup-scope-retention-integrity.md`. Story 2 (**US-037**) must **test restoration** and **document the recovery procedure** so operators can restore calendar, campaigns, runs, posts, images, and LinkedIn artifacts from a **verified** (integrity `pass`) package.

Today:

- Integrity verify/create/prune exist; restore is explicitly refused / out of scope in US-036 code and docs.
- No restore-drill automation, no recovery runbook, no structured restore `pass` / `fail` / `blocked` outcomes.
- GLOSSARY already separates US-036 integrity from US-037 restoration/recovery.

Constraints: ADR-0001 (n8n → worker HTTP only); fail closed on live production mutation; no secrets in reports or restored trees; do not reopen US-036 contracts except additive restore pointers; no Git push / deploy / production n8n activation; prefer fixtures and dry-run first.

## Goals / Non-Goals

**Goals:**

- Automated **restoration drills** against US-036 pass-integrity packages (fixture / non-production target trees first).
- Operator **recovery runbook** documenting how to restore from a verified backup, including gates for any live mutation.
- Restore coverage of US-036 **included scope** (calendar, campaigns, runs, blog/LinkedIn trees, prompts, co-located binaries).
- Structured, secret-safe restore outcomes (`pass` / `fail` / `blocked`) understandable to system operators.
- Library + CLI extension; no new primary FastAPI routes by default.
- Leave US-037 / BL-014 open until later acceptance.

**Non-Goals:**

- Changing US-036 scope, retention, integrity verification, package layout, or integrity reason codes (additive pointer only).
- Reopening BL-013 / US-033–US-035.
- Restoring secrets; using public GitHub Pages checkout as editorial restore SoT.
- Unattended production restore; shared-stack backup-runner; claiming BL-014 closed from this change alone.
- New primary HTTP restore endpoints.

## Decisions

### D1 — Deliverable shape: runbook + restore library/CLI + fixture drills

**Decision:** US-037 ships:

1. Operator recovery procedure: `docs/operations/editorial-backup-restore-recovery.md`
2. Normative OpenSpec capability `editorial-backup-restore-recovery`
3. Restore / restore-drill library API (sibling module or additive functions) + CLI subcommands on `scripts/editorial_backup.py` (or thin wrapper)
4. Automated fixture tests proving restore drill pass/fail/blocked and protected-class coverage
5. Additive cross-links from US-036 policy / GLOSSARY / optional ADDED requirement on the US-036 capability

**Rationale:** Matches proposal (docs + library/CLI). Fixture drills demonstrate “test restoration” without requiring production mutation for AC evidence.

**Rejected:** New FastAPI restore routes; absorbing US-036 integrity rewrites; claiming BL-014 closed from docs alone.

### D2 — Integrity `pass` is a hard prerequisite

**Decision:** Any restore or restore-drill that would write files MUST first run (or accept a fresh result from) US-036 `verify_editorial_backup` and proceed with mutation only when `status == "pass"`.

- Integrity `fail` → restore result `blocked` or `fail` with stable reason (prefer `blocked` when restore MUST NOT start; `fail` if a drill started and then detected integrity violation mid-flight — default: **do not start** → `blocked` with `restore_integrity_not_pass`).
- Integrity `blocked` → restore `blocked` (cannot restore from unverifiable package).
- Missing package → `blocked`.

**Rationale:** US-037 restores from a **verified** backup; US-036 owns verify.

**Rejected:** Restoring from unverified packages “for convenience.”

### D3 — Fixture / dry-run first; live mutation fail-closed

**Decision:** Default restore mode is **dry-run** or **restore-to-target** where target is an explicit path (fixture/staging tree), **not** an implicit overwrite of the production editorial base.

Modes:

| Mode | Behavior |
|------|----------|
| `dry_run` | Plan + validate only; no writes to target trees |
| `restore_drill` | Materialize package content into an explicit **target base path** (fixture/staging); never implies production |
| `live_restore` | Overwrite/replace included scope under an editorial base that the operator explicitly identifies as the live mount — **requires explicit confirmation flag** (e.g. `--i-understand-live-restore`) and documented runbook steps; default CLI refuses |

Without the live confirmation flag, attempts to restore into a path that looks like the operator’s production mount (or when `--live` is requested without confirmation) MUST `blocked`.

**Rationale:** Fail closed; ACs can be demonstrated on fixtures; production mutation remains operator-gated.

**Rejected:** Default overwrite of `SILVERMAN_BLOG_LINKEDIN_BASE_PATH`; silent live mutation from n8n/automation.

### D4 — Protected classes = US-036 included scope

**Decision:** Restore MUST cover (when present in the package) the same included classes as US-036 `INCLUDED_SCOPE_CLASSES`:

- `blog-posts/{ready,queued,processed,error}/`
- `linkedin-posts/{review,approved,published}/`
- `metadata/campaigns/`, `metadata/runs/`
- `editorial-calendar/`
- `prompts/`
- co-located images/binaries inside those trees

Restore MUST NOT:

- write secrets / credential-like paths into the target
- treat public GitHub Pages checkout as restore source or required target
- nest `metadata/backups/` package contents into restored editorial trees as source content
- mutate `metadata/backups/` packages as part of restore (packages remain read-only inputs)

**Rationale:** AC3 “protect calendar, campaigns, runs, posts, images, and LinkedIn artifacts” maps 1:1 to US-036 scope.

### D5 — Restore semantics for target trees

**Decision (v1):** For `restore_drill` / confirmed `live_restore`:

1. Precheck integrity `pass`.
2. Optionally snapshot or refuse if target included-scope paths already have unexpected content — v1 prefer: **replace included-scope subtrees from package content** for classes present in the package, after writing to a staging area under the target (or temp) and swapping atomically where practical; if atomic swap is impractical on all platforms, write file-by-file with path-safety checks and document the limitation.
3. After restore, optionally re-hash restored files against the manifest for a post-restore verification step included in the structured result.
4. Never delete or rewrite packages under `metadata/backups/` during restore.
5. Never restore excluded classes even if present in a malicious package (integrity should already `fail`; restore still double-checks and `fail`s closed).

**Rationale:** Deterministic drill outcomes; path safety inherited from US-036 helpers.

**Rejected:** Merging arbitrary unknown paths; restoring from `/public-blog`.

### D6 — Outcome model: pass / fail / blocked (secret-safe)

**Decision:** Restore results mirror integrity reporting style:

- `status` ∈ {`pass`, `fail`, `blocked`}
- `reason_codes[]` stable, empty on clean `pass`
- summary counts (files restored / planned, mismatches)
- relative paths only — no content bodies, tokens, `.env` values, or absolute secret-bearing paths

Status meanings:

| Status | Meaning |
|--------|---------|
| `pass` | Drill/restore completed (or dry-run validated) with protected classes covered and post-checks OK |
| `fail` | Operation ran far enough to detect a contract violation (hash mismatch post-write, excluded content attempted, incomplete protected class when package claimed it) |
| `blocked` | Prerequisite missing or policy gate refused (integrity not pass, missing confirmation for live, ambiguous target, dry-run-only policy) |

Example reason codes (prefix `restore_` to avoid colliding with `backup_*` integrity codes):

- `restore_integrity_not_pass`
- `restore_package_missing`
- `restore_live_confirmation_required`
- `restore_target_unsafe`
- `restore_secret_path_refused`
- `restore_postcheck_hash_mismatch`
- `restore_scope_class_incomplete`

**Rationale:** Operator-visible, aligns with US-036 communication pattern, secret-safe.

### D7 — No new primary HTTP endpoints; CLI extension

**Decision:** Expose restore via Python API + CLI subcommands (`restore-drill`, `restore` with live gate, `dry-run`). n8n MUST NOT use Execute Command (ADR-0001). No new FastAPI routes in this change.

**Rationale:** Same posture as US-036; restore is operator/maintenance, not Flow A orchestration.

**Rejected:** `POST /flow-a/restore` in this change.

### D8 — Module layout

**Decision:** Prefer a dedicated module `editorial_backup_restore.py` that **imports** US-036 verify/scope helpers from `editorial_backup_integrity.py`, rather than expanding integrity into restore mutation. CLI `scripts/editorial_backup.py` gains restore subcommands that call the restore module.

**Rationale:** Clear US-036 vs US-037 boundary in code; avoids accidental integrity contract churn.

**Rejected:** Rewriting integrity module into a combined “backup everything” blob; duplicating scope lists (reuse `INCLUDED_SCOPE_CLASSES`).

### D9 — Operator runbook content

**Decision:** Recovery procedure MUST include:

1. Prerequisites (integrity `pass`, backup id, target type: fixture vs live)
2. How to run fixture restore drills and interpret outcomes
3. Controlled live restore steps with explicit confirmation and rollback notes (e.g. take a fresh backup before live restore)
4. What is protected / what is excluded (secrets, public checkout, stack)
5. Failure and blocked communication (reason codes table)
6. Explicit statement that Git push / Pages deploy / LinkedIn publication are **not** part of restore
7. Cross-link to US-036 policy; GLOSSARY terms

### D10 — Product status discipline

**Decision:** Apply may mark US-037 work-started / criteria demonstrated when accurate; **must not** check Story accepted or BL-014 closed until later operator acceptance. Do not mark US-036 acceptance as a side effect.

### D11 — Additive US-036 pointer only

**Decision:** Optional ADDED requirement on `editorial-backup-scope-retention-integrity`: operators SHALL be pointed to US-037 for restore drills and recovery procedure. Do **not** MODIFY existing US-036 requirements’ normative text for scope/retention/integrity.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Accidental production overwrite | Default dry-run/fixture; live requires explicit confirmation flag; runbook gates |
| Operators treat Pages checkout as SoT | Explicit exclusion in runbook + spec scenarios |
| Secrets leak into restore target or reports | Reuse exclusion helpers; secret-safe result shape tests |
| US-036 contract drift | Separate restore module; tasks forbid integrity requirement edits beyond additive pointer |
| Partial restore leaves inconsistent trees | Prefer full included-class replace from package + postcheck; fail closed on postcheck mismatch |
| Overbuilding HTTP/automation | Spec and tasks forbid primary endpoints and n8n Execute Command |

## Migration Plan

1. Approve proposal → `/opsx-apply`.
2. Add runbook, restore module, CLI subcommands, fixture tests.
3. Demonstrate ACs on fixtures (no production mutation required).
4. Optional later operator-controlled live drill only with explicit approval (out of band from apply).
5. Rollback: remove restore module/CLI/docs; US-036 integrity/create/prune remain unchanged.

## Open Questions

None blocking proposal. Atomic directory swap vs file-by-file write is an apply-time implementation detail as long as path safety, postcheck, and fail-closed live gates hold.
