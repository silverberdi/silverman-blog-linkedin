# Editorial Backup Scope, Retention, and Integrity (US-036)

Operator contract for **BL-014 / US-036** only: define editorial-state backup
**scope**, **retention**, and **integrity verification**.

## Status

- **Accepted 2026-07-18** against automated fixture evidence and this policy.
- **BL-014 closed 2026-07-18** after US-036 + US-037 acceptance.
- Live production restore is owned by US-037 and remains operator-gated — see
  [bl-014-editorial-backup-restore-acceptance-2026-07-18.md](bl-014-editorial-backup-restore-acceptance-2026-07-18.md).

**US-037 boundary:** restore drills, live restore mutation of production
editorial trees, and the recovery procedure are **out of scope** here. They
belong to US-037 — see
[editorial-backup-restore-recovery.md](editorial-backup-restore-recovery.md).
US-036 may list which scope classes US-037 must protect; it does not document
step-by-step restore mutation.

Policy: [GLOSSARY.md](../GLOSSARY.md) (editorial backup integrity vs restoration).
Change artifacts (archived):
`openspec/changes/archive/` (US-036 scope/retention/integrity change).

## Purpose

Protect the files and metadata required to recover the editorial system by:

1. Defining what is included and excluded under the editorial base path.
2. Defining how many backup packages to keep under `metadata/backups/`.
3. Verifying package integrity with operator-visible `pass` / `fail` / `blocked`
   outcomes that are secret-safe.

Integrity verification and optional package create/prune run via the Python
module and CLI (`scripts/editorial_backup.py`). There are **no** new FastAPI
routes for backup. n8n must **not** use Execute Command for backups (ADR-0001).
`GET /health` continues to treat `metadata/backups` as a required folder only —
it does not create, verify, prune, or restore packages.

## Included scope

Relative path classes under `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` (when present):

| Relative path / class | Why |
|----------------------|-----|
| `blog-posts/ready/` | Operator-approved inbox |
| `blog-posts/queued/` | Worker-accepted Flow A work |
| `blog-posts/processed/` | Successfully consumed sources |
| `blog-posts/error/` | Terminal-failure sources |
| `linkedin-posts/review/` | LinkedIn distribution artifacts (review) |
| `linkedin-posts/approved/` | LinkedIn distribution artifacts (approved) |
| `linkedin-posts/published/` | LinkedIn distribution artifacts (published) |
| `metadata/campaigns/` | Campaign lifecycle and publication evidence |
| `metadata/runs/` | Run records |
| `editorial-calendar/` (including `calendar.json`) | Master calendar planning state |
| `prompts/` | Prompt assets for generation consistency |
| Image/binary assets **inside** the trees above | Media co-located with posts/packages |

Ambiguous requests to treat an excluded class as in-scope **fail closed** until
a new approved OpenSpec change expands the contract.

## Exclusions

| Exclusion | Why |
|-----------|-----|
| Contents of `metadata/backups/` when assembling a new package | No recursive backup-of-backups; retention manages prior packages |
| Secrets: `.env`, credential files, API keys, LinkedIn tokens | Secret-safe policy; never copy into packages or integrity reports |
| Public GitHub Pages checkout (`/public-blog` or host equivalent) | Blog handoff target ≠ editorial source of truth |
| Worker source, Docker images, n8n/postgres/minio stack | Outside editorial mount; shared-stack backup-runner owns stack backups |
| Transient junk (`.DS_Store`, `__pycache__/`, `*.tmp`) | Not required for editorial recovery |

## Package layout

All editorial backup packages live under:

```text
{editorial_base}/metadata/backups/<backup_id>/
  manifest.json
  content/               # mirrored relative paths from included scope
```

`<backup_id>` is UTC-sortable and collision-resistant, for example:

`editorial-backup-YYYYMMDDTHHMMSSZ-<shortid>`

### `manifest.json` (schema version `1`)

Required fields:

- `schema_version` — `"1"`
- `backup_id` — package directory name
- `created_at_utc` — ISO-8601 UTC timestamp
- `scope` — declaration of included path classes (and empty-class reasons when applicable)
- `files` — per-file index: relative path (under `content/`), `sha256`, `size_bytes`
- `retention` — optional metadata (for example `keep_count` default)

Manifest path entries MUST be relative, MUST NOT contain `..` segments, and
MUST NOT be absolute filesystem paths.

## Retention (v1 active rule)

Retain the **7 most recent** integrity-eligible packages under
`metadata/backups/`.

Integrity-eligible means last integrity status is `pass` (or the package was
just created and has not failed integrity).

Retention prune MUST:

- only delete package directories under `metadata/backups/`;
- **never** modify `blog-posts/`, `linkedin-posts/`, `metadata/campaigns/`,
  `metadata/runs/`, `editorial-calendar/`, or `prompts/`;
- **never** auto-delete packages whose integrity status is `fail` or `blocked`
  (failed packages remain until explicit operator removal — fail closed,
  preserve evidence).

Numeric default `N = 7` is a policy constant, not an env-gated product flag.

## Integrity verification

Run against a package id under `metadata/backups/`:

```bash
python scripts/editorial_backup.py verify \
  --base-path /path/to/editorial \
  --backup-id editorial-backup-20260718T120000Z-ab12cd
```

Or via the library:

```python
from silverman_blog_linkedin.editorial_backup_integrity import verify_editorial_backup

result = verify_editorial_backup(base_path, backup_id)
# result["status"] in {"pass", "fail", "blocked"}
# result["reason_codes"] — stable codes; empty on clean pass
```

### Status meanings

| Status | Meaning |
|--------|---------|
| `pass` | Package readable; files match manifest; scope and path-safety contracts hold |
| `fail` | Package readable but integrity contract violated (hash/size mismatch, missing scope class, path traversal, excluded content present) |
| `blocked` | Prerequisite missing — verification cannot complete (no package, unreadable manifest, ambiguous schema) |

### Stable reason codes (examples)

| Code | Typical status |
|------|----------------|
| `backup_package_missing` | `blocked` |
| `backup_manifest_unreadable` | `blocked` |
| `backup_manifest_schema_ambiguous` | `blocked` |
| `backup_hash_mismatch` | `fail` |
| `backup_size_mismatch` | `fail` |
| `backup_file_missing` | `fail` |
| `backup_path_unsafe` | `fail` |
| `backup_excluded_content_present` | `fail` |
| `backup_scope_class_missing` | `fail` |

Verification is **read-only** with respect to source editorial trees. It does
**not** restore or rewrite `blog-posts/`, `linkedin-posts/`, campaigns, runs,
calendar, or prompts.

Optional create/prune (same CLI) may write **only** under `metadata/backups/`:

```bash
python scripts/editorial_backup.py create --base-path /path/to/editorial
python scripts/editorial_backup.py prune --base-path /path/to/editorial
```

## Secret-safe reporting

Integrity results and documentation examples MUST NOT include:

- API keys, tokens, or `.env` values;
- file content bodies;
- absolute paths that embed operator home or credential directories.

Prefer paths relative to the editorial base or the backup package root.
Summaries may include counts (files checked, mismatches) and relative paths.

## Operator visibility

Operators interpret outcomes from:

1. This policy document (scope, retention, status meanings).
2. Structured CLI/library JSON: `status`, `reason_codes`, summary counts,
   relative paths only.

Failures and blocked states use the stable reason codes above so operators can
distinguish “cannot verify yet” (`blocked`) from “package is broken” (`fail`).

## Out of scope (US-037 and beyond)

- Restore drills that mutate production editorial state — owned by US-037;
  procedure: [editorial-backup-restore-recovery.md](editorial-backup-restore-recovery.md)
- Full recovery procedure / runbook for live restore — same US-037 document
- Backing up secrets, the public GitHub Pages checkout as editorial substitute,
  or shared-stack services
- New primary worker HTTP endpoints for backup
- Claiming BL-014 complete or US-036 operator-accepted from this policy text
  alone without the acceptance record (acceptance is recorded in
  [bl-014-editorial-backup-restore-acceptance-2026-07-18.md](bl-014-editorial-backup-restore-acceptance-2026-07-18.md))
