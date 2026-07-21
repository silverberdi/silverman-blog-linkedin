## Context

P5 **BL-022 / US-053** asks the business owner to **define** measurable blog traffic, LinkedIn reach/engagement, and profile visits / audience growth so the content program has clear outcomes. Flow A/B publication, Authority Manager honesty labels, campaign metadata, and calendar evidence already exist; what is missing is a written metric contract — not another pipeline.

CURRENT-STATE: editorial backlog (BL-020 / US-049–US-050) is implemented locally but **not** Story accepted — leave open. LinkedIn API publication remains independently gated (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`). Blog handoff ≠ site live; package/schedule ≠ LinkedIn API published. No existing `docs/operations/*metrics*` artifact.

Stakeholders: business owner (primary reader); content operator who records or reviews metrics; later implementers of US-054 (outcome tracking) and BL-023 (collection / feedback).

Constraints: OpenSpec before code; ADR-0001 (n8n → HTTP only); ADR-0002 (blog canonical); MUST NOT mutate LinkedIn publication enablement; MUST NOT gate Flow A/B on metrics; prefer thin definition + docs over inventing an analytics platform; no deploy / Story accepted / BL-022 close in this change alone.

## Goals / Non-Goals

**Goals:**

- Normative ops definition naming US-053 metric families with plain-language definitions, intended sources, and review cadence.
- Clear blocked / unavailable / not-configured vocabulary distinct from numeric zero.
- Explicit reuse of existing publication evidence as **context** (what shipped when) without duplicating Flow A/B pipelines.
- Capability contracts + CURRENT-STATE / product pointers so the outcome is operator-visible.
- US-053 Story accepted remains an operator gate after apply.

**Non-Goals:**

- US-054 conversations, opportunities, topic/format performance.
- BL-023 automated collection and editorial feedback loops.
- Required worker routes that call GitHub Pages analytics, Google Analytics, or LinkedIn Analytics APIs.
- Analytics warehouse, BI product, or Authority Manager metrics dashboard as required deliverable.
- Closing BL-020 or BL-022; deploy; enablement changes.
- Gating publish/package/schedule/discover/draft/promote on metrics freshness.

## Decisions

1. **Docs/contract-first for US-053** — Match US-051 / US-052 / US-074 pattern: written rules now; automated collection is BL-023 (or a later approved change). Manual recording from external UIs is an acceptable first tracking method.
   - Alternative: build Postgres store + HTTP ingest + console charts in this change → rejected (user guardrail: thin definition first; do not invent large analytics platforms).

2. **Canonical ops artifact** — `docs/operations/business-and-content-metrics.md` as the operator-facing SoT for US-053 definitions. CURRENT-STATE gets a short capability pointer after apply (not Story accepted).
   - Alternative: only update user-stories checkboxes → insufficient for “visible and understandable” and for later BL-023 consumers.

3. **Single new capability `business-and-content-metrics`** — Documentation/contract requirements with scenarios that verify policy presence and normative statements (not HTTP). No MODIFIED deltas on Flow A/B or LinkedIn publication specs.
   - Alternative: bolt metrics requirements onto `linkedin-variant-supervision-console` → conflates operational triage chips with business outcomes; rejected.

4. **Metric families (normative names for the ops doc)** — Keep a small, memorable set:

   | Family | Defined metrics (minimum) | Intent |
   |---|---|---|
   | Blog traffic | Site page views (period); unique visitors if available; top posts by views; referral / landing context if available | Did published blog content attract attention? |
   | LinkedIn reach & engagement | Impressions (or reach); reactions; comments; shares/reposts; engagement rate = engagements ÷ impressions (when both known) | Did distribution assets get seen and interacted with? |
   | Profile visits & audience growth | Profile views (period); follower count at period end; net follower change vs prior period | Is audience finding the profile and growing? |

   Ops doc MUST state measurement period (recommend default **calendar month** and optional **per-campaign / per-post window** after Live on LinkedIn / Published on blog) and timezone note (**America/Bogota** for operator-facing dates, consistent with publishing windows).

5. **Sources of truth (manual-first)** — Document intended sources without requiring integrations:
   - **Blog:** GitHub Pages / hosting analytics, or a configured web analytics product if the operator installs one later; until configured, status is **not configured / unavailable**, not zero.
   - **LinkedIn post reach/engagement:** LinkedIn native post analytics for posts that are **Live on LinkedIn** (API-published or manually posted — honesty labels still apply; do not treat `distribution_scheduled` as published).
   - **Profile / followers:** LinkedIn profile analytics / follower count UI.
   - **Supporting context (reuse, not substitute):** campaign metadata, calendar, Authority Manager publication status — answer “what was eligible to measure,” not “how many impressions.”

6. **Tracking procedure** — Ops doc MUST describe a lightweight operator procedure: pick period → record values into a durable operator log (path TBD in apply; prefer a simple markdown or spreadsheet under `docs/operations/` or `metadata/` **only if** that does not invent a second system of record that gates pipelines). Prefer documenting “operator-owned log” location in the ops policy without requiring worker schema in this change.
   - Alternative: Postgres metrics table in this change → deferred unless apply reveals a hard need; default is docs + optional operator log template.

7. **Blocked / unavailable vocabulary** — Distinguish at least:
   - **Not configured** — analytics product / access not set up.
   - **Unavailable** — source temporarily inaccessible or LinkedIn analytics lag.
   - **Not applicable** — no Live on LinkedIn / no Published on blog content in the period (do not invent zeros that imply measured nothing when nothing was eligible).
   - **Zero (measured)** — source returned an actual zero.
   - **Blocked by publication honesty** — package/schedule/pending must not be counted as LinkedIn reach.

8. **Independence from pipelines** — Metrics definition and any optional log MUST NOT be imported by Flow A publish/package/schedule or Flow B discover/draft/gap-trigger/promote as a prerequisite. Empty or missing metrics MUST NOT change those success paths.

9. **No enablement / no LinkedIn auto-publish** — This change MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or add publish-due behavior.

10. **HTTP boundary** — No new worker endpoints required. If a later change adds authenticated read/write of recorded metrics, it MUST be n8n → worker HTTP (ADR-0001), not Execute Command. Optional Authority Manager affordance in this change is limited to a **doc link / help pointer** if needed for visibility — not a metrics dashboard.

11. **BL-020 stays open** — Editorial backlog remains optional enrichment; do not close US-049/US-050 or BL-020 in progress checklist via this change.

## Risks / Trade-offs

- [Risk] Manual-first feels incomplete vs “track” AC → Mitigation: define track as definition + operator procedure + durable log template; automation owned by BL-023.
- [Risk] Operators treat Authority Manager operational chips as business metrics → Mitigation: ops doc explicitly separates operational triage vs business/content metrics.
- [Risk] Counting scheduled/pending LinkedIn as reach → Mitigation: honesty vocabulary; only Live on LinkedIn (or explicitly manual-posted) eligible for LinkedIn post metrics.
- [Risk] Scope creep into GA/LinkedIn API integration → Mitigation: non-goals + tasks forbid required auto-fetch; later OpenSpec change.
- [Risk] Closing BL-020 or marking Story accepted from proposal → Mitigation: tasks forbid; progress updates only after demonstrated docs + operator review.
- [Risk] Gating Flow A/B on metrics → Mitigation: explicit independence requirement in capability + design.

## Migration Plan

1. After explicit approval, `/opsx-apply` writes ops definition, glossary/CURRENT-STATE pointers, capability sync later via `/opsx-sync`.
2. No deploy required for docs/contract; optional server doc sync is operator preference.
3. Rollback: revert change commit; no data migration; no runtime flag changes.

## Open Questions

- Exact durable operator-log path (markdown template vs spreadsheet vs deferred store) — resolve at apply with smallest artifact that satisfies “track”; default preference: markdown template under `docs/operations/` (e.g. metrics log template) without worker DB.
- Whether Authority Manager gets a help-link in this change — only if visibility AC needs it after ops doc + CURRENT-STATE; otherwise docs pointers suffice.
