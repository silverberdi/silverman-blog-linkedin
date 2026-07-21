## ADDED Requirements

### Requirement: Insights from recorded metrics feed future editorial planning

Normative docs SHALL define an operator **planning-feedback** procedure for **BL-023 / US-056** that feeds insights from **recorded** **US-053** / **US-054** / **US-055** period evidence into future editorial planning. The procedure MUST state: allowed inputs (recorded metric families, US-055 collection completeness / theme-variant comparison / effective-format notes, eligibility context as supporting only); where planning-insight notes are recorded (durable period log extension and/or clearly named operator-owned planning surfaces); how planning decisions for the next planning horizon are recorded separately from raw metrics; and default horizon alignment with the BL-022 measurement period (**calendar month**, **America/Bogota** operator dates). Insights MUST NOT be invented from `distribution_scheduled`, package-complete, `pending`, `queued`, unqualified Flow A completion / `flow_a_complete`, or Authority Manager operational metric chips. When US-055 collection is incomplete, unavailable, or not applicable, planning-insight notes MUST carry that blocked state — MUST NOT invent actionable ranks from missing evidence. The procedure MUST NOT redefine US-055 collection consistency / theme-variant comparison / effective-format identification (reuse as input only).

#### Scenario: Planning-feedback procedure is documented

- **WHEN** an operator reads the US-056 planning-feedback section
- **THEN** allowed inputs, where notes go, and how planning decisions are recorded are stated
- **AND** US-053 / US-054 / US-055 recorded evidence is named as the insight source (US-055 not redefined)
- **AND** inventing insight ranks from schedule/pending/package-complete metadata is forbidden
- **AND** incomplete / unavailable / not applicable collection states must be labeled on insight notes
- **AND** a required BI dashboard, recommendation engine, or auto-planning worker is not required by this capability

### Requirement: Low-performing content repetition is reduced by documented criteria

Normative docs SHALL define documented criteria for labeling **low-performing** topics, formats, or variants for a measurement period as the operator-applied inverse/complement of **US-054 high-performing** / **US-055 effective-format** criteria among eligible **Published on blog** / **Live on LinkedIn** (or documented manual-post exception) items, using a documented US-053 signal (or blocked state). The procedure MUST state how the operator records an intent to **reduce repetition** of labeled low-performing content in the next planning horizon (planning decision notes — not automated backlog deletion). Criteria MUST be thin and operator-applied — MUST NOT require a statistical engine or a second contradictory ranking table. When quantitative sources are not configured, unavailable, or not applicable, the operator MUST NOT invent low-performing ranks; record the blocked state (qualitative caution notes allowed with the state labeled). When no eligible published content exists in the period, low-performing reduction notes are **not applicable**. `distribution_scheduled`, package-complete, `pending`, `queued`, or unqualified Flow A completion language MUST NOT be used to invent low-performing ranks.

#### Scenario: Low-performing criteria align with high-performing language without schedule ranks

- **WHEN** an operator reads the US-056 low-performing / reduce-repetition section
- **THEN** criteria are stated as aligned with US-054 high-performing / US-055 effective-format language
- **AND** the signal used or blocked state must be documented
- **AND** inventing ranks from schedule/pending/package-complete metadata is forbidden
- **AND** a statistical recommendation engine is not required
- **AND** not applicable / unavailable states are named when evidence is missing

### Requirement: Human oversight is required over strategic planning changes

Normative docs SHALL require **human oversight** for strategic changes arising from performance insights: this capability’s default design MUST NOT auto-mutate strategy docs, editorial content backlog, Flow B discovery seeds, gap-trigger settings, or draft/promote queues without **explicit operator action**. Recording planning-insight or low-performing notes in the metrics log MUST NOT itself mutate those surfaces. Any optional future automation that proposes planning changes MUST be out of scope for this change or fail-closed (disabled by default; requires explicit operator approval before mutation). The docs MUST state that applying approved planning decisions to backlog / strategy / Flow B is a **human-edited** step.

#### Scenario: Strategic changes require explicit operator action

- **WHEN** an operator reads the US-056 human-oversight section
- **THEN** auto-mutation of strategy, editorial backlog, and Flow B discovery/draft/gap-trigger without explicit operator action is forbidden
- **AND** metrics-log notes are distinguished from backlog / Flow B mutations
- **AND** optional automation, if mentioned, is fail-closed / out of scope for this change’s default design

### Requirement: US-056 planning-insight failures and incompleteness stay consistent with BL-022 vocabulary

Normative docs SHALL reuse the BL-022 blocked/unavailable vocabulary for US-056 planning-insight, low-performing, and planning-decision notes, and SHALL document that **incomplete collection** or blocked US-053 / US-054 / US-055 inputs MUST NOT be silently treated as measured low- or high-performing ranks. Prefer distinguishing incomplete / **not applicable — none recorded** / **unavailable** / **not configured** from **zero (measured)** after affirmative review. Publication-honesty blocks continue to apply when LinkedIn post metrics are used as planning-insight evidence.

#### Scenario: Incomplete insight inputs are distinct from measured ranks

- **WHEN** an operator lacks complete US-055 period evidence for planning
- **THEN** the docs require an incomplete / unavailable / none-recorded / not-applicable style label on insight notes as applicable
- **AND** numeric zero or blank evidence MUST NOT be treated as an invented low-performing rank
- **AND** blocked-by-publication-honesty remains named for ineligible LinkedIn evidence

### Requirement: US-056 planning-feedback procedure is operator-visible without claiming Story accepted

The system documentation SHALL make the US-056 planning-feedback / low-performing reduction / human-oversight procedure visible via the extended normative ops definition (same `docs/operations/business-and-content-metrics.md` or a clearly linked sibling under `docs/operations/`), CURRENT-STATE and/or GLOSSARY pointers, and light product backlog/user-story pointers as needed. An optional durable log template extension for planning-insight notes, low-performing labels, planning decisions, and human-applied confirmation MAY be included. The docs MUST identify BL-023 / US-056 as the product story satisfied as procedure/policy, MUST state that Story accepted and BL-023 closure require operator review beyond this documentation change, MUST NOT mark US-053, US-054, or US-055 Story accepted solely from this change, MUST NOT close BL-022 or BL-023 solely from this change, and MUST NOT claim to close BL-020 / US-049–US-050.

#### Scenario: US-056 procedure is discoverable without closing prior stories

- **WHEN** a business owner or operator looks for how to feed performance insights into future planning
- **THEN** the extended normative procedure is reachable under `docs/operations/`
- **AND** CURRENT-STATE or GLOSSARY references the US-056 procedure without claiming Story accepted
- **AND** US-053 / US-054 / US-055 Story accepted, BL-022 close, BL-023 close, and BL-020 close are not claimed by this capability’s docs change alone

## MODIFIED Requirements

### Requirement: Metrics MUST NOT gate Flow A or Flow B; no LinkedIn enablement mutation

This capability MUST NOT require metrics collection, freshness, log presence, collection completeness, theme/variant comparison notes, effective-format labels, planning-insight notes, low-performing labels, or planning-decision notes (including US-053 / US-054 / US-055 / US-056 rows) as a prerequisite for Flow A publish/package/schedule or Flow B discover/draft/gap-trigger/promote success paths. Empty, missing, or incomplete metrics MUST NOT change those pipelines. This documentation change MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT auto-publish LinkedIn, MUST NOT auto-mutate strategy docs, editorial content backlog, or Flow B discovery/draft/gap-trigger settings without explicit operator action, and MUST NOT introduce required worker analytics-fetch endpoints, a metrics dashboard, or an auto-planning engine. **US-055** remains in scope as **operator collection consistency, theme/variant comparison, and effective-format identification procedure** (docs/contract-first; not redefined by US-056). **US-056** is in scope as **operator planning-feedback procedure only** (feed insights into future planning; reduce low-performing repetition via documented criteria; keep human oversight — docs/contract-first). Analytics platforms, statistical recommendation engines, and auto-apply planning mutation remain out of scope.

#### Scenario: Docs-only independence preserves pipelines, enablement, and human oversight

- **WHEN** this capability’s US-056 change tasks are completed
- **THEN** Flow A and Flow B success paths remain independent of metrics presence, collection completeness, and planning-insight notes
- **AND** no required analytics auto-fetch worker endpoints, metrics dashboard, or auto-planning engine are introduced by this capability
- **AND** `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not mutated by this capability
- **AND** strategy, editorial backlog, and Flow B surfaces are not auto-mutated without explicit operator action
- **AND** US-055 collection procedure remains prerequisite/input and is not redefined
- **AND** CURRENT-STATE (or equivalent ops pointer) references the US-056 procedure without claiming Story accepted solely from the proposal
