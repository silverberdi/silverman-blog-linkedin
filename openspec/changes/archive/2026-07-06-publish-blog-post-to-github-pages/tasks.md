## 1. Dependencies and module scaffold

- [x] 1.1 Add `pyyaml` to `pyproject.toml` project dependencies
- [x] 1.2 Create `src/silverman_blog_linkedin/github_pages_publish.py` with CLI argument parsing (`slug`, `--date`, `--apply`, optional `--json`)
- [x] 1.3 Load configuration from `SILVERMAN_BLOG_LINKEDIN_BASE_PATH`, `SILVERMAN_GITHUB_PAGES_REPO_PATH`, and `SILVERMAN_SITE_URL` (default `https://silverman.pro`)

## 2. Validation and path safety

- [x] 2.1 Implement slug validation (`^[a-z0-9]+(?:-[a-z0-9]+)*$`) with clear error messages
- [x] 2.2 Validate `blog-posts/ready/<slug>.md` and `blog-posts/ready/<slug>.png` exist and are readable regular files under the editorial base path
- [x] 2.3 Validate public blog repo checkout exists and contains `_posts/` and `assets/images/` directories
- [x] 2.4 Resolve all paths with traversal checks (`is_relative_to` editorial ready dir and repo root)

## 3. Transform and publish logic

- [x] 3.1 Implement publication date handling (default UTC today; parse and validate `--date YYYY-MM-DD`)
- [x] 3.2 Implement target path generation: `_posts/YYYY-MM-DD-<slug>.md` and `assets/images/<slug>.png`
- [x] 3.3 Implement public URL calculation: `https://silverman.pro/YYYY/MM/DD/<slug>/`
- [x] 3.4 Implement frontmatter parse/merge/write preserving Markdown body; set `image` to `/assets/images/<slug>.png` and required Jekyll fields
- [x] 3.5 Implement non-overwrite checks for both target post and image paths; fail before any write
- [x] 3.6 Implement dry-run mode (default): print structured summary without writing files
- [x] 3.7 Implement apply mode (`--apply`): copy PNG and write prepared Markdown to public repo checkout

## 4. Operator entry point

- [x] 4.1 Add `deploy/server/publish-blog-post.sh` thin wrapper invoking the Python module with documented env vars
- [x] 4.2 Ensure script exits non-zero on validation, conflict, or missing-config errors

## 5. Tests

- [x] 5.1 Add `tests/test_github_pages_publish.py` with temp editorial tree and fake public repo checkout
- [x] 5.2 Test slug validation (accept safe slugs; reject unsafe slugs)
- [x] 5.3 Test `_posts/YYYY-MM-DD-<slug>.md` filename generation with default and explicit dates
- [x] 5.4 Test image path convention and frontmatter `image: /assets/images/<slug>.png`
- [x] 5.5 Test public URL generation for known slug and date
- [x] 5.6 Test non-overwrite refusal when post or image target already exists
- [x] 5.7 Test dry-run creates no files; apply mode writes expected outputs
- [x] 5.8 Test source files in `blog-posts/ready/` remain unchanged after apply

## 6. Documentation

- [x] 6.1 Add `docs/workflows/blog-publishing-bridge.md` with operator workflow: paths, env vars, dry-run/apply examples, manual git commit/push steps
- [x] 6.2 Update `README.md` with brief pointer to the blog publishing bridge (no HTTP endpoint)

## 7. Validation

- [x] 7.1 Run full test suite (`pytest`) and ensure all tests pass
- [x] 7.2 Run `openspec validate publish-blog-post-to-github-pages`
- [x] 7.3 Manual smoke test: dry-run locally against sample `<slug>.md` + `<slug>.png` and fake public repo checkout; verify summary output and no writes

## 8. Source slug vs public slug adjustment

- [x] 8.1 Derive public slug from source slug (strip leading `^\d+-` ordering prefix by default)
- [x] 8.2 Add optional `--public-slug` override with validation
- [x] 8.3 Use source slug for editorial reads only; public slug for `_posts/`, `assets/images/`, frontmatter, URL, and derived title
- [x] 8.4 Include `source_slug` and `public_slug` in dry-run/apply and JSON summaries
- [x] 8.5 Update tests, OpenSpec artifacts, and operator documentation

## 9. Public metadata cleanup

- [x] 9.1 Remove editorial `status` from published frontmatter
- [x] 9.2 Fall back `description` to non-empty source `subtitle` when description is absent or empty
- [x] 9.3 Preserve categories/tags when present; default to empty lists; do not fabricate taxonomy
- [x] 9.4 Update tests, OpenSpec spec delta, and operator documentation
