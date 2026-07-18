## Context

BL-014 protects the files and metadata required to recover the editorial system. Story 1 (**US-036**) defines backup **scope**, **retention**, and **integrity verification**. Story 2 (**US-037**) will test restoration and document the recovery procedure — out of scope here.

Today:

- Editorial layout under `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` includes `blog-posts/`, `linkedin-posts/`, `metadata/{runs,campaigns,backups}/`, `prompts/`, and `editorial-calendar/` (`paths.py` / health checks).
- `metadata/backups/` is an **expected empty directory** with no package format, retention policy, or integrity contract.
- No worker module or operator doc defines what a verified editorial backup is.
- BL-013 concurrency protection is fixture-accepted and closed — must not be reopened or altered.

Operator need: a clear, secret-safe definition of what to back up, how long to keep packages, and how to prove a package is intact — without live restore drills or new primary HTTP surfaces.

Constraints: ADR-0001 (n8n → worker HTTP only); fail closed on ambiguity; no secrets in reports/docs; prefer docs + contracts + automated integrity checks; prefer existing `metadata/backups/`; no Git push / deploy / production n8n activation in this change.

## Goals / Non-Goals

**Goals:**

- Normative **scope inventory**: included and excluded path classes for editorial-state recovery.
- Normative **retention** for packages under `metadata/backups/`.
- **Backup package layout** (manifest + content) and **automated integrity verification** with pass / fail / blocked outcomes.
- Operator-visible policy under `docs/operations/` and structured integrity reports that are understandable and secret-safe.
- Smallest coherent implementation: library + CLI/script + tests; no new primary HTTP endpoints by default.
- Keep US-036 / BL-014 open until later acceptance; do not mark accepted from proposal or apply alone.

**Non-Goals:**

- US-037 restoration testing, live restore drills that mutate production editorial trees, or the full recovery runbook beyond a pointer that restore belongs to US-037.
- New primary worker HTTP endpoints for backup create/verify/restore.
- Backing up `.env`, API keys, LinkedIn tokens, worker source, Docker images, n8n/postgres (shared-stack backup-runner), or treating the public GitHub Pages checkout as a substitute for editorial source trees.
- Changing Flow A lifecycle, LinkedIn publication, concurrency (BL-013), operational status/alerts, or incomplete-campaign recovery behavior.
- Claiming BL-014 complete.

## Decisions

### D1 — Deliverable shape: policy + package contract + integrity verifier (not restore)

**Decision:** US-036 ships:

1. Operator policy: `docs/operations/editorial-backup-scope-retention-integrity.md`
2. Normative OpenSpec capability `editorial-backup-scope-retention-integrity`
3. Backup package contract under `metadata/backups/<backup_id>/`
4. Read-mostly integrity verifier module + CLI + unit tests on fixtures
5. Optional **copy-out** package builder and retention prune that mutate **only** under `metadata/backups/` (never rewrite source editorial trees)

**Rationale:** Matches proposal posture (docs + contracts + automated checks). Integrity is demonstrable without US-037 restore mutation. A builder that only writes backup packages is useful for operators and retention tests without absorbing restore.

**Rejected:** New FastAPI routes for backup; absorbing US-037 restore drills into this change; treating folder existence alone as “backup complete.”

### D2 — Canonical backup root: `metadata/backups/`

**Decision:** All editorial backup packages MUST live under `{editorial_base}/metadata/backups/`. Each package is a directory:

```text
metadata/backups/<backup_id>/
  manifest.json          # schema, scope, timestamps, file index, hashes, retention metadata
  content/               # mirrored relative paths from editorial scope (or archive equivalent)
```

`<backup_id>` MUST be UTC-sortable and collision-resistant (e.g. `editorial-backup-YYYYMMDDTHHMMSSZ-<shortid>`).

**Rationale:** Folder already expected by worker-foundation; avoids a second primary layout.

**Rejected:** Storing editorial backups only outside the mount without a local package root; nesting previous backup packages inside new package content by default.

### D3 — Backup scope (included / excluded)

**Decision — included (editorial state required for recovery):**

| Relative path / class | Why |
|----------------------|-----|
| `blog-posts/ready/`, `queued/`, `processed/`, `error/` | Source posts and lifecycle folders |
| `linkedin-posts/review/`, `approved/`, `published/` | LinkedIn distribution artifacts |
| `metadata/campaigns/` | Campaign lifecycle and publication evidence |
| `metadata/runs/` | Run records |
| `editorial-calendar/` (including `calendar.json`) | Master calendar planning state |
| `prompts/` | Prompt assets used for generation consistency |
| Image/binary assets that live **inside** the included trees above | Recoverable media co-located with posts/packages |

**Decision — excluded (fail closed if operator asks to treat as in-scope without a new change):**

| Exclusion | Why |
|-----------|-----|
| `metadata/backups/` contents when assembling a new package | Avoid recursive backup-of-backups; retention manages prior packages separately |
| Secrets: `.env`, credential files, API keys, LinkedIn tokens | Secret-safe policy; never copy into packages or integrity reports |
| Public GitHub Pages checkout (`/public-blog` or host equivalent) | Blog handoff target ≠ editorial source of truth; site recovery is separate |
| Worker source, Docker images, n8n/postgres/minio stack | Outside editorial mount; shared-stack backup-runner owns stack backups |
| Transient OS/editor junk (`.DS_Store`, `__pycache__/`, `*.tmp`) | Noise; not required for editorial recovery |

**Rationale:** Aligns with BL-014 / US-037 protect list (calendar, campaigns, runs, posts, images, LinkedIn artifacts) while defining scope here so US-037 restores against a known inventory.

**Rejected:** Including `/public-blog` as mandatory editorial backup; including secrets “for convenience.”

### D4 — Retention

**Decision:**

- Keep the **N most recent integrity-passing** packages under `metadata/backups/` (default **N = 7**), OR packages newer than **R days** (default **R = 30**), whichever policy is stated in the operator doc as the active rule.
- **Active rule for v1:** retain the **7 most recent** packages whose last integrity result is `pass` (or that have never failed integrity after create); prune older packages only under `metadata/backups/`.
- Packages with integrity `fail` or `blocked` MUST remain visible until an operator explicitly removes them or a documented prune-failed policy applies; v1 **MUST NOT** auto-delete failed packages during routine retention prune (fail closed — preserve evidence).
- Retention prune MUST NOT delete or modify anything outside `metadata/backups/`.

**Rationale:** Bounded disk use with operator-visible failed packages retained for diagnosis. Numeric defaults are policy constants, not env-gated runtime product flags.

**Rejected:** Unlimited retention; auto-deleting failed packages; pruning source editorial trees.

### D5 — Integrity verification (automated, secret-safe)

**Decision:** Integrity verification MUST:

1. Require a readable `manifest.json` with schema version, `backup_id`, created-at UTC, scope declaration, and per-file relative path + sha256 (+ size).
2. Confirm required scope path classes are represented (or explicitly recorded empty with reason).
3. Confirm every manifest entry exists under the package content root and matches hash/size.
4. Confirm no unexpected path traversal (`..`, absolute paths) in manifest entries.
5. Confirm excluded classes are not present in content (secrets patterns, nested `metadata/backups/` payloads).
6. Emit a structured report: `status` ∈ {`pass`, `fail`, `blocked`}, stable `reason_codes[]`, counts, and relative paths only — **no** file content bodies, **no** secret values, **no** absolute paths that embed operator home/credential directories (prefer paths relative to editorial base or backup package root).

**Blocked** vs **fail:**

- `blocked`: prerequisite missing (no package, unreadable manifest, ambiguous schema) — verification cannot complete.
- `fail`: package readable but integrity contract violated (hash mismatch, missing required scope class, path traversal, excluded content present).

Verification MUST be read-only w.r.t. source editorial trees and MUST NOT restore files.

**Rationale:** Satisfies “verify backup integrity” with clear operator communication and secret safety.

### D6 — No new primary HTTP endpoints

**Decision:** Expose integrity (and optional create/prune) via Python module + `scripts/` CLI (or `python -m`), not new FastAPI routes. n8n MUST NOT gain Execute Command for backups (ADR-0001). If a future change needs HTTP, it requires its own OpenSpec change.

**Rationale:** Proposal prefers no new primary endpoints; backup is operator/maintenance, not Flow A orchestration.

**Rejected:** `POST /flow-a/backup` in this change.

### D7 — worker-foundation clarification only

**Decision:** Add an ADDED requirement that `metadata/backups/` is the designated root for editorial backup packages. Do **not** expand health checks into backup create/verify. Do **not** “fix” unrelated folder-list drift (`queued`, `editorial-calendar`) in this change unless required for compile/test consistency — prefer leave existing validation as-is.

**Rationale:** Smallest delta; avoid scope creep into folder-layout cleanup.

### D8 — Product status discipline

**Decision:** Implementation may note US-036 work-started in progress checklist only when apply begins; **must not** mark Story accepted / BL-014 closed until operator acceptance after ACs demonstrated. Proposal alone leaves checkboxes open.

### D9 — Boundary with US-037

**Decision:** Policy MUST explicitly state that restoration testing and the recovery procedure are **US-037**. US-036 may include a short “restore is out of scope” pointer and list which scope classes US-037 MUST protect — without documenting step-by-step live restore mutation.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operators assume `/public-blog` is covered | Explicit exclusion + handoff ≠ live language in policy |
| Secrets accidentally copied into packages | Exclusion rules + integrity fail if secret-like paths detected; docs forbid |
| Retention prune deletes evidence | Never auto-delete `fail`/`blocked` packages in v1 |
| Scope ambiguity (images only on public checkout) | Scope includes binaries inside editorial trees; note public-checkout media as out of scope / US-037 consideration |
| Overbuilding HTTP/restore | Spec and tasks forbid primary endpoints and restore mutation |
| BL-013 accidental churn | Tasks explicitly forbid touching concurrency modules/tests except if shared path utils need a neutral import |

## Migration Plan

1. Approve proposal → `/opsx-apply`.
2. Add policy doc, specs, verifier module, CLI, fixture tests.
3. Optionally create a sample fixture package under tests (not production mount).
4. No deploy required for US-036 acceptance via fixtures; live mount smoke is optional and must not mutate source trees beyond writing under `metadata/backups/` if operator explicitly requests.
5. Rollback: remove new module/docs; `metadata/backups/` remains an empty expected folder as before.

## Open Questions

None blocking proposal. Defaults (N=7 retention, package directory layout vs single tarball) are decided in D2/D4; apply may choose tar+manifest equivalent if tests stay clearer, as long as the package root remains `metadata/backups/<backup_id>/` and integrity rules hold.
