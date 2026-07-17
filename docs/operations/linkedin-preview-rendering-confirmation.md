# LinkedIn article preview rendering confirmation (US-024)

**Scope:** BL-009 / US-024 — normative operator procedure to confirm how LinkedIn actually renders the article preview (title, description, image) for a campaign's public blog URL, diagnose cache vs input issues, perform a safe re-scrape, and record confirmation evidence.
**Status:** procedure **defined — not operationally validated, story not accepted**; BL-009 remains open. Procedure defined ≠ operationally validated ≠ accepted.
**Authority:** Canonical spec `openspec/specs/linkedin-article-preview-rendering-confirmation/` (after sync). Complements [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md) (US-023 input verification, unchanged) and [user-stories.md](../product/user-stories.md) US-024.

## Purpose and boundaries

US-023 (`POST /validate-linkedin-article-preview`) proves the **inputs** LinkedIn would scrape are correct: package `article_preview` metadata, public-checkout front matter, live OG tags at `public_url`, and HTTPS availability of `public_image_url`. It makes no claim about how LinkedIn renders the preview. This procedure covers exactly that missing half: observing LinkedIn's actual rendering, separating LinkedIn cache staleness from input problems, and recording the outcome.

Boundaries:

- **US-023 boundary (input truth):** this procedure consumes a US-023 verification run as the sole source of input-correctness truth. It never re-derives or duplicates any input check. "Inputs correct?" is always answered by the US-023 result, not by manual inspection.
- **US-025 boundary (fallback):** when the preview is genuinely incorrect and cannot be fixed by this procedure (for example an already-published post with a stale card, or a v1 text post that renders no card), the reaction is defined by the US-025 fallback policy — [linkedin-preview-fallback-policy.md](linkedin-preview-fallback-policy.md) (policy defined — not operationally validated) — and MUST NOT be improvised here. This procedure records the observation only.
- **No automation:** no worker code, no LinkedIn API calls, no UI scraping, no browser automation against LinkedIn. LinkedIn Post Inspector usage is manual, browser-based, operator-driven.
- **No secrets:** never store LinkedIn session cookies, credentials, variant body text, or image bytes in evidence records or anywhere in the repository.

## Prerequisites

LinkedIn observation (Post Inspector or post-publish) proceeds only when all three hold. Classification when a prerequisite is absent is **not** always `confirmation_blocked`:

- US-023 run is `failed` → record `preview_inputs_incorrect` (inputs wrong; no LinkedIn observation; remediate per US-023 codes).
- US-023 not run, US-023 result not operationally trusted, site not live, or Post Inspector unavailable → record `confirmation_blocked` with the named condition (see the blocked-state table).

1. **Passing US-023 run for the campaign** — a `passed` result from `POST /validate-linkedin-article-preview` for this campaign, operationally trusted (US-023 deployed and operationally validated on `192.168.0.194`; that validation is still pending at the time this procedure was defined). Reference the run by its `linkedin_article_preview_validation.validated_at_utc` (real run) or the response snapshot (dry-run).
2. **Live-site confirmation** — the blog post is reachable at the campaign's recorded `public_url` (US-002 probe evidence or equivalent). GitHub Pages deploy lag means a fresh push may not be live yet.
3. **Browser access to LinkedIn Post Inspector** — [linkedin.com/post-inspector](https://www.linkedin.com/post-inspector/), signed in with the operator's LinkedIn account in a browser.

## Observation points

The procedure has two observation points for the campaign's recorded `public_url`. Rendering is never assessed before a passing US-023 run; live-site confirmation always precedes Post Inspector inspection.

### 1. Pre-publish confirmation (Post Inspector)

1. Confirm prerequisites above.
2. Open LinkedIn Post Inspector and inspect the campaign's `public_url`. Inspection shows LinkedIn's current scrape of the URL **and itself forces a re-scrape** (this refresh affects new posts only).
3. Compare the retrieved title, description, and image against the campaign's recorded `linkedin_package.article_preview` metadata (`article_title`, `article_description`, `public_image_url`).
4. Classify the result with the decision matrix below and record the evidence.

### 2. Post-publish observation (real post)

Applicable only when the campaign has a `published` variant with stored `linkedin_post_urn` evidence.

1. Locate the actual LinkedIn post (operator profile feed/activity, matched via the stored `linkedin_post_urn` and `published_at`).
2. Observe whether an article preview card is rendered at all, and if so whether its title, description, and image match the recorded `article_preview` metadata.
3. **Honest v1 expectation:** the worker publishes personal-profile **text** posts (`POST /rest/posts`) with the blog URL inside commentary and no `content.article` entity. Whether LinkedIn renders an article card for such a post is exactly what this observation records — "no card at all" is a possible, first-class outcome (`preview_not_rendered_post_format`), not a procedure failure.
4. Classify with the decision matrix and record the evidence. Already-published posts keep the card they were rendered with; a later re-scrape never updates them.

## Decision matrix (cache vs input)

Every confirmation attempt is assigned exactly one outcome class from the US-023 input verification result combined with the observed LinkedIn rendering. **Stale-vs-wrong is decided by the US-023 result — never re-derived manually.** If US-023 says the inputs pass, a wrong card is a LinkedIn cache issue; if US-023 fails, rendering observation is meaningless until inputs are fixed.

| US-023 input verification | LinkedIn observation (Post Inspector / real post) | Outcome class | Next action |
|---|---|---|---|
| `passed` | Card matches recorded `article_preview` (title, description, image) | `preview_confirmed` | Record evidence; done |
| `passed` | Card shows outdated or wrong values | `preview_stale_cache` | Safe re-scrape (below), re-inspect, re-classify. Note: already-published posts keep the old card |
| `failed` | Any | `preview_inputs_incorrect` | Fix inputs per the reported `linkedin_preview_validation_*` codes (US-023 remediation); no cache remediation; no LinkedIn observation; repeat confirmation only after inputs pass. The US-025 fallback policy ([linkedin-preview-fallback-policy.md](linkedin-preview-fallback-policy.md)) references this same loop and adds nothing to it |
| `passed` | No article card rendered at all on the API-created text post | `preview_not_rendered_post_format` | Record honestly as a v1 text-only post-format finding — an observation, not a failure of inputs or of this procedure. Reaction (accept, escalate to a future `content.article` change) per the US-025 fallback policy: [linkedin-preview-fallback-policy.md](linkedin-preview-fallback-policy.md) |
| not run / not trusted / site not live / Post Inspector unavailable | — | `confirmation_blocked` | Record the named blocking condition and its next action (blocked-state table below); never guess a confirmation |

## Safe re-scrape procedure (stale-cache class)

When the outcome class is `preview_stale_cache`:

1. **Re-confirm inputs first.** Re-run US-023 verification for the campaign (dry-run suffices) and confirm it still passes — re-scraping wrong inputs just caches the wrong card faster.
2. **Re-scrape via Post Inspector only.** Re-inspect the campaign's `public_url` in LinkedIn Post Inspector; the inspection itself refreshes LinkedIn's cached scrape. This is the only permitted refresh mechanism.
3. **Re-inspect and re-classify.** After the re-scrape, evaluate against the decision matrix again. Allow for propagation lag before concluding failure — LinkedIn's cache duration is not officially documented (community-observed natural expiry is around 7 days; treat that as non-normative context, not a rule).

Forbidden actions:

- **Never publish additional LinkedIn posts** to test or force a preview refresh — that creates real duplicate-content side effects that no existing safeguard catches.
- **Never alter the shared URL** (for example cache-busting query parameters on `public_url`) — the canonical `public_url` is recorded in campaign metadata and the shared URL must not diverge from it.

Honest limit: a re-scrape affects **new posts only** — an already-published post with a stale card keeps it. Whether and how to react to an already-published stale card, or to a persistent stale cache after a completed re-scrape cycle, is defined by the US-025 fallback policy: [linkedin-preview-fallback-policy.md](linkedin-preview-fallback-policy.md).

## Blocked states

Blocked confirmations are recorded with the `confirmation_blocked` label plus the specific blocking condition. They are never recorded as failures of the preview inputs or of LinkedIn rendering.

| Blocking condition | Next action |
|---|---|
| US-023 input verification not run for the campaign | Run `POST /validate-linkedin-article-preview` (dry-run first); proceed only on `passed` |
| US-023 result not operationally trusted (endpoint not deployed / not operationally validated) | Complete the US-023 deploy + operational validation step (approval-gated) before relying on its verdict |
| Site not live — `public_url` not reachable | Wait for live-site confirmation (US-002 probe pattern; GitHub Pages deploy lag applies), then retry |
| LinkedIn Post Inspector unavailable or inaccessible | Retry later; record `confirmation_blocked` with retry guidance — never guess a confirmation |
| No `published` variant with `linkedin_post_urn` when post-publish observation is required | Pre-publish confirmation only; post-publish observation waits until a variant is published through the existing guarded publication path |

A US-023 run with overall status `failed` is **not** a blocked confirmation: record `preview_inputs_incorrect`, remediate per the reported `linkedin_preview_validation_*` codes, and re-verify before any LinkedIn observation.

## Evidence record template

Each confirmation attempt is recorded using this template, following the project's operations-report pattern (validation reports in `docs/operations/`). Campaign metadata (`metadata/campaigns/<campaign-id>.json`) is **never** edited to record confirmation outcomes.

```markdown
## LinkedIn preview rendering confirmation — <campaign-id>

- **Campaign id:** <campaign-id>
- **`public_url`:** <recorded public_url>
- **US-023 run reference:** `validated_at_utc` <UTC ISO-8601> (real run) or response snapshot (dry-run); overall status <passed>
- **Post Inspector observation (UTC <timestamp>):**
  - Retrieved title: <observed>
  - Retrieved description: <observed>
  - Retrieved image: <observed image URL reference>
  - Matches recorded `article_preview`: <yes/no + which fields differ>
- **Post-publish observation (when applicable):**
  - `linkedin_post_urn` reference: <urn>
  - Card rendered: <yes/no>; matches recorded metadata: <yes/no/n-a>
- **Outcome label:** one of `preview_confirmed` / `preview_stale_cache` / `preview_inputs_incorrect` / `preview_not_rendered_post_format` / `confirmation_blocked`
- **Blocking condition (blocked only):** <named condition + next action>
- **Operator:** <name> — **confirmed at (UTC):** <ISO-8601>
```

Rules:

- Outcome labels are documented checklist values from the fixed vocabulary above — no worker codes are introduced; use them exactly and exclusively.
- No secrets, LinkedIn session cookies or session data, credentials, variant body text, or image bytes in evidence records. Screenshots are optional and must respect the same rule.
- Campaign metadata files are never modified by this recording procedure.
