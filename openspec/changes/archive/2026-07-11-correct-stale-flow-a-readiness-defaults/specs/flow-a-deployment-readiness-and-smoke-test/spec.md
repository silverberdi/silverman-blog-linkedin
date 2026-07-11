## MODIFIED Requirements

### Requirement: Repository state verification

The readiness command SHALL verify repository state independently of the running worker.

#### Scenario: Repo HEAD equals origin/main and expected commits present

- **WHEN** the configured repo path is a git checkout, `git rev-parse HEAD` equals `git rev-parse origin/main`, and each configured expected commit (default: `88cd5bc`, `96519c3`, `9dba064`) is an ancestor of HEAD
- **THEN** Phase 0 reports pass for repository state checks

#### Scenario: Required Flow A files exist in checkout

- **WHEN** Phase 0 runs against the configured repo path
- **THEN** it verifies the Flow A file manifest exists, including at minimum `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json`, `content-strategy/silverman-editorial-system.md`, and the worker modules for publish, package generation, distribution scheduling, and ready-post validation

## ADDED Requirements

### Requirement: Documented default expected-commit milestones

The readiness script default expected commits SHALL represent the current operational capability floor documented in operator deployment docs and cross-referenced from `docs/CURRENT-STATE.md`, not obsolete slice-7-only assumptions. `DEFAULT_EXPECTED_COMMITS` MUST NOT be conflated with `last_verified_baseline` in CURRENT-STATE — the latter is a timestamped verification snapshot; the former gates validated capabilities via ancestry.

Default milestones MUST be:

| Short SHA | Meaning |
|-----------|---------|
| `88cd5bc` | Flow A calendar completion archived (core operational validation floor) |
| `96519c3` | Guarded blog Git publication automation (US-001) |
| `9dba064` | Live-site confirmation and Git reconciliation (US-002) |

Operators MAY override defaults with repeatable `--expected-commit` flags without changing script behavior for other checks.

#### Scenario: Default milestones documented in script

- **WHEN** a maintainer inspects `scripts/flow_a_readiness.py`
- **THEN** `DEFAULT_EXPECTED_COMMITS` matches the three milestones above and includes a brief comment describing each milestone purpose

#### Scenario: Operator overrides defaults for bisect or fork

- **WHEN** an operator runs `python scripts/flow_a_readiness.py --expected-commit <sha>` one or more times
- **THEN** Phase 0 uses only the supplied commits for ancestry checks and does not merge them with `DEFAULT_EXPECTED_COMMITS`

#### Scenario: Readiness defaults distinct from last verified baseline

- **WHEN** a contributor reads `docs/CURRENT-STATE.md` after this change is applied
- **THEN** `last_verified_baseline` (timestamped snapshot) and `DEFAULT_EXPECTED_COMMITS` (capability milestones) are documented as separate concepts and `DEFAULT_EXPECTED_COMMITS` does not include docs-only archive commits such as `615091c` unless a future dedicated change adds them
