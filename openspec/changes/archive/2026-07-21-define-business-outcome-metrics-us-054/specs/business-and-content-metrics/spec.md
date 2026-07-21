## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Normative business and content metrics artifact

The system documentation SHALL publish an operator-facing normative metrics definition at `docs/operations/business-and-content-metrics.md` (or that path plus a clearly linked sibling under `docs/operations/` for outcome sections) that the business owner and content operator can open as the shared meaning of **BL-022** metrics for **US-053** (blog traffic; LinkedIn reach and engagement; profile visits and audience growth) and **US-054** (recruiter/executive conversations; job/consulting opportunities; high-performing topics and formats). The document MUST identify the applicable product stories it satisfies as definition/policy, MUST state that Story accepted and BL-022 closure require operator review beyond this documentation change, MUST NOT claim US-053 Story accepted solely from the US-054 docs change, and MUST NOT claim to close BL-020 / US-049–US-050.

#### Scenario: Metrics definition artifact is operator-visible

- **WHEN** a business owner or operator opens the normative business and content metrics definition
- **THEN** the document exists at `docs/operations/business-and-content-metrics.md` (and any sibling is clearly linked)
- **AND** it identifies BL-022 / US-053 and BL-022 / US-054 as the product stories it satisfies as definition where applicable
- **AND** it states that Story accepted / BL-022 closure require operator review beyond this docs change
- **AND** it does not mark BL-020 / US-049–US-050 closed
- **AND** it does not mark US-053 Story accepted solely from the US-054 extension

### Requirement: Metrics MUST NOT gate Flow A or Flow B; no LinkedIn enablement mutation

This capability MUST NOT require metrics collection, freshness, or log presence (including US-054 outcome rows) as a prerequisite for Flow A publish/package/schedule or Flow B discover/draft/gap-trigger/promote success paths. Empty or missing metrics MUST NOT change those pipelines. This documentation change MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT auto-publish LinkedIn, and MUST NOT introduce required worker analytics-fetch endpoints. **BL-023 / US-055–US-056** collection/feedback loops (automated collection, theme/variant comparison engines, feeding insights into planning automation) remain out of scope. US-054 outcome metrics are in scope as **definition and operator recording procedure only**.

#### Scenario: Docs-only independence preserves pipelines and enablement

- **WHEN** this capability’s US-054 change tasks are completed
- **THEN** Flow A and Flow B success paths remain independent of metrics presence
- **AND** no required analytics auto-fetch worker endpoints are introduced by this capability
- **AND** `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not mutated by this capability
- **AND** BL-023 automated collection and planning-feedback loops remain explicitly out of scope
- **AND** CURRENT-STATE (or equivalent ops pointer) references the US-054 outcome definition without claiming Story accepted solely from the proposal
