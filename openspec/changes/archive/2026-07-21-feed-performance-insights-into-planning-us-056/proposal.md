## Why

US-053 / US-054 published metric-family meaning, and US-055 published consistent collection, theme/variant comparison, and effective-format identification — but operators still lack a written **planning-feedback** contract: how period insights feed future editorial planning, how to reduce repetition of low-performing content with documented criteria, and how strategic changes stay under human oversight. Without that, BL-023 Story 2 cannot be accepted as “feed insights into future planning,” and intuition (or unsafe auto-mutation of backlog / Flow B) risks replacing evidence-based decisions.

## What Changes

- Extend the operator-facing metrics ops artifact (`docs/operations/business-and-content-metrics.md` or a clearly linked sibling under `docs/operations/`) with **US-056 Story 2** procedure: feed insights from recorded US-053 / US-054 / US-055 period evidence into future editorial planning; reduce repetition of low-performing content using documented criteria aligned with existing high-performing / effective-format language; keep human oversight over strategic changes.
- Extend capability `business-and-content-metrics` with requirements for that planning-feedback procedure (allowed inputs; where planning notes go; how decisions are recorded; low-performing criteria; fail-closed human oversight — no auto-mutation of strategy, editorial backlog, or Flow B discovery/draft/gap-trigger without explicit operator action).
- Optionally extend the durable operator log template with planning-insight / low-performing / strategic-decision notes only if needed for durable recording.
- Cross-link CURRENT-STATE / GLOSSARY / product pointers so the outcome is visible; reuse US-053 / US-054 / US-055 vocabulary, publication honesty, blocked-state language, and collection completeness as the **source contract** for what insights may be based on — do not redefine collection consistency.
- Leave US-053 / US-054 / US-055 Story accepted, BL-022 close, BL-023 close, BL-020 close, deploy, and LinkedIn publication enablement untouched.

### Goals

- Satisfy **BL-023 / US-056** acceptance criteria as a thin operator planning-feedback procedure + documentation/contract (Story accepted still requires operator review after apply).
- Define how an operator **feeds insights** from recorded period evidence into future editorial planning (where notes go, what inputs are allowed, how planning decisions are recorded).
- Define how to **reduce repetition of low-performing content** using documented criteria aligned with US-054 high-performing / US-055 effective-format language — not ranks from schedule/pending/package-complete — with blocked-state honesty when evidence is incomplete.
- Keep **human oversight** over strategic changes: MUST NOT auto-mutate strategy docs, editorial content backlog, or Flow B discovery seeds / gap-trigger settings without explicit operator action; any automation is out of scope or optional and fail-closed.
- Keep failures/blocked/incomplete insight states consistent with BL-022 vocabulary (including **not applicable — none recorded** vs **zero (measured)**).
- Make the outcome visible and understandable to the business owner / operator.
- Prefer reuse of existing ops definition + log template over inventing a CRM, BI dashboard, or second publication pipeline.
- Keep metrics **out of band** from Flow A / Flow B — MUST NOT gate pipelines on metrics presence, freshness, collection completeness, or planning-insight notes.

### Non-goals

- Re-opening or redefining US-055 collection consistency / theme-variant comparison / effective-format identification (reuse as input only).
- Analytics platform, required GA/LinkedIn Analytics API auto-fetch, metrics dashboard, or statistical recommendation engine.
- Auto-apply planning changes: MUST NOT mutate editorial content backlog, Flow B discovery seeds, gap-trigger settings, or strategy docs without explicit human approval in this change’s default design.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or auto-publishing LinkedIn.
- Gating Flow A / Flow B on metrics presence, freshness, collection completeness, or planning-insight notes.
- Marking **US-053** / **US-054** / **US-055** Story accepted; closing **BL-022** or **BL-023**.
- Closing **BL-020 / US-049–US-050** or marking them Story accepted.
- Deploy, push, or claiming Story accepted by this proposal alone.
- Unrelated refactors or `src/` changes unless a thin docs pointer is truly needed for visibility AC (default: docs-only).

### Acceptance criteria addressed

| US-056 criterion | How this change addresses it |
|---|---|
| Feed insights into future planning | Thin operator procedure: allowed inputs (recorded US-053/US-054/US-055 period evidence); where planning notes go; how decisions are recorded durably |
| Reduce repetition of low-performing content | Documented “low-performing” criteria aligned with high-performing / effective-format language; blocked-state honesty when evidence incomplete; forbid ranks from schedule/pending/package-complete |
| Keep human oversight over strategic changes | Explicit fail-closed rule: no auto-mutation of strategy, backlog, or Flow B without explicit operator action; automation out of scope or optional fail-closed |
| Outcome visible and understandable to intended user | Ops extension + CURRENT-STATE / GLOSSARY / product pointers; plain-language vocabulary |
| Failures or blocked states clearly communicated | Reuse BL-022 vocabulary; incomplete / blocked insight states labeled (not silently treated as actionable ranks) |
| Existing completed work not duplicated or unintentionally changed | Docs/contract-first; no Flow A/B rewrite; US-053/US-054/US-055 Story accepted and BL-022/BL-023 left open |

### Intentionally excluded

- Redefining US-055 collection / comparison / effective-format procedure.
- Required analytics auto-fetch worker, BI dashboard, or auto-planning engine.
- Live deploy, Story accepted for US-053/US-054/US-055/US-056, or BL-022/BL-023 close without operator gate.

## Capabilities

### New Capabilities

- (none — extend the existing BL-022 / BL-023 documentation/contract capability with US-056 Story 2 planning-feedback procedure)

### Modified Capabilities

- `business-and-content-metrics`: Add normative requirements for **BL-023 / US-056 Story 2** — feed insights from recorded period evidence into future editorial planning; reduce repetition of low-performing content with documented criteria; keep human oversight (no auto-mutation of strategy / backlog / Flow B without explicit operator action); planning-insight blocked-state honesty; visibility pointers — without requiring a BI platform, auto-planning engine, Flow A/B gating, US-053/US-054/US-055 Story accepted, BL-022/BL-023 close, or changes to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. Update the prior “US-056 out of scope” independence language so US-056 **planning-feedback procedure** is in scope while analytics platforms, auto-apply planning mutation, and statistical recommendation engines remain out.

## Impact

- **Product:** Advances **BL-023 / US-056** only; leaves US-053 / US-054 / US-055 Story accepted and BL-022 / BL-023 open; does not mark Story accepted by proposal alone; does not close BL-020.
- **Docs:** Extend ops definition (and optional log template) under `docs/operations/`; CURRENT-STATE / GLOSSARY capability-language pointers; light product cross-links as needed.
- **OpenSpec:** Delta on `business-and-content-metrics` under `openspec/specs/` after sync; no requirement deltas that rewrite Flow A/B or LinkedIn publication behavior.
- **Worker / n8n / Docker / cron / enablement / console:** No required runtime behavior changes; optional thin doc link only if needed for visibility AC without inventing a dashboard or auto-planner.
- **Preserved:** ADR-0001 (n8n → HTTP only); ADR-0002 (blog canonical); LinkedIn publication guard; Flow A/B independence from metrics; US-053 / US-054 / US-055 published status; BL-020 implemented-but-open status.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-023 / US-056** | Primary — feed insights into future planning; reduce low-performing repetition; keep human oversight |
| US-055 | Prerequisite collection procedure (published docs); Story accepted remains operator gate — do not close in this change; do not redefine collection consistency |
| US-053 / US-054 | Prerequisite definitions (published docs); Story accepted remain operator gates — do not close in this change |
| BL-022 | Definition backlog; close remains operator gate — do not close in this change |
| BL-023 | Parent backlog; close remains operator gate until US-055 and US-056 Story accepted — do not close in this change |
| BL-020 / US-049–US-050 | Must remain open; optional enrichment context only — do not close |
| ADR-0001 / ADR-0002 | HTTP-only orchestration; blog canonical, LinkedIn is distribution |
