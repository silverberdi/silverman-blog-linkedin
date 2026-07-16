# LinkedIn variant quality and differentiation criteria (Flow A)

**Scope:** US-016 (BL-006 story 2) — operator-visible quality and differentiation criteria for Flow A LinkedIn variants during the optional supervision window.  
**Status:** Criteria defined (docs/spec + campaign metadata `objective`); US-017 enforcement and automated queue-time checks remain deferred.  
**Authority:** Complements [linkedin-variant-review-policy.md](linkedin-variant-review-policy.md) (US-015), [GLOSSARY.md](../GLOSSARY.md), [user-stories.md](../product/user-stories.md) US-016, and [silverman-editorial-system.md](../../content-strategy/silverman-editorial-system.md) `#audience-map`, `#linkedin-derivative-package`, `#no-redundancy-rules`, `#anti-ai-writing-rules`, `#linkedin-distribution-strategy`, `#flow-a-vs-flow-b`.

## Purpose and scope

This document answers: **“Is this variant good enough and distinct enough to publish for its intended audience and objective?”** during the optional supervision window while `publish_state` is `pending`.

**In scope (US-016):**

- Quality and differentiation criteria for operator judgment during supervision.
- Normative default variant mapping (audience lens + publication objective + differentiation checks).
- Supervision-window checklist derived from the mapping.
- Criteria-failure vs technical-block vs deferred-capability communication.

**Out of scope (deferred):**

- **US-017** — correction, rejection, defer, or cancel before queue; persisted operator overrides; supervision console UI.
- **BL-007** — `auto_queue_pending` WIP, publish-pending n8n workflow, deploy publish-pending scripts (see [bl-007-auto-queue-pending-handoff.md](../product/bl-007-auto-queue-pending-handoff.md) as future consumer only — **do not merge or run that WIP from this criteria doc**).
- Worker HTTP routes, n8n LinkedIn publish workflow changes, and permanent LinkedIn enablement (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`).
- Automated criteria enforcement at package generation, queue, or publish time.
- Mandatory per-variant approval gates or new `publish_state` values for criteria failure.

## Relationship to US-015 supervision window

US-015 defines **strategy-driven publication** (all scheduled variants expected to publish unless operator override) and the **optional supervision window** while `pending` before LinkedIn API queue/send.

This criteria document **guides optional supervision** — it does **not**:

- Convert Flow A into mandatory per-variant approval.
- Change US-015 strategy-driven defaults or `publish_state` enum values.
- Block auto-queue or publish when criteria are not formally recorded (BL-007 / US-017 deferred).

Operators **MAY** use these criteria while supervising; absence of a recorded criteria pass does **not** mean “do not publish.” See [linkedin-variant-review-policy.md](linkedin-variant-review-policy.md).

## Normative default variant mapping

Source of truth for audience lens, publication objective, and differentiation focus. Canon definitions: `#audience-map`, `#linkedin-derivative-package`.

| Variant ID | Primary audience lens | Publication objective | Differentiation focus |
|------------|----------------------|----------------------|------------------------|
| `executive-recruiter` | Recruiters + C-level | Signal seniority, scope, hireable judgment in 60-second read | Business outcome framing; distinct hook from technical variants |
| `technical-architect` | Software architects | Teach the design move; name trade-offs | Constraint → pattern arc; deepest technical angle |
| `engineering-leadership` | Engineering managers | Team/delivery implications of the architectural choice | Leadership stakes; coaching angle |
| `short-provocative` | Senior ICs + enthusiasts | One sharp insight; pattern interrupt | Shortest form; boldest opening; no blog-summary opener |

**Metadata visibility:** After Flow A package generation, each `variants[]` entry in `metadata/campaigns/<campaign-id>.json` includes `audience`, `audience_lens`, `objective`, and `tone`. `objective` is publication purpose; `tone` is voice/style for generation — see [GLOSSARY.md](../GLOSSARY.md).

Sibling variants in the same package **MUST** differ on hook, objective angle, structure, and CTA phrasing per `#no-redundancy-rules`.

## Quality criteria

Evaluate each variant against the canonical blog and editorial canon. Quality checks apply during optional supervision — not as automated queue gates in US-016.

### Source fidelity

- Facts, examples, and thesis derive from the canonical blog only.
- **MUST NOT** invent metrics, companies, client names, or URLs not present in the source.
- **MUST NOT** contradict the blog’s technical or business claims.

### Voice and style fit

- Senior, practical tone per `#voice-and-style`.
- **MUST NOT** use engagement bait, hashtags, or emoji by default.
- Reads as architecture leadership — not generic thought leadership or marketing copy.

### Anti-AI editorial patterns (derivatives)

Generated LinkedIn derivatives follow `#anti-ai-writing-rules` **rewrite/blocking posture** for derivatives — **not** the Flow A user-blog warning posture.

During supervision, if the variant sounds AI-generated (template openers, hollow transitions, buzzword stacking), the operator **SHOULD** edit or defer (US-017 mechanics to persist override). US-016 documents this as quality criteria for human judgment only.

### CTA and URL rules

- CTA placement and phrasing per `#cta-rules`.
- `source_public_url` appears exactly once per variant (publish-confirmed URL from campaign).
- **MUST NOT** use “follow for more” as primary close.

### Independent readability

- Each variant stands alone without requiring the blog opening.
- A reader who never saw the blog still understands the insight and why it matters for that variant’s audience lens.

## Differentiation criteria (sibling variants)

Aligned with `#no-redundancy-rules`. Across variants in the same package, the following **MUST** be unique per variant:

| Dimension | Requirement |
|-----------|-------------|
| **Opening hook** | First 1–2 sentences differ materially — not paraphrase of another variant |
| **Primary objective angle** | Each variant optimizes for its lens (see mapping table) |
| **Central thesis angle** | Same blog fact, different emphasis — not copy-paste takeaway |
| **Structure** | Vary paragraph count, list usage, and narrative arc |
| **CTA phrasing** | Different natural-language close; same URL allowed but phrasing **MUST** differ |

**MUST NOT** duplicate variant text with only the audience label changed.

Automated similarity checks remain deferred per canon “Validation (future).”

## Supervision-window checklist

Use while `publish_state` is `pending` and before LinkedIn API queue/send. Optional — not a mandatory approval gate.

For each variant, answer:

1. **Audience + objective fit** — Does the draft serve the mapped primary audience lens and publication objective (mapping table above)?
2. **Source fidelity** — Are all claims traceable to the canonical blog?
3. **Voice** — Senior, practical, no engagement bait/hashtags/emoji?
4. **Anti-AI** — Free of template/AI patterns per `#anti-ai-writing-rules` derivative posture?
5. **Standalone readability** — Understandable without reading the blog first?
6. **CTA/URL** — One correct `source_public_url`; CTA per `#cta-rules`?
7. **Sibling differentiation** — Unique hook, objective angle, structure, and CTA phrasing vs other variants in this package?

**Pass:** Variant meets criteria; proceed per US-015 strategy unless other override.  
**Criteria failure:** See table below — operator **SHOULD** edit, defer, or cancel during supervision (US-017 to persist).

## Criteria failure, technical blocks, and deferred states

| Condition | Classification | Operator implication |
|-----------|----------------|----------------------|
| Variant passes criteria | Normal supervision | Proceed per US-015 strategy unless other override |
| Variant fails quality/differentiation | **Criteria failure** (editorial guidance) | Operator **SHOULD** edit, defer, or cancel during supervision — **US-017 mechanics to persist override** |
| `pending`, before `scheduled_at_utc` | Normal supervision window | Not a failure (US-015) |
| Enablement off / `failed` / OAuth action-required | Technical block | Existing publication semantics; not criteria failure |
| US-017 / supervision console absent | Deferred capability | Criteria still apply to human judgment; absence is **not** a worker defect |
| BL-007 not implemented | Deferred capability | Manual queue/publish or wait for BL-007 OpenSpec apply |
| Automated similarity check | Deferred | Operator judges differentiation manually per checklist |

**Criteria failure** is editorial guidance during optional supervision — not a new worker `publish_state` value and **not** a mandatory approval gate in US-016.

## Preserved behavior (no duplication)

US-016 is criteria + minimal metadata alignment. It does **not** change:

- US-015 strategy-driven publication or optional supervision window substance.
- Flow A ready-path completion, package, or schedule behavior.
- US-011 publication-guard semantics (`distribution_scheduled` ≠ LinkedIn API published; enablement fail-closed).
- ADR-0001 (n8n → worker HTTP only).
- Existing `POST /queue-linkedin-publication`, `POST /publish-linkedin-due-variants`, or `POST /cancel-linkedin-publication` contracts.

## Related documents

- [linkedin-variant-review-policy.md](linkedin-variant-review-policy.md) — US-015 publication and supervision policy
- [GLOSSARY.md](../GLOSSARY.md) — variant publication objective, criteria failure, supervision window
- [user-stories.md](../product/user-stories.md) — US-016 acceptance criteria
- [silverman-editorial-system.md](../../content-strategy/silverman-editorial-system.md) — `#audience-map`, `#linkedin-derivative-package`, `#no-redundancy-rules`, `#anti-ai-writing-rules`, `#linkedin-distribution-strategy`, `#flow-a-vs-flow-b`
- [bl-007-auto-queue-pending-handoff.md](../product/bl-007-auto-queue-pending-handoff.md) — future auto-queue consumer (WIP, out of scope)
