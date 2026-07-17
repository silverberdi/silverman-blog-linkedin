# Design: validate-linkedin-article-preview-rendering-us-023

## Context

BL-009 / US-023. v1 LinkedIn publication posts text-only commentary containing the variant text and `source_public_url`; LinkedIn builds any article preview from the Open Graph metadata of that public blog URL. The worker already resolves package-time preview metadata (`linkedin_article_preview.py`, canonical spec `linkedin-article-preview-image-support`): `linkedin_package.article_preview` with `article_title`, `article_description`, `public_image_url`, `public_url`, plus checkout-file existence validation when `SILVERMAN_GITHUB_PAGES_REPO_PATH` is set and stable warning codes (`linkedin_article_preview_*`).

What does not exist today: any verification that the **live** public site serves OG title/description tags matching the recorded metadata, or that `public_image_url` is actually reachable over HTTPS. Package-time resolution is deliberately forbidden from fetching the live page ("MUST NOT perform OG metadata HTTP fetch of the live blog page"), because handoff ≠ live. US-023 needs a separate, on-demand verification step that runs after the site is live.

Constraints: ADR-0001 (worker HTTP only), ADR-0002 (blog post canonical), no LinkedIn API calls (US-024 boundary), no new env vars, no n8n changes, no secrets or variant body text in responses.

## Goals / Non-Goals

**Goals:**

- One authenticated worker endpoint that, for a single campaign with a generated LinkedIn package, verifies:
  1. package preview metadata presence and completeness (title, description, `public_image_url`, `public_url`);
  2. consistency of recorded title/description against the canonical post front matter in the public checkout (when configured);
  3. live OG tags (`og:title`, `og:description`, `og:image`) served at `public_url` match the recorded metadata;
  4. HTTP availability of `public_image_url` (2xx + image content type).
- Stable machine-readable outcome codes distinguishing missing metadata, unreachable public URL/image, and mismatched title/description.
- Dry-run-safe: identical checks, no campaign metadata mutation; real runs persist a timestamped evidence block.

**Non-Goals:**

- Confirming LinkedIn's actual rendering, Post Inspector, cache-busting, or LinkedIn API usage (US-024).
- Fallback definition when a preview is wrong (US-025).
- Any change to package generation, publish-due, queue/cancel/correct/defer flows, or enablement guards.
- Re-scraping or forcing LinkedIn to refresh a preview.

## Decisions

### D1 — Worker endpoint, not a standalone script

`POST /validate-linkedin-article-preview` on the FastAPI worker, guarded by `require_api_key` like all sibling LinkedIn endpoints.

- *Why:* the operator already drives every LinkedIn operation over worker HTTP (curl or n8n later); the worker owns campaign metadata reads/writes, so evidence persistence stays inside the established filesystem boundary. A Mac-side script would duplicate metadata parsing and could not persist evidence into the deployed editorial mount. ADR-0001 is respected because this stays HTTP-only.
- *Alternative considered:* `scripts/` operator script — rejected: no clean path to campaign metadata on the server, duplicates existing helpers, and diverges from how every other LinkedIn capability is operated.

### D2 — New capability, no delta to `linkedin-article-preview-image-support`

New canonical capability `linkedin-article-preview-verification`. The existing package-time spec explicitly forbids live OG fetch in its entry point; verification is a different lifecycle moment (post-live, on-demand) with different requirements. Adding it as a delta to the existing capability would blur that boundary and force MODIFIED requirements where no existing behavior changes.

### D3 — Four checks with per-check status and stable codes

Request body: `{"campaign_id": "...", "dry_run": true}` (`dry_run` defaults `true`, matching sibling endpoints). Response carries `status` (`passed` / `failed` / `blocked`), `dry_run`, `campaign_id`, `checks{}`, and flat `codes[]`.

| Check | Source(s) compared | Pass | Fail codes |
|---|---|---|---|
| `package_metadata` | `linkedin_package.article_preview` | block exists with non-empty `article_title`, `article_description`, `public_image_url`, `public_url` | `linkedin_preview_validation_metadata_missing` (block or `public_url` absent), `linkedin_preview_validation_title_missing`, `linkedin_preview_validation_description_missing`, `linkedin_preview_validation_image_url_missing` |
| `checkout_consistency` | package `article_title`/`article_description` vs front matter `title`/`description` of `_posts/` file in `SILVERMAN_GITHUB_PAGES_REPO_PATH` | exact match after whitespace normalization | `linkedin_preview_validation_title_mismatch`, `linkedin_preview_validation_description_mismatch`, `linkedin_preview_validation_checkout_post_missing`; status `skipped` with `linkedin_preview_validation_checkout_not_configured` when repo path unset |
| `live_og_metadata` | HTTP GET `public_url` → parse `og:title`, `og:description`, `og:image` | page 2xx and each present tag matches recorded metadata (whitespace-normalized; `og:image` equals `public_image_url`) | `linkedin_preview_validation_public_url_unreachable`, `linkedin_preview_validation_og_title_mismatch`, `linkedin_preview_validation_og_description_mismatch`, `linkedin_preview_validation_og_image_mismatch`, `linkedin_preview_validation_og_tags_missing` |
| `public_image_availability` | HTTP request to `public_image_url` | 2xx response with `Content-Type: image/*` | `linkedin_preview_validation_public_image_unreachable`, `linkedin_preview_validation_public_image_not_image` |

Blocked (HTTP 200 with `status: blocked`, no checks executed beyond prerequisite detection): campaign not found → `linkedin_preview_validation_campaign_not_found`; no generated LinkedIn package → `linkedin_preview_validation_package_not_generated`. Unknown/invalid request body → HTTP 422 per existing worker validation conventions.

Overall verdict: `passed` when every executed check passes (`skipped` does not fail the run but is reported); `failed` when any check fails; downstream checks still run when earlier ones fail (report everything in one pass), except when `package_metadata` lacks the URL needed by a dependent check — that dependent check reports `skipped` with the missing-metadata code already recorded.

- *Why exact-match after whitespace normalization:* the site templates emit front matter values verbatim into OG tags; normalization only guards against insignificant whitespace/HTML-entity encoding, not semantic drift. Anything else is a real mismatch the operator must see.

### D4 — HTTP boundary and safety

- Outbound requests only to the recorded `public_url` / `public_image_url` origins (expected `https://silverman.pro`); the module MUST refuse non-HTTPS URLs and MUST NOT contact `api.linkedin.com` or read OAuth tokens.
- `httpx` (already a worker dependency) with a bounded timeout (~10 s) and no redirects beyond a small limit; response bodies capped for parsing (OG tags live in `<head>`).
- OG parsing via a small regex/HTML-meta scan over the fetched document head — no new dependency.
- Requests are read-only GETs; the endpoint never mutates the public site, editorial lifecycle folders, variant `publish_state`, or scheduling metadata.

### D5 — Evidence persistence and dry-run semantics

Real runs (`dry_run: false`) write an additive `linkedin_article_preview_validation` block on the campaign document: `{status, checks, codes, validated_at_utc, public_url, public_image_url}` — last-write-wins snapshot (validation is repeatable; historical audit is not a US-023 criterion). Atomic write via the existing campaign-save helper. Dry-run performs identical checks and returns identical response shape (plus `dry_run: true`) with zero campaign mutation. No variant body text, no secrets, no image bytes in metadata or responses.

- *Alternative considered:* append-only history like `linkedin_publication_attempts` — rejected as over-engineering; verification has no once-only budget semantics.

### D6 — Qualified status language

Merging this change means the capability is **implemented (+ unit-tested)** only. Deployment to `192.168.0.194` and a real validation run against the live site are separate approval-gated steps; US-023 acceptance and BL-009 progress are recorded only after the operator demonstrates the outcome. Docs updates must say so explicitly.

## Risks / Trade-offs

- [Live site fetch depends on network/GitHub Pages availability] → transient failures surface as `linkedin_preview_validation_public_url_unreachable` / `_public_image_unreachable`; the operator can simply re-run — no retry loop inside the worker, no false "failed metadata" claims (unreachable is a distinct code from mismatch).
- [GitHub Pages deploy lag: handoff ≠ live] → a run immediately after push may fail legitimately; documented operator guidance is to verify after live-site confirmation (US-002 probe) has passed.
- [OG parsing via regex could miss exotic HTML] → the public site is our own Jekyll template with stable, well-formed meta tags; if a tag is genuinely absent, `linkedin_preview_validation_og_tags_missing` is the honest signal. No HTML-parser dependency added.
- [Description source ambiguity: front matter `description` vs excerpt] → package metadata already resolves this at generation time (`article_description`); verification compares against that recorded value and against checkout front matter `description`, mirroring `linkedin_article_preview.py` semantics rather than inventing a new derivation.
- [Endpoint is unauthenticated outbound HTTP from the worker] → target origin is restricted to the recorded public site URLs (HTTPS only); no credentials attached to outbound requests.
- [US-024 scope creep] → hard boundary in spec: no LinkedIn API calls, no token reads, no preview-rendering claims. Passing this validation means the **inputs** LinkedIn would scrape are correct — it does not confirm LinkedIn's rendering or cache state.

## Migration Plan

Additive only: new module, one new route, additive metadata block. No schema migration, no backfill, no rollback concerns beyond reverting the commit. Deploy is a separate approval-gated step; no deploy scripts change.

## Open Questions

None blocking. If the operator later wants n8n orchestration of this check, that is a separate change (no n8n changes here).
