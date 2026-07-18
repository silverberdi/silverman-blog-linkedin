## ADDED Requirements

### Requirement: Concurrent image paths re-check reusable assets before ComfyUI

On concurrent or repeated `publish_blog_post` / image-ensure paths for the same source post, the worker MUST re-check reusable image locations immediately before invoking ComfyUI:

- active-folder sibling PNG beside the active Markdown, and
- public checkout `assets/images/<public_slug>.png` when configured

When either location already provides a reusable readable asset, the worker MUST NOT call ComfyUI, MUST record a skipped/reuse outcome consistent with existing handoff metadata fields, and MUST NOT overwrite an existing readable public asset solely because a concurrent generation attempt also entered the image path.

Flow A connector executions that lost execution claim contention MUST NOT reach ComfyUI for the losing attempt (claim gate owns that prevention).

#### Scenario: Repeated publish with existing public asset skips ComfyUI

- **WHEN** a publish/image path runs and `assets/images/<public_slug>.png` already exists as a readable regular file
- **THEN** ComfyUI is not called and generation status reflects skipped/reuse

#### Scenario: Asset appears before provider call skips ComfyUI

- **WHEN** a reusable public or active-folder PNG becomes present after an earlier check but before the ComfyUI provider call
- **THEN** the worker skips ComfyUI and does not overwrite the reusable public asset

#### Scenario: Claim contention prevents a second ComfyUI attempt via connector

- **WHEN** a concurrent calendar Flow A execution fails with `flow_a_execution_already_claimed`
- **THEN** that execution does not invoke ComfyUI for the contested campaign
