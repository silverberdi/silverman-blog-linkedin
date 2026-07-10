## 0. Preconditions (before implementation)

- [x] 0.1 Confirm Flow A blog publish records publish-confirmed `source_public_url` and blog posts use front matter `image` path convention per `github-pages-blog-publishing`
- [x] 0.2 Confirm `SILVERMAN_GITHUB_PAGES_REPO_PATH` is documented for operators who want public-repo existence validation (optional but recommended on staging/production worker)

## 1. Article preview metadata module

- [x] 1.1 Create `linkedin_article_preview.py` (or equivalent) with `LinkedInArticlePreviewMetadata` dataclass and `resolve_linkedin_article_preview()` entry point
- [x] 1.2 Implement front matter `image` parsing and site-root-relative path validation (`/assets/images/<public_slug>.png`)
- [x] 1.3 Implement `public_image_url` resolution as `{site_base_url}{public_image_path}` (default site base `https://silverman.pro`)
- [x] 1.4 Implement optional public-repo file existence check when `SILVERMAN_GITHUB_PAGES_REPO_PATH` is configured
- [x] 1.5 Map outcomes to status values `available`, `missing`, `skipped`, `invalid` with stable warning codes

## 2. Package generation integration

- [x] 2.1 Integrate `resolve_linkedin_article_preview()` into `generate_linkedin_package()` / `linkedin_package_flow.py`
- [x] 2.2 Add package-level `article_preview` to `LinkedInPackageResult` and campaign `linkedin_package` metadata
- [x] 2.3 Add per-variant preview summary fields (`article_preview_status`, `public_image_url`, `public_image_path`, `article_title`, `article_description`, `public_url` as applicable)
- [x] 2.4 Append stable warning codes to `warnings[]` when preview is incomplete; package generation MUST still complete on success
- [x] 2.5 Preserve existing eligibility, idempotency, lifecycle transitions, and scheduling side-effect boundaries (no `publish_state`, no LinkedIn API)

## 3. HTTP response

- [x] 3.1 Extend `POST /generate-linkedin-package` response with `article_preview` object and per-variant preview summary fields
- [x] 3.2 Ensure response still excludes variant body text, tokens, and image bytes

## 4. Tests

- [x] 4.1 Extend `tests/test_linkedin_package_generation.py` for preview metadata resolution and status mapping
- [x] 4.2 Test `available` when front matter and public repo file exist
- [x] 4.3 Test `missing` when repo configured but public image file absent (package still `completed`)
- [x] 4.4 Test `skipped` when public repo path not configured
- [x] 4.5 Test `invalid` for malformed front matter image paths
- [x] 4.6 Test absolute `public_image_url` normalization from `/assets/images/x.png`
- [x] 4.7 Confirm no LinkedIn API, OAuth, OG HTTP fetch, or media upload in default `pytest` runs

## 5. Operator documentation

- [x] 5.1 Update `docs/deployment/linkedin-publication-prerequisites.md` (or adjacent ops doc) with package-generation article preview metadata semantics — metadata only, not LinkedIn upload
- [x] 5.2 Update README package-generation section with `article_preview` fields and warning behavior

## 6. Validation

- [x] 6.1 Run `openspec validate linkedin-article-preview-image-support --strict` and fix any spec issues
- [x] 6.2 Run full `pytest` and fix regressions
- [x] 6.3 Manual staging dry-run: `POST /generate-linkedin-package` returns `article_preview` without LinkedIn API calls

## Deferred (not in this change)

- LinkedIn Images API client (`linkedin_image_client.py`)
- OG metadata fetch and `og_metadata` / `linkedin_explicit` / `auto` strategies
- `publish_linkedin_due_variants()` preview integration
- `SILVERMAN_LINKEDIN_PREVIEW_*` env vars and fail-closed publication semantics
- Smoke-script preview publication reporting
