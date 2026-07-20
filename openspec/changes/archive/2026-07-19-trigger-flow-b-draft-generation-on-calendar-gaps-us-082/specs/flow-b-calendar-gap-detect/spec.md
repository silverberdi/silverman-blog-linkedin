## MODIFIED Requirements

### Requirement: US-077 scope excludes trigger and downstream Flow B runtime

This capability MUST NOT implement gap trigger orchestration, AI discovery/draft (US-078/US-079), blog approve/promote (US-080/US-081), or LinkedIn API publication. Detect MUST remain non-mutating and MUST NOT start discovery or draft generation. Fail-closed auto-trigger semantics for `gap_trigger_enabled` are owned by capability `flow-b-calendar-gap-trigger` (US-082), which MAY consume this detect result. Detect MAY continue to run for inspection when `gap_trigger_enabled=false`.

#### Scenario: Detect remains non-mutating when trigger exists

- **WHEN** an authenticated client calls the gap-detect endpoint
- **THEN** campaigns, calendar rows, and draft folders are unchanged by detect alone
- **AND** detect does not itself create files under `blog-posts/pending-approval/`

#### Scenario: Trigger consumption does not change detect contract

- **WHEN** gap trigger (US-082) consumes a detect result to decide whether to start drafts
- **THEN** the detect HTTP contract remains read-only / detect-only
- **AND** gap definition remains coverage ≤ `gap_posts_threshold` (default 0), not remaining density capacity under US-040K max 2
