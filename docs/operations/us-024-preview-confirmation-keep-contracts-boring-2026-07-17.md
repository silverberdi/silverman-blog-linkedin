# US-024 — LinkedIn preview rendering confirmation: post-publish observation (2026-07-17)

Evidence record per the template in [linkedin-preview-rendering-confirmation.md](linkedin-preview-rendering-confirmation.md). Observation source: real published post (Post Inspector remained unavailable — see [blocked attempt](us-024-preview-confirmation-blocked-2026-07-17.md)).

## LinkedIn preview rendering confirmation — flow-a-2026-07-15-keep-contracts-boring

- **Campaign id:** `flow-a-2026-07-15-keep-contracts-boring`
- **`public_url`:** `https://silverman.pro/2026/07/15/keep-contracts-boring/`
- **US-023 run reference:** `validated_at_utc` `2026-07-17T18:11:32Z` (real run); overall status `passed`. Inputs trusted ([us-023 validation](us-023-linkedin-preview-input-validation-2026-07-17.md)).
- **Post Inspector observation:** unavailable (prior `confirmation_blocked` for the same URL; app crash at init across browsers). Not used for this classification.
- **Post-publish observation (UTC 2026-07-17T18:41Z):**
  - `linkedin_post_urn` reference: `urn:li:share:7483953784612786177`
  - `published_at`: `2026-07-17T18:40:27Z`
  - Variant: `executive-recruiter`
  - Card rendered: **no** — LinkedIn feed shows the full commentary text and a shortened `https://lnkd.in/...` link only; no article preview card (no scraped title, description, or image).
  - Matches recorded metadata: n/a (no card to compare against `article_title` / `article_description` / `public_image_url`)
- **Outcome label:** `preview_not_rendered_post_format`
- **Classification rationale:** US-023 inputs are correct and live OG tags are present; the worker published a v1 personal-profile **text** post (`POST /rest/posts`) with the blog URL inside commentary and no `content.article` entity. Absence of an article card is therefore a first-class post-format observation, not a failure of inputs or of this procedure.
- **Next action:** reaction per the US-025 fallback policy ([linkedin-preview-fallback-policy.md](linkedin-preview-fallback-policy.md)) — post-publish default is **accept and record**; format-change escalation (`content.article`) is a deferred future-change candidate, not an improvised action.
- **Operator:** Silverio Bernal — **confirmed at (UTC):** 2026-07-17T18:41:00Z

## Scope note

Campaign metadata was not modified by this recording. A same-day observation of `domain-first-is-not-anti-infrastructure :: executive-recruiter` (`urn:li:share:7483952071243898881`) also showed no article card, but that campaign has `article_preview.status = skipped` and no US-023 `passed` run — it is corroborating context only, not formal US-024 evidence.
