## Context

### Current state

Flow A package generation (`linkedin_package_flow.py` → `generate_linkedin_package()` / `POST /generate-linkedin-package`) produces multi-variant LinkedIn derivative artifacts and campaign metadata with publish-confirmed `source_public_url`. It does not record structured article preview metadata from the blog hero image.

LinkedIn publication (`publish_linkedin_due_variants()`) remains a separate, opt-in capability per `linkedin-publication-integration` and is **out of scope** for this change.

Blog posts use front matter `image: /assets/images/<public_slug>.png` and publish to the public Jekyll site at [silverman.pro](https://silverman.pro). When `SILVERMAN_GITHUB_PAGES_REPO_PATH` is configured, the worker can verify the public asset file exists locally before marking preview status `available`.

### Policy references

- Package generation: `openspec/specs/linkedin-derivative-package-generation/spec.md`, `linkedin_package_flow.py`
- Blog images and public paths: `github-pages-blog-publishing`, archived `blog-image-public-asset-handoff`, active/proposed `comfyui-blog-image-generation`
- Flow A umbrella: `openspec/specs/flow-a-automatic-publishing/spec.md`
- LinkedIn publication (unchanged by this change): `openspec/specs/linkedin-publication-integration/spec.md`
- ADR-0001: worker HTTP boundary; n8n does not resolve preview metadata directly in this change

## Goals / Non-Goals

**Goals:**

- During package generation, resolve and record article preview metadata from blog front matter and campaign context.
- Normalize site-root-relative image paths to absolute HTTPS `public_image_url` on the configured site base (default `https://silverman.pro`).
- Validate public image file existence when public repo path is configured.
- Use preview status values: `available`, `missing`, `skipped`, `invalid`.
- Warn (not fail package generation) when preview metadata is incomplete, using stable warning codes.
- Preserve existing package generation eligibility, idempotency, lifecycle transitions, and scheduling behavior.

**Non-Goals:**

- LinkedIn Images API upload, direct media upload, or any LinkedIn API call.
- OG metadata HTTP fetch/scraping at package generation or publish time.
- `publish_linkedin_due_variants()` preview integration, `linkedin_explicit` / `og_metadata` / `auto` strategies.
- Fail-closed publication semantics, LinkedIn token requirements, or `SILVERMAN_LINKEDIN_PREVIEW_*` env vars.
- Smoke-script reporting for real LinkedIn preview publication.
- n8n activation; cron; `--real-publish`; modifying archived changes.

## Decisions

### 1. Metadata at package generation, not publish time

**Decision:** Resolve article preview metadata inside `generate_linkedin_package()` and persist it on `linkedin_package` and per-variant entries. Do not modify `publish_linkedin_due_variants()` or `linkedin_publication` publish metadata in this change.

**Rationale:** Immediate operator need is visible, canonical preview fields on generated packages. Publication-time visual strategies are a separate, higher-risk slice.

**Alternatives considered:** Implement full publish-time preview in the same change — rejected; scope too broad and not formally approved.

### 2. Image URL resolution

**Decision:** Resolve preview fields as:

| Field | Source |
|-------|--------|
| `public_image_path` | Front matter `image` when it matches `/assets/images/<slug>.png` site-root-relative pattern |
| `public_image_url` | `{site_base_url}{public_image_path}` where `site_base_url` defaults to `https://silverman.pro` (no trailing slash) |
| `article_title` | Blog front matter `title` when available |
| `article_description` | Blog front matter `description` or excerpt equivalent when available |
| `public_url` | Campaign publish-confirmed `source_public_url` |

**Rationale:** Aligns with `github-pages-blog-publishing` and existing publish settings; no network fetch required.

### 3. Public repo existence validation

**Decision:** When `SILVERMAN_GITHUB_PAGES_REPO_PATH` is set, verify `assets/images/<public_slug>.png` exists under that checkout before status `available`. When unset, skip filesystem validation and set status `skipped` (metadata still resolved from front matter when valid).

When configured and file missing, set status `missing` and add stable warning `linkedin_article_preview_public_image_missing`. Package generation still completes.

Invalid front matter `image` paths set status `invalid` with `linkedin_article_preview_image_invalid`. Missing/unparseable image path sets `missing` with `linkedin_article_preview_image_missing`.

**Rationale:** Operators need a trustworthy `available` signal without blocking derivative generation when images are still in flight.

### 4. Module split

**Decision:**

| Module | Responsibility |
|--------|----------------|
| `linkedin_article_preview.py` (or equivalent) | `resolve_linkedin_article_preview(...)`, path normalization, optional public-repo check, `LinkedInArticlePreviewMetadata` dataclass |
| `linkedin_package_flow.py` (extend) | Invoke resolver once per package run; attach `article_preview` to result, campaign `linkedin_package`, and per-variant metadata |

No `linkedin_image_client.py`, no `linkedin_preview_flow.py` publish planner, no OG HTTP client in this change.

### 5. No new publication configuration

**Decision:** This change introduces no `SILVERMAN_LINKEDIN_PREVIEW_*` environment variables. Reuse existing `SILVERMAN_GITHUB_PAGES_REPO_PATH` and site URL configuration only.

**Rationale:** Metadata resolution is always attempted during package generation; incomplete preview surfaces as status + warnings, not gated by a publication flag.

### 6. Package generation must not fail on incomplete preview

**Decision:** Incomplete or missing preview metadata MUST NOT change package `status` from `completed` when variant generation otherwise succeeds. Warnings carry stable codes; operators review `article_preview.status` and `warnings[]`.

**Rationale:** Preview metadata is additive; blocking packages would regress Flow A Core.

### 7. HTTP boundary unchanged

**Decision:** No new endpoints. Extend existing `POST /generate-linkedin-package` response with `article_preview` and per-variant preview summary fields. Request body unchanged.

**Rationale:** n8n and Flow A connectors already call package generation; additive response fields are sufficient.

### 8. Test strategy

**Decision:** Tests in `tests/test_linkedin_package_generation.py` (and fixtures as needed) cover:

- valid front matter → `available` when public file exists
- missing public file when repo configured → `missing` + warning, package still `completed`
- repo not configured → `skipped`
- invalid image path → `invalid`
- absolute `public_image_url` normalization
- no LinkedIn API, no OAuth, no HTTP OG fetch

## Deferred (future change)

The following were removed from this change and belong in a future publication-time follow-up (for example `linkedin-article-preview-publication`):

- LinkedIn Images API upload and `linkedin_image_urn`
- `og_metadata` / `linkedin_explicit` / `auto` strategies and OG HTTP sufficiency checks
- `publish_linkedin_due_variants()` integration and fail-closed `preview_required` semantics
- `SILVERMAN_LINKEDIN_PREVIEW_*` configuration and smoke-script preview reporting

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Package generated before public image handoff completes | Status `missing` + warning; operator can re-run idempotent package generation after publish/handoff |
| Front matter `image` out of sync with public asset | Public-repo check when configured; stable `invalid` / `missing` codes |
| Operators confuse metadata with LinkedIn upload | Docs state metadata-only; no API calls; publication remains disabled by default |

## Migration Plan

1. Implement resolver and package-flow integration behind additive metadata fields (no behavior change to scheduling or publication).
2. Run `pytest` and staging package generation; confirm `article_preview` on campaign JSON and HTTP response.
3. Operators use preview metadata for review; publication-time preview implemented only in a future approved change.

## Open Questions

- Whether idempotent package re-runs should refresh `article_preview` when a previously `missing` public image later exists (default: yes on non-idempotent-short-circuit regeneration paths; idempotent return SHOULD include stored preview metadata).
