# Design: define-linkedin-preview-fallback-us-025

## Context

BL-009 has three stories. US-023 (`POST /validate-linkedin-article-preview`) is the sole source of input-correctness truth: it proves the title, description, OG tags, and public image LinkedIn would scrape are correct. It is implemented and unit-tested, not deployed, not operationally validated. US-024 is the sole rendering-observation source: a defined (not operationally validated) operator procedure that classifies every confirmation attempt into exactly one of `preview_confirmed`, `preview_stale_cache`, `preview_inputs_incorrect`, `preview_not_rendered_post_format`, or `confirmation_blocked`, with a safe Post Inspector-only re-scrape for the stale-cache class.

US-024 deliberately stops at observation. Three of its outcomes have no defined reaction today:

- **Persistent stale cache (pre-publish):** inputs pass, the safe re-scrape was performed, propagation lag was allowed for, and Post Inspector still shows a wrong card. US-024 says re-inspect and re-classify; it does not say what to do when the loop does not converge.
- **No card at all (post-publish):** the v1 publication path creates personal-profile **text** posts (`POST /rest/posts`, URL in commentary, no `content.article` entity). US-024 records "no card" honestly as `preview_not_rendered_post_format` and explicitly defers remediation to US-025.
- **Published post with a stale or incorrect card:** a Post Inspector re-scrape affects new posts only; an already-published post keeps the card it was rendered with. US-024 records the observation and stops.

The relevant safeguard landscape the fallback must not break:

- **Idempotency and duplicate prevention** (`linkedin-publication-integration`): already-published protection and the US-020 cadence guard both key on stored `published_at` / `linkedin_post_urn` evidence. `POST /queue-linkedin-publication` accepts only `pending` or `failed` variants — there is no state path that re-publishes a `published` variant.
- **Retry/recovery** (`linkedin-retry-recovery-classification`, US-021/US-022): the retry budget counts only real LinkedIn API calls; `failed`-state recovery confirmations exist for publication failures, not preview problems. A wrong preview never makes a variant `failed`.
- **Supervision mechanics** (US-017): `POST /correct-linkedin-variant` (pending, or failed content-invalid only), `POST /defer-linkedin-variant` (pending only, future time, blocks sequence followers), `POST /cancel-linkedin-publication` (pending/queued/failed; cancel releases the US-020 sequence and sets `auto_queue_eligible` false).
- **Scheduling** (`linkedin-distribution-scheduling-model`): defer moves only the target variant's `scheduled_at_utc`; schedule idempotency proof is preserved.
- **Blog post is canonical (ADR-0002):** preview inputs (title, description, OG tags, hero image) are owned by the blog post and public checkout; fixing them is a blog-side correction followed by re-verification, and any Git commit/push to the live site is operator-approved.

## Goals / Non-Goals

**Goals:**

- A normative, operator-executed fallback decision policy covering every US-024 outcome that can require a reaction, split into pre-publish fallback and post-publish recovery.
- Every candidate action classified as supported, approval-gated, or forbidden, with the safety reasoning recorded (duplicate risk, idempotency, evidence, variant state, scheduling, retry safeguards, LinkedIn API support).
- Operator-visible outcome labels, blocked states with next actions, and an evidence-record template consistent with the US-024 pattern.
- An honest, evidence-based disposition for the two actions that would need worker changes (`content.article` post format; post deletion/re-publication): analyzed here, deferred to named future changes with preconditions — not improvised and not speculatively implemented.

**Non-Goals:**

- No worker code, endpoints, request/response fields, env vars, n8n workflows, or deploy changes; no new `publish_state` values; no MODIFIED requirements on US-018–US-024 capabilities.
- No LinkedIn UI scraping, browser automation against LinkedIn, undocumented API behavior, or cache-busting URL manipulation.
- No automatic fallback execution; no re-implementation of US-023 input checks or US-024 observation steps.
- Not closing US-025 or BL-009 — demonstration and acceptance are separate, approval-gated steps.

## Decisions

### D1 — US-025 is documentation/procedure only (no worker/API implementation)

**Decision:** Deliver US-025 as an operator fallback policy (new canonical procedure capability `linkedin-article-preview-fallback` + `docs/operations/linkedin-preview-fallback-policy.md`), composing existing guarded worker capabilities.

**Alternatives considered:**

- *Worker fallback orchestration endpoint* (e.g. `POST /fallback-linkedin-preview` that inspects US-023/US-024 state and executes an action): rejected. Every supported action already exists as an authenticated, dry-run-defaulting, idempotency-aware endpoint (defer, cancel, correct, re-verify). A new endpoint would duplicate their validation, add automation for decisions that are inherently human judgments (accept vs delay vs withdraw), and contradict the US-024 spec's "no new automation surface" boundary pattern for this backlog family. It is speculative automation with no demonstrated need.
- *Worker implementation of new fallback actions* (`content.article` posts, post deletion): rejected for this change — see D5 and D6. The evidence needed to justify them (an operationally validated US-024 confirmation showing `preview_not_rendered_post_format` or a persistent wrong card on a real post) does not exist yet, because US-023 deploy/validation is still pending.
- *Status quo (no policy)*: rejected. The forbidden-action list in US-024 exists precisely because the tempting improvised reactions are dangerous; leaving the reaction undefined invites them.

This mirrors US-021 (policy defined first; mechanics later under a separate approved story) and US-024 (procedure-spec capability with no code).

### D2 — Fallback triggers are consumed US-024 outcomes only

**Decision:** A fallback decision is triggered only by a recorded US-024 evidence record with one of these outcomes:

1. `preview_stale_cache` **after a completed safe re-scrape cycle** (inputs re-confirmed via US-023, Post Inspector re-inspection performed, propagation lag allowed) that still does not show the intended card — pre-publish trigger.
2. `preview_not_rendered_post_format` — post-publish trigger (the no-card observation is made on a real published post).
3. Post-publish observation of a published post retaining a stale or incorrect card (recorded under `preview_stale_cache` with the US-024 honest limit that re-scrape never updates an already-published post) — post-publish trigger.

`preview_inputs_incorrect` is **not** a fallback trigger: US-023/US-024 already define its remediation (fix inputs per `linkedin_preview_validation_*` codes, re-verify, re-confirm). The fallback policy references that loop as the "correct metadata and repeat US-023/US-024" path and adds nothing to it — US-023 stays the sole input-truth source and US-024 the sole rendering-observation source. `preview_confirmed` needs no fallback; `confirmation_blocked` routes to the US-024 blocked-state table, not to fallback.

**Rationale:** anchoring triggers to the fixed US-024 vocabulary keeps stale-vs-wrong decided by US-023 evidence (never re-derived), prevents fallback-on-impression, and preserves the story boundaries the user stories define.

### D3 — Pre-publish fallback: four supported actions over existing endpoints

For a fallback-triggering outcome on a campaign whose affected variants are **not yet published** (`pending` or `queued`), the operator chooses exactly one of:

| Action | Mechanism | Safety notes |
|---|---|---|
| **Accept and proceed** | No endpoint call; record decision | The v1 text post carries the blog URL in commentary regardless of card rendering; the link remains functional. Duplicate risk: none. |
| **Delay publication** | `POST /defer-linkedin-variant` (pending variants; future UTC time) | Buys LinkedIn cache expiry time (non-normative community-observed ~7 days; never presented as a rule). Deferring an earlier-sequence variant blocks followers at publish time (US-020) — a deliberate, documented consequence, not a side effect. Honest limit: `queued` variants cannot be deferred and cannot return to `pending`; delaying a queued variant means not issuing a real publish-due for it (safe today: publish-pending n8n export is `active: false` and publish-due requires an explicit request), or cancelling it (irreversible — see below). The policy directs preview fallback decisions into the pending supervision window wherever possible, before queueing. |
| **Correct inputs and repeat US-023/US-024** | Blog/checkout correction (ADR-0002 canonical side), then `POST /validate-linkedin-article-preview`, then the US-024 confirmation | Only applicable when inputs are actually wrong (`preview_inputs_incorrect` loop) — for a genuine stale-cache the inputs already pass and there is nothing to correct. Any Git commit/push needed to fix the live page follows the existing guarded/manual publication paths with operator approval. |
| **Withdraw the variant** | `POST /cancel-linkedin-publication` | Releases the US-020 sequence for followers; sets `auto_queue_eligible` false; irreversible through existing endpoints (no `cancelled → pending` path). Evidence preserved. |

All endpoint-backed actions run dry-run first, then real, per existing endpoint defaults.

### D4 — Post-publish recovery: accept-and-record is the default; no evidence mutation, ever

For a published post with a wrong or missing card:

- **Default supported action: accept and record.** The post exists, the URL in commentary works, stored `linkedin_post_urn`/`published_at` evidence is correct, and every safeguard (idempotency, cadence, sequence release) depends on that evidence staying intact. The fallback record captures the rendering defect; campaign metadata is never edited.
- **Forbidden:** editing or removing `linkedin_post_urn`, `published_at`, `linkedin_publication`, attempt history, or recovery history to "reset" a published variant for re-publication. This would defeat the exact safeguards (already-published idempotency, US-020 cadence keyed on `published_at`) that prevent duplicates, and it would falsify the US-022 append-only evidence contract. The existing endpoints already make re-publication of a `published` variant impossible (queue accepts `pending`/`failed` only; publish-due is idempotent); the policy forbids working around that at the metadata layer.
- **Approval-gated exceptional action: manual post removal via the LinkedIn UI** (D6). Even when approved, it never re-opens the variant: the variant stays `published` with its evidence, and the removal is recorded in the fallback evidence record (the URN then references a removed post — recorded, not deleted).
- **Re-scrape is never presented as a post-publish remedy** — US-024 already establishes that an already-published post keeps its card.

### D5 — `content.article` post format: analyzed, deferred to a named future change

**Analysis without assuming the answer:**

- *LinkedIn API support:* the versioned LinkedIn Posts API documents an article content entity (`content.article` with `source`, `title`, `description`, and an optional `thumbnail` that requires a prior Images API upload). This is documented behavior, not undocumented API use — so the option is legitimate in principle.
- *What it would buy:* for new posts only, it makes the article card an explicit request instead of a scrape-dependent side effect, directly addressing `preview_not_rendered_post_format` and reducing exposure to cache staleness (title/description supplied in the payload).
- *What it costs:* it contradicts two normative requirements of `linkedin-publication-integration` as written — "personal-profile text posts" and "MUST NOT upload images" (thumbnail upload) — so it requires MODIFIED requirements, worker code in the publish path, payload verification against current official documentation at apply time, new mocked tests, and its own dry-run/idempotency/evidence treatment. That is a worker/API change with real blast radius on the most safety-critical path in the system.
- *What evidence exists today:* none operationally. US-024 has never been executed on a real post (it depends on the pending US-023 deploy/validation). Whether v1 text posts render a card at all is precisely the open question US-024 exists to answer.

**Decision:** do not prescribe or implement a post-format change in US-025. The fallback policy records `preview_not_rendered_post_format` outcomes and, when the operator judges the business impact warrants it, directs them to open a **separate future OpenSpec change** ("explicit article post format") with named preconditions: at least one operationally recorded `preview_not_rendered_post_format` evidence record; verification against current LinkedIn Posts API documentation; MODIFIED requirements on `linkedin-publication-integration`; unchanged guard, dry-run, idempotency, retry-budget, and evidence contracts; applies to new posts only (never retroactive). Deciding the format change *here* would assume the answer to a question US-024 has not yet asked.

### D6 — Delete/re-post: analyzed, forbidden as a standard fallback; deletion alone approval-gated; re-post via existing variants forbidden

**Analysis without assuming the answer:**

- *LinkedIn API support:* the versioned Posts API documents post deletion, and the LinkedIn UI lets a member delete their own post. Deletion itself is not undocumented behavior. However, the worker has no delete capability, and adding one is a worker/API change out of scope here.
- *Duplicate risk:* the re-post half is where the danger lives. Re-posting the same variant through the worker is impossible without either falsifying evidence (forbidden per D4) or creating a new variant/campaign for already-distributed content — a duplicate-content side effect that no existing safeguard models. A delete-then-repost sequence also has an uncertain window (delete succeeded? new post created?) exactly like the US-021 uncertain class, but without any of its evidence machinery.
- *Evidence integrity:* deleting the external post makes stored URN evidence reference a removed artifact. That is tolerable if recorded (evidence describes history, not current LinkedIn state) but must never be "repaired" by clearing the evidence.

**Decision:**

- **Delete-then-re-post as a fallback procedure: forbidden** in this policy. No supported or approval-gated path re-publishes an already-published variant's content through existing endpoints or metadata edits.
- **Manual post removal alone (LinkedIn UI, operator's own post): approval-gated.** Requires explicit prior operator/owner approval recorded in the evidence record, applies when leaving the defective post up is judged worse than having no post (business-image decision), preserves all campaign evidence unchanged, and never re-opens the variant. The US-020 cadence anchored to the stored `published_at` is intentionally left in force.
- Any future worker-supported delete/re-publish capability requires its own OpenSpec change defining state, evidence, and duplicate semantics; the policy names this as deferred, with the same evidence precondition as D5.

### D7 — Cache-busting URLs, test posts, UI scraping: forbidden (reaffirmed, with reasons)

The policy restates and extends the US-024 prohibitions as fallback-scope rules: no cache-busting query parameters or URL variants (the canonical `public_url` is recorded in campaign metadata and used for OG verification — a diverged share URL breaks input-truth traceability and creates a second scrape identity); no additional LinkedIn posts to test or force a refresh (real duplicate-content side effects outside every safeguard); no LinkedIn UI scraping or automation and no reliance on undocumented cache behavior (LinkedIn's cache TTL remains non-normative context).

### D8 — Outcome vocabulary, evidence records, blocked states

- **Fixed fallback outcome labels** (documented checklist values, no worker codes — same pattern as US-024): `fallback_accept_rendering`, `fallback_delay_publication`, `fallback_correct_inputs_reverify`, `fallback_cancel_variant`, `fallback_post_removal_approved`, `fallback_format_change_deferred`, `fallback_blocked`.
- **Evidence record** per fallback decision, following the operations-report pattern (`docs/operations/`), capturing: campaign id, affected variant(s) and `publish_state` at decision time, the referenced US-024 evidence record (outcome label + UTC timestamp), the referenced US-023 run, the chosen action with its classification (supported / approval-gated) and — for gated actions — the recorded approval, the endpoint calls made (dry-run and real) with key response fields, the resulting variant state, and operator + UTC timestamp. Campaign metadata is never edited to record fallback outcomes; no secrets, session data, variant body text, or image bytes.
- **Blocked states** (recorded as `fallback_blocked` with the named condition, never as a fallback failure): no US-024 evidence record with a triggering outcome exists; the US-024 safe re-scrape cycle has not been completed for a stale-cache trigger; approval absent for an approval-gated action; a required correction needs a live-site Git push that has not been approved; the chosen action is invalid for the variant's `publish_state` (e.g. defer on `queued`).

## Risks / Trade-offs

- [US-023/US-024 are not yet operationally validated, so the demonstration of this policy is chained behind their pending deploy/validation] → The policy is definable now (it consumes only their fixed contracts); tasks.md keeps the operational demonstration as a separate approval-gated task, and all product docs use qualified status language (defined ≠ validated ≠ accepted).
- [Accept-and-record may be unsatisfying for a business-visible defect on a published post] → That is an honest reflection of what LinkedIn allows for already-published posts without duplicate risk; the approval-gated removal option and the named future format-change candidate give the operator escalation paths that stay inside safety boundaries.
- [A `queued` variant cannot be deferred, leaving a narrower pre-publish window than operators might expect] → Documented honestly; the policy steers preview confirmation and fallback decisions into the `pending` supervision window, and notes that no automation currently publishes queued variants without an explicit request (publish-pending export `active: false`).
- [An approved manual post removal leaves stored URN evidence pointing at a removed post] → Recorded explicitly in the evidence record; evidence remains append-only history and continues to drive idempotency/cadence correctly (both safeguards remain conservative in the right direction).
- [Deferring an earlier-sequence variant as preview fallback blocks followers (US-020)] → Stated as a deliberate consequence in the action table so the operator makes the trade-off knowingly; cancel is documented as the sequence-releasing alternative.
- [LinkedIn cache behavior is undocumented; a delay may not converge] → The policy never promises convergence; delay carries a re-confirmation step (repeat US-024) and the accept/cancel exits remain available.

## Migration Plan

Docs and spec only: no deployment, no rollback machinery. Order: policy document + delta spec land at apply; cross-references and product/status docs updated in the same apply; canonical spec lands at `/opsx-sync`; the operational demonstration task executes only after explicit operator approval and after US-023 deploy + operational validation provides a trusted input verdict.

## Open Questions

- Should `preview_not_rendered_post_format`, once operationally observed, adopt a standing default of accept-and-record for subsequent campaigns (rather than a per-campaign decision) until a format-change proposal is opened? Deferred to the operator at demonstration review; the policy supports either without change.
