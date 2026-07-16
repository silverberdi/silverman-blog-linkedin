## Why

After BL-005, Flow A leaves LinkedIn variants in `pending` with distribution scheduled, but operators still lack an explicit, visible policy for whether every scheduled variant is expected to publish and when human review is mandatory versus optional supervision. BL-007 scheduled auto-queue must not proceed without that policy; US-015 defines it now so later automation follows the intended Flow A posture (strategy-driven publication with an optional pre-send supervision window), not ad hoc rules invented during BL-007 work.

## Goals

- Define whether all Flow A scheduled LinkedIn variants are expected to publish (strategy-driven default vs operator override).
- Define when human review is **mandatory** (Flow B) versus **optional supervision** (Flow A pre-send window).
- Make the policy operator-visible, understandable, and auditable under `docs/`.
- Communicate failures and blocked states clearly in the policy (what blocks progress vs what remains deferred).
- Preserve existing Flow A lifecycle, publication guards (US-011), and ADR-0001 without duplicating completed work.

## Non-Goals

- US-016 quality/differentiation criteria and audience/objective association mechanics.
- US-017 correction/rejection-before-queue worker, console UI, or folder mechanics (future hooks only).
- BL-007 `auto_queue_pending`, publish-pending n8n workflows, or deploy scripts — leave [bl-007-auto-queue-pending-handoff.md](../../../docs/product/bl-007-auto-queue-pending-handoff.md) untouched as construction WIP.
- LinkedIn API publish, permanent enablement flip, or weakening of `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- New worker HTTP routes or n8n LinkedIn publish workflows unless later justified (not required for US-015).
- BL-008 retry/recovery and BL-009 article preview image work.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-006** | Partial (story 1 only) | Full BL-006 completion outcome remains after US-016 + US-017 |
| **US-015** | Yes | All five acceptance criteria |
| **US-016** | No | Intentionally excluded |
| **US-017** | No | Intentionally excluded; may note future supervision console hooks |
| **BL-007+** | No | Policy informs auto-queue eligibility; gate not implemented here |

**US-015 acceptance criteria addressed:**

1. Define whether all variants may eventually be published → **yes, per distribution strategy**, unless operator cancels or defers.
2. Define when review is mandatory → **Flow B: mandatory before any publish; Flow A: not mandatory** (optional supervision window while `pending`).
3. Outcome visible and understandable to the intended user (operator docs + glossary/status pointers).
4. Failures or blocked states clearly communicated.
5. Existing completed work not duplicated or unintentionally changed.

## What Changes

- Add an operator-facing LinkedIn variant review policy document under `docs/operations/` that states Flow A strategy-driven publication defaults and the optional pre-send supervision window.
- Add a new OpenSpec capability `linkedin-variant-review-process` that normatively requires the policy artifact, its decisions, visibility, and blocked-state language.
- Clarify vocabulary in `docs/GLOSSARY.md` for supervision window vs `publish_state`, and Flow A vs Flow B review obligations.
- After demonstrated ACs only: update CURRENT-STATE and product progress for US-015 (not BL-006 closed; not US-016/US-017).
- Align editorial-canon Flow A vs Flow B wording so Flow A LinkedIn publication follows distribution strategy with optional operator supervision before API send — not a mandatory per-variant approval gate.

## Capabilities

### New Capabilities

- `linkedin-variant-review-process`: Operator-visible policy for Flow A LinkedIn variant publication expectations — strategy-driven publish default (all scheduled variants unless operator overrides), optional supervision window while `pending`, when review is mandatory (Flow B only), blocked/deferred states, and how the policy later informs BL-007 eligibility without implementing that gate.

### Modified Capabilities

- `editorial-canon`: Align Flow A vs Flow B publication-policy wording so Flow A blog/package/schedule remain automatic after validation; Flow A LinkedIn API publish follows distribution strategy with optional pre-send supervision; Flow B requires mandatory human review before any publish. Documentation/canon requirement change only — no new worker endpoints.

## Impact

- **Product:** Advances BL-006 / US-015 only; leaves US-016, US-017, BL-007–BL-009 open.
- **Docs:** New operator policy; GLOSSARY/CURRENT-STATE/progress updates after validation; editorial-canon section alignment.
- **OpenSpec:** New capability under `openspec/specs/` after sync; delta for `editorial-canon`.
- **Worker / n8n / Docker:** No runtime behavior, routes, workflows, or enablement changes in this change.
- **BL-007:** Policy documents that auto-queue targets scheduled `pending` variants not cancelled or deferred by operator; does not merge or formalize `auto_queue_pending` WIP.
- **Preserved:** ADR-0001 (n8n → worker HTTP only); US-011 (Flow A independent of LinkedIn publication enablement); existing `pending`/`queued`/`published` publication state machine.
