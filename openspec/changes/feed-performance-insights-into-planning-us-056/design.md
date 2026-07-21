## Context

P5 **BL-023 / US-056** asks the business owner to **feed insights into future planning**, **reduce repetition of low-performing content**, and **keep human oversight over strategic changes** so editorial decisions are informed by evidence rather than intuition alone. US-053 / US-054 already published metric-family definitions, measurement period (calendar month, America/Bogota), blocked-state vocabulary (including **not applicable — none recorded** vs **zero (measured)**), publication honesty eligibility (**Live on LinkedIn** / **Published on blog**), and high-performing criteria. US-055 published consistent collection, theme/variant comparison, and effective-format identification (§§14–16). What is missing is Story 2’s **planning-feedback procedure** — not a BI platform, auto-planning engine, or worker that mutates editorial backlog / Flow B without human oversight.

CURRENT-STATE: US-053 / US-054 definitions and US-055 collection procedure published; Story accepted / BL-022 close / BL-023 close remain operator gates. Editorial backlog (BL-020 / US-049–US-050) implemented locally but **not** Story accepted — leave open. LinkedIn API publication remains independently gated (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`). Blog handoff ≠ site live; package/schedule ≠ LinkedIn API published.

Stakeholders: business owner (primary reader / strategic decisions); content operator who writes planning-insight notes from period evidence and applies approved editorial choices; later operators validating Story accepted.

Constraints: OpenSpec before code; ADR-0001; ADR-0002; MUST NOT mutate LinkedIn publication enablement; MUST NOT gate Flow A/B on metrics or planning notes; reuse US-053 / US-054 / US-055 vocabulary and eligibility as the source contract for insights — do not redefine collection consistency; no deploy / Story accepted / BL-022 or BL-023 close / US-053–US-055 Story accepted in this change alone; default docs-only; fail-closed human oversight (no auto-mutation of strategy / backlog / Flow B).

## Goals / Non-Goals

**Goals:**

- Extend the normative ops definition with US-056 Story 2 procedure: feed insights into future planning; reduce low-performing repetition; keep human oversight.
- Define allowed inputs (recorded US-053 / US-054 / US-055 period evidence only — not schedule ranks or intuition-as-evidence without labeling).
- Define where planning notes go and how planning decisions are recorded durably (prefer extending the same log template + thin pointers to operator-owned planning surfaces).
- Define documented “low-performing” criteria aligned with US-054 high-performing / US-055 effective-format language, with blocked-state honesty when evidence is incomplete.
- Explicit fail-closed human oversight: MUST NOT auto-mutate strategy docs, editorial content backlog, or Flow B discovery/draft/gap-trigger without explicit operator action.
- Optional log-template extension; CURRENT-STATE / GLOSSARY / product pointers for visibility.
- Capability delta on `business-and-content-metrics`; US-056 Story accepted remains an operator gate after apply.
- Preserve US-053 / US-054 / US-055 Story accepted and BL-022 / BL-023 close as separate operator gates.

**Non-Goals:**

- Redefining US-055 collection consistency / theme-variant comparison / effective-format identification.
- Required worker analytics-fetch routes, GA/LinkedIn Analytics API integration, metrics dashboard, statistical recommendation engine, or auto-planning engine.
- Closing BL-020, marking US-053 / US-054 / US-055 Story accepted, closing BL-022 or BL-023, deploy, enablement changes.
- Gating publish/package/schedule/discover/draft/promote on metrics freshness or planning-insight notes.
- Inventing new metric families beyond US-053 / US-054.

## Decisions

1. **Docs/contract-first for US-056 Story 2** — Written planning-feedback procedure now; auto-planning / BI / recommendation engines remain later or out of scope.
   - Alternative: auto-apply worker that mutates backlog / Flow B from metrics → rejected (user guardrail: human oversight MUST; AC require oversight, not automation).

2. **Extend the existing ops artifact** — Prefer extending `docs/operations/business-and-content-metrics.md` with US-056 sections (and update scope banner / non-goals / preserved behavior) over a disconnected sibling. A sibling is allowed only if clearly linked both ways; default is one SoT file so vocabulary, eligibility, collection, and planning feedback stay unified.
   - Alternative: separate `performance-planning-feedback.md` only → acceptable if apply finds the file too large, but prefer single file for reuse of §§2–16.

3. **Modify capability `business-and-content-metrics`** — ADDED requirements for US-056 planning feed, low-performing reduction, human oversight, visibility; MODIFY the independence/out-of-scope requirement so US-056 **planning-feedback procedure** is in scope while auto-apply mutation, BI platforms, and recommendation engines remain out. No MODIFIED deltas on Flow A/B or LinkedIn publication specs.
   - Alternative: new capability `performance-planning-feedback` → rejected for Story 2 (would split planning feedback from the vocabulary/eligibility/collection contract operators already use; user asked to reuse US-053 / US-054 / US-055 as source contract).

4. **What “feed insights into future planning” means (normative)** — After a US-055 consistent collection pass for a measurement period (or with incomplete-collection / blocked states explicitly labeled), the operator:
   - Reviews recorded US-053 / US-054 values and US-055 comparison / effective-format notes as **allowed inputs**;
   - Writes **planning-insight notes** for the next planning horizon (default: next calendar month, America/Bogota) — topics/formats to prioritize, de-emphasize, or revisit;
   - Records **planning decisions** (what will change in editorial planning) separately from raw metrics — decision ≠ measured metric;
   - Places notes in the durable period log (US-056 block) and MAY copy approved decisions into operator-owned planning surfaces (editorial backlog notes, strategy docs, Flow B seed lists) **only via explicit human edit** — never via automated mutation in this change’s default design.
   - When US-055 collection is **incomplete** / **unavailable** / **not applicable**, planning insights MUST carry that state — MUST NOT invent actionable ranks from missing evidence.

5. **Allowed inputs vs forbidden inputs**
   - **Allowed:** Recorded US-053 families; US-054 conversations/opportunities/high-performing notes; US-055 collection completeness, theme/variant comparison, effective-format labels; eligibility context (**Published on blog** / **Live on LinkedIn** / documented manual-post exception) as supporting context only.
   - **Forbidden as insight ranks:** `distribution_scheduled`, package-complete, `pending`, `queued`, unqualified Flow A completion / `flow_a_complete`, Authority Manager operational metric chips as “performance.”
   - **Intuition:** MAY appear as a labeled qualitative note (“operator judgment”) — MUST NOT be presented as measured US-053 evidence.

6. **Low-performing content (thin, aligned with high-performing language)** — “Low-performing” for US-056 SHALL be the operator-applied inverse/complement of US-054 §8 high-performing / US-055 §16 effective-format criteria among eligible Published on blog / Live on LinkedIn items for the period, using a documented US-053 signal (or blocked state). Typical practice: relative bottom-tier by the same signal used for high-performing / effective-format labels in that period; and/or absence of outcome linkage when peers have it. Criteria MUST be thin and operator-applied — MUST NOT require a statistical engine. When quantitative sources are **not configured** / **unavailable** / **not applicable**, the operator MUST NOT invent low-performing ranks; record the blocked state instead (qualitative caution notes allowed with state labeled). When no eligible published content exists, low-performing reduction notes are **not applicable**.
   - **Reduce repetition:** Planning notes SHOULD name themes/formats/variants labeled low-performing that the operator intends to avoid repeating in the next horizon (or to revise materially), and record the decision. “Reduce repetition” is a **planning decision**, not an automated backlog delete.

7. **Human oversight (fail-closed)** — This change’s default design MUST NOT introduce worker/n8n/cron behavior that mutates:
   - strategy docs;
   - editorial content backlog (BL-020 surfaces);
   - Flow B discovery seeds, gap-trigger settings, draft/promote queues;
   - campaign metadata used as planning state.
   Any future automation that proposes planning changes MUST be out of scope here or optional and **fail-closed** (disabled by default; requires explicit operator approval before any mutation). Recording a planning-insight note in the metrics log is **not** a mutation of backlog or Flow B.

8. **Sources of truth** — Insights based on operator-recorded period evidence (log template + normative procedure). Supporting context: campaign metadata, calendar, Authority Manager honesty for eligibility only. No required GA/LinkedIn Analytics API.

9. **Blocked / unavailable vocabulary** — Reuse BL-022 §11 unchanged as the source vocabulary. US-056 adds procedural guidance only: incomplete / blocked insight inputs ≠ actionable performance ranks; planning decisions under incomplete evidence MUST label the blocked state.

10. **Log template** — Extend `docs/operations/business-and-content-metrics-log-TEMPLATE.md` with a US-056 block: planning-insight notes (inputs cited); low-performing labels (signal or blocked state); planning decisions for next horizon; explicit confirmation that backlog / Flow B / strategy were **not** auto-mutated (human-applied checkbox / note). Keep secrets/PII out of git.

11. **Independence from pipelines** — Planning-insight notes, low-performing labels, and collection completeness MUST NOT gate Flow A/B. Empty or incomplete metrics MUST NOT change success paths.

12. **No enablement / no LinkedIn auto-publish** — MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

13. **HTTP boundary** — No new worker endpoints required. Optional Authority Manager affordance limited to a **doc link** if visibility still needs it after docs + CURRENT-STATE — not a metrics dashboard or planning UI.

14. **US-053 / US-054 / US-055 / BL-022 / BL-023 / BL-020 stay as-is for acceptance** — Do not mark US-053, US-054, or US-055 Story accepted; do not close BL-022 or BL-023; do not close BL-020 / US-049–US-050.

## Risks / Trade-offs

- [Risk] “Feed insights” interpreted as required auto-planning / backlog mutation → Mitigation: define feed as procedure + durable notes + human-applied decisions; forbid auto-mutation in non-goals and independence requirement.
- [Risk] “Low-performing” invents a second ranking engine that contradicts §8 / §16 → Mitigation: explicit inverse/complement of high-performing / effective-format criteria; same signal documentation; no second contradictory table.
- [Risk] Insights based on schedule/pending ranks → Mitigation: forbidden-inputs list; publication honesty reuse.
- [Risk] Incomplete collection treated as actionable low-performing ranks → Mitigation: blocked-state honesty; incomplete ≠ measured ranks.
- [Risk] Scope creep into redefining US-055 collection → Mitigation: non-goals + tasks forbid; US-055 stays prerequisite/input only.
- [Risk] Marking US-053/US-054/US-055 accepted or closing BL-022/BL-023 from this change → Mitigation: tasks forbid; progress updates only Work started for US-056.
- [Risk] Gating Flow A/B on planning-insight notes → Mitigation: explicit independence requirement.

## Migration Plan

1. After explicit approval, `/opsx-apply` extends ops definition + log template, updates GLOSSARY/CURRENT-STATE/product pointers, then `/opsx-sync` merges capability delta.
2. No deploy required for docs/contract; optional server doc sync is operator preference.
3. Rollback: revert change commit; no data migration; no runtime flag changes.

## Open Questions

- Whether any Authority Manager help-link is needed after docs + CURRENT-STATE — default no (docs-only).
- Exact log-template wording for the US-056 planning-decision / human-applied confirmation fields — resolve at apply using Decisions 4–7.
- Whether planning notes MAY optionally point at a specific operator-owned editorial planning surface path — prefer naming the pattern (human-edited backlog / strategy / Flow B seeds) without inventing a new SoT file unless apply needs a thin pointer.
