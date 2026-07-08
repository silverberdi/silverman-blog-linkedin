## ADDED Requirements

### Requirement: LinkedIn article preview image support (deferred slice)

After OpenSpec change `comfyui-blog-image-generation` is archived and canonical blog images are available on the public site, Flow A SHALL support LinkedIn article/link preview image support via canonical spec `linkedin-article-preview-image-support` when the operator enables preview configuration.

This slice is **deferred** and MUST NOT be implemented until `comfyui-blog-image-generation` is validated and archived.

When enabled, LinkedIn publish-due MUST use blog image metadata and `source_public_url` to preserve visual link preview quality instead of publishing degraded plain text with URL only.

Preview behavior MUST remain disabled by default (`SILVERMAN_LINKEDIN_PREVIEW_ENABLED=false`) until the operator explicitly enables it.

#### Scenario: Preview deferred until blog images archived

- **WHEN** `comfyui-blog-image-generation` is not archived
- **THEN** Flow A documentation and implementation MUST NOT include LinkedIn preview image runtime behavior

#### Scenario: Preview enabled after dependency complete

- **WHEN** `comfyui-blog-image-generation` is archived, blog posts have canonical images on the public site, and operator enables preview
- **THEN** Flow A LinkedIn publish-due MUST use `linkedin-article-preview-image-support` strategies for visual preview when preview is enabled

#### Scenario: Preview disabled preserves text-only publish

- **WHEN** preview is not enabled
- **THEN** Flow A LinkedIn publication continues text-only behavior per `linkedin-publication-integration`
