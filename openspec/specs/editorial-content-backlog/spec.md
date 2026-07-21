# editorial-content-backlog

## Purpose

Durable Postgres-backed hand-curated editorial content backlog (US-049 / US-050 / BL-020): authenticated HTTP create/list/update (and optional reorder) for topic, audience, objective, format, priority, status, target date, LinkedIn derivative planning notes, dependency edges (`depends_on_item_ids`), and queue order (`queue_rank`). Optional enrichment only — MUST NOT gate Flow B discovery, draft generation, or gap trigger. Discovery seed/override remains out of scope.

## Requirements

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
| `depends_on_item_ids` | Optional list of stable backlog `item_id` strings this item depends on (empty allowed) |
| `queue_rank` | Non-negative integer queue order (lower = earlier); server-assigned default on create when omitted |

Each item MUST also support linking the topic to zero or more **LinkedIn derivative planning notes** (audience hint, format hint, and optional free-text notes). Those links are planning/distribution intent only (ADR-0002); this capability MUST NOT generate LinkedIn package files or publish to LinkedIn.

Connection secrets MUST come from environment only and MUST NEVER appear in HTTP responses, logs, or error bodies.

#### Scenario: Item round-trip through the database

- **WHEN** an authenticated client creates a valid backlog item and then lists or reads it
- **THEN** the persisted capture fields, LinkedIn derivative notes, `depends_on_item_ids`, and `queue_rank` are returned unchanged aside from server-managed metadata (`item_id`, timestamps, `row_version`)
- **AND** the store target is `silverman_linkedin_db` (or the test memory store)

#### Scenario: Empty backlog is a valid state

- **WHEN** no backlog items exist and an authenticated client lists the backlog
- **THEN** the worker returns an empty collection successfully
- **AND** does not treat emptiness as a system failure

### Requirement: Persist and validate backlog item dependencies

The worker SHALL allow each editorial content backlog item to declare zero or more **dependencies** on other backlog items via stable `item_id` references (`depends_on_item_ids`). Dependencies are optional planning metadata on the optional backlog enrichment. An empty dependency list MUST be valid. Creating or updating an item MUST NOT require dependencies.

Dependency writes MUST fail closed with structured **4xx** errors and actionable messages when:

- a referenced `item_id` does not exist (dangling reference)
- an item lists itself as a dependency
- applying the write would introduce a cycle in the directed dependency graph
- the dependency list exceeds the bounded maximum length

Invalid dependency writes MUST NOT partially persist. Responses MUST NOT expose secrets. Dependency metadata MUST NOT generate LinkedIn packages, publish to LinkedIn, or mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

#### Scenario: Dependencies round-trip on create and read

- **WHEN** an authenticated client creates a valid backlog item that depends on one or more existing backlog item ids
- **THEN** the worker persists those `depends_on_item_ids`
- **AND** subsequent list or detail responses return the same dependency ids

#### Scenario: Empty dependencies remain valid

- **WHEN** an authenticated client creates or updates a backlog item without dependency ids (or with an empty list)
- **THEN** the write succeeds
- **AND** the item’s `depends_on_item_ids` is empty

#### Scenario: Dangling dependency reference is rejected

- **WHEN** an authenticated client writes a dependency id that does not exist in the backlog store
- **THEN** the worker rejects the write with a structured validation error
- **AND** no invalid dependency set is persisted

#### Scenario: Self-dependency is rejected

- **WHEN** an authenticated client writes a dependency list that includes the item’s own `item_id`
- **THEN** the worker rejects the write with a structured validation error

#### Scenario: Cyclic dependency is rejected

- **WHEN** an authenticated client writes dependencies that would create a cycle among backlog items
- **THEN** the worker rejects the write with a structured validation error identifying a cycle
- **AND** the prior acyclic dependency state remains unchanged

### Requirement: Prioritize and reprioritize backlog items

The worker SHALL support **prioritization** and **reprioritization** of editorial content backlog items over authenticated HTTP. Prioritization MUST include at least:

- updating the existing `priority` enum (`low`, `medium`, `high`)
- an explicit durable queue order field (`queue_rank`, lower = earlier in the operator queue)

List responses MUST order items by the prioritization contract (at minimum `queue_rank` ascending, with a documented tie-break that includes the priority band). Authenticated clients MUST be able to change `priority` and/or `queue_rank` so an item moves relative to others in the queue. The worker MAY expose a dedicated authenticated reorder endpoint that reassigns ranks from an ordered list of `item_id` values.

Invalid priority or rank writes MUST fail closed with structured **4xx** errors. Reprioritization MUST NOT enable LinkedIn API publication, MUST NOT write LinkedIn packages, and MUST NOT gate Flow B discovery, draft generation, or gap trigger.

#### Scenario: Priority change reprioritizes an item

- **WHEN** an authenticated client updates an existing backlog item’s `priority` from one allowed enum value to another
- **THEN** the persisted item reflects the new priority
- **AND** subsequent list responses include the updated priority under the prioritization contract

#### Scenario: Queue rank change reorders the list

- **WHEN** an authenticated client updates `queue_rank` (or calls the reorder endpoint with a new ordered id list) so item A should appear before item B
- **THEN** a subsequent authenticated list returns A before B according to the prioritization contract

#### Scenario: Invalid queue rank is rejected

- **WHEN** an authenticated client writes a `queue_rank` that is not a valid non-negative integer
- **THEN** the worker rejects the write with a structured validation error
- **AND** the prior ordering remains unchanged

### Requirement: Validate backlog writes at the HTTP edge

Authenticated create and update requests MUST validate the capture field set, LinkedIn derivative notes, `depends_on_item_ids`, and `queue_rank`. Invalid writes MUST fail closed with structured **4xx** errors and actionable messages, MUST NOT partially persist invalid values, and MUST NOT expose secrets.

Validation MUST include at least:

- required non-empty trimmed strings for `topic`, `audience`, and `objective`
- `format`, `priority`, and `status` as allowed enums
- `target_date` as null or a valid `YYYY-MM-DD` calendar date
- LinkedIn derivative notes as a bounded list of objects with string hints/notes (empty list allowed)
- `depends_on_item_ids` as a bounded list of existing distinct backlog item ids (empty allowed); no self-reference; no cycles
- `queue_rank` as a non-negative integer when provided

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

The worker SHALL expose authenticated HTTP endpoints to create, list, and update editorial content backlog items (for example under `/editorial/content-backlog`), including dependency and prioritization fields. Unauthenticated requests MUST be rejected. Responses MUST be JSON and MUST NOT include API keys, OAuth tokens, database passwords, or other secrets.

Orchestration remains **n8n → worker HTTP only** (ADR-0001). This capability MUST NOT introduce n8n Execute Command usage. Creating or updating backlog items MUST NOT enable LinkedIn API publication and MUST NOT modify `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

List responses MUST be understandable to an editorial operator (item identity plus capture fields, derivative notes, dependencies, and queue order) and MUST apply the prioritization sort contract. Store-unavailable or unexpected failures MUST be clearly communicated with structured errors distinct from an empty backlog.

#### Scenario: Unauthenticated list is rejected

- **WHEN** a client calls the backlog list endpoint without valid worker authentication
- **THEN** the request is rejected and no backlog items are returned

#### Scenario: Authenticated create returns the new item

- **WHEN** an authenticated client posts a valid backlog item including optional LinkedIn derivative notes and optional dependencies
- **THEN** the worker persists the item and returns it with a server-assigned `item_id` and `queue_rank`
- **AND** LinkedIn API publication enablement is unchanged

#### Scenario: Authenticated update changes capture fields

- **WHEN** an authenticated client updates an existing item with valid fields including dependencies and/or priority / queue rank
- **THEN** the persisted item reflects the new capture fields, derivative notes, dependencies, and prioritization fields
- **AND** server-managed `updated_at_utc` (and concurrency metadata when used) advances

#### Scenario: Store failure is distinct from empty backlog

- **WHEN** the backlog store is misconfigured or unavailable
- **THEN** the worker returns a clear operator-visible failure
- **AND** does not present the failure as a successful empty backlog

### Requirement: Optional enrichment must not gate Flow B

The editorial content backlog is **optional enrichment**. An empty backlog, a missing backlog table row set, unused dependency fields, unused queue ranks, or non-use of backlog APIs MUST NOT be required before Flow B AI topic discovery (BL-017 / US-078), blog draft generation (US-079), or calendar gap trigger (BL-019 / US-082) can run. This capability MUST NOT wire backlog contents, dependencies, or ranks as a mandatory seed or override input to those Flow B paths in this change.

#### Scenario: Flow B paths remain independent of backlog contents

- **WHEN** the backlog has zero items (or backlog APIs are unused)
- **THEN** Flow B discovery and gap-trigger contracts remain operable under their existing enablement and validation rules
- **AND** this capability does not introduce a hard dependency that blocks those endpoints solely because the backlog is empty

### Requirement: US-050 scope excludes discovery seeding and publication side effects

This capability slice (US-050) MUST implement dependency identification and prioritization / reprioritization only. It MUST NOT implement Flow B discovery seed or override as a required input, MUST NOT auto-publish blog or LinkedIn content, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, and MUST NOT claim BL-020 closed or US-049 / US-050 Story accepted without operator acceptance gates outside this capability. Future optional seeding from the backlog MAY be proposed in a separate change.

#### Scenario: Dependency write does not publish or package LinkedIn

- **WHEN** an authenticated client updates dependencies or queue order on a backlog item
- **THEN** no LinkedIn package files are generated under `linkedin-posts/`
- **AND** no LinkedIn API publish is attempted by this capability

#### Scenario: Dependency and priority fields are not required for Flow B

- **WHEN** the backlog is empty or items have no dependencies and default ranks
- **THEN** Flow B discovery and gap-trigger contracts remain operable under their existing enablement and validation rules
- **AND** this capability does not introduce a hard dependency that blocks those endpoints solely because dependencies are unused
