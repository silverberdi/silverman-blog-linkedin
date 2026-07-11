# Blog publishing bridge (GitHub Pages)

Operator workflow for preparing one editorial blog post pair from `blog-posts/ready/` into a local checkout of [silverberdi.github.io](https://github.com/silverberdi/silverberdi.github.io) for publication at [silverman.pro](https://silverman.pro).

**Terminology:** Worker `POST /publish-blog-post` performs **blog handoff** (writes to public checkout). This CLI and manual Git steps achieve **site published/live**. See [GLOSSARY.md](../GLOSSARY.md).

This is a **CLI helper only**. It is not an HTTP worker endpoint and does not use n8n Execute Command. It does not run `git commit` or `git push`, move sources out of `ready/`, or publish to LinkedIn.

## Input convention

The CLI accepts a **source slug** that locates editorial files in `blog-posts/ready/`. Numeric ordering prefixes such as `01-` are editorial only and are stripped when deriving the **public slug** used for URLs and published filenames.

Example with ordering prefix:

| Editorial source | Path |
|------------------|------|
| Markdown | `blog-posts/ready/01-why-i-did-not-start-with-the-database.md` |
| Hero image | `blog-posts/ready/01-why-i-did-not-start-with-the-database.png` |

Derived public slug: `why-i-did-not-start-with-the-database`

Example without prefix:

| Editorial source | Path |
|------------------|------|
| Markdown | `blog-posts/ready/my-post.md` |
| Hero image | `blog-posts/ready/my-post.png` |

Derived public slug: `my-post`

Both source slug and public slug must match `^[a-z0-9]+(?:-[a-z0-9]+)*$`.

Override the derived public slug when needed:

```bash
./deploy/server/publish-blog-post.sh 01-my-post --public-slug my-post
```

## Output convention

Written to the public blog repo checkout when `--apply` is used (using the **public slug**):

| Asset | Path |
|-------|------|
| Jekyll post | `_posts/YYYY-MM-DD-<public-slug>.md` |
| Image | `assets/images/<public-slug>.png` |

Frontmatter includes `layout`, `title`, `date`, `categories`, `tags`, `description`, and `image: /assets/images/<public-slug>.png`.

When the intended URL date would be **future-relative** to publish execution time, Jekyll would exclude the post from the site build (GitHub Pages does not enable `future: true`). Flow A and bridge `--apply` therefore write a **safe publication timestamp** (`date` at or before execution time) and add an explicit `permalink` preserving the intended `/YYYY/MM/DD/<public-slug>/` path. The `_posts/` filename and reported `public_url` still use the **intended URL date**.

When the intended URL date is already safe, `date` uses `YYYY-MM-DD 00:00:00 -0500` as before and no `permalink` is added.

**Do not manually edit public-repo `date` or `permalink` after a normal Flow A publish** — the bridge computes Jekyll-safe values automatically. Manual edits are only for exceptional recovery.

Optional bridge parameter `on_future_date=fail` rejects future-relative intended dates with error code `blog_publish_future_date_requires_scheduled_execution` instead of adjusting (Flow A uses `adjust` by default).

### Metadata expectations

Before real publication, source posts in `blog-posts/ready/` should already include appropriate `categories` and `tags`. The helper preserves them when present and defaults to empty lists when absent; it does not fabricate taxonomy.

`status` is editorial-only (for example `draft` in the internal workspace) and is **not** written to the public Jekyll post.

When `description` is missing or empty, a non-empty source `subtitle` is used as the public `description` fallback. The helper does not invent descriptions from body content or other fields.

Expected public URL:

`https://silverman.pro/YYYY/MM/DD/<public-slug>/`

For the ordering-prefix example above:

`https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/`

## Environment variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` | No | `./data/silverman-blog-linkedin` | Editorial workspace root |
| `SILVERMAN_GITHUB_PAGES_REPO_PATH` | **Yes** | — | Local clone of `silverberdi.github.io` |
| `SILVERMAN_SITE_URL` | No | `https://silverman.pro` | Canonical public site URL |

### Example paths

**Local Mac development:**

```bash
export SILVERMAN_BLOG_LINKEDIN_BASE_PATH="$PWD/data/silverman-blog-linkedin"
export SILVERMAN_GITHUB_PAGES_REPO_PATH="$HOME/src/silverberdi.github.io"
```

**Ubuntu server:**

```bash
export SILVERMAN_BLOG_LINKEDIN_BASE_PATH="/home/silverman/compartido_mac/silverman-blog-linkedin"
export SILVERMAN_GITHUB_PAGES_REPO_PATH="/home/silverman/src/silverberdi.github.io"
```

Confirm the public repo clone path on the server before first use.

## Dry-run (default)

Preview planned outputs without writing files:

```bash
./deploy/server/publish-blog-post.sh 01-why-i-did-not-start-with-the-database
```

Or directly:

```bash
python -m silverman_blog_linkedin.github_pages_publish 01-why-i-did-not-start-with-the-database
```

With an explicit publication date:

```bash
./deploy/server/publish-blog-post.sh 01-why-i-did-not-start-with-the-database --date 2026-07-06
```

Example output:

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

Dry-run validates sources, repo layout, slug safety, and non-overwrite constraints. If a target post or image already exists, the helper exits with an error and writes nothing.

## Apply mode

Write prepared files after reviewing dry-run output:

```bash
./deploy/server/publish-blog-post.sh 01-why-i-did-not-start-with-the-database --date 2026-07-06 --apply
```

Apply copies the PNG and writes normalized Jekyll Markdown. Source files in `blog-posts/ready/` are not modified, moved, or deleted.

When the worker publish flow (`POST /publish-blog-post`) runs before bridge apply, it may already copy the hero image into `assets/images/<public-slug>.png` via automatic public asset handoff. In that case, bridge apply reuses the matching public image and writes only the `_posts/` Markdown file. Manual image copy is not required for normal Flow A automation.

## Automatic public asset handoff (Flow A worker)

During `POST /publish-blog-post`, the worker evaluates blog image prerequisites **before** validation and bridge apply:

1. **Public asset is canonical for Jekyll.** If `assets/images/<public-slug>.png` already exists in the configured public repo checkout (`SILVERMAN_GITHUB_PAGES_REPO_PATH`), the worker reuses it and does not call ComfyUI solely because the editorial ready sibling PNG is missing.
2. **Ready sibling adoption.** If `blog-posts/ready/<source-slug>.png` exists but the public asset is missing, the worker copies it into `assets/images/<public-slug>.png` automatically (no manual `cp`, no ComfyUI).
3. **ComfyUI generation.** When no reusable public or local PNG exists and ComfyUI generation is enabled, the worker generates the editorial PNG, then immediately hands it off to the public repo asset path.
4. **Optional ready sibling backfill.** When only the public asset exists, the worker may copy it back to `blog-posts/ready/<source-slug>.png` for bridge compatibility. Backfill failure is a non-blocking warning when publish can proceed using the public asset.
5. **Front matter.** Canonical Jekyll path is always `image: /assets/images/<public-slug>.png`.

### Retry behavior

Retries reuse existing valid public or local PNGs. ComfyUI is not invoked again when:

- the public asset already exists, or
- a prior run wrote the ready sibling PNG but publish failed before completion (the worker adopts the sibling into public assets on retry).

### Troubleshooting `blog_image_public_asset_handoff_failed`

This stable error means the worker could not copy or adopt into `assets/images/<public-slug>.png` (permissions, missing `assets/images/` layout, I/O error, or unset `SILVERMAN_GITHUB_PAGES_REPO_PATH` when handoff is required).

Checklist:

- Confirm `SILVERMAN_GITHUB_PAGES_REPO_PATH` points at a valid `silverberdi.github.io` checkout with `_posts/` and `assets/images/`.
- Ensure the worker process user can write to `assets/images/` (readable copied files use mode `0644`).
- Retry after fixing permissions; existing valid PNGs are reused without duplicate ComfyUI generation.

## Manual git commit and push (fallback)

When automatic Git publication is disabled or not opted in, commit and push manually after a successful handoff:

```bash
cd "$SILVERMAN_GITHUB_PAGES_REPO_PATH"
git status
git diff
git add _posts/2026-07-06-why-i-did-not-start-with-the-database.md assets/images/why-i-did-not-start-with-the-database.png
git commit -m "Add blog post: why-i-did-not-start-with-the-database"
git push origin main
```

GitHub Pages rebuilds from the pushed commit. The CLI helper does not automate git operations.

## Automatic Git publication (worker)

When **both** `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true` and request opt-in `git_publication: true` are set, the worker may commit and push only the two publication artifact paths after successful blog handoff (`POST /publish-blog-post` or calendar `POST /editorial-calendar/execute-flow-a-due`).

- Environment enablement alone does **not** trigger Git publication.
- Scoped staging: only `_posts/YYYY-MM-DD-<public-slug>.md` and `assets/images/<public-slug>.png`.
- Handoff success with Git failure returns overall `status: partial` (not `failed`).
- Git publication includes `git fetch` and fast-forward-only reconciliation before push; non-fast-forward divergence returns `blog_git_publication_remote_diverged`.
- Optional live-site confirmation: when **both** `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED=true` and request opt-in `live_site_confirmation: true` are set after successful Git push, the worker HTTP-probes publish-confirmed `source_public_url` and records `blog_live_site_publication` metadata. Push success with probe failure returns overall `status: partial`.

### Deploy key prerequisite (operator)

1. Create a repository-scoped GitHub deploy key for `silverberdi.github.io` with write access for push.
2. Store the private key only on the server (for example under the worker secrets directory).
3. Mount the key read-only into the worker container and configure SSH for Git (for example `GIT_SSH_COMMAND` with the mounted key path).
4. Do not commit keys, tokens, or credential contents to git, docs, HTTP responses, or campaign metadata.

Verify `git --version` succeeds inside the built worker container after deploy.

### Git publication environment variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED` | No | `false` | Master enablement (fail closed) |
| `SILVERMAN_BLOG_GIT_PUBLICATION_BRANCH` | No | `main` | Target branch |
| `SILVERMAN_BLOG_GIT_PUBLICATION_REMOTE` | No | `origin` | Target remote |
| `SILVERMAN_BLOG_GIT_COMMIT_MESSAGE_TEMPLATE` | No | `Add blog post: {public_slug} ({campaign_id})` | Commit message template |
| `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED` | No | `false` | Master enablement for HTTP live-site probe after Git push |
| `SILVERMAN_BLOG_LIVE_SITE_PROBE_TIMEOUT_SECONDS` | No | `10` | Per-attempt probe timeout |
| `SILVERMAN_BLOG_LIVE_SITE_PROBE_MAX_ATTEMPTS` | No | `5` | Probe retry budget |
| `SILVERMAN_BLOG_LIVE_SITE_PROBE_RETRY_DELAY_SECONDS` | No | `2` | Delay between probe attempts |

## JSON output

For scripting or inspection:

```bash
python -m silverman_blog_linkedin.github_pages_publish 01-why-i-did-not-start-with-the-database --date 2026-07-06 --json
```

## Safety rules

- Default is dry-run; writes require explicit `--apply`.
- Refuses to overwrite existing `_posts/YYYY-MM-DD-<public-slug>.md` or `assets/images/<public-slug>.png`.
- Does not modify editorial sources under `blog-posts/ready/`.
- Does not expose secrets in output.

## Related docs

- Worker HTTP endpoints (LinkedIn pipeline): [README.md](../../README.md)
- Architecture phasing: [docs/context/backlog-and-phasing.md](../context/backlog-and-phasing.md)
- ADR-0001 (worker over Execute Command): [docs/decisions/ADR-0001-use-worker-instead-of-n8n-execute-command.md](../decisions/ADR-0001-use-worker-instead-of-n8n-execute-command.md)
