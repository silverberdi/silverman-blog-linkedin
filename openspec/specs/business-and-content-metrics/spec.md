# business-and-content-metrics

## Purpose

Operator-visible normative definition of **BL-022** business and content metric families for **US-053** (blog traffic; LinkedIn reach and engagement; profile visits and audience growth) and **US-054** (recruiter/executive conversations; job/consulting opportunities; high-performing topics and formats), plus **BL-023 / US-055** operator collection consistency, theme/variant comparison, and effective-format identification procedure, and **BL-023 / US-056** planning-feedback procedure (feed insights into future planning; reduce low-performing repetition; keep human oversight). Includes plain-language definitions, intended sources, review cadence, supporting reuse of existing publication evidence, blocked/unavailable vocabulary, and the US-055 / US-056 procedures — without requiring an analytics platform, required auto-fetch worker, metrics dashboard, auto-planning engine, Flow A/B gating, auto-mutation of strategy / backlog / Flow B, or changes to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

Operator definition: `docs/operations/business-and-content-metrics.md`.

## Requirements

### Requirement: Normative business and content metrics artifact

The system documentation SHALL publish an operator-facing normative metrics definition at `docs/operations/business-and-content-metrics.md` (or that path plus a clearly linked sibling under `docs/operations/` for outcome sections) that the business owner and content operator can open as the shared meaning of **BL-022** metrics for **US-053** (blog traffic; LinkedIn reach and engagement; profile visits and audience growth) and **US-054** (recruiter/executive conversations; job/consulting opportunities; high-performing topics and formats). The document MUST identify the applicable product stories it satisfies as definition/policy, MUST state that Story accepted and BL-022 closure require operator review beyond this documentation change, MUST NOT claim US-053 Story accepted solely from the US-054 docs change, and MUST NOT claim to close BL-020 / US-049–US-050.

#### Scenario: Metrics definition artifact is operator-visible

- **WHEN** a business owner or operator opens the normative business and content metrics definition
- **THEN** the document exists at `docs/operations/business-and-content-metrics.md` (and any sibling is clearly linked)
- **AND** it identifies BL-022 / US-053 and BL-022 / US-054 as the product stories it satisfies as definition where applicable
- **AND** it states that Story accepted / BL-022 closure require operator review beyond this docs change
- **AND** it does not mark BL-020 / US-049–US-050 closed
- **AND** it does not mark US-053 Story accepted solely from the US-054 extension

### Requirement: Blog traffic metrics are defined

Normative docs SHALL define blog traffic metrics in plain language, including at minimum: site page views for a measurement period; unique visitors when the source provides them; top posts by views; and referral or landing context when available. The definition MUST state why each metric matters for the content program and MUST name intended sources (e.g. hosting / web analytics when configured). Blog handoff to the public checkout MUST NOT be treated as equivalent to measured live traffic.

#### Scenario: Blog traffic family is named and sourced

- **WHEN** an operator reads the blog traffic section
- **THEN** page views, unique visitors (when available), top posts by views, and referral/landing context (when available) are defined
- **AND** intended sources are stated
- **AND** blog handoff is not equated with measured live traffic

### Requirement: LinkedIn reach and engagement metrics are defined

Normative docs SHALL define LinkedIn reach and engagement metrics in plain language, including at minimum: impressions (or reach); reactions; comments; shares or reposts; and engagement rate when both engagements and impressions are known. Metrics for a LinkedIn post MUST apply only when the post is eligible as published for measurement (**Live on LinkedIn** or an explicitly documented manually posted exception) — `distribution_scheduled`, package-complete, or `pending` MUST NOT be counted as reach or engagement. The definition MUST name LinkedIn native post analytics (or equivalent) as the intended source for the first tracking method.

#### Scenario: LinkedIn engagement requires published eligibility

- **WHEN** an operator reads the LinkedIn reach and engagement section
- **THEN** impressions/reach, reactions, comments, shares/reposts, and engagement rate (when computable) are defined
- **AND** scheduled/pending/package-complete states are forbidden as substitutes for measured reach
- **AND** intended source is LinkedIn native analytics (or equivalent) for the first tracking method

### Requirement: Profile visits and audience growth are tracked by definition and procedure

Normative docs SHALL define profile visits and audience growth metrics, including at minimum: profile views for a measurement period; follower count at period end; and net follower change versus the prior period. The docs SHALL provide an operator tracking procedure (measurement period, where to read values, where to record them) so tracking does not require an automated worker in this change. A lightweight durable operator log template MAY be included; a required analytics API integration MUST NOT be required to satisfy this requirement.

#### Scenario: Profile and growth tracking procedure is documented

- **WHEN** an operator follows the profile visits and audience growth section
- **THEN** profile views, follower count, and net follower change are defined
- **AND** a measurement period and recording procedure are stated
- **AND** automated LinkedIn Analytics API ingestion is not required by this capability

### Requirement: Recruiter and executive conversations are tracked by definition and procedure

Normative docs SHALL define recruiter and executive conversation metrics for **BL-022 / US-054**, including at minimum: what counts as a conversation (a two-way professional exchange related to professional positioning — not one-way likes/reactions); how an operator records conversations for a measurement period (count, optional channel, optional content/campaign attribution); intended sources (operator-owned records such as LinkedIn inbox, email, calendar notes, or a personal tracker — no required CRM); and review cadence consistent with the US-053 default (**calendar month**, **America/Bogota** operator dates). One-way LinkedIn reactions or comments without a two-way exchange MUST NOT be counted as conversations (those remain US-053 engagement).

#### Scenario: Conversation tracking procedure is documented

- **WHEN** an operator reads the recruiter and executive conversations section
- **THEN** a plain-language definition of a qualifying conversation is stated
- **AND** a recording procedure, intended sources, and review cadence are stated
- **AND** one-way engagement is excluded from the conversation count
- **AND** a required CRM or analytics API is not required by this capability

### Requirement: Job and consulting opportunities are tracked by definition and procedure

Normative docs SHALL define job and consulting opportunity metrics for US-054, including at minimum: what counts as an opportunity (a concrete professional prospect being tracked — not vague aspiration); how an operator records opportunities for a measurement period (count, type such as job/consulting/other, optional stage label, optional content attribution); intended sources (operator-owned records — no required ATS/CRM); and the same default measurement period and review cadence as US-053. Vague prospects without a recordable identity MUST NOT be counted as opportunities.

#### Scenario: Opportunity tracking procedure is documented

- **WHEN** an operator reads the job and consulting opportunities section
- **THEN** a plain-language definition of a qualifying opportunity is stated
- **AND** recording fields (count, type, optional stage, optional attribution), intended sources, and review cadence are stated
- **AND** a required ATS/CRM integration is not required by this capability

### Requirement: High-performing topics and formats are identified by documented criteria

Normative docs SHALL define how an operator identifies high-performing topics and formats for a measurement period using US-053 traffic/reach/engagement signals **where available**, plus optional attribution from recorded conversations or opportunities. Criteria MUST be thin and operator-applied (e.g. top-tier by a documented US-053 signal among eligible Published on blog / Live on LinkedIn items; and/or outcome linkage). The docs MUST NOT require a BI platform, statistical comparison engine, or automated theme/variant ranking. When US-053 quantitative sources are not configured, unavailable, or not applicable, the operator MAY still record qualitative topic/format notes with that blocked state labeled — MUST NOT invent numeric ranks from `distribution_scheduled`, package-complete, pending, or unqualified Flow A completion language.

#### Scenario: High-performing identification does not invent a BI engine

- **WHEN** an operator reads the high-performing topics and formats section
- **THEN** criteria for labeling high-performing topics/formats are stated
- **AND** US-053 signals are named as supporting evidence when available
- **AND** inventing ranks from schedule/pending/package-complete metadata is forbidden
- **AND** a BI platform or automated comparison engine is not required

### Requirement: Measurement period, visibility, and supporting evidence reuse

Normative docs SHALL state a default measurement period (**calendar month**) and MAY allow optional per-post or per-campaign windows after Published on blog / Live on LinkedIn. Operator-facing dates SHOULD use **America/Bogota** consistently with publishing-window guidance. The docs MUST make the metric set understandable to the business owner (plain language; no unqualified “Flow A complete” as a traffic claim). The docs MAY reuse existing campaign metadata, calendar, and Authority Manager publication honesty as **supporting context** for what was eligible to measure, and MUST NOT invent a second publication pipeline to produce metrics.

#### Scenario: Context reuse without pipeline duplication

- **WHEN** an operator reads how to interpret a measurement period
- **THEN** a default calendar-month period is stated
- **AND** existing publication evidence MAY be used as eligibility context
- **AND** the docs do not require duplicating Flow A or Flow B publication pipelines for metrics

### Requirement: Failures and blocked states are clearly communicated

Normative docs SHALL communicate metric failures and blocked states in vocabulary that distinguishes at least: **not configured**; **unavailable**; **not applicable** (no eligible published content in period); **zero (measured)**; and **blocked by publication honesty** (scheduled/pending must not be counted as LinkedIn reach). Numeric zero MUST NOT be used to mean “not configured” or “not applicable.”

#### Scenario: Unavailable is distinct from measured zero

- **WHEN** an operator cannot read a metric because analytics is not configured or the source is inaccessible
- **THEN** the documented state is not configured or unavailable (as applicable)
- **AND** the docs forbid treating that state as a measured zero
- **AND** publication-honesty blocks are named separately from analytics outages

### Requirement: US-054 outcome blocked states stay consistent with US-053 vocabulary

Normative docs SHALL reuse the US-053 blocked/unavailable vocabulary (**not configured**, **unavailable**, **not applicable**, **zero (measured)**, **blocked by publication honesty**) for outcome metrics and SHALL document US-054-specific guidance: no conversations (or opportunities) **recorded** in a period MUST NOT be silently written as measured zero when tracking was not performed; prefer distinguishing **not applicable — none recorded** (or equivalent) from **zero (measured)** when the operator affirmatively reviewed sources and found none. Publication-honesty blocks continue to apply when US-053 LinkedIn post metrics are used as evidence for high-performing labels.

#### Scenario: None recorded is distinct from measured zero outcomes

- **WHEN** an operator has no conversation or opportunity rows for a period
- **THEN** the docs distinguish not performing outcome tracking / none recorded from an affirmative measured zero
- **AND** numeric zero MUST NOT mean “we did not track”
- **AND** blocked-by-publication-honesty remains named for ineligible LinkedIn reach used as high-performing evidence

### Requirement: US-054 outcome definition is operator-visible without claiming Story accepted

The system documentation SHALL make US-054 outcome metrics visible via the extended normative ops definition (same `docs/operations/business-and-content-metrics.md` or a clearly linked sibling under `docs/operations/`), CURRENT-STATE and/or GLOSSARY pointers, and light product backlog/user-story pointers as needed. An optional durable log template extension for conversations, opportunities, and topic/format notes MAY be included. The docs MUST identify BL-022 / US-054 as the product story satisfied as definition/policy, MUST state that Story accepted and BL-022 closure require operator review beyond this documentation change, MUST NOT mark US-053 Story accepted solely from this change, and MUST NOT claim to close BL-020 / US-049–US-050.

#### Scenario: Outcome metrics definition is discoverable

- **WHEN** a business owner or operator looks for US-054 outcome metrics
- **THEN** the extended normative definition is reachable under `docs/operations/`
- **AND** CURRENT-STATE or GLOSSARY references the US-054 outcome extension without claiming Story accepted
- **AND** US-053 Story accepted and BL-020 closure are not claimed by this capability’s docs change alone

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
