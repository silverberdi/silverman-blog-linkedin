## Context

### Current state

Flow A LinkedIn publication (`linkedin_publication_flow.py` → `publish_linkedin_due_variants()`) publishes personal-profile **text posts** via `create_member_text_post()` in `linkedin_client.py`. Commentary is variant text plus `source_public_url`. The canonical spec explicitly forbids image upload and company pages.

A real publication succeeded but appeared on LinkedIn as plain text with a URL—no link preview card—despite the live blog having a canonical hero image at `/assets/images/<public_slug>.png` (1200×900, 4:3) exposed through the Jekyll theme at [silverman.pro](https://silverman.pro).

### Dependency

OpenSpec change `comfyui-blog-image-generation` (proposed) ensures every Flow A ready post can receive a canonical blog image before publish when generation is enabled. **This change MUST NOT be implemented until `comfyui-blog-image-generation` is validated and archived.** After that, Flow A campaigns will reliably have:

- front matter `image: /assets/images/<public_slug>.png`
- companion PNG in editorial workspace and public `assets/images/` after blog publish
- publish-confirmed `source_public_url` in campaign metadata

### Policy references

- LinkedIn publication: `openspec/specs/linkedin-publication-integration/spec.md`, `linkedin_publication_flow.py`, `linkedin_client.py`
- Blog images: proposed `comfyui-blog-image-generation`, `ready-post-editorial-validation`, `github-pages-blog-publishing`
- Flow A umbrella: `openspec/specs/flow-a-automatic-publishing/spec.md`
- ADR-0001: worker HTTP boundary; n8n does not call LinkedIn or fetch OG metadata directly in this change

## Goals / Non-Goals

**Goals:**

- When preview is enabled, publish LinkedIn posts that preserve visual link/article preview when a public blog image exists.
- Support two strategies with explicit selection and `auto` fallback ordering.
- Default **disabled**; dry-run plans strategy and image resolution without LinkedIn API calls.
- When `preview_required` is true, fail closed before publishing a degraded text-only post.
- Record preview strategy, image URL/path, and LinkedIn image URN in `linkedin_publication` metadata.
- Injectable LinkedIn Images API client for tests; no live LinkedIn in default test runs.

**Non-Goals:**

- Implementing in this proposal phase; n8n activation; cron; `--real-publish`.
- Modifying ComfyUI generation, public blog theme, or `silverberdi.github.io` directly.
- Company page publishing, video/carousel media, LinkedIn native scheduling.
- Guaranteed OG crawler behavior (LinkedIn controls link preview rendering for OG strategy).
- Archiving or git commit/push.

## Decisions

### 1. Dependency gate before implementation

**Decision:** Add an explicit OpenSpec dependency on archived `comfyui-blog-image-generation`. Apply phase MUST verify that change is archived before merging runtime code.

**Rationale:** Preview support assumes canonical blog images exist; implementing earlier would encode brittle fallbacks for missing images.

**Alternatives considered:** Soft dependency with optional preview — rejected because it encourages URL-only posts when images are missing.

### 2. Preview strategies: OG metadata vs LinkedIn explicit image

**Decision:** Support three strategy modes via `SILVERMAN_LINKEDIN_PREVIEW_STRATEGY`:

| Mode | Behavior |
|------|----------|
| `og_metadata` | Publish article/link-style post referencing `source_public_url`; rely on live page `og:image`, `og:title`, `og:description`, and canonical URL for LinkedIn crawler preview. |
| `linkedin_explicit` | Upload blog image bytes to LinkedIn Images API (initialize → upload → register), obtain image URN, attach to post payload as supported media/thumbnail reference. |
| `auto` (default when preview enabled) | Attempt `og_metadata` sufficiency check first; if insufficient or validation fails, fall back to `linkedin_explicit` when image bytes are resolvable. |

**Rationale:** OG is zero-upload and matches how most link shares work when metadata is correct. Explicit upload gives control when OG is missing, stale, or LinkedIn crawler does not render the card.

**Alternatives considered:** OG only — rejected; real publication already showed URL-only despite live blog. Explicit only — rejected; higher API surface and scope requirements when OG would suffice.

**Apply-phase note:** Verify exact LinkedIn REST Posts API fields for article/link posts and Images API upload sequence against current official documentation (same discipline as original `linkedin-publication-integration`).

### 3. Public image URL resolution

**Decision:** Resolve preview image URL as:

```
{site_base_url}{front_matter_image}
```

where `site_base_url` defaults to `https://silverman.pro` (from existing publish settings), and `front_matter_image` is `/assets/images/<public_slug>.png` from campaign/blog metadata or processed post record.

For `linkedin_explicit`, download image bytes from the resolved public URL (preferred after blog publish) or read companion PNG from editorial workspace when public fetch is unavailable in dry-run tests.

**Rationale:** Aligns with `github-pages-blog-publishing` and ComfyUI output conventions; public URL is what OG strategy exposes.

### 4. OG sufficiency check (planning and optional gate)

**Decision:** Before choosing `og_metadata`, worker performs a bounded HTTP GET of `source_public_url` (HEAD/GET, configurable timeout) and parses HTML for:

- `og:image` (absolute URL)
- `og:title`
- `og:description`
- canonical link or final URL matching expected blog URL

Mark OG **sufficient** when all four are present and `og:image` resolves to an absolute HTTPS URL. Dry-run reports sufficiency without publishing.

**Rationale:** Prevents selecting OG strategy when the live page would not produce a card; supports `auto` fallback.

**Alternatives considered:** Skip validation and always use OG — rejected given observed production gap.

### 5. Module split

**Decision:**

| Module | Responsibility |
|--------|----------------|
| `linkedin_preview_flow.py` | `plan_linkedin_preview(...)`, `resolve_preview_image_url(...)`, OG sufficiency check, strategy selection, fail-closed gating |
| `linkedin_image_client.py` | Images API upload protocol + `upload_member_image(...)` returning image URN; fake for tests |
| `linkedin_client.py` (extend) | `build_article_post_payload(...)` / `create_member_article_post(...)` alongside existing text post helpers |

`publish_linkedin_due_variants()` calls preview planner before post creation when preview enabled.

**Rationale:** Mirrors `linkedin_client` / `linkedin_publication_flow` separation; keeps image upload testable.

### 6. Configuration (disabled by default)

**Decision:** New environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SILVERMAN_LINKEDIN_PREVIEW_ENABLED` | `false` | Master enable for visual preview path |
| `SILVERMAN_LINKEDIN_PREVIEW_REQUIRED` | `false` | When `true`, block publish if preview cannot be planned/executed |
| `SILVERMAN_LINKEDIN_PREVIEW_STRATEGY` | `auto` | `og_metadata` \| `linkedin_explicit` \| `auto` |
| `SILVERMAN_LINKEDIN_PREVIEW_OG_TIMEOUT_SECONDS` | `10` | Bounded timeout for OG fetch |
| `SILVERMAN_LINKEDIN_PREVIEW_IMAGE_MAX_BYTES` | `10485760` | Reject oversized uploads (10 MiB) |

When `SILVERMAN_LINKEDIN_PREVIEW_ENABLED` is `false`, behavior MUST remain identical to current text-only publication.

### 7. Fail-closed when preview required

**Decision:** If `SILVERMAN_LINKEDIN_PREVIEW_REQUIRED=true` and preview planning or execution fails (missing image URL, OG insufficient in `og_metadata` mode, upload failure in `linkedin_explicit` mode), publish-due MUST NOT call LinkedIn Posts API and MUST return stable error `linkedin_preview_required_blocked_publish`. Variant `publish_state` remains `queued` (configuration/planning failure, not API failure).

If `preview_required=false` and preview fails, fall back to legacy text-only post with warning in response/metadata.

**Rationale:** Prevents accidental degraded URL-only posts when operator expects visual presence.

### 8. Publication metadata shape

**Decision:** Extend `linkedin_publication` object on variant metadata and publish-due per-variant results:

```json
{
  "preview_enabled": true,
  "preview_strategy": "og_metadata",
  "preview_image_url": "https://silverman.pro/assets/images/my-slug.png",
  "preview_image_path": "/assets/images/my-slug.png",
  "linkedin_image_urn": null,
  "og_metadata_sufficient": true
}
```

For `linkedin_explicit`, set `linkedin_image_urn` to registered URN. Never include image bytes or tokens.

### 9. HTTP boundary unchanged

**Decision:** No new HTTP endpoints. Preview integrates into existing `POST /publish-linkedin-due-variants` request/response fields. Optional request override `preview_strategy` MAY be added with `extra="forbid"` model discipline.

**Rationale:** Queue/cancel flow unchanged; preview is a publish-time concern.

### 10. Test strategy

**Decision:** Fake `LinkedInImageClientProtocol` and HTTP client for OG fetch. Tests cover:

- disabled preview → text-only unchanged
- dry-run reports planned strategy
- `og_metadata` sufficient → article payload planned
- `og_metadata` insufficient + `auto` → explicit upload path
- `preview_required` + failure → no API call, variant stays `queued`
- successful explicit upload → URN in metadata
- no live LinkedIn API in default `pytest` runs

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| LinkedIn OG crawler still omits card despite valid metadata | Offer `linkedin_explicit` and `auto` fallback; document Post Inspector / cache refresh for operators |
| Images API requires additional LinkedIn product/scopes | Document prerequisites; explicit strategy fails with stable code; `auto` can still use OG |
| OG fetch adds latency to publish-due | Bounded timeout; optional skip in dry-run; cache not required in v1 |
| Posts API article payload changes | Apply phase verifies against official docs; keep text-only fallback when preview not required |
| Publishing before blog is live breaks OG | Eligibility already requires `source_public_url`; OG check fails closed when page 404 |

## Migration Plan

1. Archive `comfyui-blog-image-generation` and confirm canonical images on live posts.
2. Implement preview modules behind `SILVERMAN_LINKEDIN_PREVIEW_ENABLED=false` (no behavior change).
3. Validate dry-run on staging campaign; confirm planned strategy and image URL.
4. Enable preview in staging with `preview_required=false`; verify link card on test post.
5. Enable `preview_required=true` for production Flow A when operator confident in OG or explicit path.
6. Rollback: set `SILVERMAN_LINKEDIN_PREVIEW_ENABLED=false` to restore text-only behavior.

## Open Questions

- Exact LinkedIn Posts API field for article/link posts with thumbnail URN (verify at apply against current REST docs).
- Whether additional OAuth scopes beyond `w_member_social` are required for Images API in the operator's LinkedIn app.
- Whether campaign metadata should store resolved `public_image_url` at blog-publish time to avoid re-derivation (optional enhancement; v1 may derive at publish-due).
