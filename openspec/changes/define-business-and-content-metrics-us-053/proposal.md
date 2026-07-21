## Why

The content program (blog + LinkedIn distribution) now has Flow A/B publication paths and Authority Manager evidence, but BL-022 Story 1 still lacks a written, operator-facing definition of which **business and content metrics** matter — blog traffic, LinkedIn reach/engagement, and profile visits / audience growth. Without that contract, operators cannot measure outcomes consistently, and later collection/feedback stories (US-054, BL-023) risk inventing ad-hoc dashboards or wiring metrics into pipelines.

## What Changes

- Publish an operator-facing **business and content metrics** definition under `docs/operations/` that names the US-053 metric families, definitions, intended sources, review cadence, and blocked/unavailable vocabulary.
- Introduce capability `business-and-content-metrics` as documentation/contract requirements (no analytics platform, no mandatory auto-collection worker, no Flow A/B gating in this change).
- Cross-link from CURRENT-STATE / product docs so the intended business owner can open and understand the metric set; reuse existing campaign/calendar/publication evidence as **supporting context** where useful, without duplicating publication pipelines.
- Leave US-054 outcome metrics, BL-023 collection/feedback loops, BL-020 Story acceptance, deploy, and LinkedIn publication enablement untouched.

### Goals

- Satisfy **BL-022 / US-053** acceptance criteria as a thin metrics definition + documentation/contract (Story accepted still requires operator review after apply).
- Define blog traffic metrics in plain language (what is measured, why it matters, how an operator obtains or records it).
- Define LinkedIn reach and engagement metrics the same way.
- Define how profile visits and audience growth are tracked (definition + operator procedure / source — not necessarily automated ingestion).
- Make the outcome visible and understandable to the business owner / operator.
- Communicate failures, blocked, or unavailable metric states clearly (e.g. analytics not configured, LinkedIn API publication not validated, source missing).
- Prefer reuse of existing evidence (campaign metadata, calendar status, Authority Manager publication honesty) over inventing a second measurement pipeline.
- Keep metrics **out of band** from Flow A / Flow B execution — MUST NOT gate publish/package/schedule/discover/draft/promote on metrics collection.

### Non-goals

- **US-054** — recruiter/executive conversations, job/consulting opportunities, high-performing topics/formats.
- **BL-023 / US-055–US-056** — consistent automated collection, theme/variant comparison, feeding insights into planning.
- Building a large analytics platform, warehouse, BI dashboard product, or third-party GA/LinkedIn Analytics full integration as required runtime.
- New worker routes that auto-fetch external analytics APIs (MAY be proposed later; MUST NOT be required to close US-053 definition).
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, auto-publishing LinkedIn, or treating LinkedIn package/schedule as API-published.
- Closing **BL-020 / US-049–US-050** or marking them Story accepted (remain open pending operator acceptance).
- Closing **BL-022**, marking US-053 Story accepted, or deploying by this proposal/apply alone.
- Gating Flow A or Flow B pipelines on metrics presence or freshness.
- Redesigning Authority Manager chrome beyond an optional thin pointer/doc link if needed for visibility.

### Acceptance criteria addressed

| US-053 criterion | How this change addresses it |
|---|---|
| Define blog traffic metrics | Normative ops definition + capability requirements (named metrics, intent, sources) |
| Define LinkedIn reach and engagement metrics | Same — reach/impressions/engagement family with clear definitions |
| Track profile visits and audience growth | Definition + operator tracking procedure / source of truth (manual-first OK) |
| Outcome visible and understandable to intended user | Ops policy + CURRENT-STATE / product pointers; plain-language vocabulary |
| Failures or blocked states clearly communicated | Explicit unavailable/blocked/not-configured vocabulary distinct from “zero” |
| Existing completed work not duplicated or unintentionally changed | Docs/contract-first; no Flow A/B pipeline rewrite; BL-020 left open |

### Intentionally excluded

- US-054 business-outcome conversation/opportunity/topic-performance metrics.
- Automated periodic collection and editorial feedback loops (BL-023).
- Live deploy, Story accepted, or BL-022 close without operator gate.

## Capabilities

### New Capabilities

- `business-and-content-metrics`: Operator-visible normative definition of US-053 metric families (blog traffic; LinkedIn reach and engagement; profile visits and audience growth), including definitions, intended sources, review cadence, supporting reuse of existing publication evidence, and clear blocked/unavailable communication — without requiring an analytics platform, auto-collection worker, Flow A/B gating, or US-054 outcome metrics.

### Modified Capabilities

- (none — documentation/contract capability; existing Flow A publication, LinkedIn publication, Flow B, and editorial backlog specs unchanged in requirements)

## Impact

- **Product:** Advances **BL-022 / US-053** only; leaves US-054 and BL-022 open; does not mark Story accepted by proposal alone; does not close BL-020.
- **Docs:** New ops definition under `docs/operations/`; CURRENT-STATE capability-language pointer; light product cross-links as needed.
- **OpenSpec:** New capability under `openspec/specs/` after sync; no requirement deltas that rewrite Flow A/B or LinkedIn publication behavior.
- **Worker / n8n / Docker / cron / enablement / console:** No required runtime behavior changes; optional thin doc link in Authority Manager only if needed for visibility AC without inventing a dashboard.
- **Preserved:** ADR-0001 (n8n → HTTP only); ADR-0002 (blog canonical); LinkedIn publication guard; Flow A/B independence from metrics; BL-020 implemented-but-open status.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-022 / US-053** | Primary — define blog traffic, LinkedIn reach/engagement, profile visits / audience growth |
| US-054 | Explicit follow-up — conversations, opportunities, high-performing topics/formats |
| BL-023 / US-055–US-056 | Later — collect consistently and feed insights into planning |
| BL-020 / US-049–US-050 | Must remain open; optional enrichment context only — do not close |
| ADR-0001 / ADR-0002 | HTTP-only orchestration; blog canonical, LinkedIn is distribution |
