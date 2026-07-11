## MODIFIED Requirements

### Requirement: Flow A blog Git publication layer (US-001)

Flow A SHALL support an optional blog Git publication layer that commits and pushes validated publication artifacts from the public checkout to the configured remote after successful blog handoff.

This layer advances **US-001** — validated publication artifacts are committed and pushed safely without manual Git intervention — when enabled, opted in, and operationally validated with real remote push evidence.

Blog handoff alone MUST continue to mean files written to the public checkout mount.

Git publication MUST include remote reconciliation (fetch and fast-forward-only pull) and cross-campaign duplicate prevention per canonical spec `github-pages-git-publication`.

Git publication MUST be invoked only through worker HTTP endpoints (ADR-0001), not n8n Execute Command.

Git publication MUST be reachable through both `POST /publish-blog-post` and `POST /editorial-calendar/execute-flow-a-due` with per-request `git_publication: true`.

US-001 progress MAY be recorded when acceptance criteria are demonstrated. **BL-001** completion additionally requires **US-002** live-site confirmation per the **Flow A blog live-site confirmation layer (US-002)** requirement.

#### Scenario: US-001 path without live-site confirmation opt-in

- **WHEN** Flow A publish completes with Git publication enabled, opted in, and push succeeds without `live_site_confirmation: true`
- **THEN** campaign metadata records `blog_git_publication.status` `pushed` and the worker does not claim HTTP reachability of `source_public_url`

#### Scenario: Handoff without Git remains valid

- **WHEN** Flow A publish completes with `git_publication` false or omitted
- **THEN** behavior matches handoff-only semantics and no `git` operations run

#### Scenario: Calendar execution supports Git opt-in

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=false` and `git_publication=true` while Git publication is enabled
- **THEN** the connector passes `git_publication` to `publish_blog_post` for eligible items

#### Scenario: Remote divergence handled via fetch and ff-only

- **WHEN** Git publication runs and the local branch is behind remote after fetch
- **THEN** the worker attempts fast-forward-only reconciliation per `github-pages-git-publication` before push

#### Scenario: BL-001 not complete until US-002 demonstrated

- **WHEN** US-001 acceptance criteria are demonstrated with real remote push evidence but US-002 live-site confirmation is not operationally validated
- **THEN** progress may be recorded for US-001 only and BL-001 remains open

## ADDED Requirements

### Requirement: Flow A blog live-site confirmation layer (US-002)

Flow A SHALL support an optional live-site confirmation layer that HTTP-probes publish-confirmed `source_public_url` after successful Git publication.

This layer advances **US-002** — the pushed publication is confirmed reachable on the public site — when enabled, opted in, and operationally validated with real HTTP evidence.

Live-site confirmation MUST be implemented per canonical spec `blog-live-site-confirmation`.

Live-site confirmation MUST be reachable through both `POST /publish-blog-post` and `POST /editorial-calendar/execute-flow-a-due` with per-request `live_site_confirmation: true`.

When live-site confirmation succeeds with Git publication, campaign metadata MUST record `blog_live_site_publication.status` `confirmed`.

**BL-001** MAY be marked complete only when both US-001 and US-002 acceptance criteria are demonstrated with operational evidence.

#### Scenario: Full BL-001 path with live confirmation

- **WHEN** Flow A publish completes with Git publication and live-site confirmation enabled, opted in, push succeeds, and HTTP probe succeeds
- **THEN** campaign metadata records `blog_git_publication.status` `pushed` and `blog_live_site_publication.status` `confirmed`

#### Scenario: Calendar execution supports live confirmation opt-in

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=false`, `git_publication=true`, and `live_site_confirmation=true` while both features are enabled
- **THEN** the connector passes both flags to `publish_blog_post` for eligible items

#### Scenario: Push without live confirmation does not claim site live

- **WHEN** Git push succeeds but `live_site_confirmation` is false or omitted
- **THEN** the worker MUST NOT record `blog_live_site_publication.status` `confirmed` and MUST NOT claim site published/live beyond Git push evidence

#### Scenario: BL-001 complete after US-002 validation

- **WHEN** US-002 acceptance criteria are demonstrated with real live-site HTTP evidence
- **THEN** BL-001 completion outcome MAY be recorded in product progress artifacts
