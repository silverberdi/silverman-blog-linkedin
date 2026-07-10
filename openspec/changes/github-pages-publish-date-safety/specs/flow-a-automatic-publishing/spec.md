## MODIFIED Requirements

### Requirement: Publish-confirmed public URL

After successful blog publication, the system SHALL record a publish-confirmed `source_public_url` in campaign metadata.

The confirmed URL MUST follow `https://silverman.pro/YYYY/MM/DD/<public-slug>/` (or configured `site_base_url`) using the **intended URL date** and public slug from the publish result, including when publish date safety adjusts the Jekyll frontmatter `date` and adds an explicit `permalink`.

A merely derived URL from frontmatter and filename BEFORE publish MUST NOT be stored or passed to LinkedIn generation as publish-confirmed.

LinkedIn derivative generation for Flow A MUST use publish-confirmed `source_public_url` for CTA behavior when the blog is live.

#### Scenario: Confirmed URL after publish

- **WHEN** blog publish completes successfully for source slug `01-why-i-did-not-start-with-the-database` with intended URL date `2026-07-06` and public slug `why-i-did-not-start-with-the-database`
- **THEN** metadata records `source_public_url` `https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/`

#### Scenario: Confirmed URL preserves intended path when date adjusted

- **WHEN** blog publish completes successfully for intended URL date `2026-07-10`, public slug `deferring-is-not-avoiding-it-can-be-architecture`, and publish date safety adjusts the Jekyll `date` to an earlier execution timestamp
- **THEN** metadata records `source_public_url` `https://silverman.pro/2026/07/10/deferring-is-not-avoiding-it-can-be-architecture/`

#### Scenario: Derivative generation blocked without confirmed URL

- **WHEN** blog publish has not completed and no publish-confirmed URL exists
- **THEN** Flow A LinkedIn package generation MUST NOT include a live-blog CTA claiming a publish-confirmed URL
