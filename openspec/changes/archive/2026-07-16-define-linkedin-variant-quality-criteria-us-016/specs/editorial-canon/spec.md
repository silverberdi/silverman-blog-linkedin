## ADDED Requirements

### Requirement: Review-process criteria consume editorial canon anchors

The `linkedin-variant-review-process` capability US-016 criteria artifact (`docs/operations/linkedin-variant-quality-criteria.md`) MUST consume and cross-reference editorial canon anchors in `content-strategy/silverman-editorial-system.md` without duplicating full canon text:

- `#audience-map` — primary audience lens per variant
- `#linkedin-derivative-package` — variant objectives and structure sketches
- `#no-redundancy-rules` — sibling differentiation requirements
- `#anti-ai-writing-rules` — rewrite/blocking posture for generated LinkedIn derivatives
- `#linkedin-distribution-strategy` — sequencing context (criteria do not change scheduling)

The criteria artifact MUST NOT contradict editorial-canon Flow A vs Flow B publication policy encoded in `#flow-a-vs-flow-b`.

#### Scenario: Criteria reference audience map

- **WHEN** an operator reads US-016 criteria cross-links
- **THEN** `#audience-map` is referenced for primary audience lens definitions

#### Scenario: Criteria reference no-redundancy rules

- **WHEN** an operator reads the differentiation criteria section
- **THEN** `#no-redundancy-rules` is referenced as the authoritative sibling-uniqueness source
