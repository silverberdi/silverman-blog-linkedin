## Context

P5 **BL-023 / US-055** asks the business owner to **collect metrics consistently**, **compare themes and variants**, and **identify effective formats** so future editorial decisions can be informed by evidence. US-053 / US-054 already published the metric-family definitions, measurement period (calendar month, America/Bogota), blocked-state vocabulary (including **not applicable — none recorded** vs **zero (measured)**), publication honesty eligibility (**Live on LinkedIn** / **Published on blog**), high-performing criteria, and a durable log template. What is missing is Story 1’s **collection consistency and comparison procedure** — not a BI platform, auto-fetch worker, or US-056 planning feed.

CURRENT-STATE: US-053 and US-054 definitions published; Story accepted / BL-022 close remain operator gates. Editorial backlog (BL-020 / US-049–US-050) implemented locally but **not** Story accepted — leave open. LinkedIn API publication remains independently gated (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`). Blog handoff ≠ site live; package/schedule ≠ LinkedIn API published.

Stakeholders: business owner (primary reader); content operator who collects period metrics and writes comparison / effective-format notes; later implementers of US-056 (planning feed).

Constraints: OpenSpec before code; ADR-0001; ADR-0002; MUST NOT mutate LinkedIn publication enablement; MUST NOT gate Flow A/B on metrics; reuse US-053 / US-054 vocabulary and eligibility; no deploy / Story accepted / BL-022 close / US-053–US-054 Story accepted in this change alone; default docs-only; keep US-056 out.

## Goals / Non-Goals

**Goals:**

- Extend the normative ops definition with US-055 Story 1 procedure: consistent collection, theme/variant comparison, effective-format identification.
- Define what “consistent” means for a measurement period (cadence, required fields, completeness rules, blocked-state honesty when sources are not configured / unavailable / not applicable).
- Define thin operator criteria for comparing themes and variants from **recorded** eligible metrics — no statistical engine; no ranks from schedule/pending/package-complete.
- Align “effective formats” with US-054 high-performing criteria using the same evidence; avoid duplicating Flow A/B or inventing a second ranking section that contradicts §8.
- Optional log-template extension for collection-completeness / comparison notes; CURRENT-STATE / GLOSSARY / product pointers for visibility.
- Capability delta on `business-and-content-metrics`; US-055 Story accepted remains an operator gate after apply.
- Preserve US-053 / US-054 Story accepted and BL-022 close as separate operator gates.

**Non-Goals:**

- US-056 feeding insights into planning; reducing low-performing repetition; strategic automation loops.
- Required worker analytics-fetch routes, GA/LinkedIn Analytics API integration, metrics dashboard, statistical comparison engine.
- Closing BL-020, marking US-053 / US-054 Story accepted, closing BL-022, deploy, enablement changes.
- Gating publish/package/schedule/discover/draft/promote on metrics freshness.
- Inventing new metric families beyond US-053 / US-054.

## Decisions

1. **Docs/contract-first for US-055 Story 1** — Written collection + comparison procedure now; auto-fetch / BI / planning feed remain later or out of scope.
   - Alternative: analytics API worker + dashboard in this change → rejected (user guardrail: thin operator procedure; AC do not require automation).

2. **Extend the existing ops artifact** — Prefer extending `docs/operations/business-and-content-metrics.md` with US-055 sections (and update scope banner) over a disconnected sibling. A sibling is allowed only if clearly linked both ways; default is one SoT file so vocabulary and eligibility stay unified.
   - Alternative: separate `performance-feedback-collection.md` only → acceptable if apply finds the file too large, but prefer single file for reuse of §§2–11.

3. **Modify capability `business-and-content-metrics`** — ADDED requirements for US-055 collection consistency, theme/variant comparison, effective formats, visibility; MODIFY the independence/out-of-scope requirement so US-055 **procedure** is in scope while US-056, BI platforms, and auto-fetch remain out. No MODIFIED deltas on Flow A/B or LinkedIn publication specs.
   - Alternative: new capability `performance-feedback-collection` → rejected for Story 1 (would split procedure from the vocabulary/eligibility contract operators already use; user asked to reuse US-053 / US-054 as source contract).

4. **What “collect consistently” means (normative)** — For each default measurement period (calendar month, America/Bogota), a consistent collection pass is complete when the operator:
   - Labels the period and timezone;
   - Records eligibility context (Published on blog / Live on LinkedIn / documented manual-post exception) from campaign/calendar/Authority Manager as **supporting context only**;
   - For each US-053 family in scope for the period (blog traffic; LinkedIn reach/engagement for eligible items; profile/audience growth), records either a value **or** an explicit blocked state (**not configured** / **unavailable** / **not applicable** / **blocked by publication honesty** / **zero (measured)** as applicable) — never silent blanks that look like measured zeros;
   - For each US-054 outcome family (conversations; opportunities; high-performing topic/format notes), records either values/notes **or** an explicit period summary state (**zero (measured)** / **not applicable — none recorded** / **unavailable** / other per §11);
   - Completes the pass at least once after the period closes (same review cadence as US-053 / US-054), optionally sooner after a notable Live on LinkedIn / Published on blog wave.
   - **Incomplete collection** MUST be labeled (e.g. period marked incomplete / unavailable for unfinished families) — MUST NOT invent filler zeros to “complete” a pass.

5. **Required fields vs optional** — Reuse US-053 / US-054 recording fields already defined. US-055 adds a **collection completeness** record for the period (which families were collected; which blocked states apply; recorded-at / recorded-by). Theme/variant comparison notes and effective-format labels are **required for Story 1 demonstration of those AC** when at least one eligible Published on blog or Live on LinkedIn item exists in the period; when **not applicable** (no eligible published content), the operator records that state instead of inventing comparisons.

6. **Theme and variant comparison (thin, not BI)** — For a period, the operator MAY compare:
   - **Themes / topics** — using recorded US-053 signals (e.g. top posts by views; engagement rate / reactions when impressions known) and optional US-054 outcome attribution among eligible items;
   - **Variants** — among Live on LinkedIn (or documented manual-post exception) variants with recorded post metrics for the same period / campaign context.
   - Comparison output is **operator notes** (relative strength, signal used, eligibility) — MUST NOT require statistical significance, automated A/B, or a ranking engine.
   - MUST NOT invent comparison ranks from `distribution_scheduled`, package-complete, `pending`, `queued`, or unqualified Flow A completion language.
   - When quantitative sources are **not configured** / **unavailable** / **not applicable**, comparison notes MUST carry that state; qualitative notes remain allowed with the state labeled.

7. **Effective formats (align with US-054, do not duplicate)** — “Effective formats” for US-055 SHALL reuse US-054 high-performing topic/format criteria (§8) as the identification method. The US-055 ops extension clarifies the **collection-period practice**: after consistent US-053 / US-054 recording, the operator writes effective-format labels for the period (signal used or blocked state). Do **not** invent a second contradictory criteria table; do **not** duplicate Flow A packaging or Flow B discovery pipelines to “produce” effectiveness.

8. **Sources of truth** — Manual-first from intended sources already named in US-053 / US-054. Supporting context: campaign metadata, calendar, Authority Manager honesty. No required GA/LinkedIn Analytics API.

9. **Blocked / unavailable vocabulary** — Reuse BL-022 §11 unchanged as the source vocabulary. US-055 adds procedural guidance only: incomplete collection ≠ measured zero; comparison/effective-format sections inherit publication-honesty blocks for LinkedIn evidence.

10. **Log template** — Extend `docs/operations/business-and-content-metrics-log-TEMPLATE.md` with a US-055 block: collection completeness checklist; theme/variant comparison notes; effective-format labels (pointing at US-054 criteria). Keep secrets/PII out of git.

11. **Independence from pipelines** — Collection completeness MUST NOT gate Flow A/B. Empty or incomplete metrics MUST NOT change success paths.

12. **No enablement / no LinkedIn auto-publish** — MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

13. **HTTP boundary** — No new worker endpoints required. Optional Authority Manager affordance limited to a **doc link** if visibility still needs it after docs + CURRENT-STATE — not a metrics dashboard.

14. **US-053 / US-054 / BL-022 / BL-020 stay as-is for acceptance** — Do not mark US-053 or US-054 Story accepted; do not close BL-022; do not close BL-020 / US-049–US-050; do not implement US-056.

## Risks / Trade-offs

- [Risk] “Collect consistently” interpreted as required analytics API auto-fetch → Mitigation: define consistent as procedure + completeness rules + log; forbid required auto-fetch in non-goals and independence requirement.
- [Risk] Theme/variant comparison becomes a fake ranking engine → Mitigation: thin operator notes + mandatory signal documentation; forbid inventing ranks from schedule metadata.
- [Risk] Effective formats diverge from US-054 high-performing criteria → Mitigation: explicit reuse of §8; no second criteria table.
- [Risk] Scope creep into US-056 planning feed → Mitigation: non-goals + tasks forbid.
- [Risk] Marking US-053/US-054 accepted or closing BL-022 from this change → Mitigation: tasks forbid; progress updates only Work started for US-055.
- [Risk] Incomplete collection logged as measured zeros → Mitigation: completeness checklist + vocabulary reuse.
- [Risk] Gating Flow A/B on metrics freshness → Mitigation: explicit independence requirement.

## Migration Plan

1. After explicit approval, `/opsx-apply` extends ops definition + log template, updates GLOSSARY/CURRENT-STATE/product pointers, then `/opsx-sync` merges capability delta.
2. No deploy required for docs/contract; optional server doc sync is operator preference.
3. Rollback: revert change commit; no data migration; no runtime flag changes.

## Open Questions

- Whether any Authority Manager help-link is needed after docs + CURRENT-STATE — default no (docs-only).
- Exact log-template wording for the collection-completeness checklist — resolve at apply using Decision 4.
