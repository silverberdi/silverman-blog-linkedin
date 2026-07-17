# Tasks: validate-linkedin-article-preview-rendering-us-023

## 1. Pre-implementation inspection

- [x] 1.1 Re-read `openspec/specs/linkedin-article-preview-image-support/spec.md`, `src/silverman_blog_linkedin/linkedin_article_preview.py`, `linkedin_package_flow.py`, and the campaign-save helper to confirm reuse points (constants, front matter parsing, atomic campaign writes) and confirm no package-time behavior is touched.
- [x] 1.2 Confirm `httpx` is already an installed worker dependency usable for outbound GETs with timeout; identify the existing pattern for mocking HTTP in tests (no new dependencies).

## 2. Verification service module

- [x] 2.1 Create `src/silverman_blog_linkedin/linkedin_preview_validation.py` with stable code constants (`linkedin_preview_validation_*` per delta spec), check/verdict status constants, and a serializable result structure (`status`, `campaign_id`, `dry_run`, `checks{}`, `codes[]`).
- [x] 2.2 Implement prerequisite resolution: load campaign by `campaign_id`; return `blocked` with `linkedin_preview_validation_campaign_not_found` / `linkedin_preview_validation_package_not_generated` without any outbound HTTP.
- [x] 2.3 Implement `package_metadata` check over `linkedin_package.article_preview` (missing block/`public_url`, missing title, missing description, missing image URL codes).
- [x] 2.4 Implement `checkout_consistency` check against `_posts/` front matter under `SILVERMAN_GITHUB_PAGES_REPO_PATH` (whitespace-normalized exact compare; `skipped` + `linkedin_preview_validation_checkout_not_configured` when unset; `linkedin_preview_validation_checkout_post_missing` when file absent).
- [x] 2.5 Implement `live_og_metadata` check: HTTPS-only GET of `public_url` with bounded timeout, OG tag extraction (`og:title`, `og:description`, `og:image`), unreachable vs missing-tags vs per-field mismatch codes.
- [x] 2.6 Implement `public_image_availability` check: HTTPS request to `public_image_url`, 2xx + `image/*` content type, unreachable vs not-image codes, no image bytes retained.
- [x] 2.7 Implement overall verdict aggregation (all executed checks run in one pass; dependent checks `skipped` when required metadata is missing; `skipped` never fails a run) and evidence persistence: additive `linkedin_article_preview_validation` block written atomically on real runs only; dry-run and blocked runs persist nothing.

## 3. HTTP endpoint

- [x] 3.1 Add `POST /validate-linkedin-article-preview` route in `main.py` with `require_api_key` dependency, request model (`campaign_id` required, `dry_run` default `true`, HTTP 422 on invalid body), structured JSON response, and log line consistent with sibling endpoints (no secrets, no variant body text).

## 4. Tests (mocked HTTP, no live network)

- [x] 4.1 Add `tests/test_linkedin_preview_validation.py` (or extend the closest existing suite per project convention) covering: full pass; each failure class (missing metadata fields, checkout title/description mismatch, checkout post missing, unreachable `public_url`, OG tag missing/mismatch per field, unreachable public image, non-image content type); blocked campaign-not-found and package-not-generated with zero outbound HTTP; skipped checkout when repo path unset with `passed` verdict; multi-failure single-pass reporting.
- [x] 4.2 Add dry-run/evidence tests: dry-run leaves the campaign document byte-identical; real run persists `linkedin_article_preview_validation` with `validated_at_utc` and changes no other field (including `linkedin_package` and `variants[]`); endpoint auth required; 422 on invalid body.
- [x] 4.3 Run targeted suites for touched modules, then full `pytest`; zero new warnings; `git diff --check` clean.

## 5. Documentation

- [x] 5.1 Update `docs/deployment/linkedin-publication-prerequisites.md`: operator procedure for `POST /validate-linkedin-article-preview` (dry-run first, run after live-site confirmation to avoid Pages-lag false negatives), check table with stable codes, and explicit US-024 boundary (inputs verified ≠ LinkedIn rendering confirmed).
- [x] 5.2 Update `docs/CURRENT-STATE.md`: add the capability under "Implemented but not operationally validated" with qualified language (implemented ≠ deployed ≠ operationally validated; no LinkedIn API involvement), and adjust spec/test counts if tracked.
- [x] 5.3 Update `docs/product/user-stories.md` US-023: map each acceptance criterion to its mechanism and unit evidence at implemented scope only; story explicitly not accepted until operational demonstration. Update `docs/product/progress-checklist.md` BL-009/US-023 rows only for states actually reached (e.g. "Work started"); leave demonstration/acceptance unchecked.

## 6. Validation and business gate

- [x] 6.1 Run `openspec validate "validate-linkedin-article-preview-rendering-us-023" --strict` and resolve any findings.
- [ ] 6.2 Business validation gate (post-implementation, approval-gated, outside implementation commit): after explicit operator approval to deploy, run the verification against a real campaign on `192.168.0.194` with the live site, capture evidence (dry-run + real run, persisted `linkedin_article_preview_validation` block), and only then update US-023 acceptance and progress-checklist demonstration items. Do not deploy, push, or mark the story accepted within this change's implementation scope.
