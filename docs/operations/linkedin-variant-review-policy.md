# LinkedIn variant review policy (Flow A)

**Scope:** US-015 (BL-006 story 1) — operator-visible publication and supervision policy for Flow A LinkedIn variants.
**Status:** Policy defined (docs/spec); US-016 criteria defined (see [linkedin-variant-quality-criteria.md](linkedin-variant-quality-criteria.md)); US-017 supervision mechanics defined (see [linkedin-variant-supervision-mechanics.md](linkedin-variant-supervision-mechanics.md)); US-038–US-040 supervision console implemented at `GET /flow-a/console/linkedin-variant-supervision` (edit/defer/cancel via US-017 POSTs; **Story accepted**; **BL-015 closed**) — see [CURRENT-STATE.md](../CURRENT-STATE.md).
**Authority:** Complements [GLOSSARY.md](../GLOSSARY.md), [silverman-editorial-system.md](../../content-strategy/silverman-editorial-system.md) `#flow-a-vs-flow-b`, and [user-stories.md](../product/user-stories.md) US-015.

## Purpose and scope

This document is the operator source of truth for:

1. Whether Flow A scheduled LinkedIn variants are **expected to publish** (strategy-driven default vs operator override).
2. When human review is **mandatory** (Flow B) versus **optional supervision** (Flow A pre-send window).

**In scope (US-015):** Policy language, glossary alignment, editorial-canon alignment, and product traceability.

**Out of scope (deferred):**

- **BL-007** — `auto_queue_pending` WIP, publish-pending n8n workflow, deploy publish-pending scripts (see [bl-007-auto-queue-pending-handoff.md](../product/bl-007-auto-queue-pending-handoff.md) as future consumer only — **do not merge or run that WIP from this policy**).
- Worker HTTP routes beyond policy scope, n8n LinkedIn publish workflow changes, and permanent LinkedIn enablement (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`).
- **BL-022 / US-053 business and content metrics** (blog traffic, LinkedIn reach/engagement, profile/audience growth) — Authority Manager **operational metric chips** (upcoming / pending / due soon / blocked / failed / recently published) are **triage counts**, not US-053 business outcomes. Normative metrics definition: [business-and-content-metrics.md](business-and-content-metrics.md).

**Implemented elsewhere (US-017):** Correction, rejection/cancel-from-pending, defer, and `operator_supervision` metadata — see [linkedin-variant-supervision-mechanics.md](linkedin-variant-supervision-mechanics.md). `POST /cancel-linkedin-publication` now accepts `pending` (pre-queue) in addition to `queued` (post-queue); post-queue cancel semantics unchanged.

## Strategy-driven publication default

Flow A posture (operator-confirmed, non-conservative):

- The **blog** is user-provided and pre-reviewed in `blog-posts/ready/` before Flow A runs.
- **LinkedIn variants** are generated derivatives scheduled per `#linkedin-distribution-strategy` (audience lens, spacing, `scheduled_at_utc`).
- **Default:** all variants scheduled by distribution strategy are **expected to publish** at their scheduled times when publication integration and enablement allow.
- **Operator override only:** explicit **cancel**, **defer/delay**, or **edit** removes or changes that expectation — mechanics in [linkedin-variant-supervision-mechanics.md](linkedin-variant-supervision-mechanics.md) (US-017).
- **Absence of operator action does not mean “do not publish.”** Non-intervention allows publication per strategy when automation exists (BL-007, not implemented here).

This is **not** selective-by-default publication where only a subset is expected to publish without operator override. BL-002 left sibling variants `pending` as a controlled smoke choice, not as the default product posture.

## Optional supervision window (`pending` before API send)

While a variant’s technical `publish_state` is `pending` and before real LinkedIn API queue/send:

- The variant is in the **LinkedIn variant supervision window** (see [GLOSSARY.md](../GLOSSARY.md)).
- The variant is visible on the editorial calendar and in campaign metadata with `scheduled_at_utc`.
- The operator **MAY** supervise: **edit**, **delay**, or **cancel**.
- Supervision is **optional** — not a mandatory approval gate.
- If the operator does not intervene, publication **proceeds per distribution strategy** when BL-007 (or manual queue/publish) runs.

Recording edits, delays, and cancellations in metadata is defined in [linkedin-variant-supervision-mechanics.md](linkedin-variant-supervision-mechanics.md) (US-017). The operator surface is the US-038–US-040 console at `GET /flow-a/console/linkedin-variant-supervision` (data via `GET /flow-a/linkedin-variants/pending-supervision`); edit/defer/cancel call existing US-017 POSTs.

## Mandatory review: Flow A vs Flow B

| Step | Flow A | Flow B |
|------|--------|--------|
| Blog source | User-provided, pre-reviewed `ready` content | AI-generated draft; **never** pre-approved |
| Blog publish / package / schedule | Automatic after validation — **no mandatory human review** | **Mandatory** human **blog** approval first; then same as Flow A |
| Campaign lifecycle (`distribution_scheduled`, `flow_a_complete`) | Automatic after validation — not LinkedIn API published | Same as Flow A **after** blog approval |
| LinkedIn API queue/publish | **Not mandatory** human review; optional supervision while `pending` | **Same as Flow A** after blog approval — optional supervision only (no second mandatory LinkedIn gate) |

**Flow B guardrail:** Unapproved drafts in `blog-posts/pending-approval/` MUST NOT enter Flow A publish paths. After recorded blog approval and promote to `ready/`, content MAY enter Flow A like other ready posts. See [flow-b-simplified-policy.md](flow-b-simplified-policy.md) and `#flow-a-vs-flow-b` in [silverman-editorial-system.md](../../content-strategy/silverman-editorial-system.md). Product backlog: BL-016–BL-019 (US-074–US-082).

## `publish_state`, enablement, and supervision

These concepts are **distinct**:

| Concept | Meaning |
|---------|---------|
| **`publish_state` (`pending`, `queued`, …)** | Technical worker publication state machine. US-015 does not redefine enum values. |
| **`pending` after Flow A schedule** | Scheduled variant in the **optional supervision window** — not yet API-queued, not LinkedIn API published. |
| **`distribution_scheduled` / `flow_a_complete`** | Campaign lifecycle metadata after package/schedule/lifecycle — **≠** LinkedIn API published (US-011). |
| **`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`** | Technical fail-closed guard for real API publish. Separate from Flow A strategy expectations and from Flow B mandatory review. |
| **Supervision window** | Operator MAY intervene while `pending` before send; optional, not an approval gate. |
| **Mandatory review (Flow B)** | Human approval of the **AI blog** before Flow A eligibility — not a mandatory LinkedIn gate after approval. |

## Blocked and deferred states

| State / condition | Meaning | Operator action |
|-------------------|---------|-----------------|
| `pending`, before `scheduled_at_utc` | Scheduled; supervision window open; not yet API-queued | Optional edit/delay/cancel per [linkedin-variant-supervision-mechanics.md](linkedin-variant-supervision-mechanics.md) — **normal**, not a policy failure |
| `pending`, operator cancelled/deferred | Override; not eligible for strategy-driven auto-queue | See US-017 mechanics; `auto_queue_eligible` metadata |
| LinkedIn publication not enabled | Blocked for real API publish (fail-closed) | Enable only for controlled windows; not permanent off (US-011) |
| `failed`, OAuth action-required, missing URN | Integration failure | Existing publication error semantics; BL-008 later |
| Supervision console (BL-015) | Operator UI for pending window | US-038–US-040 console implemented; **Story accepted**; **BL-015 closed** — see CURRENT-STATE |
| BL-007 not implemented | No scheduled auto-queue yet | Manual queue/publish or wait for BL-007 OpenSpec apply |

## Future BL-007 eligibility (documentation only)

When BL-007 scheduled LinkedIn publication is implemented under its own OpenSpec change:

- Auto-queue **SHOULD** target Flow A variants that remain `pending`, are due per `scheduled_at_utc` / queue rules, and have **not** been operator-cancelled or deferred (per [linkedin-variant-supervision-mechanics.md](linkedin-variant-supervision-mechanics.md)).
- Auto-queue **MUST NOT** require a mandatory Flow A human review flag from US-015.
- This policy **does not** instruct operators to merge, deploy, or run the local `auto_queue_pending` WIP, publish-pending n8n workflow, or permanent LinkedIn enablement.

Reference: [bl-007-auto-queue-pending-handoff.md](../product/bl-007-auto-queue-pending-handoff.md) (construction WIP — future consumer only).

## Supervision console (BL-015)

**Backlog:** [BL-015 — Implement Flow A LinkedIn Variant Supervision Console](../product/backlog.md) (US-038–US-040), placed before Flow B (P4). Priority P3; end of operations wave before Flow B starts.

**US-038–US-040 surface:** `GET /flow-a/console/linkedin-variant-supervision` (static HTML) consuming authenticated `GET /flow-a/linkedin-variants/pending-supervision`. Pending list with calendar join, edit/defer/cancel via US-017 POSTs, and blocked-state display (enablement, deferred eligibility, sibling integration failures). **Story accepted**; **BL-015 closed** — see [CURRENT-STATE.md](../CURRENT-STATE.md).

The console is the intended operator surface for calendar-visible supervision (edit, delay, cancel while `pending`). Edit/defer/cancel actions are **not** part of US-015 policy itself. US-017 worker mechanics remain defined in [linkedin-variant-supervision-mechanics.md](linkedin-variant-supervision-mechanics.md).

## Preserved behavior (no duplication)

US-015 is policy-only. It does **not** change:

- Flow A ready-path completion, package, or schedule behavior.
- US-011 publication-guard semantics (`distribution_scheduled` ≠ LinkedIn API published; enablement fail-closed).
- ADR-0001 (n8n → worker HTTP only).
- Existing `POST /queue-linkedin-publication`, `POST /publish-linkedin-due-variants`, `POST /cancel-linkedin-publication` (extended to accept `pending` for pre-queue cancel), `POST /correct-linkedin-variant`, and `POST /defer-linkedin-variant` contracts per US-017 mechanics doc.

## Related documents

- [linkedin-variant-quality-criteria.md](linkedin-variant-quality-criteria.md) — US-016 quality and differentiation criteria
- [GLOSSARY.md](../GLOSSARY.md) — supervision window, `publish_state`, mandatory review
- [user-stories.md](../product/user-stories.md) — US-015 acceptance criteria
- [silverman-editorial-system.md](../../content-strategy/silverman-editorial-system.md) `#flow-a-vs-flow-b`
- [linkedin-variant-supervision-mechanics.md](linkedin-variant-supervision-mechanics.md) — US-017 edit, defer, cancel mechanics
- [bl-007-auto-queue-pending-handoff.md](../product/bl-007-auto-queue-pending-handoff.md) — future auto-queue consumer (WIP, out of scope)
- [backlog.md](../product/backlog.md) — BL-015 supervision console (US-038–US-040)
