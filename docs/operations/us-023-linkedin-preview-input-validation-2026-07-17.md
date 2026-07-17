# US-023 — LinkedIn article preview input verification: operational validation (2026-07-17)

**Host:** `192.168.0.194`
**Deployed revision:** `BUILD_REVISION=d15d85b0c5827cc8d0a4fdb5038b01530a009f87` (HEAD after US-025 archive; container env and `.build_git_sha` match)
**Worker:** `http://192.168.0.194:8010`; `verify-worker-deploy.sh` OVERALL PASS (12 checks); OpenAPI exposes `POST /validate-linkedin-article-preview`
**Operator approval:** deploy, live-site remediation commit/push, and real validation runs explicitly approved in session 2026-07-17

## Scope

Operational demonstration of `POST /validate-linkedin-article-preview` (US-023 / BL-009 story 1) against real campaigns and the live site, including a real failure detection, input remediation on the public blog repo, and passing re-verification with persisted evidence. No LinkedIn API calls at any step (US-024 boundary).

## Campaigns

Only the two 2026-07-15 campaigns have `linkedin_package.article_preview.status = available`:

| Campaign | `article_preview` |
|----------|-------------------|
| `flow-a-2026-07-15-keep-contracts-boring` | `available` |
| `flow-a-2026-07-15-search-is-not-one-model` | `available` |

The 2026-07-10 campaigns carry `status = skipped` (`linkedin_article_preview_public_repo_not_configured` at package-generation time) and were excluded — `package_metadata` prerequisites are not met for them by design.

## Timeline and results

### 1. Initial dry-run — real failure detected (both campaigns)

`dry_run: true` (default) returned `status: failed` with identical codes on both campaigns:

- `linkedin_preview_validation_og_tags_missing` — live pages had **no `og:image` tag at all**
- `linkedin_preview_validation_og_description_mismatch` — `og:description` rendered the post title, not the front-matter description

Per-check detail: `package_metadata` passed, `checkout_consistency` passed, `live_og_metadata` failed, `public_image_availability` passed. Campaign documents verified **byte-identical** (sha256 pre/post) — dry-run zero mutation confirmed.

### 2. Root cause (public blog repo `silverberdi.github.io`)

`_layouts/default.html` built `og:description` from `page.excerpt` (which resolves to the leading `# Title` heading) instead of `page.description`, and emitted no `og:image` despite front matter carrying `image:`. `_config.yml` `url` also pointed at `https://silverberdi.github.io` instead of the canonical `https://silverman.pro` (affects `absolute_url` and `og:url`).

### 3. Remediation (approved live-site change)

Commit `e4d10de` on `silverberdi.github.io` `main` (pushed with the repository deploy key):

- `og:description` / `twitter:description` / `meta name="description"` prefer `page.description`, falling back to excerpt then `site.description`
- added `og:image` and `twitter:image` from `page.image | absolute_url` (emitted only when `page.image` is set)
- `_config.yml` `url` set to `https://silverman.pro`

GitHub Pages deploy confirmed live ~40s after push: `og:description` = front-matter description, `og:image` = `https://silverman.pro/assets/images/keep-contracts-boring.png`, `og:url` on `silverman.pro`.

### 4. Passing dry-run after remediation

Both campaigns: `status: passed`, `codes: []`, `metadata_written: false`.

### 5. Real runs — evidence persisted

`dry_run: false` on both campaigns: `status: passed`, `metadata_written: true`. Persisted `linkedin_article_preview_validation` blocks show `status: passed` with `validated_at` `2026-07-17T18:11:32Z` / `2026-07-17T18:11:33Z`. Pre/post JSON comparison (evidence block excluded) confirmed **no other campaign field changed**.

## Acceptance-criteria demonstration mapping

| Criterion | Operational evidence |
|-----------|----------------------|
| Verify title and description | `live_og_metadata` failed with real mismatch, passed after remediation; `checkout_consistency` passed against `_posts/` front matter |
| Verify image availability | `public_image_availability` passed (HTTPS 2xx, `image/*`); missing `og:image` detected and remediated |
| Outcome visible and understandable | Structured `status`/`checks{}`/`codes[]` responses; persisted evidence block on real runs only |
| Failures or blocked states clearly communicated | Stable codes `linkedin_preview_validation_og_tags_missing`, `linkedin_preview_validation_og_description_mismatch` observed on a real failure |
| Existing work unchanged | Dry-run byte-identical documents; real runs changed only the evidence block; no LinkedIn API calls, no variant/schedule/publication changes |

## Qualified status

- US-023 **operationally validated** on real campaigns and the live site; no LinkedIn API involvement — passing means the inputs LinkedIn would scrape are correct, not that LinkedIn renders the preview (US-024).
- BL-009 remains open: US-024 (rendering confirmation via Post Inspector — manual operator step) and US-025 (fallback demonstration) are still pending.
- The 2026-07-10 campaigns keep `article_preview.status = skipped`; regenerating their packages was out of scope.
