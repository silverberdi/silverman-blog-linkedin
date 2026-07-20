## MODIFIED Requirements

### Requirement: No publication or Flow A side effects

This capability MUST NOT auto-publish blog posts, invoke Flow A publish/package/schedule endpoints, create Flow A campaign lifecycle side effects, hand off to GitHub Pages git publication, or call LinkedIn API publish. Generated drafts MUST remain in `blog-posts/pending-approval/` until a separate approve/reject presentation capability (`flow-b-blog-draft-approval` / US-080) and, on approve, a separate promote capability (US-081) run. This capability MUST NOT enable LinkedIn API publication or modify `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

#### Scenario: No ready folder writes

- **WHEN** draft generation completes successfully
- **THEN** `blog-posts/ready/` gains no new files from this capability

#### Scenario: No Flow A publish invocation

- **WHEN** draft generation runs
- **THEN** Flow A publish, package, and schedule operations are not invoked

#### Scenario: No LinkedIn API publish

- **WHEN** draft generation runs successfully or unsuccessfully
- **THEN** LinkedIn API publication enablement remains governed solely by existing env guards

### Requirement: US-079 scope excludes approve, promote, trigger, and discovery contract changes

This capability MUST NOT implement blog approve/reject UI (US-080), promote-to-`ready/` (US-081), or gap trigger orchestration (US-082). Approve/reject presentation is owned by capability `flow-b-blog-draft-approval` (US-080) and MUST NOT be re-implemented inside this generation capability. It MUST NOT change the HTTP contracts of `flow-b-topic-discovery` (`POST /flow-b/discover-topics`), `flow-b-calendar-gap-detect` (`GET /flow-b/calendar-gaps`), or `flow-b-gap-operator-settings` (`GET`/`PUT /flow-b/gap-operator-settings`) except by consuming shared settings via `load_gap_operator_settings()`. Generated `pending-approval/` packages (Markdown + PNG + `.flow-b.json` sidecar fields including `topic_id`, discovery summary, optional gap context, and `status`) remain the read/update surface for US-080 list/approve/reject.

#### Scenario: Discover-topics contract unchanged

- **WHEN** this capability is implemented
- **THEN** `POST /flow-b/discover-topics` remains discovery-only with no draft filesystem writes

#### Scenario: No approve or trigger routes required

- **WHEN** this capability's requirements are evaluated
- **THEN** approve/promote and gap trigger endpoints are not required for US-079 completion

#### Scenario: Pending-approval packages are the US-080 surface

- **WHEN** draft generation writes a successful pending-approval package
- **THEN** the sibling `.flow-b.json` sidecar includes `status` and discovery fields suitable for later US-080 presentation
- **AND** generation itself does not perform approve or reject actions
