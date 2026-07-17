# Design: confirm-linkedin-preview-rendering-us-024

## Context

BL-009 / US-024. US-023 (`linkedin-article-preview-verification`, implemented + unit-tested, not deployed, not operationally validated, not committed at the time of this proposal) verifies the **inputs** LinkedIn would scrape: package `article_preview` metadata, public-checkout front matter, live OG tags at `public_url`, and HTTPS availability of `public_image_url`, with stable `linkedin_preview_validation_*` codes and an additive evidence block on real runs. Its canonical spec explicitly excludes LinkedIn rendering confirmation and cache diagnosis — that is this story.

What does not exist today: any defined way for the operator to (a) observe how LinkedIn actually renders the preview for a campaign's URL, (b) decide whether a wrong preview means stale LinkedIn cache or wrong inputs, (c) safely force LinkedIn to re-scrape, and (d) record the confirmed outcome traceably.

Facts constraining the design:

- **No API surface.** The project holds scopes `openid profile w_member_social` (share + OIDC). None exposes LinkedIn's scrape cache or rendered preview. LinkedIn Post Inspector (`linkedin.com/post-inspector`) is an interactive browser tool with no public API; inspecting a URL shows LinkedIn's current scrape *and* forces a re-scrape.
- **Cache semantics.** LinkedIn caches scraped preview data (community-observed ≈7 days, not officially documented). A Post Inspector re-scrape updates the preview for **new** posts only; already-published posts keep the card they were rendered with.
- **v1 post format.** The worker publishes personal-profile **text** posts via `POST /rest/posts` with the blog URL inside commentary; it sets no `content.article` entity and uploads no media. Whether LinkedIn renders an article card for an API-created text post with a URL in commentary is precisely what US-024 must observe honestly — "no card at all" is a possible, reportable outcome, and changing the post format is US-025/future territory.
- Constraints: ADR-0001 (worker HTTP only — moot here, no worker change), no LinkedIn API usage without explicit justification and guards (none proposed), no new env vars, no n8n or deploy changes, qualified status language, BL-009 stays open.

## Goals / Non-Goals

**Goals:**

- A normative, repeatable operator procedure to confirm LinkedIn's actual rendering of a campaign's article preview (title, description, image), pre-publish (Post Inspector) and post-publish (real post observation).
- A decision matrix that separates input problems (US-023's territory) from LinkedIn cache staleness, with a safe re-scrape procedure and its limits stated honestly.
- A fixed outcome vocabulary and an evidence-record template so every confirmation is visible, understandable, and traceable.
- Explicit blocked states with the next action per state.

**Non-Goals:**

- Worker code of any kind (endpoints, metadata writes, stable worker codes) — evaluated and rejected below (D1).
- LinkedIn API calls, UI scraping, or browser automation against LinkedIn.
- Fallback definition when the preview is genuinely incorrect (US-025), including any post-format change (`content.article`).
- Modifying US-023 behavior, package generation, publication, variant states, scheduling, or US-022 retry/recovery semantics.

## Decisions

### D1 — Procedure + evidence capture, no worker code

US-024 is delivered as a documented operator procedure with a canonical procedure-as-spec, not as worker capability.

- *Why:* the confirmation subject (LinkedIn's rendered card and cache state) is observable only by a human in a browser. Every automatable part of the problem — "are the inputs right?" — is already US-023; re-implementing any of it would duplicate completed work. A worker endpoint here could only record an operator attestation, which the established operations-report pattern already covers without new code (see D4).
- *Alternatives considered:*
  - **Attestation endpoint** (e.g. `POST /record-linkedin-preview-rendering` persisting an operator-confirmed block on campaign metadata) — rejected: adds HTTP surface, tests, and metadata schema for what is a manual observation; no consumer of that block exists; can be proposed later if BL-010 observability wants machine-readable confirmation state.
  - **Automated Post Inspector usage / LinkedIn scraping** — rejected: no API, terms-of-service-hostile, brittle, and explicitly the kind of invented automation the story forbids.
  - **oEmbed/preview third-party services** — rejected: they report their own scrape, not LinkedIn's cache; would create a false-confidence signal.

### D2 — New procedure capability, no delta to `linkedin-article-preview-verification`

New canonical capability `linkedin-article-preview-rendering-confirmation`, following the US-021 precedent (`linkedin-retry-recovery-classification`: normative procedure capability without endpoint requirements).

- *Why:* the US-023 spec's boundary ("no claim about how LinkedIn renders the preview") is a feature, not a gap — the input-verification contract stays crisp and its implementation untouched. Rendering confirmation is a different lifecycle moment (after live-site confirmation, around LinkedIn publication) with different actors (operator + browser instead of worker + HTTP). A delta would force MODIFIED requirements where no existing behavior changes.

### D3 — Decision matrix keyed on US-023 outcome × observed rendering

The procedure's diagnostic core, normative in the spec and operational in the docs:

| US-023 input verification | LinkedIn observation (Post Inspector / real post) | Class | Next action |
|---|---|---|---|
| `passed` | Card matches recorded `article_preview` (title, description, image) | **Confirmed** (`preview_confirmed`) | Record evidence; done |
| `passed` | Card shows outdated/wrong values | **Stale cache** (`preview_stale_cache`) | Safe re-scrape (D5), re-inspect, re-evaluate; note: already-published posts keep the old card |
| `failed` | Any | **Inputs incorrect** (`preview_inputs_incorrect`) | Fix inputs per US-023 stable codes; rendering confirmation is meaningless until inputs pass. Fallback/remediation policy beyond existing US-023 guidance is US-025 |
| `passed` | No article card rendered at all on the API-created text post | **Not rendered — post format** (`preview_not_rendered_post_format`) | Record honestly as a v1 post-format finding; remediation (e.g. `content.article`) is out of scope (US-025/future change) |
| not run / not trusted / site not live / Post Inspector unavailable | — | **Blocked** (`confirmation_blocked`) | Named blocking condition + next action (run US-023, wait for live-site confirmation, retry Post Inspector) |

- *Why US-023 is the input-truth source:* it exists precisely to answer "are the inputs right?" with stable codes and persisted evidence; duplicating any input check in this procedure would violate the no-duplication criterion.
- *Why "no card" is a first-class outcome:* v1 publishes text-only posts with the URL in commentary. Pretending a card is guaranteed would make the procedure dishonest; observing and recording the actual behavior **is** the story's business value.

### D4 — Evidence capture via operations record, not campaign metadata

Each confirmation produces an evidence record using a template in the new operations doc: campaign id, `public_url`, US-023 run reference (`validated_at_utc` / response snapshot), Post Inspector observation (retrieved title/description/image and timestamp; screenshots optional), post-publish observation when applicable (`linkedin_post_urn` reference), outcome label from the fixed vocabulary, and operator + UTC timestamp.

- *Why:* this is the project's established pattern for operator-demonstrated outcomes (US-009/US-010/US-018 validation reports). It keeps campaign metadata untouched (no worker code, no schema change) while making the outcome visible and reviewable.
- *Alternative considered:* manual JSON edits to `metadata/campaigns/<id>.json` — rejected: manual metadata edits are reserved for deliberate evidence repair (US-020/US-021 patterns); routine confirmations must not normalize hand-editing campaign documents.

### D5 — Safe re-scrape procedure (cache remediation)

Normative rules for the stale-cache class:

1. Re-scrape **only** via LinkedIn Post Inspector inspection of the campaign's `public_url` (inspection itself refreshes LinkedIn's cached scrape). Never publish additional LinkedIn posts to test or force a refresh — that creates real duplicate-content side effects no safeguard catches.
2. Before re-scraping, re-run US-023 verification (dry-run suffices) to confirm the live site currently serves the intended OG tags — re-scraping wrong inputs just caches the wrong card faster.
3. After re-scrape, re-inspect and re-evaluate against the decision matrix. Allow for propagation lag before concluding failure (cache TTL is not officially documented; community-observed ≈7 days for natural expiry).
4. State the limit honestly: a re-scrape affects **new** posts only. An already-published post with a stale card keeps it; whether and how to react (delete/re-post, accept, change format) is US-025 fallback territory and MUST NOT be improvised here.
5. URL cache-busting tricks (query-parameter suffixes on `public_url`) are **not** part of the safe procedure: they change the canonical shared URL and would diverge from campaign metadata.

### D6 — Qualified status language and dependency on US-023 validation

Merging this change means the procedure is **defined** only. US-024 acceptance requires an operator-demonstrated confirmation on a real campaign, which depends on US-023 being deployed and operationally validated first (archived US-023 task 6.2, still pending — its implementation is not yet committed either). The two can share one approved validation window: deploy, US-023 real run against the live site, then Post Inspector confirmation per this procedure. Docs must keep BL-009 open and never conflate procedure-defined / implemented / deployed / operationally validated / accepted.

## Risks / Trade-offs

- [Post Inspector behavior, UI, or availability changes without notice] → the procedure references it functionally (inspect = view LinkedIn's scrape + force re-scrape) rather than prescribing UI steps pixel-by-pixel; if the tool is unavailable, the outcome is `confirmation_blocked` with retry guidance — never a guessed confirmation.
- [Cache TTL is undocumented and variable] → the procedure treats TTL as unknown (≈7 days community-observed, stated as non-normative context), relies on forced re-scrape rather than waiting, and requires re-evaluation instead of assuming refresh success.
- [v1 text posts may render no article card] → surfaced as a first-class, honestly-labeled outcome (`preview_not_rendered_post_format`) instead of being masked as failure or success; remediation deferred to US-025 to avoid scope creep into post-format changes.
- [Manual procedure = human error risk] → fixed outcome vocabulary, mandatory US-023 evidence reference, and a per-confirmation template minimize free-form judgment; the checklist orders steps so rendering is never assessed before inputs pass.
- [Evidence lives in docs, not machine-readable metadata] → acceptable for BL-009's scope; if BL-010 observability later needs machine-readable confirmation state, that is a separate proposed change (noted, not designed here).
- [Operator uses a personal LinkedIn session for Post Inspector] → the procedure forbids storing LinkedIn session cookies/credentials in the repository (same rule as the US-004 visibility checklist).

## Migration Plan

Docs + canonical spec only: new operations document, new spec capability, pointer updates in existing docs. No deploy, no rollback concerns beyond reverting the commit. No runtime state changes; RUNTIME-STATE untouched.

## Open Questions

None blocking. Machine-readable confirmation evidence (campaign metadata block) is deliberately deferred; propose separately if BL-010 observability needs it.
