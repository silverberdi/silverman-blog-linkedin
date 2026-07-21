## ADDED Requirements

### Requirement: Empty or unused editorial backlog must not gate discovery

When capability `editorial-content-backlog` exists, Flow B AI topic discovery MUST remain independent of backlog contents. Discovery MUST NOT require backlog items to be present, MUST NOT fail solely because the backlog is empty, and MUST NOT treat backlog seeding or override as a required input in this change. Existing BL-020 independence requirements remain authoritative; this requirement clarifies behavior after the backlog store ships.

#### Scenario: Discovery succeeds with empty backlog store

- **WHEN** the editorial content backlog has zero items and an authenticated client requests discovery under otherwise valid configuration
- **THEN** discovery proceeds using its existing authority brief, canon, and soft anti-dup inputs
- **AND** the worker does not return a backlog-required failure
