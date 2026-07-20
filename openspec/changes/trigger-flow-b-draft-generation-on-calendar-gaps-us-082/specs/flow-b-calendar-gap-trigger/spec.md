## ADDED Requirements

### Requirement: Gap trigger starts Flow B drafts when enabled and gaps exist

The worker SHALL provide an authenticated gap-trigger orchestrator that, when effective `gap_trigger_enabled` is true, the operator-local weekly run window is satisfied, and next-week gap detect reports one or more actionable gaps, starts Flow B topic discovery and blog draft generation into `blog-posts/pending-approval/` for at most N drafts where N is ≤ effective `max_drafts_per_weekly_run` from `load_gap_operator_settings()` (documented default **2**).

Trigger MUST pass gap context (`target_week` ISO week string and `empty_days[]` local dates) into discovery and draft generation. Trigger MUST NOT write under `blog-posts/ready/`, MUST NOT invoke Flow A publish/package/schedule, MUST NOT approve or promote drafts, and MUST NOT call the LinkedIn publication API or mark variants LinkedIn API published.

#### Scenario: Enabled with gaps produces pending-approval drafts

- **WHEN** effective settings have `gap_trigger_enabled=true`, the operator-local clock is inside the weekly run window, and detect returns one or more actionable gaps for the target week
- **THEN** the trigger runs discovery and draft generation capped by `max_drafts_per_weekly_run`
- **AND** new Markdown + image packages appear under `blog-posts/pending-approval/` with gap context recorded when provided
- **AND** no blog publish, LinkedIn API publish, or promote-to-`ready/` side effects occur

#### Scenario: Batch size respects max_drafts_per_weekly_run

- **WHEN** effective `max_drafts_per_weekly_run` is `2` and a gap trigger run succeeds
- **THEN** at most 2 draft packages are created for that batch

### Requirement: Clean no-ops for disabled, outside window, no gap, and idempotent week

The gap trigger MUST perform a clean no-op (no new draft packages) when any of the following hold:

- effective `gap_trigger_enabled` is false
- the operator-local weekday/time is outside the configured weekly run window (`weekly_run_local_day` / `weekly_run_local_time` through end of that local day)
- detect reports no actionable gaps for the target week
- an idempotent batch already exists for key `flow_b_gap_week:{operator_tz}:{YYYY}-W{ww}` in status `in_progress` or `completed`

Default settings MUST keep `gap_trigger_enabled=false` (fail-closed). Saving gap operator settings MUST NOT by itself start a trigger run.

#### Scenario: Disabled trigger is a no-op

- **WHEN** effective `gap_trigger_enabled` is false and an authenticated client calls the gap-trigger endpoint
- **THEN** the response indicates a disabled no-op
- **AND** no files are created under `blog-posts/pending-approval/`

#### Scenario: Outside weekly window is a no-op

- **WHEN** `gap_trigger_enabled` is true but the operator-local day/time is outside the configured weekly run window
- **THEN** the response indicates an outside-window no-op
- **AND** no draft packages are created

#### Scenario: No-gap week is a no-op

- **WHEN** `gap_trigger_enabled` is true, the window is satisfied, and detect returns no actionable gaps
- **THEN** the response indicates a no-gap no-op
- **AND** no draft packages are created
- **AND** no idempotency batch is claimed for that week

#### Scenario: Idempotent ISO-week re-run is a no-op

- **WHEN** a completed gap-trigger batch already exists for `flow_b_gap_week:{operator_tz}:{YYYY}-W{ww}`
- **AND** an authenticated client calls gap trigger again for the same operator timezone and ISO week
- **THEN** the response indicates an idempotent no-op
- **AND** no additional draft packages are created for that week

### Requirement: ISO-week idempotency batch durability

The worker MUST persist gap-trigger batch records keyed by `flow_b_gap_week:{operator_tz}:{YYYY}-W{ww}` using the editorial Postgres database shared with gap operator settings (`SILVERMAN_CALENDAR_DATABASE_URL`; `memory://` acceptable in tests). Batch status MUST distinguish at least `in_progress`, `completed`, and `failed`.

- `in_progress` and `completed` MUST no-op subsequent runs for that key
- `failed` MUST allow a later retry to re-claim and run
- Stale `in_progress` beyond a documented reclaim TTL MUST be reclaimable so a crash cannot permanently block the week

#### Scenario: Failed batch may retry

- **WHEN** a prior gap-trigger batch for the ISO-week key is stored as `failed`
- **AND** gaps still exist and enablement/window allow a run
- **THEN** a new authenticated trigger call MAY run discovery/draft generation again
- **AND** on success the batch status becomes `completed`

#### Scenario: Completed batch blocks duplicate drafts

- **WHEN** a batch for the ISO-week key is stored as `completed`
- **THEN** a subsequent trigger call returns an idempotent no-op without creating drafts

### Requirement: Authenticated gap-trigger HTTP endpoint

The worker SHALL expose authenticated `POST /flow-b/gap-trigger` (or equivalent under `/flow-b/`). Unauthenticated requests MUST be rejected. Responses MUST be JSON, MUST include a clear status suitable for orchestration, and MUST NOT include secrets.

Optional `dry_run=true` MUST evaluate enablement, window, detect, and idempotency and return the would-be outcome without claiming a batch or writing draft packages.

Optional diagnostic clock override (`now_utc`) MAY be accepted for tests. A diagnostic `force_window` flag MAY bypass only the local day/time window and MUST NOT bypass `gap_trigger_enabled`.

The endpoint MUST NOT introduce n8n Execute Command usage (ADR-0001: n8n → worker HTTP only).

#### Scenario: Unauthenticated trigger is rejected

- **WHEN** a client calls the gap-trigger endpoint without valid worker authentication
- **THEN** the request is rejected and no draft packages are created

#### Scenario: Dry-run does not write drafts or claim batch

- **WHEN** an authenticated client calls gap trigger with `dry_run=true` under conditions that would otherwise trigger
- **THEN** the response indicates the would-be triggered outcome
- **AND** no files are created under `blog-posts/pending-approval/`
- **AND** no completed idempotency batch is persisted for that week

### Requirement: n8n Schedule orchestration export stays inactive

The repository SHALL include an n8n workflow export that uses Schedule (and optional Manual) trigger nodes to call the worker gap-trigger HTTP endpoint with worker API-key authentication. The export MUST use HTTP Request only for worker invocation and MUST NOT use Execute Command nodes. The exported workflow MUST have `active: false` until an operator explicitly activates it after validation.

#### Scenario: Repo n8n export is HTTP-only and inactive

- **WHEN** an operator inspects the Flow B gap-trigger n8n workflow export in the repository
- **THEN** the workflow is marked `active: false`
- **AND** worker invocation uses HTTP Request to the gap-trigger endpoint
- **AND** no Execute Command node is present

### Requirement: US-082 scope excludes re-implementation and auto-publish

This capability MUST consume existing settings (`flow-b-gap-operator-settings`), detect (`flow-b-calendar-gap-detect`), discovery (`flow-b-topic-discovery`), and draft generation (`flow-b-blog-draft-generation`) without re-implementing them. It MUST leave drafts for approve/reject (`flow-b-blog-draft-approval`) and promote/spill A (`flow-b-blog-draft-promotion`). It MUST NOT enable `gap_trigger_enabled` by default, MUST NOT auto-publish blog or LinkedIn without Flow A guards, and MUST NOT mark LinkedIn API published.

#### Scenario: Trigger does not skip the blog gate

- **WHEN** a successful gap-trigger run creates draft packages
- **THEN** those packages remain under `blog-posts/pending-approval/` awaiting operator approve/promote
- **AND** Flow A publish paths are not invoked by the trigger itself

#### Scenario: Detect and settings contracts remain authoritative

- **WHEN** gap trigger runs
- **THEN** it loads knobs via `load_gap_operator_settings()` and gap days via the existing detect capability
- **AND** it does not redefine gap as remaining density capacity under US-040K max 2
