## MODIFIED Requirements

### Requirement: Empty or unused editorial backlog must not gate discovery

When capability `editorial-content-backlog` exists, Flow B AI topic discovery MUST remain independent of backlog contents, dependencies, and queue ranks. Discovery MUST NOT require backlog items to be present, MUST NOT fail solely because the backlog is empty or because dependency / prioritization fields are unused, and MUST NOT treat backlog seeding, dependency graphs, or ranks as a required input in this change. Existing BL-020 independence requirements remain authoritative; this requirement clarifies behavior after US-050 dependency and prioritization enrichment ships.

#### Scenario: Discovery succeeds with empty backlog store

- **WHEN** the editorial content backlog has zero items and an authenticated client requests discovery under otherwise valid configuration
- **THEN** discovery proceeds under existing discovery rules
- **AND** the worker does not return a backlog-required failure

#### Scenario: Discovery succeeds when backlog dependencies are unused

- **WHEN** backlog items exist (with or without `depends_on_item_ids` / `queue_rank`) and an authenticated client requests discovery under otherwise valid configuration
- **THEN** discovery proceeds under existing discovery rules
- **AND** the worker does not require consuming those dependency or rank fields as seed input
