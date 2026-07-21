## Context

P5 **BL-022 / US-054** asks the business owner to **track** recruiter/executive conversations, job/consulting opportunities, and high-performing topics/formats so the content program has measurable business outcomes beyond traffic and reach. US-053 already published the traffic/reach/audience-growth contract at `docs/operations/business-and-content-metrics.md` with shared measurement period (calendar month, America/Bogota), blocked-state vocabulary, publication honesty eligibility, and a durable log template. What is missing is Story 2’s outcome layer — not a BI platform or collection automation.

CURRENT-STATE: US-053 definition published; Story accepted / BL-022 close remain operator gates. Editorial backlog (BL-020 / US-049–US-050) implemented locally but **not** Story accepted — leave open. LinkedIn API publication remains independently gated (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`). Blog handoff ≠ site live; package/schedule ≠ LinkedIn API published.

Stakeholders: business owner (primary reader); content operator who records conversations/opportunities and reviews topic/format notes; later implementers of BL-023 (collection / feedback).

Constraints: OpenSpec before code; ADR-0001; ADR-0002; MUST NOT mutate LinkedIn publication enablement; MUST NOT gate Flow A/B on metrics; reuse US-053 vocabulary and eligibility; no deploy / Story accepted / BL-022 close in this change alone; default docs-only.

## Goals / Non-Goals

**Goals:**

- Extend the normative ops definition for US-054 outcome metric families with plain-language definitions, intended sources, recording procedure, and review cadence.
- Define criteria for “high-performing” topics/formats that consume US-053 traffic/reach/engagement where available — operator judgment notes, not a ranking engine.
- Keep blocked / unavailable vocabulary consistent with US-053; add US-054-specific not-applicable cases (e.g. no conversations recorded ≠ measured zero outcomes).
- Optional log-template extension; CURRENT-STATE / GLOSSARY / product pointers for visibility.
- Capability delta on `business-and-content-metrics`; US-054 Story accepted remains an operator gate after apply.
- Preserve US-053 Story accepted as a separate operator gate (do not mark accepted in this change).

**Non-Goals:**

- BL-023 automated collection, theme/variant comparison engines, feeding insights into planning.
- Required worker analytics-fetch routes, GA/LinkedIn Analytics API integration, metrics dashboard.
- Closing BL-020, marking US-053 Story accepted, closing BL-022, deploy, enablement changes.
- Gating publish/package/schedule/discover/draft/promote on metrics freshness.
- Inventing a CRM or ATS as the system of record in this change.

## Decisions

1. **Docs/contract-first for US-054** — Same pattern as US-053: written rules + manual recording now; automated collection is BL-023.
   - Alternative: CRM ingest + worker endpoints in this change → rejected (user guardrail: thin definition; no BI platform).

2. **Extend the existing ops artifact** — Prefer extending `docs/operations/business-and-content-metrics.md` with US-054 sections (and update scope banner) over a disconnected sibling. A sibling is allowed only if clearly linked both ways; default is one SoT file.
   - Alternative: separate `business-outcome-metrics.md` only → acceptable if apply finds the US-053 file too large, but prefer single file for vocabulary reuse.

3. **Modify capability `business-and-content-metrics`** — ADDED requirements for outcome families; MODIFY the independence/out-of-scope requirement so US-054 definition is in scope while BL-023 remains out. No MODIFIED deltas on Flow A/B or LinkedIn publication specs.
   - Alternative: new capability `business-outcome-metrics` → rejected (splits vocabulary and eligibility from US-053; user asked to reuse US-053 contract).

4. **Outcome families (normative names for the ops doc)**

   | Family | Defined items (minimum) | Intent |
   |---|---|---|
   | Recruiter & executive conversations | Count of conversations in period; optional attribution to content/campaign when known; channel (LinkedIn message, email, call, meeting, other) | Did the program start professional dialogue? |
   | Job & consulting opportunities | Count of opportunities in period; type (job / consulting / other); stage (identified / exploring / interview / offer / closed-won / closed-lost / not tracked); optional content attribution | Did dialogue convert toward professional opportunities? |
   | High-performing topics & formats | Operator-identified topic and format notes for the period, using US-053 page views / LinkedIn engagement (when available) as supporting evidence; qualitative note when quantitative sources are unavailable | Which themes/formats appear worth repeating? |

5. **What counts as a “conversation” (definition)** — A recruiter or executive conversation is a **two-way professional exchange** (message thread, email thread, call, or meeting) initiated or meaningfully advanced in the measurement period and related to Silverio’s professional positioning (roles, consulting, technical leadership). One-way likes/reactions alone are **not** conversations (those remain US-053 engagement). Operator judgment applies; record enough identity to review later without committing secrets or third-party PII into git.

6. **What counts as an “opportunity”** — A job or consulting opportunity is a **concrete professional prospect** the business owner is tracking (role/requisition, consulting brief, warm intro toward a scoped engagement). Vague “someone might hire me someday” without a recordable prospect is **not** an opportunity. Stages are operator labels for review, not a CRM workflow engine.

7. **High-performing criteria (thin, not BI)** — For a period, a topic or format MAY be labeled high-performing when **at least one** of:
   - Relative US-053 strength: among eligible Published on blog / Live on LinkedIn items, it is in the **top tier by the operator’s chosen US-053 signal** for that period (e.g. top posts by views; top posts by engagement rate or reactions when impressions known) — document which signal was used;
   - Outcome linkage: one or more recorded conversations or opportunities in the period are **attributed** (operator judgment) to that topic/format;
   - Qualitative note when US-053 sources are **not configured / unavailable**: operator may still note a topic/format as noteworthy with explicit state that quantitative ranking was **not applicable** or **unavailable** — MUST NOT invent numeric ranks from schedule metadata.
   - MUST NOT require a comparison engine, statistical significance, or automated variant A/B.

8. **Sources of truth (manual-first)** — Intended sources without requiring integrations:
   - **Conversations / opportunities:** Operator memory + LinkedIn inbox / email / calendar notes / personal tracker; record into the durable metrics log (or private spreadsheet). No required CRM.
   - **High-performing topics/formats:** US-053 blog traffic and LinkedIn reach/engagement rows for the same period (when available) + conversation/opportunity attribution notes + eligibility context from campaign/calendar/Authority Manager.
   - **Supporting context (reuse, not substitute):** publication honesty answers eligibility for quantitative content signals; it does not invent conversations or opportunities.

9. **Measurement period reuse** — Same defaults as US-053: calendar month, America/Bogota operator dates; optional per-campaign notes. Outcome metrics use the same period label in the log.

10. **Blocked / unavailable vocabulary** — Reuse US-053 classes; add US-054-specific guidance:
    - **Not configured** — rare for conversations/opportunities (no external analytics product required); may apply if a future private tracker is planned but not adopted.
    - **Unavailable** — source temporarily inaccessible (e.g. cannot access inbox archive for the period).
    - **Not applicable** — no conversations (or no opportunities) **recorded** in the period because none occurred **or** the operator did not operate an outcome log that period — MUST NOT be written as measured **zero outcomes** implying “we measured and got zero” when tracking simply was not done. Prefer explicit: **not applicable — none recorded** vs **zero (measured)** when the operator affirmatively reviewed sources and found none.
    - **Zero (measured)** — operator reviewed intended sources for the period and affirmatively found no qualifying conversations/opportunities.
    - **Blocked by publication honesty** — still applies when using US-053 LinkedIn post metrics as evidence for high-performing labels; scheduled/pending MUST NOT be ranked as high-performing reach.
    - High-performing section when US-053 signals missing: mark quantitative ranking **unavailable** / **not configured** / **not applicable** as appropriate; qualitative notes remain allowed with that state labeled.

11. **Tracking procedure** — Extend US-053 procedure: after eligibility + US-053 values, record conversations and opportunities for the period; then write topic/format high-performing notes using those signals. Review cadence: at least once per calendar month after the period closes (same as US-053), optionally sooner after a notable Live on LinkedIn / Published on blog wave or a notable conversation.

12. **Log template** — Extend `docs/operations/business-and-content-metrics-log-TEMPLATE.md` with sections for conversations, opportunities, and topic/format notes. Keep secrets/PII out of git.

13. **Independence from pipelines** — Outcome metrics MUST NOT gate Flow A/B. Empty outcome log MUST NOT change success paths.

14. **No enablement / no LinkedIn auto-publish** — MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

15. **HTTP boundary** — No new worker endpoints required. Optional Authority Manager affordance limited to a **doc link** if visibility still needs it after docs + CURRENT-STATE — not a metrics dashboard.

16. **US-053 / BL-020 stay as-is for acceptance** — Do not mark US-053 Story accepted; do not close BL-022; do not close BL-020 / US-049–US-050.

## Risks / Trade-offs

- [Risk] “Track” AC interpreted as CRM automation → Mitigation: define track as definition + recording procedure + log template; BL-023 owns collection consistency automation.
- [Risk] Operators confuse LinkedIn reactions with conversations → Mitigation: explicit definition that one-way engagement is US-053, two-way exchange is US-054.
- [Risk] “No conversations recorded” logged as measured zero → Mitigation: vocabulary table distinguishing not applicable / none recorded vs zero (measured).
- [Risk] High-performing becomes a fake ranking engine → Mitigation: thin criteria + mandatory signal documentation; forbid inventing ranks from schedule metadata.
- [Risk] Scope creep into BL-023 comparison/planning feed → Mitigation: non-goals + tasks forbid.
- [Risk] Marking US-053 accepted or closing BL-022 from this change → Mitigation: tasks forbid; progress updates only Work started for US-054.
- [Risk] Gating Flow A/B on outcome metrics → Mitigation: explicit independence requirement.

## Migration Plan

1. After explicit approval, `/opsx-apply` extends ops definition + log template, updates GLOSSARY/CURRENT-STATE/product pointers, then `/opsx-sync` merges capability delta.
2. No deploy required for docs/contract; optional server doc sync is operator preference.
3. Rollback: revert change commit; no data migration; no runtime flag changes.

## Open Questions

- Whether any Authority Manager help-link is needed after docs + CURRENT-STATE — default no (docs-only).
- Exact wording for “none recorded” vs “zero measured” in the log template — resolve at apply using the vocabulary decided above.
