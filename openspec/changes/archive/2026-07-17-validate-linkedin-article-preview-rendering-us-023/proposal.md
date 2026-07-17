# Proposal: validate-linkedin-article-preview-rendering-us-023

**Backlog item:** BL-009 — Validate LinkedIn Article Preview Rendering (`docs/product/backlog.md`)
**User story:** US-023 — "As a content operator, I want to verify title and description, so that published LinkedIn posts display the intended article preview." (`docs/product/user-stories.md`)

## Why

v1 LinkedIn publication is a text-only post via the REST Posts API; LinkedIn derives any article preview from the public blog URL's Open Graph metadata — the worker uploads no image bytes. Package generation already records `linkedin_package.article_preview` (title, description, `public_image_url`, `public_url`) and validates public-checkout image existence, but nothing verifies that the **live public site** actually serves matching Open Graph title/description tags or that the preview image URL is reachable over HTTP. Until that verification exists, the operator cannot know before (or after) a LinkedIn publish whether the intended preview inputs are correct, and BL-009/US-023 cannot progress.

## Goals

- Give the operator a repeatable, on-demand verification of the article preview **inputs** for one campaign:
  1. **Title and description verification** — package `article_preview.article_title` / `article_description` compared against (a) the canonical post front matter in the public GitHub Pages checkout when configured, and (b) the `og:title` / `og:description` meta tags served by the live `public_url`.
  2. **Image availability verification** — `public_image_url` reachable over HTTPS (success status, image content type) and consistent with the live page's `og:image` when present.
- Report a clear pass/fail/blocked outcome per check and overall, with stable machine-readable codes distinguishing missing metadata, missing/unreachable public image, and mismatched title/description.
- Optionally persist a timestamped validation evidence block on the campaign metadata (skipped under dry-run) so the outcome is traceable.

## Non-goals

- **US-024 territory (explicit boundary):** confirming how LinkedIn actually renders the preview, LinkedIn Post Inspector usage, and LinkedIn cache/metadata issue diagnosis are out of scope. This change makes **no LinkedIn API calls** and reads no LinkedIn OAuth tokens.
- **US-025 territory:** defining a fallback when the preview is incorrect.
- No change to package generation behavior (`POST /generate-linkedin-package`), publish-due behavior, variant lifecycle, or enablement guards.
- No new environment variables, no n8n workflow changes, no deploy script changes, no image upload.

## What Changes

- Add a new worker capability that verifies article preview inputs for a single Flow A campaign that has a generated LinkedIn package:
  - New guarded HTTP endpoint `POST /validate-linkedin-article-preview` (worker HTTP only, ADR-0001; `require_api_key` auth like sibling endpoints; `dry_run` default `true`).
  - New service module performing four checks: package preview metadata presence/completeness, public-checkout front matter consistency (when `SILVERMAN_GITHUB_PAGES_REPO_PATH` is configured; otherwise skipped), live-page Open Graph tag verification via HTTP GET of `public_url`, and HTTP availability of `public_image_url`.
  - Stable outcome codes for every failure/blocked condition; overall status `passed` / `failed` / `blocked`.
  - Evidence persistence: a `linkedin_article_preview_validation` block written to campaign metadata on real runs only; dry-run performs the same read-only checks without mutating campaign metadata.
- Documentation updates: `docs/deployment/linkedin-publication-prerequisites.md` (operator procedure), `docs/CURRENT-STATE.md` (capability status, qualified language), `docs/product/user-stories.md` US-023 mapping, `docs/product/progress-checklist.md`.

## Capabilities

### New Capabilities

- `linkedin-article-preview-verification`: on-demand verification of article preview inputs (title, description, public image availability) for a campaign with a generated LinkedIn package, comparing package metadata, public-checkout front matter, and the live public site's Open Graph tags and image URL over HTTP — with stable outcome codes, dry-run-safe evidence handling, and no LinkedIn API involvement.

### Modified Capabilities

_None._ The existing `linkedin-article-preview-image-support` requirements (package-time metadata resolution, no live OG fetch at package time) are unchanged; the new capability references them as its metadata source of truth and lives behind a separate endpoint, so no delta to existing requirements is needed.

## Acceptance criteria addressed (US-023)

- **Verify title and description** — checks 1–3 above (metadata presence, checkout front matter consistency, live OG tags).
- **Verify image availability** — public-checkout existence already covered at package time; this change adds live HTTP availability of `public_image_url` and `og:image` consistency.
- **Outcome visible and understandable** — structured JSON response with per-check results plus optional persisted evidence block.
- **Failures or blocked states clearly communicated** — stable codes distinguishing missing metadata, unreachable public URL/image, and title/description mismatch; `blocked` for missing prerequisites (campaign/package absent).
- **Existing completed work not duplicated or unintentionally changed** — package generation, publication, retry/recovery (US-022), and all existing endpoints are untouched; verification is additive and read-only toward external systems.

### Acceptance criteria intentionally excluded

- None within US-023. US-024 (confirm preview behavior on LinkedIn, cache/metadata issues) and US-025 (fallback definition) are deliberately excluded as separate stories.

## Impact

- **Code:** new service module (e.g. `linkedin_preview_validation.py`) under `src/silverman_blog_linkedin/`; one new route in `main.py`; reuse of `linkedin_article_preview.py` constants and `github_pages_publish` helpers.
- **HTTP surface:** one new authenticated endpoint (ADR-0001 compliant); outbound HTTP GET/HEAD only to the public blog site (`silverman.pro`), never to `api.linkedin.com`.
- **Data:** additive `linkedin_article_preview_validation` block on `metadata/campaigns/<campaign-id>.json` (real runs only); no changes to existing fields, no variant body text, no secrets.
- **Config:** reuses existing `SILVERMAN_GITHUB_PAGES_REPO_PATH` / site URL configuration; no new env vars.
- **Tests:** new unit suite with mocked HTTP (no live network in default pytest); existing suites unchanged.
- **Docs:** prerequisites doc, CURRENT-STATE, user stories, progress checklist.
- **Operations:** implemented ≠ deployed ≠ operationally validated — deploy to `192.168.0.194` and live validation remain separate, approval-gated steps outside this change's implementation scope.
