## Context

US-020 / BL-007 already enforce per-campaign LinkedIn publish-time cadence (minimum 72 hours between successful `published` variants with evidence) and report `linkedin_publish_blocked_cadence` (plus related auto-queue cadence skip). US-040K density (max 2 publications per operator-local day) and BL-019 gap trigger coexist as interim controls. Operator decisions (2026-07-20) set BL-021 apply order US-051 → US-087 → US-088 → US-089 and define cadence conflict as that same publish-time cadence gate — not density-full alone, not OAuth, not enablement-off, and not sequence.

This change is **documentation/policy only**: write the shared meaning so calendar, scheduler, and console stories share one definition. No HTTP routes, worker cadence math, cron, or console UI.

Stakeholders: editorial manager / content operator; implementers of US-087–US-089.

Constraints: ADR-0001; blog canonical (ADR-0002); US-020 / BL-007 stay closed and authoritative at send time; no application code in this change.

## Goals / Non-Goals

**Goals:**

- Normative ops policy that ratifies US-020 72h same-campaign spacing and cross-campaign independence.
- Reaffirm LinkedIn frequency planning ≈ fill toward ~2/local day via US-040K (not superseded).
- Reaffirm blog frequency at strategy level (no blog cadence automation).
- Ratify US-040K density and BL-019 gap as interim coexisting controls (density ≠ cadence; gap does not bypass cadence).
- Define “cadence conflict” for US-087/US-088/US-089 consumers.
- Capability spec with documentation contracts later runtime changes MUST not contradict.
- CURRENT-STATE pointer when capability language is updated.

**Non-Goals:**

- US-087 warning UI, US-088 shift-forward, US-089 replan.
- Full US-052 windows/rescheduling policy.
- Any change to worker publish/auto-queue cadence evaluation, env defaults, n8n, cron, OAuth, or enablement.
- Sequence-conflict UX (document only that sequence is distinct).

## Decisions

1. **Docs-only first story** — US-051 is a definition story; shipping console/scheduler mechanics in the same change would mix US-087–US-089 and risk a second cadence engine.
   - Alternative considered: mega-change for all of BL-021 → rejected (operator apply order and one-coherent-capability rule).

2. **Single new capability `linkedin-cadence-spacing-policy`** — holds ratification, frequency assumptions, coexistence, and cadence-conflict definition as documentation contracts (scenarios verify doc presence and normative statements, not HTTP).
   - Alternative: MODIFIED delta on `linkedin-publication-integration` → rejected; US-020 requirements are already normative and must not be rewritten for a docs ratification.

3. **Canonical ops doc** — `docs/operations/linkedin-cadence-spacing-policy.md` as the operator-facing normative policy; cross-link from `docs/deployment/linkedin-publication-prerequisites.md` (US-020 section) and CURRENT-STATE; light GLOSSARY entry for “cadence conflict” if helpful.
   - Alternative: only extend prerequisites → too thin for US-051 “calendar, scheduler, and console share one cadence meaning” and frequency/coexistence ACs.
   - Alternative: invent a new 72h constant in env → forbidden; worker remains source of enforcement math.

4. **Cadence conflict evaluation viewpoint** — For later stories, a slot is cadence-conflicted when a real publish-due / auto-queue path would refuse or skip **for cadence** if that variant were due at `scheduled_at_utc` (or the proposed slot), i.e. same meaning as `linkedin_publish_blocked_cadence` / related cadence skip — evaluated against same-campaign successful `published` evidence timing, not against density-full, OAuth missing, enablement-off, or sequence alone.
   - Note for implementers (US-087+): this change does **not** require a new worker evaluator; later stories may add read-only projection HTTP if needed, but MUST reuse the same rule semantics as US-020.

5. **No supersession of density or gap** — Explicitly ratify coexistence; do not claim BL-021 Story 1 supersedes US-040K or BL-019.
   - Editorial schedule-intent stagger (≥3 days in editorial canon) remains schedule planning guidance; publish-time cadence remains authoritative at send and is what “cadence conflict” means.

6. **Blog frequency** — Strategy-level: blogs are paced to support LinkedIn filling (Flow A packages + Flow B weekly gap fills ≤ `max_drafts_per_weekly_run`, default 2) rather than a daily automated blog cadence; this story does not automate blog cadence.

7. **No new endpoints** — Docs-only; ADR-0001 unchanged. Later BL-021 stories that need HTTP MUST open their own approved changes.

## Risks / Trade-offs

- [Risk] Operators confuse density-full with cadence conflict → Mitigation: policy table contrasting controls and blocked-reason vocabulary.
- [Risk] Later stories invent a second 72h constant → Mitigation: capability MUST require citing US-020 / this policy; tasks forbid worker cadence edits in this change.
- [Risk] Schedule-intent “≥3 days” language in editorial canon is mistaken for publish-time cadence → Mitigation: policy explicitly separates schedule planning stagger from publish-time `published_at` + 72h guard.
- [Risk] Proposal alone treated as Story accepted → Mitigation: progress checklist Work started only after docs exist; Story accepted unchecked pending operator review; proposal/tasks forbid closing BL-021.
- [Risk] US-052 windows left undefined → Accepted trade-off; full windows belong to US-052; this story may note “preferred windows deferred to US-052” without implementing them.

## Migration Plan

1. Apply doc + capability artifacts on Mac branch after explicit approval + `/opsx-apply`.
2. No deploy required for capability; optional doc sync on server is operator preference.
3. Rollback: revert change commit; no data migration; no runtime flag changes.

## Open Questions

- None for this docs slice. Exact console warning affordance (US-087) and shift-forward search bounds (US-088/US-052) deferred to those stories.
