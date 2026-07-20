# LinkedIn article preview fallback policy (US-025)

**Scope:** BL-009 / US-025 — normative operator fallback policy for reacting to an incorrect or missing LinkedIn article preview detected for a Flow A campaign: decision procedures (pre-publish fallback and post-publish recovery), action classification (supported / approval-gated / forbidden), outcome vocabulary, evidence records, and blocked states.
**Status:** policy **defined — not operationally validated, story not accepted**; BL-009 remains open. Policy defined ≠ deployed ≠ operationally validated ≠ accepted.
**Authority:** Canonical spec `openspec/specs/linkedin-article-preview-fallback/` (after sync). Consumes [linkedin-preview-rendering-confirmation.md](linkedin-preview-rendering-confirmation.md) (US-024) and the US-023 verification procedure in [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md#article-preview-input-verification-us-023) unchanged.

## Purpose and boundaries

US-023 (`POST /validate-linkedin-article-preview`) proves whether the preview **inputs** LinkedIn would scrape are correct. US-024 observes how LinkedIn **actually renders** the preview and classifies every confirmation attempt with a fixed outcome vocabulary. Neither defines a reaction. This policy covers exactly that missing piece: given a recorded US-024 outcome that shows a wrong or missing preview, what the operator may do, must record, and must never do.

Boundaries:

- **US-023 boundary (input truth):** US-023 is the sole source of input-correctness truth. This policy never re-derives, duplicates, or manually re-checks whether inputs are correct — "inputs correct?" is always answered by a referenced US-023 verification result.
- **US-024 boundary (rendering observation):** US-024 is the sole source of rendering observations. A fallback decision is triggered only by a recorded US-024 evidence record — never by an operator impression, a screenshot, or any observation made outside the US-024 procedure. This policy defines no competing observation step.
- **Existing capabilities only:** every endpoint-backed action in this policy uses existing guarded worker capabilities — `POST /validate-linkedin-article-preview`, `POST /defer-linkedin-variant`, `POST /cancel-linkedin-publication`, `POST /correct-linkedin-variant` — plus the documented US-024 confirmation procedure. No worker code, endpoints, request/response fields, environment variables, `publish_state` values, n8n workflows, or deploy scripts are added or changed, and no new LinkedIn API usage is introduced.
- **No LinkedIn automation:** no LinkedIn UI scraping or automation, no reliance on undocumented LinkedIn API or cache behavior, no LinkedIn session data or credentials stored in the repository.
- **No automatic execution:** every fallback action is an explicit, recorded operator decision. Nothing in this policy runs automatically or on a schedule.

## Fallback triggers

A fallback decision is triggered **only** by a recorded US-024 evidence record with one of these outcomes:

| # | Triggering US-024 outcome | Condition | Window |
|---|---|---|---|
| 1 | `preview_stale_cache` | The US-024 safe re-scrape cycle has been **completed** (inputs re-confirmed via US-023, Post Inspector re-inspection performed, propagation lag allowed) and the intended card is still not shown | Pre-publish |
| 2 | `preview_not_rendered_post_format` | Recorded on a real published v1 text post: inputs pass, no article card rendered at all | Post-publish |
| 3 | `preview_stale_cache` observed on a **published** post | The US-024 post-publish observation shows an already-published post retaining a stale or incorrect card, with the US-024 honest limit recorded that a re-scrape affects new posts only | Post-publish |

Non-triggers:

- **`preview_inputs_incorrect` is not a fallback trigger.** Its remediation is already defined: fix the inputs per the reported `linkedin_preview_validation_*` codes, re-verify via US-023, and re-confirm via US-024. This policy references that loop (as the "correct inputs and repeat US-023/US-024" pre-publish action) and adds nothing to it.
- **`preview_confirmed`** requires no fallback.
- **`confirmation_blocked`** routes to the US-024 blocked-state table, not to this policy.
- **Unrecorded observations never trigger fallback.** If an operator believes a preview looks wrong but no US-024 evidence record with a triggering outcome exists, the US-024 confirmation procedure must be completed first; a premature fallback attempt is recorded as `fallback_blocked` (see blocked states).

## Pre-publish fallback decision procedure

Applies when a triggering outcome is recorded and the affected variants are **not `published`** (`pending` or `queued`). The operator chooses exactly one of four supported actions. Endpoint-backed actions run **dry-run first, then real**, per the existing endpoint defaults (`dry_run` defaults to `true`). Wherever possible, preview fallback decisions are made in the `pending` supervision window, **before queueing** — the action space is widest there.

| Action | Mechanism | Safety consequences |
|---|---|---|
| **1. Accept and proceed** | No endpoint call; the decision and rationale are recorded in a fallback evidence record | The v1 text post carries the blog URL in commentary regardless of card rendering — the link remains functional even with a wrong or missing card. Duplicate risk: none. Outcome label: `fallback_accept_rendering` |
| **2. Delay publication** | `POST /defer-linkedin-variant` for **`pending` or `queued`** variants (US-084) with a future UTC time (dry-run first, then real); repeat the US-024 confirmation before publication proceeds | Buys time for LinkedIn cache expiry — LinkedIn's cache duration is **not officially documented and no specific TTL is normative** (community-observed ~7-day natural expiry is context, not a rule); a delay is not guaranteed to converge. Deferring an earlier-sequence variant **blocks its followers at publish time** under the US-020 sequence rule — a deliberate, documented consequence the operator accepts knowingly. Deferring a `queued` variant **keeps** `publish_state` `queued` (does not return to `pending`) while updating `scheduled_at_utc` and aligning `publish_after_utc` so due evaluation waits for the new time. Cancellation remains the withdraw path (action 4 / US-085); postpone is not cancel. Outcome label: `fallback_delay_publication` |
| **3. Correct inputs and repeat US-023/US-024** | Blog-post / public-checkout correction, then `POST /validate-linkedin-article-preview`, then the US-024 confirmation | Applicable **only when inputs are actually wrong** (the `preview_inputs_incorrect` remediation loop) — for a genuine stale cache the inputs already pass and there is nothing to correct. Corrections follow ADR-0002 (the blog post is canonical; preview inputs are owned by the blog post and public checkout). Any Git commit/push needed to update the live site follows the existing guarded or manual publication paths **with operator approval** — an unapproved required push is a blocked state, not an improvised action. Outcome label: `fallback_correct_inputs_reverify` |
| **4. Withdraw the variant** | `POST /cancel-linkedin-publication` (dry-run first, then real) | Cancellation **releases the US-020 sequence** for follower variants, sets `operator_supervision.auto_queue_eligible` to `false`, preserves all evidence, and is **irreversible through existing endpoints** — there is no `cancelled → pending` path. Outcome label: `fallback_cancel_variant` |

Accept (action 1) calls no worker endpoint and changes no campaign metadata; the decision lives entirely in the fallback evidence record.

## Post-publish recovery decision procedure

Applies when a triggering outcome concerns a **published** post showing a stale, incorrect, or missing article card.

**Default supported action: accept and record.** The post exists, the blog URL in its commentary works, and the stored evidence (`linkedin_post_urn`, `published_at`, `linkedin_publication`, attempt and recovery history) is correct — it describes what actually happened. The rendering defect is captured in a fallback evidence record (`fallback_accept_rendering`); campaign metadata is byte-identical to its pre-decision state.

**Re-scrape is never a post-publish remedy.** US-024 establishes that a Post Inspector re-scrape affects new posts only; an already-published post keeps the card it was rendered with. This policy does not present re-scrape as a fix for a published post.

**Evidence mutation is forbidden.** No procedure step may edit or remove `linkedin_post_urn`, `published_at`, `linkedin_publication`, attempt history, or recovery history to make a `published` variant publishable again. Reason: already-published idempotency and the US-020 cadence guard **key on exactly that stored evidence** — mutating it would disable the very safeguards that prevent duplicate posts, and would violate the US-022 append-only evidence contract. The existing endpoints already make re-publication of a `published` variant impossible (`POST /queue-linkedin-publication` accepts `pending` or eligible `failed` variants only; publish-due is idempotent for `published` variants); this policy forbids working around that at the metadata layer.

**The only non-default post-publish action** is the approval-gated manual post removal defined in the action classification below. Even when executed, the variant remains `published` with all evidence intact.

## Action classification

Every fallback action belongs to exactly one class:

| Class | Actions |
|---|---|
| **Supported** (operator decision, no additional approval) | Accept and proceed / accept and record; delay via `POST /defer-linkedin-variant` for **`pending` or `queued`** variants (US-084); correct inputs and repeat US-023/US-024 (the input-remediation loop itself — any live-site Git push within it keeps its existing approval requirement); withdraw via `POST /cancel-linkedin-publication`; US-023 re-verification runs; repeated US-024 confirmations |
| **Approval-gated** (explicit prior operator/owner approval recorded in the evidence record) | Manual removal of the operator's own published LinkedIn post via the LinkedIn UI, when leaving the defective post visible is judged worse than removing it (business-image decision) |
| **Forbidden** | Delete-then-re-post as a fallback procedure; cache-busting query parameters or any divergence of the shared URL from the canonical recorded `public_url`; publishing additional LinkedIn posts to test or force a preview refresh; editing campaign metadata to record fallback outcomes or to reset publication state; LinkedIn UI scraping or automation; reliance on undocumented LinkedIn API or cache behavior; any automatic or scheduled execution of fallback actions |

### Approval-gated: manual post removal rules

- The approval record **must precede the removal** — a removal without recorded prior approval is a blocked state, not an approved action.
- The variant **stays `published`** with all evidence intact; removal never re-opens the variant for publication.
- The removal is captured in the fallback evidence record, including the fact that the stored `linkedin_post_urn` now references a removed post (recorded honestly — evidence describes history, not current LinkedIn state; it is never "repaired" by clearing it).
- The US-020 cadence anchored to the stored `published_at` **remains in force** — an approved removal does not reset or shorten the 72-hour cadence window.
- Outcome label: `fallback_post_removal_approved`.

### Forbidden: delete/re-post safety analysis

Delete-then-re-post is forbidden as a fallback procedure for three reasons:

1. **Duplicate-content risk outside every existing safeguard.** Re-posting an already-published variant's content requires either falsifying evidence (forbidden above) or creating a new variant/campaign for already-distributed content — a duplicate-publication side effect that no existing safeguard (already-published idempotency, US-020 cadence, queue state rules) models or catches.
2. **Uncertain-outcome window without evidence machinery.** A delete-then-repost sequence has an uncertain window (did the delete succeed? was a new post created?) exactly like the US-021 uncertain class — but with none of its classification, confirmation, or evidence machinery.
3. **Evidence integrity.** Deleting the external post makes stored URN evidence reference a removed artifact. That is tolerable when recorded (see approval-gated removal above) but must never be "repaired" by clearing or rewriting evidence.

No supported or approval-gated path re-publishes an already-published variant's content through endpoints, metadata edits, or a new variant/campaign created for that purpose.

### Forbidden: cache-busting, test posts, scraping (reaffirmed)

- **No cache-busting query parameters or URL variants.** The canonical `public_url` is recorded in campaign metadata and used for OG verification; a diverged share URL breaks input-truth traceability and creates a second scrape identity.
- **No additional LinkedIn posts to test or force a refresh.** Real duplicate-content side effects outside every safeguard.
- **No LinkedIn UI scraping or automation; no reliance on undocumented API or cache behavior.** LinkedIn's cache TTL remains non-normative context.

### Deferred future-change candidates (named, not implemented)

Two candidate actions would require worker/API changes. Both are analyzed and **deferred** — evaluated on their merits, not improvised and not speculatively implemented:

1. **Explicit article post format (for example `content.article`).** Would make the article card an explicit request instead of a scrape-dependent side effect for new posts, directly addressing `preview_not_rendered_post_format`. It contradicts the current `linkedin-publication-integration` contract as written (personal-profile text posts; no image upload), so it requires its own OpenSpec change with MODIFIED requirements. Preconditions: at least one operationally recorded `preview_not_rendered_post_format` US-024 evidence record; verification against current official LinkedIn Posts API documentation at apply time; unchanged guard, dry-run, idempotency, retry-budget, and evidence contracts; applies to new posts only (never retroactive). When the operator judges the business impact warrants escalation, the fallback outcome is recorded as `fallback_format_change_deferred` and a separate future OpenSpec change is opened.
2. **Worker-supported post deletion/re-publication.** Any future delete or re-publish capability requires its own OpenSpec change defining state, evidence, and duplicate semantics, with the same evidence precondition: at least one operationally recorded triggering US-024 evidence record and verification against current official LinkedIn API documentation.

## Duplicate prevention and safeguard preservation

Every existing publication safeguard is preserved unchanged. How each interacts with fallback actions:

- **Already-published protection.** Re-publication of a `published` variant remains impossible through existing endpoints: `POST /queue-linkedin-publication` accepts `pending` or eligible `failed` variants only, and publish-due is idempotent for `published` variants (no LinkedIn call, evidence preserved). This policy defines no path around that.
- **Retry budget (US-022) is never consumed.** No fallback action is a real LinkedIn API call, so no variant's `publication_attempt_count`, `manual_retries_used`, or `manual_retries_remaining` changes under any supported or approval-gated fallback action.
- **Recovery confirmations are not repurposed.** `recovery_confirmation` values (`remediation_completed`, `linkedin_post_absence_verified`) belong to US-021/US-022 failed-state recovery only. A wrong preview never makes a variant `failed`, so this policy directs no use of `recovery_confirmation` for any variant whose `publish_state` is not `failed`.
- **Sequence and cadence (US-020) effects are stated per action.** Defer **blocks** follower variants at publish time while the deferred earlier variant awaits publication; cancel **releases** the sequence for followers. The 72-hour cadence remains anchored to stored `published_at` evidence — including after an approved manual post removal (removal changes no metadata, so cadence continues to apply from the recorded `published_at`).
- **Scheduling contracts are untouched.** Defer moves only the target variant's `scheduled_at_utc` (single-variant defer semantics; no automatic sibling rescheduling); the original schedule idempotency proof is preserved and repeat `POST /schedule-linkedin-distribution` behavior is unchanged.
- **The enablement guard stays fail-closed.** `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` remains fail-closed; no fallback step bypasses or weakens it, and no fallback step requires enabling it.

## Fallback outcome vocabulary

Fixed documented checklist labels — no worker codes are introduced. Used exactly and exclusively for recording fallback decisions:

| Label | Meaning |
|---|---|
| `fallback_accept_rendering` | Wrong or missing card accepted (pre-publish "accept and proceed" or post-publish "accept and record"); defect described in the evidence record |
| `fallback_delay_publication` | `pending` variant deferred via `POST /defer-linkedin-variant` (or a `queued` variant's real publish-due request withheld) to allow cache expiry; US-024 re-confirmation required before publication |
| `fallback_correct_inputs_reverify` | Inputs corrected on the canonical blog side (ADR-0002), then US-023 re-verification and US-024 re-confirmation |
| `fallback_cancel_variant` | Variant withdrawn via `POST /cancel-linkedin-publication`; sequence released; irreversible |
| `fallback_post_removal_approved` | Approval-gated manual removal of the operator's own published post via the LinkedIn UI, with prior recorded approval; variant stays `published` |
| `fallback_format_change_deferred` | `preview_not_rendered_post_format` escalated to the named future OpenSpec change (explicit article post format); no change to current publication behavior |
| `fallback_blocked` | A named blocking condition prevented the fallback decision or action (see blocked states); never recorded as a failure of inputs, rendering, or this policy |

## Evidence record template

Each fallback decision is recorded using this template, following the operations-report pattern (`docs/operations/`). Campaign metadata (`metadata/campaigns/<campaign-id>.json`) is **never** edited to record fallback outcomes.

```markdown
## LinkedIn preview fallback decision — <campaign-id>

- **Campaign id:** <campaign-id>
- **Affected variant(s) and `publish_state` at decision time:** <variant-id: state, ...>
- **Triggering US-024 evidence record:** outcome label <label>, confirmed at (UTC) <ISO-8601>
- **Referenced US-023 verification run:** `validated_at_utc` <UTC ISO-8601> (real run) or response snapshot (dry-run); overall status <status>
- **Chosen action:** <accept / delay / correct-and-reverify / cancel / manual post removal>
- **Classification:** <supported / approval-gated>
- **Prior approval (approval-gated only):** <who approved, when (UTC), where recorded>
- **Endpoint calls made:** <endpoint, dry_run true/false, key response fields — or "none (accept-and-record)">
- **Resulting variant `publish_state`:** <state per variant>
- **Outcome label:** one of the fixed fallback vocabulary above
- **Blocking condition (`fallback_blocked` only):** <named condition + next action>
- **Operator:** <name> — **decided at (UTC):** <ISO-8601>
```

Rules:

- Outcome labels come from the fixed vocabulary above — use them exactly and exclusively.
- No LinkedIn session data, credentials, secrets, variant body text, or image bytes in evidence records.
- Campaign metadata files are never modified by this recording procedure.

## Blocked states

Blocked fallback attempts are recorded with the `fallback_blocked` label plus the specific blocking condition. They are never recorded as failures of the preview inputs, of LinkedIn rendering, or of this policy — and they never result in guessing or improvising an action.

| Blocking condition | Next action |
|---|---|
| No US-024 evidence record with a fallback-triggering outcome exists for the campaign | Complete the US-024 confirmation procedure first; fallback proceeds only from a recorded triggering outcome |
| US-024 safe re-scrape cycle not completed for a stale-cache trigger | Complete the US-024 safe re-scrape (US-023 re-confirmation, Post Inspector re-inspection, propagation lag) and re-classify before any fallback decision |
| Prior approval absent for an approval-gated action | Obtain and record explicit operator/owner approval first; the post remains untouched until then |
| A required input correction depends on a live-site Git commit/push that has not been approved | Obtain explicit operator approval for the push through the existing guarded/manual publication paths, then continue the correct-and-reverify loop |
| Chosen action invalid for the affected variant's `publish_state` (for example defer on a `queued` variant) | Choose an action valid for the state (for a `queued` variant: withhold the real publish-due request, or cancel); no un-queue path is invented |

## Status language

- This policy is **defined** — it is not deployed (nothing to deploy: docs + canonical procedure-spec only, no worker code), not operationally validated, and US-025 is **not accepted**.
- US-025 acceptance requires an operator-demonstrated fallback decision with a completed evidence record on a real campaign — which transitively depends on the pending US-023 deploy + operational validation on `192.168.0.194` and a US-024 confirmation producing a triggering outcome.
- BL-009 remains open until the US-023, US-024, and US-025 business outcomes are all demonstrated and accepted.
