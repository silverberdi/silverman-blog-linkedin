## ADDED Requirements

### Requirement: Flow A blog Git publication layer (US-001)

Flow A SHALL support an optional blog Git publication layer that commits and pushes validated publication artifacts from the public checkout to the configured remote after successful blog handoff.

This layer advances **US-001** — validated publication artifacts are committed and pushed safely without manual Git intervention — when enabled, opted in, and operationally validated with real remote push evidence.

Blog handoff alone MUST continue to mean files written to the public checkout mount.

**US-002** — the pushed publication is reconciled against remote history and confirmed live on the public site — MUST remain out of scope for this layer.

US-002 concerns deferred to a follow-up change include: remote-history divergence reconciliation; equivalent commits after amend or rebase; cross-campaign duplicate detection; automatic fetch, pull, merge, or rebase; GitHub Pages deployment confirmation; live URL reachability.

Git publication MUST be invoked only through worker HTTP endpoints (ADR-0001), not n8n Execute Command.

Git publication MUST be reachable through both `POST /publish-blog-post` and `POST /editorial-calendar/execute-flow-a-due` with per-request `git_publication: true`.

**BL-001** MUST NOT be marked complete after this change. US-001 progress may be recorded separately when acceptance criteria are demonstrated.

#### Scenario: US-001 path without live-site confirmation

- **WHEN** Flow A publish completes with Git publication enabled, opted in, and push succeeds
- **THEN** campaign metadata records `blog_git_publication.status` `pushed` and operators can trace the remote commit, without the worker claiming HTTP reachability of `source_public_url`

#### Scenario: Handoff without Git remains valid

- **WHEN** Flow A publish completes with `git_publication` false or omitted
- **THEN** behavior matches pre-change blog handoff semantics and manual Git remains the operator path until Git publication is opted in

#### Scenario: Calendar execution supports Git opt-in

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=false` and `git_publication=true` while Git publication is enabled
- **THEN** the connector passes `git_publication` to `publish_blog_post` for eligible items

#### Scenario: US-002 concerns deferred

- **WHEN** Git push fails due to remote divergence after successful handoff
- **THEN** the worker returns overall `status: partial` with structured `blog_git_publication_push_failed` and does not implement fetch/pull/rebase in this change

#### Scenario: BL-001 not complete after US-001

- **WHEN** US-001 acceptance criteria are demonstrated with real remote push evidence
- **THEN** progress may be recorded for US-001 only and BL-001 remains open pending US-002
