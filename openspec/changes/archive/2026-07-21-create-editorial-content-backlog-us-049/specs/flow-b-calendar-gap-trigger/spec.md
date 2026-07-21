## ADDED Requirements

### Requirement: Empty or unused editorial backlog must not gate gap trigger

When capability `editorial-content-backlog` exists, Flow B calendar gap trigger MUST remain independent of backlog contents. Gap trigger MUST NOT require backlog items to be present, MUST NOT change clean no-op or trigger semantics solely because the backlog is empty or unused, and MUST NOT consume backlog items as a mandatory seed for discovery or draft generation in this change.

#### Scenario: Gap trigger semantics unchanged with empty backlog

- **WHEN** the editorial content backlog has zero items and an authenticated client calls gap trigger under conditions that would otherwise no-op or trigger
- **THEN** gap-trigger outcomes follow existing settings, window, detect, and idempotency rules
- **AND** the worker does not return a backlog-required failure or new blocked status caused only by an empty backlog
