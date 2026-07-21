## Why

US-053 published the operator-facing contract for traffic, reach/engagement, and audience-growth metrics, but BL-022 Story 2 still lacks a written definition of **business outcome** metrics — recruiter/executive conversations, job/consulting opportunities, and high-performing topics/formats. Without that extension, operators cannot record outcomes consistently, and BL-023 risks inventing ad-hoc “insights” without a shared vocabulary.

## What Changes

- Extend the operator-facing metrics definition (same `docs/operations/business-and-content-metrics.md` or a clearly linked sibling under `docs/operations/`) to cover **US-054** outcome metrics: conversations, opportunities, and high-performing topics/formats.
- Extend capability `business-and-content-metrics` requirements for those outcome families: definitions, intended sources, operator recording procedure, review cadence, and US-054-specific not-applicable / blocked vocabulary consistent with US-053.
- Optionally extend the durable operator log template for conversations / opportunities / topic-format notes.
- Cross-link CURRENT-STATE / GLOSSARY / product pointers so the outcome is visible; reuse US-053 metric families and campaign/calendar/Authority Manager honesty as **supporting context** only.
- Leave US-053 Story accepted, BL-022 close, BL-023 automation, BL-020 Story acceptance, deploy, and LinkedIn publication enablement untouched.

### Goals

- Satisfy **BL-022 / US-054** acceptance criteria as a thin metrics definition + documentation/contract (Story accepted still requires operator review after apply).
- Define how to track recruiter and executive conversations (definition, intended sources, how an operator records them, review cadence).
- Define how to track job and consulting opportunities the same way.
- Define criteria for identifying high-performing topics and formats using US-053 traffic/reach/engagement where available — without inventing a BI platform.
- Keep failures/blocked/unavailable vocabulary consistent with US-053 and add US-054-specific not-applicable cases (e.g. no conversations recorded in period ≠ measured zero outcomes).
- Make the outcome visible and understandable to the business owner / operator.
- Prefer reuse of existing publication honesty + US-053 families over duplicating Flow A/B pipelines.
- Keep metrics **out of band** from Flow A / Flow B — MUST NOT gate pipelines on metrics presence or freshness.

### Non-goals

- **BL-023 / US-055–US-056** — automated collection, theme/variant comparison engines, feeding insights into planning automation.
- Analytics platform, required GA/LinkedIn Analytics API auto-fetch worker routes, or metrics dashboard.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or auto-publishing LinkedIn.
- Gating Flow A / Flow B on metrics presence or freshness.
- Closing **BL-020 / US-049–US-050** or marking them Story accepted.
- Marking **US-053** Story accepted, closing **BL-022**, deploy, or push by this proposal/apply alone.
- Unrelated refactors or `src/` changes unless a thin docs pointer is truly needed for visibility AC (default: docs-only).

### Acceptance criteria addressed

| US-054 criterion | How this change addresses it |
|---|---|
| Track recruiter and executive conversations | Normative ops definition + capability requirements (definition, sources, recording procedure, cadence) |
| Track job and consulting opportunities | Same — opportunity family with clear definitions and recording rules |
| Identify high-performing topics and formats | Criteria using US-053 traffic/reach/engagement where available; operator review notes — not a BI engine |
| Outcome visible and understandable to intended user | Ops extension + CURRENT-STATE / GLOSSARY / product pointers; plain-language vocabulary |
| Failures or blocked states clearly communicated | Reuse US-053 vocabulary + US-054-specific not-applicable cases |
| Existing completed work not duplicated or unintentionally changed | Docs/contract-first; no Flow A/B rewrite; US-053 Story accepted / BL-020 left open |

### Intentionally excluded

- Automated periodic collection and editorial feedback loops (BL-023).
- Theme/variant comparison engines or planning automation feed.
- Live deploy, Story accepted for US-053 or US-054, or BL-022 close without operator gate.

## Capabilities

### New Capabilities

- (none — extend the existing US-053 documentation/contract capability)

### Modified Capabilities

- `business-and-content-metrics`: Add normative requirements for US-054 outcome metrics (recruiter/executive conversations; job/consulting opportunities; high-performing topics and formats), including definitions, intended sources, operator recording procedure, review cadence, blocked/unavailable vocabulary consistent with US-053 plus US-054-specific not-applicable cases, and visibility pointers — without requiring a BI platform, auto-collection worker, Flow A/B gating, US-053 Story accepted, or changes to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

## Impact

- **Product:** Advances **BL-022 / US-054** only; leaves US-053 Story accepted and BL-022 open; does not mark Story accepted by proposal alone; does not close BL-020.
- **Docs:** Extend ops definition (and optional log template) under `docs/operations/`; CURRENT-STATE / GLOSSARY capability-language pointers; light product cross-links as needed.
- **OpenSpec:** Delta on `business-and-content-metrics` under `openspec/specs/` after sync; no requirement deltas that rewrite Flow A/B or LinkedIn publication behavior.
- **Worker / n8n / Docker / cron / enablement / console:** No required runtime behavior changes; optional thin doc link only if needed for visibility AC without inventing a dashboard.
- **Preserved:** ADR-0001 (n8n → HTTP only); ADR-0002 (blog canonical); LinkedIn publication guard; Flow A/B independence from metrics; US-053 definition published status; BL-020 implemented-but-open status.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-022 / US-054** | Primary — track conversations, opportunities, high-performing topics/formats |
| US-053 | Prerequisite definition (published docs); Story accepted remains operator gate — do not close in this change |
| BL-023 / US-055–US-056 | Later — collect consistently and feed insights into planning |
| BL-020 / US-049–US-050 | Must remain open; optional enrichment context only — do not close |
| ADR-0001 / ADR-0002 | HTTP-only orchestration; blog canonical, LinkedIn is distribution |
