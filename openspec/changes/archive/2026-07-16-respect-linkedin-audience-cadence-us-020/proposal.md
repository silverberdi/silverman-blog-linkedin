# Proposal: respect-linkedin-audience-cadence-us-020

## Why

US-020 (BL-007 story 3) requires that due LinkedIn variants are published **once, in order, with complete publication evidence** — respecting audience cadence and sequence. Once-only publication (US-018, operationally validated) and complete evidence (US-019, implemented) are already covered. The remaining gap is execution-time enforcement: the `flow_a_staggered` schedule encodes canonical audience order with ≥3-day spacing at **schedule time**, but nothing enforces order or real spacing at **publish time**. When several variants of one campaign are simultaneously due or queued (delayed orchestration, worker downtime, campaign-wide `publish_now`, or manual queueing out of order), the current publish phase publishes them within the same request, collapsing the audience cadence to seconds — exactly the audience saturation the stagger exists to prevent. Schedule-time spacing also degrades under accumulated delays: two variants scheduled 3 days apart can both become due and then publish back-to-back.

## Goals

- Make the cadence/sequence contract of scheduled LinkedIn publication execution normative and test-verified **at publish time**, where it cannot be bypassed by invocation patterns or manual queueing.
- Add a per-campaign **publish-time guard** with two rules applied to every publish-due evaluation over `queued` variants — plain publish-due, the combined `auto_queue_pending` flow, targeted requests, and the cross-campaign scan:
  - **Sequence rule:** variant N is never published while an earlier variant in the canonical audience sequence is still awaiting publication (`pending` — including operator-deferred — or `queued` and unpublished).
  - **Real cadence rule:** successful publications within one campaign are separated by a minimum of 3 days (72 hours), measured against stored `published_at` evidence (US-019), regardless of invocation frequency, accumulated delays, or `publish_now`. A publish completed within the current run counts, so at most one variant per campaign publishes per run.
- Keep an auto-queue **pre-filter** (skip reason `linkedin_publish_auto_queue_skipped_sequence`) so sequence-blocked `pending` variants are not needlessly queued; the publish-time guard remains the normative enforcement point.
- Fail closed and visibly when cadence cannot be computed: a `published` variant with missing/invalid `published_at` blocks its campaign with a dedicated stable reason instead of guessing.
- Surface each block with a distinct stable reason: `linkedin_publish_blocked_sequence`, `linkedin_publish_blocked_cadence`, `linkedin_publish_blocked_evidence_invalid` (publish time) and `linkedin_publish_auto_queue_skipped_sequence` (auto-queue pre-filter), preserving existing US-018 skip-reason precedence and semantics.

## Non-Goals

- No retry, recovery, recoverable/non-recoverable classification, token-renewal behavior, timeout duplicate mitigation, or attempt history after manual re-queue — all **BL-008**, named as an explicit exclusion in the delta.
- No changes to `POST /queue-linkedin-publication`'s queue contract, to US-017 supervision mechanics or endpoints, or to any synced US-018/US-019 contract (no renames, no retyping, no new endpoints, no new request flags, no new `publish_state` values).
- No global cross-campaign cadence: each campaign's sequence and cadence are evaluated independently in the cross-campaign scan; two campaigns may still publish the same day (global rhythm is editorial-calendar territory, BL-020/BL-021).
- No claim of unconditional strict canonical publication order: `failed` and `cancelled` release the chain by design, and manual re-queue of a failed earlier variant after followers published is a recorded operator consequence. The normative guarantee is: **no later variant publishes while an earlier variant is awaiting publication.**
- No automatic evidence repair: invalid `published_at` on a `published` variant is a manual metadata fix outside this capability.
- No deploy, no n8n activation, no closure of US-019/US-020/BL-007 — closure is a separate authorized validation step.

## What Changes

- `linkedin-publication-integration` gains an ADDED requirement: per-campaign publish-time sequence and cadence guard (sequence rule over awaiting-publication earlier variants including deferred ones, 72-hour real cadence from `published_at`, within-run cadence, evidence fail-closed rule, stable reasons and their precedence, `publish_now` timing-only scope, per-campaign independence in the scan, auto-queue pre-filter, dry-run semantics, BL-008 exclusion boundary).
- MODIFIED (full canonical blocks copied, additive only): publish due variants service (guard enforcement point in the publish path for all invocation modes), auto-queue eligibility exclusions (sequence pre-filter evaluated last, deferred earlier variants block followers), auto-queue outcome visibility (publish-time guard reasons surfaced per variant), stable error codes (three new codes), and test coverage (US-020 scenario-mirroring tests, mocked LinkedIn client, zero real calls).
- `linkedin-distribution-scheduling-model` is **not** modified: canonical order, schedule-time stagger, distinct `scheduled_at_utc`, and US-017 defer mechanics remain exactly as synced; this change only consumes them at execution time. No delta on that capability is necessary because no scheduling-time behavior changes.
- Minimal code change in `linkedin_publication_flow.py`: guard evaluation in the publish path (`_publish_single_variant` call sites / target evaluation) plus the auto-queue pre-filter in `_auto_queue_skip_reason`, reusing the canonical `AUDIENCE_SEQUENCE` from `linkedin_distribution_schedule.py`. No new endpoints, no request/response field renames.
- Operator documentation: publish-time sequence and cadence semantics, blocking vs releasing states, defer blocking followers, fail-closed evidence behavior, and the fact that manual queueing cannot bypass the guard at publish time — in `docs/deployment/linkedin-publication-prerequisites.md`; CURRENT-STATE updated with "implemented, not deployed" language.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `linkedin-publication-integration`: adds the per-campaign publish-time sequence and cadence guard (new requirement + additive modifications to the publish-due service, auto-queue eligibility exclusions, outcome visibility, stable error codes, and test coverage).

## Traceability (BL-007 / US-020)

| US-020 acceptance criterion | How this change addresses it |
|---|---|
| Respect audience cadence and sequence | Publish-time guard: no later variant publishes while an earlier one awaits publication; real ≥72-hour interval between successful publications per campaign, from `published_at` evidence; enforced in every invocation mode including `publish_now` and manual queueing |
| The outcome is visible and understandable to the intended user | Distinct stable reasons for sequence block, cadence block, and invalid evidence; operator docs describe blocking vs releasing states and defer behavior |
| Failures or blocked states are clearly communicated | `failed`/`cancelled` release the chain (no silent freeze); blocked variants keep their state, make no LinkedIn calls, and never fail the whole scan; missing `published_at` fails closed with its own visible reason; US-019 failure taxonomy untouched |
| Existing completed work is not duplicated or unintentionally changed | Additive-only delta; US-018 auto-queue and US-019 evidence contracts preserved; existing tests must pass unmodified without weakened assertions |

Acceptance criteria intentionally excluded: none excluded from US-020 itself; story **closure** (demonstration/validation) is out of scope of this change per BL-007 governance — US-020 remains in progress after implementation, and BL-007 stays open.

## Impact

- **Code**: `src/silverman_blog_linkedin/linkedin_publication_flow.py` (publish path guard + auto-queue pre-filter); import of the canonical audience sequence from `linkedin_distribution_schedule.py`.
- **Tests**: `tests/test_linkedin_publication.py` — new US-020 scenario-mirroring tests (all with mocked LinkedIn client, zero real calls); existing US-018/US-019 tests must pass unmodified.
- **Docs**: `docs/deployment/linkedin-publication-prerequisites.md` (operator contract), `docs/CURRENT-STATE.md`, `docs/product/user-stories.md` / `progress-checklist.md` (acceptance-criteria mapping without closing the story).
- **APIs**: no new endpoints or request fields; `POST /publish-linkedin-due-variants` responses gain only new values in the existing stable reason taxonomy.
- **Behavior change bounded to**: publication of `queued` variants when an earlier variant awaits publication, when the campaign published less than 72 hours ago, or when `published_at` evidence is invalid — previously published anyway, now blocked with visible stable reasons. Single-variant nominal paths (US-018 validated scenarios) are unaffected.
- **Guardrails honored**: ADR-0001 (worker HTTP only), fail-closed `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, dry-run default, no secrets or variant body text in responses/metadata, no deploy or n8n activation.
