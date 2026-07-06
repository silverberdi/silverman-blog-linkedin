## Context

The `silverman-blog-linkedin` worker already processes ready blog posts for LinkedIn draft generation via HTTP endpoints (`POST /process-ready`, `POST /process-file`). Editorial content lives on the Ubuntu server at `/home/silverman/compartido_mac/silverman-blog-linkedin` with ready posts in `blog-posts/ready/`.

The public blog at [silverman.pro](https://silverman.pro) is a Jekyll/GitHub Pages site backed by [silverberdi/silverberdi.github.io](https://github.com/silverberdi/silverberdi.github.io). Published posts use `_posts/YYYY-MM-DD-slug.md`, images live under `assets/images/`, and permalinks resolve to `/YYYY/MM/DD/slug/`.

Operators provide editorial input as a matching pair: `blog-posts/ready/<source-slug>.md` and `blog-posts/ready/<source-slug>.png`. The source slug is the editorial identifier used in the ready folder; numeric ordering prefixes such as `01-` are stripped when deriving the public slug for URLs and published filenames unless overridden with `--public-slug`.

This MVP adds a controlled CLI bridge—not a new HTTP worker endpoint—to prepare one post pair in a local checkout of the public repo. The operator reviews dry-run output, applies when satisfied, then commits and pushes manually.

## Goals / Non-Goals

**Goals:**

- Implement a testable Python publishing module with a thin `deploy/server/` shell wrapper consistent with existing deployment scripts.
- Support dry-run by default and explicit `--apply` for writes.
- Validate source slug and public slug safety, source pair existence, and non-overwrite constraints.
- Derive public slug from source slug (strip leading `^\d+-` ordering prefix by default) or accept `--public-slug` override.
- Transform editorial inputs into Jekyll conventions (filename, frontmatter, image path, public URL).
- Preserve Markdown body content; normalize required frontmatter fields.
- Document the operator workflow for the Ubuntu server and local Mac development.

**Non-Goals:**

- HTTP worker endpoint, n8n workflow, or Execute Command integration.
- `git commit` / `git push` automation.
- Moving sources out of `blog-posts/ready/`.
- Overwrite mode, batch publish, ComfyUI image generation, LinkedIn publish.
- Changes to existing worker routes or Docker worker container behavior.

## Decisions

### 1. CLI helper under `deploy/server/` (not HTTP endpoint)

**Decision:** Add `src/silverman_blog_linkedin/github_pages_publish.py` (core logic) and `deploy/server/publish-blog-post.sh` (operator entry point). The shell script invokes the Python module via `python -m silverman_blog_linkedin.github_pages_publish` or equivalent, matching the pattern of `deploy-worker.sh` as a thin wrapper.

**Rationale:** Publishing is an operator-initiated, infrequent action with filesystem side effects outside the editorial workspace. A CLI with dry-run default is safer than exposing a push-capable HTTP endpoint in MVP. Future changes can wrap this module in an authenticated worker route if n8n orchestration is needed.

**Alternatives considered:**

- **New `POST /publish-blog` worker endpoint:** Rejected for MVP—adds auth/deploy scope and encourages remote triggers before manual git review is established.
- **n8n Execute Command with inline shell:** Rejected per ADR-0001 spirit—logic must live in version-controlled, tested code.

### 2. Configuration via environment variables and CLI flags

**Decision:** Support:

| Variable / flag | Purpose | Default |
|-----------------|---------|---------|
| `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` | Editorial workspace root | existing worker setting |
| `SILVERMAN_GITHUB_PAGES_REPO_PATH` | Local clone of `silverberdi.github.io` | required at runtime |
| `SILVERMAN_SITE_URL` | Canonical public base URL | `https://silverman.pro` |
| `--slug` / positional slug | Source editorial slug | required |
| `--public-slug` | Override derived public slug | derived from source slug |
| `--date YYYY-MM-DD` | Publication date | current UTC date |
| `--apply` | Write files (omit for dry-run) | dry-run |
| `--json` (optional) | Machine-readable summary | off |

**Rationale:** Reuses the editorial base path env var already known to the worker. Public repo path is operator-specific (may differ between Mac dev and Ubuntu server) and must be explicit.

**Security:** Source slug is the only user-supplied path component for editorial reads; public slug affects only public repo outputs. Resolve all paths under configured roots and verify with `Path.resolve()` + `is_relative_to()`.

### 3. Source slug vs public slug

**Decision:** Accept a required source slug for locating `blog-posts/ready/<source-slug>.{md,png}`. Derive public slug by stripping a leading numeric ordering prefix (`^\d+-<rest>`) when present; otherwise use the source slug unchanged. Allow `--public-slug` to override the derived value. Validate both slugs with `^[a-z0-9]+(?:-[a-z0-9]+)*$`.

**Rationale:** Editorial ready files use ordering prefixes (`01-`, `02-`) that must not appear in public URLs or Jekyll filenames.

### 4. Slug validation rules

**Decision:** Accept slugs matching `^[a-z0-9]+(?:-[a-z0-9]+)*$`. Reject empty slugs, uppercase, underscores, dots, slashes, and `..`. Apply to both source slug and public slug (including `--public-slug` overrides).

**Rationale:** Matches observed public blog slug style (`architect-solution-state-of-art`) and prevents path traversal.

### 5. Frontmatter handling

**Decision:** Add `pyyaml` dependency for parsing and emitting YAML frontmatter. Split source file on first `---` delimiters; parse existing frontmatter if present; merge required keys; re-serialize with body unchanged.

Required keys and defaults:

| Key | Behavior |
|-----|----------|
| `layout` | Default `post` if missing |
| `title` | Keep from source; else title-case public slug words |
| `date` | ISO date from chosen publication date |
| `categories` | Keep from source; else empty list `[]` |
| `tags` | Keep from source; else empty list `[]` |
| `description` | Keep from source; else empty string or first paragraph excerpt (implementation choice—must not fabricate claims) |
| `image` | Always set to `/assets/images/<public-slug>.png` |

**Rationale:** Jekyll expects YAML frontmatter; PyYAML is standard and testable. Body preservation is a business requirement.

**Alternatives considered:**

- **Regex-only frontmatter:** Fragile for nested YAML lists; rejected.
- **python-frontmatter package:** Additional dependency; PyYAML suffices.

### 6. Output paths and URL calculation

**Decision:**

- Post: `{repo}/_posts/{YYYY-MM-DD}-{public-slug}.md`
- Image: `{repo}/assets/images/{public-slug}.png`
- Public URL: `{site_url}/{YYYY}/{MM}/{DD}/{public-slug}/` (no trailing slash omission in reports; Jekyll permalink pattern)

Use UTC for default date when operator does not pass `--date`.

### 7. Non-overwrite policy

**Decision:** Before any write (and during dry-run validation), check existence of both target paths. If either exists, fail with clear error naming the conflicting path. No `--force` in MVP.

**Rationale:** Prevents accidental replacement of live blog content. Future change can add explicit `--replace` with additional safeguards.

### 8. Dry-run output contract

**Decision:** Print human-readable summary to stdout:

```
source_slug: 01-why-i-did-not-start-with-the-database
public_slug: why-i-did-not-start-with-the-database
mode: dry-run
publication_date: 2026-07-06
post_target: _posts/2026-07-06-why-i-did-not-start-with-the-database.md
image_target: assets/images/why-i-did-not-start-with-the-database.png
public_url: https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/
status: ready
```

On error (missing source, unsafe slug, overwrite conflict): non-zero exit, `status: error`, reason on stderr.

Optional `--json` emits the same fields as JSON for future automation.

### 9. Module layout and tests

**Decision:**

```
src/silverman_blog_linkedin/
  github_pages_publish.py    # core: validate, transform, publish, dry_run
deploy/server/
  publish-blog-post.sh       # wrapper script
tests/
  test_github_pages_publish.py
docs/
  workflows/blog-publishing-bridge.md   # operator documentation
```

Tests use `tmp_path` for editorial tree and fake public repo checkout; no network or real git operations.

### 10. Docker / worker container scope

**Decision:** Do not add publishing to the worker Docker image in MVP unless needed for shared Python env. The helper runs on the Ubuntu host (or dev Mac) where both the editorial workspace and `silverberdi.github.io` clone are accessible. Document paths for server usage.

**Rationale:** Public repo checkout is outside the editorial data mount; operator git workflow is manual. Worker container remains focused on LinkedIn pipeline.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operator points `SILVERMAN_GITHUB_PAGES_REPO_PATH` at wrong directory | Require path exists and contains `_posts/` and `assets/images/`; fail fast with validation |
| Source frontmatter has incompatible YAML | Catch parse errors; exit with actionable message; do not partial-write |
| UTC default date differs from operator's intended local publication date | Document `--date`; show chosen date prominently in dry-run output |
| Public repo checkout out of date vs remote | Out of scope—operator responsible for `git pull` before publish |
| Duplicate public slug with different dates | Only exact `_posts/YYYY-MM-DD-<public-slug>.md` collision is blocked; same public slug new date is allowed by Jekyll but may be editorially wrong—operator judgment |
| Missing categories/tags defaults | Empty lists; operator can edit in public repo before commit |

## Migration Plan

1. Implement Python module and tests locally against temp directories.
2. Add `pyyaml` to `pyproject.toml` dependencies.
3. Add shell wrapper and operator documentation.
4. On Ubuntu server: ensure clone of `silverberdi.github.io` exists; set `SILVERMAN_GITHUB_PAGES_REPO_PATH`; run dry-run against a real ready post; review output.
5. Run with `--apply`; verify files in public repo checkout; operator `git diff`, commit, push to publish.
6. Rollback: delete uncommitted files from public repo checkout; no editorial source changes.

## Open Questions

- Exact default for `layout` if absent (`post` assumed—confirm against existing `silverberdi.github.io` posts during implementation).
- Whether `categories`/`tags` should be required non-empty for MVP or left to operator post-apply edit (spec allows empty lists).
- Preferred location of `silverberdi.github.io` clone on Ubuntu server (document in workflow doc once operator confirms path).
