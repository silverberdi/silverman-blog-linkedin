# flow-b-gap-operator-settings

## ADDED Requirements

### Requirement: Blog draft generation consumes max_drafts_per_weekly_run

Internal and HTTP blog-draft-generation paths (capability `flow-b-blog-draft-generation` / US-079) MUST resolve the draft batch ceiling via `load_gap_operator_settings()` when present, applying documented defaults when a row is missing. Effective `max_drafts_per_weekly_run` (default **2**) MUST cap how many draft packages a single generation request may produce. Saving or loading settings MUST NOT by itself start draft generation, topic discovery, gap detect, gap trigger, or LinkedIn publication. Settings persist/UI HTTP contracts (`GET`/`PUT /flow-b/gap-operator-settings`) MUST remain unchanged.

#### Scenario: Draft generation loader uses stored max_drafts_per_weekly_run

- **WHEN** a settings row exists with `max_drafts_per_weekly_run=1` and blog draft generation runs with multiple topics
- **THEN** draft generation applies `1` as the batch ceiling rather than the default `2`

#### Scenario: Settings save does not start draft generation

- **WHEN** an authenticated client saves valid gap operator settings
- **THEN** this capability does not invoke blog draft generation or create `pending-approval/` packages as a side effect

## MODIFIED Requirements

### Requirement: US-076 scope excludes later Flow B runtime

This capability MUST NOT implement gap detection (US-077), gap trigger orchestration (US-082), AI topic discovery (US-078), AI blog draft generation (US-079), or blog approve/promote (US-080/US-081). Orchestration remains **n8n → worker HTTP only** (ADR-0001); this change MUST NOT introduce n8n Execute Command usage. Gap detect is owned by a separate capability (`flow-b-calendar-gap-detect`) when present. Topic discovery is owned by a separate capability (`flow-b-topic-discovery`) when present. Blog draft generation is owned by a separate capability (`flow-b-blog-draft-generation`) when present; this settings capability supplies knobs such as `max_drafts_per_weekly_run` via `load_gap_operator_settings()`.

#### Scenario: No gap-detect or trigger routes required

- **WHEN** this capability's requirements are evaluated
- **THEN** gap-detect, gap-trigger, discovery, and draft endpoints are not required to be implemented inside the settings capability
- **AND** discovery and draft generation remain owned by their separate capabilities when present
