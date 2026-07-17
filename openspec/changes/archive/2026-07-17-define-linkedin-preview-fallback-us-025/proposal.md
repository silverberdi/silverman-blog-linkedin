# Proposal: define-linkedin-preview-fallback-us-025

## Why

BL-009 ("Validate LinkedIn Article Preview Rendering") closes only when published LinkedIn posts display the intended article preview. US-023 (input verification, implemented + unit-tested, not deployed) and US-024 (rendering-confirmation procedure, defined, not operationally validated) can now **detect** an incorrect or missing preview, but neither defines a **reaction**. Three US-024 outcomes currently end as recorded observations with no defined next step:

1. `preview_stale_cache` when the safe Post Inspector re-scrape does not produce the intended card;
2. `preview_not_rendered_post_format` — the v1 personal-profile text post (URL in commentary, no `content.article` entity) renders no card at all;
3. an already-published post retaining a stale or incorrect card (a re-scrape affects new posts only).

Without a normative fallback policy, the operator is left to improvise exactly the reactions the US-024 procedure had to forbid: publishing extra posts to force a refresh, cache-busting the canonical `public_url`, deleting and re-posting, or hand-editing campaign metadata — all of which carry duplicate-publication or evidence-corruption risk that no existing safeguard catches. US-025 is the last open story of BL-009; defining this policy is the remaining definitional work before the backlog item's business outcome can be demonstrated.

## Scope determination (documentation/procedure vs worker implementation)

This proposal determines that **US-025 is a documentation/procedure-only change** (operator policy document + one new canonical procedure-capability spec), with **no worker/API implementation**:

- Every supported fallback action already exists as guarded worker surface: `POST /defer-linkedin-variant` (delay), `POST /cancel-linkedin-publication` (withdraw), `POST /correct-linkedin-variant` (pre-queue content correction), `POST /validate-linkedin-article-preview` (US-023 re-verification), and the US-024 confirmation procedure (re-observation). The fallback policy composes them; it does not need new endpoints, request fields, env vars, or `publish_state` values.
- The two candidate actions that *would* require worker changes — an explicit article post format (e.g. `content.article`) and post deletion/re-publication — fail the safety analysis for this change (see design.md) and are **evaluated and explicitly deferred** as named future-change candidates, not implemented. Adding speculative automation for them would violate the smallest-coherent-diff rule and the US-024 boundary contracts.

This mirrors the accepted pattern of US-021 (retry/recovery classification: policy first, mechanics later under US-022) and US-024 (procedure-spec only).

## Goals

- Define a normative, operator-executed fallback decision policy for every US-024 outcome that can require one, separated into **pre-publish fallback** (no variant published yet) and **post-publish recovery** (a published post shows a wrong/missing card).
- Classify every candidate action as **supported**, **approval-gated**, or **forbidden**, with explicit reasoning tied to duplicate-publication risk, idempotency protections, publication evidence, variant state, scheduling/sequence effects, and the US-021/US-022 retry-recovery safeguards.
- Define operator-visible fallback outcome labels, blocked states with next actions, and an evidence-record template (extending the US-024 record pattern; campaign metadata never edited to record fallback outcomes).
- Keep US-023 as the sole source of input-correctness truth and US-024 as the sole rendering-observation source; the fallback policy consumes their verdicts and never re-derives them.
- Evaluate the required alternatives (accept text-only, delay, correct-and-repeat, `content.article`, handling an already-published wrong card) on their merits, without pre-assuming the answer.

## Non-goals

- No worker code, endpoints, request/response fields, environment variables, n8n workflows, or deploy-script changes.
- No implementation of a `content.article` (or any) post-format change, LinkedIn image upload, or post-deletion capability — these are analyzed and deferred with named preconditions for a future OpenSpec change.
- No LinkedIn UI scraping, no browser automation against LinkedIn, no reliance on undocumented API behavior, no cache-busting URL manipulation.
- No modification of US-018–US-024 contracts: publication integration (states, guards, idempotency, evidence), retry-recovery classification, distribution scheduling, preview-image support, US-023 verification, and the US-024 procedure all remain unchanged. No MODIFIED requirements are proposed.
- No automatic fallback execution of any kind; every fallback action is an explicit operator decision.
- Closing US-025 or BL-009: this change defines the policy; story acceptance requires a separate approval-gated operator demonstration, and BL-009 stays open until US-023, US-024, and US-025 business outcomes are demonstrated and accepted.

## What Changes

- **New canonical procedure capability** `linkedin-article-preview-fallback` (spec delta in this change; lands under `openspec/specs/` at sync) defining:
  - fallback triggers: consumed US-024 outcomes (`preview_stale_cache` after a completed safe re-scrape cycle, `preview_not_rendered_post_format`, and post-publish observation of a stale/incorrect card on a published post) — never raw operator impressions;
  - the pre-publish fallback decision procedure over existing worker capabilities (accept, delay via defer, correct inputs and repeat US-023/US-024, cancel), with per-action safety notes (sequence blocking under US-020, defer future-time rule, cancel irreversibility);
  - the post-publish recovery decision procedure (accept-and-record default; approval-gated manual actions with mandatory evidence);
  - the supported / approval-gated / forbidden action classification, including the explicit prohibition list;
  - fixed fallback outcome vocabulary and an evidence-record template;
  - blocked states and operator communication;
  - an existing-capabilities-unchanged requirement with qualified status language.
- **New operator policy document** `docs/operations/linkedin-preview-fallback-policy.md` (the operator-facing artifact of the capability, following the US-021/US-024 document pattern).
- **Cross-reference updates (docs only):** pointers from `docs/operations/linkedin-preview-rendering-confirmation.md` (US-024's "fallback is US-025 territory" notes) and `docs/deployment/linkedin-publication-prerequisites.md` to the new policy; `docs/product/user-stories.md` US-025 mechanism mapping; `docs/product/progress-checklist.md` work-started state; `docs/CURRENT-STATE.md` entry with qualified status language.

## Capabilities

### New Capabilities

- `linkedin-article-preview-fallback`: Normative operator fallback policy for BL-009 / US-025 — the decision procedure, action classification (supported / approval-gated / forbidden), outcome vocabulary, evidence records, and blocked states for reacting to an incorrect or missing LinkedIn article preview detected via US-023/US-024. Procedure capability only: no worker code, no LinkedIn API usage beyond existing capabilities.

### Modified Capabilities

None. `linkedin-article-preview-verification` (US-023), `linkedin-article-preview-rendering-confirmation` (US-024), `linkedin-article-preview-image-support`, `linkedin-publication-integration` (US-018/US-019/US-020), `linkedin-retry-recovery-classification` (US-021/US-022), and `linkedin-distribution-scheduling-model` are consumed as-is. If the fallback analysis had required changing any of their requirements, this proposal would carry an explicit MODIFIED delta with justification; it does not.

## Backlog and user-story traceability

- **Backlog item:** BL-009 — Validate LinkedIn Article Preview Rendering (expected outcome: "Define a fallback when the preview is incorrect").
- **User story:** US-025 — "As a content operator, I want to define a fallback when the preview is incorrect, so that published LinkedIn posts display the intended article preview."
- **Acceptance criteria addressed** (at policy-definition scope; demonstration is a separate approval-gated task):
  - *Define a fallback when the preview is incorrect* — the decision procedures and action classification above.
  - *The outcome is visible and understandable to the intended user* — operator policy document, fixed outcome vocabulary, evidence-record template.
  - *Failures or blocked states are clearly communicated* — blocked-state table with named conditions and next actions, distinct from fallback outcomes.
  - *Existing completed work is not duplicated or unintentionally changed* — zero changes under `src/`, `tests/`, `n8n/`, `deploy/`; US-018–US-024 contracts untouched; no duplicate input checks or rendering observations defined.
- **Acceptance criteria intentionally excluded from this change's implementation:** none excluded at definition scope; however, criteria checkboxes remain unchecked until the operator demonstrates the fallback procedure on a real campaign (which transitively depends on the pending US-023 deploy + operational validation and a US-024 confirmation producing a fallback-triggering outcome).

## Impact

- **Code:** none (no changes under `src/`, `tests/`, `n8n/`, `deploy/`; full pytest not required for a docs/spec-only change per engineering standards).
- **Docs:** one new operations document; targeted cross-reference edits in the US-024 procedure doc and LinkedIn publication prerequisites doc; product docs (user stories, progress checklist) and CURRENT-STATE updated with qualified status language.
- **Specs:** one new capability spec (`linkedin-article-preview-fallback`) at sync; no deltas to existing specs.
- **Operations:** operators gain a defined, safe reaction path for wrong/missing previews; the approval-gated demonstration task (tasks.md) is the only step touching the live system, and it executes existing guarded endpoints only.
- **Status language:** proposed/defined ≠ deployed ≠ operationally validated ≠ accepted; BL-009 remains open until US-023, US-024, and US-025 outcomes are demonstrated and accepted.
