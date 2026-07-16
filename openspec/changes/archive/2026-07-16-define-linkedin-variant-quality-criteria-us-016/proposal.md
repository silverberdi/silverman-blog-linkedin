## Why

US-015 defined Flow A LinkedIn publication expectations and the optional supervision window, but operators still lack explicit criteria to answer whether a scheduled variant is **good enough and distinct enough** to publish for its intended audience and objective. US-016 closes that gap now so supervision during `pending` is guided by normative quality and differentiation rules—not ad hoc judgment or accidental reopening of US-015 strategy-driven defaults.

## Goals

- Establish operator-visible **quality** and **differentiation** criteria for Flow A LinkedIn variants during the optional supervision window.
- Associate each default variant ID with a **primary audience lens** and **publication objective** the operator can verify.
- Make criteria outcomes understandable without reading worker source code.
- Communicate what constitutes a criteria failure or blocked/deferred state versus normal `pending` supervision.
- Preserve US-015 publication defaults, Flow A lifecycle, US-011 guards, and ADR-0001 without duplicating completed work.

## Non-Goals

- US-017 — correction, rejection, defer, cancel mechanics; persisted operator overrides; supervision console UI.
- BL-007 — `auto_queue_pending`, publish-pending n8n, deploy publish-pending scripts.
- New worker HTTP routes, n8n LinkedIn publish workflows, or LinkedIn API publish behavior changes.
- Permanent LinkedIn enablement changes or US-011 guard weakening.
- Automated enforcement of criteria at queue/publish time (deferred to future generation/validation work).
- BL-006 closure (remains open until US-017).
- Flow B mandatory review implementation.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-006** | Partial (story 2 only) | Full BL-006 completion remains after US-017 |
| **US-016** | Yes | All five acceptance criteria |
| **US-015** | No | Extend via cross-links only; do not contradict |
| **US-017** | No | Criteria failures inform operator action; mechanics deferred |
| **BL-007+** | No | Criteria do not add queue eligibility gates beyond US-015 |

**US-016 acceptance criteria addressed:**

1. Establish quality and differentiation criteria → normative criteria artifact + spec requirements.
2. Associate each variant with audience and objective → default variant mapping table + campaign `variants[]` metadata (`audience` today; add `objective` per design D6).
3. Outcome visible and understandable → operator doc, cross-links from US-016 / policy / GLOSSARY.
4. Failures or blocked states clearly communicated → criteria-failure vs technical-block vs US-017-deferred table.
5. Existing completed work not duplicated or unintentionally changed → no publication-flow or US-015 policy rewrite.

**Intentionally excluded:** US-017 enforcement, BL-007 automation, console UI, worker route additions.

## What Changes

- Add operator-facing quality and differentiation criteria at `docs/operations/linkedin-variant-quality-criteria.md` (separate from US-015 policy; cross-linked).
- Extend `linkedin-variant-review-process` capability with normative US-016 requirements (criteria artifact, variant audience/objective association, blocked-state communication).
- Add lightweight presence/contract test mirroring `tests/test_linkedin_variant_review_policy.py`.
- Update `docs/operations/linkedin-variant-review-policy.md` out-of-scope/deferred sections to point at US-016 criteria (not rewrite US-015 decisions).
- Cross-link `docs/GLOSSARY.md`, `docs/product/user-stories.md` US-016, and editorial canon anchors (`#audience-map`, `#linkedin-derivative-package`, `#no-redundancy-rules`, `#anti-ai-writing-rules`, `#linkedin-distribution-strategy`).
- **Minimal metadata alignment (optional, design-justified):** persist `objective` in campaign `variants[]` at package generation via `DEFAULT_VARIANT_EDITORIAL_MAP` — closes spec↔implementation gap with `flow-a-automatic-publishing` (`objective` already normative; worker currently writes `tone` only). Does **not** touch `linkedin_publication_flow.py` BL-007 WIP.
- After demonstrated ACs only: update CURRENT-STATE and product progress for US-016 (not BL-006 closed).

## Capabilities

### New Capabilities

_None — extends existing `linkedin-variant-review-process` rather than introducing a separate capability._

### Modified Capabilities

- `linkedin-variant-review-process`: Add US-016 quality/differentiation criteria artifact, default variant audience/objective mapping, supervision-window evaluation guidance, and criteria-failure vs blocked/deferred communication. Does not modify US-015 strategy-driven publication defaults.
- `editorial-canon`: Add requirement that review-process criteria consume editorial canon anchors (`#audience-map`, `#no-redundancy-rules`, `#anti-ai-writing-rules`, `#linkedin-derivative-package`) without duplicating canon text.
- `flow-a-automatic-publishing`: Clarify that campaign `variants[]` entries MUST include `objective` (publication purpose) alongside `audience` at package generation for default variant IDs — minimal worker metadata alignment only.

## Impact

- **Product:** Advances BL-006 / US-016 only; US-017 and BL-007 remain open.
- **Docs:** New criteria artifact; policy cross-links; GLOSSARY/CURRENT-STATE/progress updates after validation.
- **OpenSpec:** Delta specs for `linkedin-variant-review-process`, `editorial-canon`, and `flow-a-automatic-publishing`.
- **Worker:** Optional tiny change in `linkedin_package_flow.py` only (`objective` in `variants[]` metadata). No `linkedin_publication_flow.py`, routes, n8n, or enablement changes.
- **Tests:** New or extended presence test for criteria doc; optional assertion that default variant map includes `objective`.
- **Preserved:** US-015 strategy-driven defaults; ADR-0001; US-011; existing `publish_state` machine; Flow B deferred mandatory review.
