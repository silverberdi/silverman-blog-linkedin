## ADDED Requirements

### Requirement: Queued generated companion image lifecycle move

When ComfyUI generates `blog-posts/queued/<source_slug>.png` during Flow A execution, lifecycle completion MUST discover that companion PNG beside the queued Markdown and move it with the Markdown to `blog-posts/processed/`.

Campaign metadata MUST record `queued_image_relative_path` when the generated PNG exists at queue time and `processed_image_relative_path` after successful move.

Logical `source_slug`, `public_slug`, `source_content_sha256`, generated-image metadata, and public asset handoff metadata MUST be preserved across the move.

Partial-move recovery semantics MUST apply when Markdown moves but image move fails (`physical_move_state=partial`, `recovery_classification=repair_required`).

#### Scenario: Generated queued PNG moves to processed with Markdown

- **WHEN** Flow A completes scheduling for a campaign whose queued source is `blog-posts/queued/01-example.md` and ComfyUI generated `blog-posts/queued/01-example.png`
- **THEN** lifecycle completion moves both files to `blog-posts/processed/`, no copy remains in `blog-posts/queued/`, and metadata records processed image path

#### Scenario: No Markdown or PNG remains in ready or queued after success

- **WHEN** lifecycle completion succeeds after queue acceptance and generation
- **THEN** neither the Markdown nor the generated PNG remains under `blog-posts/ready/` or `blog-posts/queued/`

## MODIFIED Requirements

### Requirement: Successful lifecycle completion moves companion image when present

When `complete_flow_a_source_lifecycle` is called and the companion PNG exists beside the queued source Markdown (including ComfyUI-generated `blog-posts/queued/<source_slug>.png`), the PNG MUST be moved to `blog-posts/processed/` (same basename unless collision handling applies), and `processed_image_relative_path` MUST be recorded in the result.

When no companion PNG exists, lifecycle completion MUST proceed with Markdown only and `processed_image_relative_path` MUST be null.

#### Scenario: Successful lifecycle completion moves companion image when present

- **WHEN** `complete_flow_a_source_lifecycle` is called and the companion PNG exists beside the queued source Markdown
- **THEN** the PNG is moved to `blog-posts/processed/` (same basename unless collision handling applies), and `processed_image_relative_path` is recorded in the result

#### Scenario: Generated image discovered at completion time

- **WHEN** companion PNG was created in `blog-posts/queued/` during publish but `queued_image_relative_path` was not set at queue acceptance
- **THEN** lifecycle completion discovers the PNG beside queued Markdown and moves it to processed
