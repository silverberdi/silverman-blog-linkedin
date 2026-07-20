## ADDED Requirements

### Requirement: Pending-approval paths are not publishable

`publish_blog_post` MUST reject `source_relative_path` values under `blog-posts/pending-approval/` (including path variants that resolve into that folder). Unapproved Flow B drafts MUST NOT be accepted as Flow A publish input. The operation MUST fail closed with a stable structured error (for example `blog_publish_pending_approval_not_allowed`) and MUST NOT write public repo files, invoke LinkedIn API publish, or treat pending-approval Markdown as a ready inbox source.

#### Scenario: Publish from pending-approval fails closed

- **WHEN** `publish_blog_post` is called with `source_relative_path` under `blog-posts/pending-approval/`
- **THEN** the operation fails with a stable pending-approval-not-allowed error
- **AND** no public repo files are written

#### Scenario: Unapproved draft is not Flow A publish input

- **WHEN** an unapproved Flow B draft exists only under `blog-posts/pending-approval/`
- **THEN** Flow A publish paths MUST NOT accept that draft as a ready source
- **AND** promotion to `blog-posts/ready/` (US-081) remains required before eligibility
