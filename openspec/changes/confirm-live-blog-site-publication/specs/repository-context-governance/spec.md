## MODIFIED Requirements

### Requirement: Canonical glossary

The repository MUST maintain `docs/GLOSSARY.md` defining at minimum: Flow A, Flow A Core, `distribution_scheduled`, `flow_a_complete`, operational smoke pass, fully unattended Flow A, Flow B, `ready`/`queued`/`processed`/`error`, blog handoff, blog files written, blog Git publication, live-site confirmation, site published/live, LinkedIn publication states (`pending`, `queued`, `publishing`, `published`), active OpenSpec change, canonical spec, archived change, reconciliation, and idempotency.

#### Scenario: Campaign state vs product complete

- **WHEN** documentation uses `flow_a_complete`
- **THEN** `docs/GLOSSARY.md` defines it strictly as a campaign lifecycle metadata state and distinguishes it from fully unattended Flow A or site published/live

#### Scenario: Blog handoff vs publication layers

- **WHEN** documentation describes blog output or publication progress
- **THEN** `docs/GLOSSARY.md` separates worker file writes (blog handoff), guarded worker Git commit/push (`blog_git_publication`), optional worker HTTP live-site confirmation (`blog_live_site_publication`), and site published/live as public HTTP reachability

#### Scenario: Git push alone is not site published/live

- **WHEN** documentation describes a successful `blog_git_publication.status` `pushed` without live-site confirmation
- **THEN** `docs/GLOSSARY.md` states that Git push evidence alone MUST NOT be described as site published/live

#### Scenario: Confirmed site published/live

- **WHEN** documentation claims site published/live after US-002 validation
- **THEN** `docs/GLOSSARY.md` defines site published/live as public HTTP reachability that MAY be recorded by `blog_live_site_publication.status` `confirmed` (when enabled, opted in, and operationally validated) or by operator manual verification

#### Scenario: LinkedIn implementation vs API validation

- **WHEN** documentation describes LinkedIn capabilities
- **THEN** `docs/GLOSSARY.md` distinguishes implemented package/scheduling support from operationally validated real LinkedIn API publication
