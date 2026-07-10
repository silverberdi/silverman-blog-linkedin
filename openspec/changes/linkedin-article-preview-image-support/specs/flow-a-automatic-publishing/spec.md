## ADDED Requirements

### Requirement: LinkedIn article preview metadata at package generation (deferred publication slice)

Flow A `POST /generate-linkedin-package` SHALL record article preview metadata via canonical spec `linkedin-article-preview-image-support` so campaigns expose `public_image_url` and related fields at derivative generation time.

This metadata slice MUST NOT call LinkedIn APIs, require LinkedIn tokens, or change distribution scheduling semantics.

LinkedIn publication-time visual preview (OG strategy, Images API upload, `publish_linkedin_due_variants()` integration) is **deferred** to a separate future change and MUST NOT be implemented under `linkedin-article-preview-image-support`.

Package generation MUST continue to satisfy Flow A Core boundaries: no `publish_state` writes and no automatic LinkedIn publication.

#### Scenario: Package generation records preview metadata

- **WHEN** Flow A package generation succeeds for a campaign with publish-confirmed `source_public_url`
- **THEN** campaign metadata and HTTP response include `article_preview` per `linkedin-article-preview-image-support`

#### Scenario: Publication-time preview deferred

- **WHEN** this change is applied
- **THEN** `publish_linkedin_due_variants()` does not gain preview strategy or image upload behavior

#### Scenario: Scheduling unchanged

- **WHEN** package generation records article preview metadata
- **THEN** `POST /schedule-linkedin-distribution` eligibility and behavior are unchanged
