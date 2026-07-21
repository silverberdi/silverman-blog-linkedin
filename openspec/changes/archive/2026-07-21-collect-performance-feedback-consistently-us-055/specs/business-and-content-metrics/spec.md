## ADDED Requirements

### Requirement: Metrics are collected consistently per measurement period

Normative docs SHALL define an operator **consistent collection** procedure for **BL-023 / US-055** over the existing **US-053** and **US-054** metric families for each default measurement period (**calendar month**, **America/Bogota** operator dates). The procedure MUST state cadence (at least once after the period closes, optionally sooner after a notable Live on LinkedIn / Published on blog wave), required period identity fields (period label, timezone, recorded-at, recorded-by), eligibility-context recording as supporting context only, and **completeness rules**: for each in-scope family the operator records either values/notes **or** an explicit blocked/unavailable state from the BL-022 vocabulary (**not configured**, **unavailable**, **not applicable**, **not applicable — none recorded**, **zero (measured)**, **blocked by publication honesty**) — MUST NOT invent filler numeric zeros to complete a pass, and MUST NOT treat silent blanks as measured zeros. Incomplete collection for a family MUST be labeled incomplete or unavailable as applicable.

#### Scenario: Consistent collection procedure is documented

- **WHEN** an operator reads the US-055 consistent collection section
- **THEN** cadence, required period identity fields, and completeness rules are stated
- **AND** US-053 / US-054 families are named as the metrics to collect (not redefined)
- **AND** inventing filler zeros for not configured / unavailable / not applicable / none recorded is forbidden
- **AND** a required analytics auto-fetch worker is not required by this capability

### Requirement: Themes and variants are compared using recorded metrics

Normative docs SHALL define how an operator **compares themes and variants** for a measurement period using **recorded** eligible US-053 traffic/reach/engagement signals where available, plus optional US-054 outcome attribution. Comparison MUST be thin and operator-applied (relative strength notes with the signal used documented) — MUST NOT require a BI platform, statistical significance test, or automated A/B engine. Comparison MUST apply only to eligible **Published on blog** / **Live on LinkedIn** (or documented manual-post exception) items; `distribution_scheduled`, package-complete, `pending`, `queued`, or unqualified Flow A completion language MUST NOT be used to invent comparison ranks. When quantitative sources are not configured, unavailable, or not applicable, comparison notes MUST carry that blocked state; qualitative notes remain allowed with the state labeled. When no eligible published content exists in the period, comparison is **not applicable** (not a fabricated ranking).

#### Scenario: Theme and variant comparison does not invent ranks from schedule metadata

- **WHEN** an operator reads the US-055 theme and variant comparison section
- **THEN** thin operator comparison criteria and required signal documentation are stated
- **AND** inventing ranks from schedule/pending/package-complete metadata is forbidden
- **AND** a BI platform or statistical comparison engine is not required
- **AND** not applicable / unavailable states are named when evidence is missing

### Requirement: Effective formats are identified from collected evidence

Normative docs SHALL define how an operator **identifies effective formats** for a measurement period by **reusing US-054 high-performing topic/format criteria** (relative US-053 strength among eligible items; optional outcome linkage; qualitative notes when quantitative sources are blocked) after a consistent collection pass. The docs MUST NOT invent a second contradictory criteria table, MUST NOT duplicate Flow A publish/package/schedule or Flow B discover/draft/gap-trigger/promote pipelines to produce effectiveness, and MUST NOT invent numeric effectiveness ranks from schedule/pending/package-complete metadata. The operator MUST document which US-053 signal was used or which blocked state applies.

#### Scenario: Effective formats align with US-054 high-performing criteria

- **WHEN** an operator reads the US-055 effective formats section
- **THEN** identification reuses US-054 high-performing criteria rather than a divergent ranking engine
- **AND** the signal used or blocked state must be documented
- **AND** Flow A / Flow B pipelines are not duplicated for metrics
- **AND** inventing ranks from schedule/pending/package-complete is forbidden

### Requirement: US-055 collection failures and incompleteness stay consistent with BL-022 vocabulary

Normative docs SHALL reuse the BL-022 blocked/unavailable vocabulary for US-055 collection, comparison, and effective-format notes, and SHALL document that **incomplete collection** (period not finished; family skipped without review) MUST NOT be silently written as measured zero. Prefer distinguishing incomplete / **not applicable — none recorded** / **unavailable** / **not configured** from **zero (measured)** after affirmative review. Publication-honesty blocks continue to apply when LinkedIn post metrics are used as comparison or effective-format evidence.

#### Scenario: Incomplete collection is distinct from measured zero

- **WHEN** an operator has not finished collecting a family for a period
- **THEN** the docs require an incomplete / unavailable / none-recorded style label as applicable
- **AND** numeric zero MUST NOT mean “we did not collect”
- **AND** blocked-by-publication-honesty remains named for ineligible LinkedIn evidence

### Requirement: US-055 collection procedure is operator-visible without claiming Story accepted

The system documentation SHALL make the US-055 consistent-collection / comparison / effective-format procedure visible via the extended normative ops definition (same `docs/operations/business-and-content-metrics.md` or a clearly linked sibling under `docs/operations/`), CURRENT-STATE and/or GLOSSARY pointers, and light product backlog/user-story pointers as needed. An optional durable log template extension for collection completeness, theme/variant comparison notes, and effective-format labels MAY be included. The docs MUST identify BL-023 / US-055 as the product story satisfied as procedure/policy, MUST state that Story accepted and BL-023 closure require operator review beyond this documentation change, MUST NOT mark US-053 or US-054 Story accepted solely from this change, MUST NOT close BL-022 solely from this change, and MUST NOT claim to close BL-020 / US-049–US-050 or implement US-056.

#### Scenario: US-055 procedure is discoverable without closing prior stories

- **WHEN** a business owner or operator looks for how to collect performance metrics consistently
- **THEN** the extended normative procedure is reachable under `docs/operations/`
- **AND** CURRENT-STATE or GLOSSARY references the US-055 procedure without claiming Story accepted
- **AND** US-053 / US-054 Story accepted, BL-022 close, BL-020 close, and US-056 are not claimed by this capability’s docs change alone

## MODIFIED Requirements

### Requirement: Metrics MUST NOT gate Flow A or Flow B; no LinkedIn enablement mutation

This capability MUST NOT require metrics collection, freshness, log presence, collection completeness, theme/variant comparison notes, or effective-format labels (including US-053 / US-054 / US-055 rows) as a prerequisite for Flow A publish/package/schedule or Flow B discover/draft/gap-trigger/promote success paths. Empty, missing, or incomplete metrics MUST NOT change those pipelines. This documentation change MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT auto-publish LinkedIn, and MUST NOT introduce required worker analytics-fetch endpoints or a metrics dashboard. **US-055** is in scope as **operator collection consistency, theme/variant comparison, and effective-format identification procedure only** (docs/contract-first). **US-056** (feeding insights into planning; reducing low-performing repetition; strategic automation loops), analytics platforms, and statistical comparison engines remain out of scope.

#### Scenario: Docs-only independence preserves pipelines and enablement

- **WHEN** this capability’s US-055 change tasks are completed
- **THEN** Flow A and Flow B success paths remain independent of metrics presence or collection completeness
- **AND** no required analytics auto-fetch worker endpoints or metrics dashboard are introduced by this capability
- **AND** `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not mutated by this capability
- **AND** US-056 planning-feedback loops remain explicitly out of scope
- **AND** CURRENT-STATE (or equivalent ops pointer) references the US-055 procedure without claiming Story accepted solely from the proposal
