# flow-b-calendar-gap-detect

## Purpose

Authenticated detect-only next-week LinkedIn calendar gap sensor; settings-driven timezone / `min_lead_days` / threshold; structured `gaps[]` result; no campaign/draft mutation; detect allowed when trigger disabled. Gap trigger orchestration is owned by `flow-b-calendar-gap-trigger` (US-082); discovery/draft/approve/promote remain out of scope.

## Requirements

### Requirement: Detect next-week LinkedIn calendar gaps

The worker SHALL provide a detect-only gap sensor that scans the **next** operator-local week (Monday–Sunday) and identifies gap days where LinkedIn coverage count is less than or equal to the effective `gap_posts_threshold` (default **0**, meaning days with **0** LinkedIn posts).

LinkedIn coverage for a local day MUST count items whose publication/source state is one of `pending`, `queued`, or `published`, bucketed by the operator-local calendar day of the item’s scheduled UTC timestamp. Days with coverage count greater than the threshold (typically ≥1 when threshold is 0) MUST NOT be treated as gaps.

The sensor MUST NOT redefine gap as remaining density capacity under US-040K max-2; density remains a separate scheduling ceiling.

Empty coverage MUST be treated as a proxy for needing upstream content. The sensor MUST NOT use filesystem inventory of `blog-posts/ready/` or `blog-posts/pending-approval/` as the gap coverage source.

#### Scenario: Empty next week yields gaps

- **WHEN** the next operator-local week has no LinkedIn items in `pending`, `queued`, or `published` on any Mon–Sun day and each empty day satisfies `min_lead_days`
- **THEN** the detect result status indicates gaps were found
- **AND** `gaps` lists those local days

#### Scenario: Day with one pending LinkedIn post is not a gap

- **WHEN** a local day in the target week has exactly one LinkedIn item with `publish_state` `pending` and `gap_posts_threshold` is `0`
- **THEN** that day is not included in actionable `gaps`
- **AND** the day is not treated as a density-capacity gap merely because count is below max-2

#### Scenario: Filesystem ready folder is not coverage

- **WHEN** `blog-posts/ready/` contains Markdown files but the target week has zero LinkedIn pending/queued/published items on a local day
- **THEN** that local day remains a gap based on LinkedIn coverage
- **AND** the ready-folder presence alone does not clear the gap

### Requirement: Apply operator settings including min_lead_days

Gap detect MUST load effective knobs via `load_gap_operator_settings()` (DB row when present; documented defaults when missing). It MUST use at least:

- `operator_timezone` for local week boundaries and day bucketing
- `gap_scan_mode` (`next_week` in v1)
- `min_lead_days` (default **5**)
- `gap_posts_threshold` (default **0**)

A zero-coverage day MUST be returned in actionable `gaps` only when the whole-local-day distance from the operator-local date of “now” to that gap day is greater than or equal to effective `min_lead_days`.

Detect MUST NOT require `gap_trigger_enabled=true` to run. The result MAY echo effective `gap_trigger_enabled` for operators and orchestrators.

#### Scenario: Settings defaults apply when row missing

- **WHEN** no gap operator settings row exists
- **THEN** detect uses documented defaults including `min_lead_days=5` and `gap_posts_threshold=0`
- **AND** the result identifies settings source as defaults

#### Scenario: min_lead_days filters near empty days

- **WHEN** a target-week local day has zero LinkedIn coverage but the day distance from operator-local today is less than effective `min_lead_days`
- **THEN** that day is not included in actionable `gaps`

#### Scenario: Detect runs when gap trigger is disabled

- **WHEN** effective settings have `gap_trigger_enabled=false`
- **THEN** authenticated detect still returns a gap/no-gap result for the next week
- **AND** no draft generation or trigger side effects occur

### Requirement: Orchestration-suitable detect result without mutation

The detect result MUST include at least:

- actionable `gaps` (list; empty when no-gap)
- a clear no-gap vs gaps-found status
- target ISO week identity for the scanned next week
- operator timezone used
- effective `min_lead_days` and `gap_posts_threshold`
- `read_only=true` / detect-only semantics
- observation timestamp in UTC

The detect-only path MUST NOT mutate campaign metadata, editorial calendar schedule rows, LinkedIn variant state, or filesystem draft/layout folders, and MUST NOT start topic discovery or blog draft generation.

#### Scenario: No-gap result when every day has coverage

- **WHEN** each Mon–Sun day of the next operator-local week has at least one LinkedIn pending/queued/published item
- **THEN** the result status indicates no gap
- **AND** `gaps` is empty

#### Scenario: Detect does not mutate campaigns

- **WHEN** detect runs successfully against an editorial base with existing campaigns
- **THEN** campaign files and calendar schedule rows are unchanged
- **AND** no files are created under `blog-posts/pending-approval/` or `blog-posts/ready/`

### Requirement: Authenticated worker gap-detect HTTP endpoint

The worker SHALL expose an authenticated HTTP endpoint for gap detect / dry-run diagnostic inspection (for example `GET /flow-b/calendar-gaps` or an equivalent non-mutating `POST` under `/flow-b/`). Unauthenticated requests MUST be rejected. Responses MUST be JSON and MUST NOT include secrets.

The endpoint MUST NOT call LinkedIn, DeepSeek, ComfyUI, or Git APIs, MUST NOT enable LinkedIn publication, and MUST NOT introduce n8n Execute Command usage (ADR-0001: n8n → worker HTTP only).

#### Scenario: Unauthenticated detect is rejected

- **WHEN** a client calls the gap-detect endpoint without valid worker authentication
- **THEN** the request is rejected and no gap result payload is returned

#### Scenario: Authenticated detect returns structured result

- **WHEN** an authenticated client calls the gap-detect endpoint
- **THEN** the worker returns JSON including gaps or no-gap status, target ISO week, and operator timezone used

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
