# business-and-content-metrics

## Purpose

Operator-visible normative definition of **BL-022 / US-053** business and content metric families: blog traffic; LinkedIn reach and engagement; profile visits and audience growth. Includes plain-language definitions, intended sources, review cadence, supporting reuse of existing publication evidence, and clear blocked/unavailable vocabulary — without requiring an analytics platform, auto-collection worker, Flow A/B gating, US-054 outcome metrics, or changes to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

Operator definition: `docs/operations/business-and-content-metrics.md`.

## ADDED Requirements

### Requirement: Normative business and content metrics artifact

The system documentation SHALL publish an operator-facing normative metrics definition at `docs/operations/business-and-content-metrics.md` that the business owner and content operator can open as the shared meaning of US-053 metrics for **BL-022**. The document MUST identify BL-022 / US-053 as the product story it satisfies as definition/policy, MUST state that Story accepted and BL-022 closure require operator review beyond this documentation change, and MUST NOT claim to close BL-020 / US-049–US-050.

#### Scenario: Metrics definition artifact is operator-visible

- **WHEN** a business owner or operator opens the normative business and content metrics definition
- **THEN** the document exists at `docs/operations/business-and-content-metrics.md`
- **AND** it identifies BL-022 / US-053 as the product story it satisfies as definition
- **AND** it states that Story accepted / BL-022 closure require operator review beyond this docs change
- **AND** it does not mark BL-020 / US-049–US-050 closed

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

### Requirement: Metrics MUST NOT gate Flow A or Flow B; no LinkedIn enablement mutation

This capability MUST NOT require metrics collection, freshness, or log presence as a prerequisite for Flow A publish/package/schedule or Flow B discover/draft/gap-trigger/promote success paths. Empty or missing metrics MUST NOT change those pipelines. This documentation change MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT auto-publish LinkedIn, and MUST NOT introduce required worker analytics-fetch endpoints. US-054 outcome metrics (conversations, opportunities, high-performing topics/formats) and BL-023 collection/feedback loops remain out of scope.

#### Scenario: Docs-only independence preserves pipelines and enablement

- **WHEN** this capability’s change tasks are completed
- **THEN** Flow A and Flow B success paths remain independent of metrics presence
- **AND** no required analytics auto-fetch worker endpoints are introduced by this capability
- **AND** `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not mutated by this capability
- **AND** US-054 and BL-023 remain explicitly out of scope
- **AND** CURRENT-STATE (or equivalent ops pointer) references the metrics definition without claiming Story accepted solely from the proposal
