## Why

US-053 and US-054 published the shared meaning of BL-022 metric families, blocked-state vocabulary, measurement period, and high-performing criteria — but operators still lack a written **collection consistency** contract: cadence, completeness rules, and how to compare themes/variants and identify effective formats from recorded evidence without inventing ranks from schedule metadata. Without that, BL-023 Story 1 cannot be accepted as “collect metrics consistently,” and US-056 risks feeding ad-hoc intuition into planning.

## What Changes

- Extend the operator-facing metrics ops artifact (`docs/operations/business-and-content-metrics.md` or a clearly linked sibling under `docs/operations/`) with **US-055 Story 1** procedure: consistent collection for each measurement period; thin theme/variant comparison; effective-format identification aligned with US-054 high-performing criteria.
- Extend capability `business-and-content-metrics` with requirements for that procedure (what “consistent” means when sources are not configured / unavailable / not applicable; completeness rules; comparison without a statistical engine; format identification without duplicating Flow A/B).
- Optionally extend the durable operator log template with collection-consistency notes (period completeness, comparison notes, effective-format labels) only if needed for durable recording.
- Cross-link CURRENT-STATE / GLOSSARY / product pointers so the outcome is visible; reuse US-053 / US-054 families, publication honesty, and campaign/calendar/Authority Manager as **supporting context** only.
- Leave US-053 / US-054 Story accepted, BL-022 close, US-056 planning feed, BL-020 close, deploy, and LinkedIn publication enablement untouched.

### Goals

- Satisfy **BL-023 / US-055** acceptance criteria as a thin operator procedure + documentation/contract (Story accepted still requires operator review after apply).
- Define how an operator **collects US-053 / US-054 metrics consistently** per measurement period (cadence, required fields, completeness rules, blocked-state honesty).
- Define how to **compare themes and variants** using recorded metrics (thin operator criteria; no invented ranks from schedule/pending/package-complete).
- Define how to **identify effective formats** from the same evidence, aligned with US-054 high-performing criteria — not a second ranking engine.
- Keep failures/blocked/unavailable vocabulary consistent with BL-022 (including **not applicable — none recorded** vs **zero (measured)**).
- Make the outcome visible and understandable to the business owner / operator.
- Prefer reuse of existing publication honesty + metric families over duplicating Flow A/B pipelines or inventing a BI platform.
- Keep metrics **out of band** from Flow A / Flow B — MUST NOT gate pipelines on metrics presence or freshness.

### Non-goals

- **US-056** — feeding insights into future planning; reducing low-performing repetition; strategic automation loops (Story 2).
- Analytics platform, required GA/LinkedIn Analytics API auto-fetch worker routes, metrics dashboard, or statistical comparison engine.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or auto-publishing LinkedIn.
- Gating Flow A / Flow B on metrics presence or freshness.
- Closing **BL-022** or marking **US-053** / **US-054** Story accepted.
- Closing **BL-020 / US-049–US-050** or marking them Story accepted.
- Deploy, push, or claiming Story accepted by this proposal alone.
- Unrelated refactors or `src/` changes unless a thin docs pointer is truly needed for visibility AC (default: docs-only).

### Acceptance criteria addressed

| US-055 criterion | How this change addresses it |
|---|---|
| Collect metrics consistently | Normative collection procedure: cadence, required fields, completeness rules, blocked-state honesty when sources are not configured / unavailable / not applicable |
| Compare themes and variants | Thin operator comparison criteria over recorded eligible metrics — no BI/statistical engine; forbid ranks from schedule/pending/package-complete |
| Identify effective formats | Align with US-054 high-performing criteria using the same evidence; document which signal was used |
| Outcome visible and understandable to intended user | Ops extension + CURRENT-STATE / GLOSSARY / product pointers; plain-language vocabulary |
| Failures or blocked states clearly communicated | Reuse BL-022 vocabulary; collection incompleteness labeled (not silently written as measured zero) |
| Existing completed work not duplicated or unintentionally changed | Docs/contract-first; no Flow A/B rewrite; US-053/US-054 Story accepted and BL-022 left open |

### Intentionally excluded

- Feeding insights into planning / low-performing repetition reduction (US-056).
- Required analytics auto-fetch worker or metrics dashboard.
- Live deploy, Story accepted for US-053/US-054/US-055, or BL-022/BL-023 close without operator gate.

## Capabilities

### New Capabilities

- (none — extend the existing BL-022 documentation/contract capability with US-055 Story 1 procedure)

### Modified Capabilities

- `business-and-content-metrics`: Add normative requirements for **BL-023 / US-055 Story 1** — consistent collection procedure over US-053 / US-054 families; thin theme/variant comparison; effective-format identification aligned with US-054 high-performing criteria; collection completeness / blocked-state honesty; visibility pointers — without requiring a BI platform, auto-fetch worker, Flow A/B gating, US-056 planning feed, US-053/US-054 Story accepted, BL-022 close, or changes to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. Update the prior “BL-023 out of scope” independence language so US-055 **procedure** is in scope while US-056 and analytics platforms remain out.

## Impact

- **Product:** Advances **BL-023 / US-055** only; leaves US-053 / US-054 Story accepted and BL-022 open; does not mark Story accepted by proposal alone; does not close BL-020; does not start US-056.
- **Docs:** Extend ops definition (and optional log template) under `docs/operations/`; CURRENT-STATE / GLOSSARY capability-language pointers; light product cross-links as needed.
- **OpenSpec:** Delta on `business-and-content-metrics` under `openspec/specs/` after sync; no requirement deltas that rewrite Flow A/B or LinkedIn publication behavior.
- **Worker / n8n / Docker / cron / enablement / console:** No required runtime behavior changes; optional thin doc link only if needed for visibility AC without inventing a dashboard.
- **Preserved:** ADR-0001 (n8n → HTTP only); ADR-0002 (blog canonical); LinkedIn publication guard; Flow A/B independence from metrics; US-053 / US-054 definition published status; BL-020 implemented-but-open status.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-023 / US-055** | Primary — collect metrics consistently; compare themes/variants; identify effective formats |
| US-053 / US-054 | Prerequisite definitions (published docs); Story accepted remain operator gates — do not close in this change |
| BL-022 | Definition backlog; close remains operator gate — do not close in this change |
| US-056 | Later — feed insights into planning; reduce low-performing repetition |
| BL-020 / US-049–US-050 | Must remain open; optional enrichment context only — do not close |
| ADR-0001 / ADR-0002 | HTTP-only orchestration; blog canonical, LinkedIn is distribution |
