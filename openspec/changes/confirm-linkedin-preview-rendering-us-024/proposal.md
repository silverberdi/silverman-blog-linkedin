# Proposal: confirm-linkedin-preview-rendering-us-024

**Backlog item:** BL-009 — Validate LinkedIn Article Preview Rendering (`docs/product/backlog.md`)
**User story:** US-024 — "As a content operator, I want to confirm preview behavior on LinkedIn, so that published LinkedIn posts display the intended article preview." (`docs/product/user-stories.md`)

## Why

US-023 delivered input verification (`POST /validate-linkedin-article-preview`): it proves the inputs LinkedIn would scrape — package metadata, checkout front matter, live OG tags, public image — are correct. It deliberately makes no claim about how LinkedIn actually renders the preview, and it cannot distinguish "inputs correct but LinkedIn shows a stale or wrong card" (LinkedIn cache) from "inputs wrong". Nothing today tells the operator how to confirm real LinkedIn rendering, how to diagnose cache staleness, or how to force a safe re-scrape. Until that exists, BL-009's business outcome — published LinkedIn posts display the intended article preview — cannot be demonstrated.

**Honest capability evaluation (no worker code):** LinkedIn's rendered preview and scrape-cache state are not observable through any API this project holds. The granted scopes (`openid profile w_member_social`) expose no preview-rendering or cache-inspection surface, and LinkedIn Post Inspector is an interactive browser tool with no public API. Automating the confirmation would mean scraping LinkedIn UI — brittle, terms-of-service-hostile, and explicitly the kind of invented automation this story must not add. US-024 is therefore an **operator procedure + evidence-capture** story: a normative documented procedure with a decision matrix and recorded evidence, building on — not duplicating — the US-023 input verification. No LinkedIn API usage is proposed.

## Goals

- Define and support a repeatable operator procedure to confirm how LinkedIn actually renders the article preview (title, description, image) for a campaign's `public_url`:
  1. **Pre-publish confirmation** via LinkedIn Post Inspector (shows LinkedIn's current scrape of the URL; inspection itself forces a re-scrape and only affects *new* posts).
  2. **Post-publish observation** of the actual LinkedIn post, including the honest possible outcome that a v1 API text-only post renders **no article card at all** (the URL lives in commentary text; v1 sets no article content entity).
- Provide a decision matrix that distinguishes, with US-023 evidence as the input-truth source:
  - inputs wrong → US-023 territory (fix inputs; not this story);
  - inputs correct but LinkedIn renders stale/incorrect → LinkedIn cache issue, with a documented **safe re-scrape** procedure (re-inspect in Post Inspector; never publish duplicate posts to force a refresh; refreshed previews apply to new posts only — existing posts keep the old card).
- Make the outcome visible and traceable: a documented checklist with a fixed outcome vocabulary (documented stable labels, since no worker capability is added) and an evidence-record template per confirmation, following the project's operations-report pattern.
- Communicate blocked states clearly (Post Inspector unavailable, US-023 input verification not yet trusted, site not live).

## Non-goals

- **No worker code:** no new endpoints, modules, request fields, metadata writes, or stable worker codes. If a later change adds worker capability here, it needs its own proposal.
- **No LinkedIn API usage or UI scraping.** Post Inspector usage is manual, browser-based, and operator-driven.
- **US-025 territory:** defining the fallback when the preview is incorrect (including any move to `content.article` posts) stays out of scope.
- No change to US-023 verification behavior, package generation, publication, variant states, scheduling, or US-022 retry/recovery semantics.
- No new environment variables, no n8n changes, no deploy script changes.

## What Changes

- New canonical **procedure capability** (procedure-as-spec, same pattern as `linkedin-retry-recovery-classification` for US-021): normative requirements for the rendering-confirmation procedure, the cache-vs-inputs decision matrix, the safe re-scrape rules, the outcome vocabulary, and evidence capture.
- New operations document `docs/operations/linkedin-preview-rendering-confirmation.md`: the operator checklist, decision matrix, safe re-scrape steps, outcome labels, and evidence-record template.
- `docs/deployment/linkedin-publication-prerequisites.md`: the US-023 section's "US-024 boundary" pointer becomes a link to the defined procedure.
- `docs/CURRENT-STATE.md`, `docs/product/user-stories.md` (US-024 mapping at procedure-defined scope only), `docs/product/progress-checklist.md` (states actually reached only) — qualified status language throughout; BL-009 stays open.

## Capabilities

### New Capabilities

- `linkedin-article-preview-rendering-confirmation`: normative operator procedure to confirm actual LinkedIn rendering of a campaign's article preview, diagnose cache vs input issues using US-023 evidence, perform a safe Post Inspector re-scrape, and record confirmation evidence — with no worker code and no LinkedIn API involvement.

### Modified Capabilities

_None._ `linkedin-article-preview-verification` (US-023) is unchanged; its Purpose already names US-024 as the complementary scope this change now defines. `linkedin-article-preview-image-support`, `linkedin-publication-integration`, and `linkedin-retry-recovery-classification` are consumed read-only as context.

## Acceptance criteria addressed (US-024)

- **Confirm preview behavior on LinkedIn** — Post Inspector pre-publish confirmation plus post-publish observation of the real post, compared against the recorded `article_preview` metadata (title, description, image).
- **Identify cache or metadata issues** — decision matrix keyed on US-023 input verification outcome × observed LinkedIn rendering; stale-cache class with documented Post Inspector re-scrape and its new-posts-only caveat; inputs-wrong class routed back to US-023 remediation.
- **The outcome is visible and understandable to the operator** — fixed documented outcome vocabulary and a per-confirmation evidence record template; no worker capability is added, so labels are documented checklist values rather than worker codes.
- **Failures or blocked states clearly communicated** — explicit blocked class (Post Inspector unavailable, US-023 verification not passed/not trusted, site not live) with the documented next action per state.
- **Existing completed work not duplicated or unintentionally changed** — zero changes under `src/`, `tests/`, `n8n/`, `deploy/`; US-023 endpoint, package generation, publication, scheduling, and US-022 semantics untouched; the procedure consumes US-023 evidence instead of re-defining input checks.

### Acceptance criteria intentionally excluded

- None within US-024. US-025 (fallback definition when the preview is incorrect — including any post-format change such as `content.article`) is deliberately excluded as a separate story.

## Dependency on US-023 operational validation

US-023 task 6.2 (deploy + operational validation of input verification on `192.168.0.194` against the live site) is **still pending** and the US-023 implementation is not yet committed. This change's artifacts and docs do **not** depend on it. The **operational demonstration** of US-024 does: the decision matrix's "inputs correct?" branch requires a trusted, operationally validated US-023 run. The two validations can share one approved validation window; US-024 acceptance is recorded only after the operator demonstrates the procedure on a real campaign.

## Impact

- **Code:** none. Docs + canonical spec only; no `src/`, `tests/`, `n8n/`, or `deploy/` changes.
- **HTTP surface:** unchanged. No new endpoints; no outbound calls added; no LinkedIn API involvement.
- **Data:** no campaign metadata changes. Evidence lives in operations documents (established validation-report pattern).
- **Config:** no new environment variables.
- **Tests:** full pytest not required (docs/spec-only change per engineering standards); `openspec validate --strict` and `git diff --check` gate the change.
- **Docs:** new operations procedure doc; updates to prerequisites doc, CURRENT-STATE, user stories, progress checklist.
- **Operations:** procedure defined ≠ operationally validated ≠ story accepted; BL-009 remains open (US-023 not accepted; US-025 not started). Deploy/validation windows remain separate, approval-gated steps.
