## ADDED Requirements

### Requirement: Persist editorial content backlog items in Postgres

The worker SHALL persist hand-curated editorial content backlog items in PostgreSQL database **`silverman_linkedin_db`**, reusing the calendar database connection configuration (`SILVERMAN_CALENDAR_DATABASE_URL` or equivalent targeting that database). Tests MAY use an in-process `memory://` store. The long-term source of truth MUST NOT be browser storage, editorial-mount JSON, or n8n Execute Command side effects.

Each backlog item MUST support at least these capture fields:

| Field | Semantics |
|-------|-----------|
| `topic` | Non-empty topic title/summary |
| `audience` | Non-empty intended audience |
| `objective` | Non-empty content objective |
| `format` | Allowed enum (`blog`, `linkedin`, or `both` in v1) |
| `priority` | Allowed enum (`low`, `medium`, or `high` in v1) |
| `status` | Allowed enum (`idea`, `planned`, `in_progress`, `done`, or `dropped` in v1) |
| `target_date` | Optional ISO calendar date (`YYYY-MM-DD`) or null |

Each item MUST also support linking the topic to zero or more **LinkedIn derivative planning notes** (audience hint, format hint, and optional free-text notes). Those links are planning/distribution intent only (ADR-0002); this capability MUST NOT generate LinkedIn package files or publish to LinkedIn.

Connection secrets MUST come from environment only and MUST NEVER appear in HTTP responses, logs, or error bodies.

#### Scenario: Item round-trip through the database

- **WHEN** an authenticated client creates a valid backlog item and then lists or reads it
- **THEN** the persisted capture fields and LinkedIn derivative notes are returned unchanged aside from server-managed metadata (`item_id`, timestamps, `row_version`)
- **AND** the store target is `silverman_linkedin_db` (or the test memory store)

#### Scenario: Empty backlog is a valid state

- **WHEN** no backlog items exist and an authenticated client lists the backlog
- **THEN** the worker returns an empty collection successfully
- **AND** does not treat emptiness as a system failure

### Requirement: Validate backlog writes at the HTTP edge

Authenticated create and update requests MUST validate the capture field set and LinkedIn derivative notes. Invalid writes MUST fail closed with structured **4xx** errors and actionable messages, MUST NOT partially persist invalid values, and MUST NOT expose secrets.

Validation MUST include at least:

- required non-empty trimmed strings for `topic`, `audience`, and `objective`
- `format`, `priority`, and `status` as allowed enums
- `target_date` as null or a valid `YYYY-MM-DD` calendar date
- LinkedIn derivative notes as a bounded list of objects with string hints/notes (empty list allowed)

#### Scenario: Missing topic is rejected

- **WHEN** an authenticated client creates or updates an item without a non-empty `topic`
- **THEN** the worker rejects the write with a structured validation error
- **AND** no invalid row is persisted

#### Scenario: Invalid status enum is rejected

- **WHEN** an authenticated client writes an item with a `status` value outside the allowed enum
- **THEN** the worker rejects the write with a structured validation error

#### Scenario: Invalid target date is rejected

- **WHEN** an authenticated client writes a `target_date` that is not null and not a valid `YYYY-MM-DD` date
- **THEN** the worker rejects the write with a structured validation error

### Requirement: Authenticated backlog create list and update HTTP API

The worker SHALL expose authenticated HTTP endpoints to create, list, and update editorial content backlog items (for example under `/editorial/content-backlog`). Unauthenticated requests MUST be rejected. Responses MUST be JSON and MUST NOT include API keys, OAuth tokens, database passwords, or other secrets.

Orchestration remains **n8n → worker HTTP only** (ADR-0001). This capability MUST NOT introduce n8n Execute Command usage. Creating or updating backlog items MUST NOT enable LinkedIn API publication and MUST NOT modify `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

List responses MUST be understandable to an editorial operator (item identity plus capture fields and derivative notes). Store-unavailable or unexpected failures MUST be clearly communicated with structured errors distinct from an empty backlog.

#### Scenario: Unauthenticated list is rejected

- **WHEN** a client calls the backlog list endpoint without valid worker authentication
- **THEN** the request is rejected and no backlog items are returned

#### Scenario: Authenticated create returns the new item

- **WHEN** an authenticated client posts a valid backlog item including optional LinkedIn derivative notes
- **THEN** the worker persists the item and returns it with a server-assigned `item_id`
- **AND** LinkedIn API publication enablement is unchanged

#### Scenario: Authenticated update changes capture fields

- **WHEN** an authenticated client updates an existing item with valid fields
- **THEN** the persisted item reflects the new capture fields and derivative notes
- **AND** server-managed `updated_at_utc` (and concurrency metadata when used) advances

#### Scenario: Store failure is distinct from empty backlog

- **WHEN** the backlog store is misconfigured or unavailable
- **THEN** the worker returns a clear operator-visible failure
- **AND** does not present the failure as a successful empty backlog

### Requirement: Optional enrichment must not gate Flow B

The editorial content backlog is **optional enrichment**. An empty backlog, a missing backlog table row set, or non-use of backlog APIs MUST NOT be required before Flow B AI topic discovery (BL-017 / US-078), blog draft generation (US-079), or calendar gap trigger (BL-019 / US-082) can run. This capability MUST NOT wire backlog contents as a mandatory seed or override input to those Flow B paths in this change.

#### Scenario: Flow B paths remain independent of backlog contents

- **WHEN** the backlog has zero items (or backlog APIs are unused)
- **THEN** Flow B discovery and gap-trigger contracts remain operable under their existing enablement and validation rules
- **AND** this capability does not introduce a hard dependency that blocks those endpoints solely because the backlog is empty

### Requirement: US-049 scope excludes dependency UX and discovery seeding

This capability MUST implement US-049 Story 1 only. It MUST NOT implement US-050 dependency graphs or prioritization/reprioritization UX. It MUST NOT auto-publish blog or LinkedIn content, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, and MUST NOT claim BL-020 closed or US-049 Story accepted without operator acceptance gates outside this capability.

#### Scenario: Create does not publish or package LinkedIn

- **WHEN** an authenticated client creates a backlog item with LinkedIn derivative notes
- **THEN** no LinkedIn package files are generated under `linkedin-posts/`
- **AND** no LinkedIn API publish is attempted by this capability

#### Scenario: Dependency fields are not required

- **WHEN** an authenticated client creates a valid backlog item without dependency graph fields
- **THEN** the create succeeds
- **AND** the API does not require US-050 dependency identifiers
