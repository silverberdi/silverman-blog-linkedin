## ADDED Requirements

### Requirement: Publication enablement independent of Flow A schedule success

Flow A n8n orchestration success through Schedule Trigger or Manual Trigger (ready-folder path through publish → package → schedule) MUST NOT require `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` and MUST NOT call LinkedIn publication APIs.

Operators MUST treat LinkedIn API publication as a separately approved step governed by `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` and LinkedIn publication endpoints — documented under capability `flow-a-linkedin-publication-guard` for US-011 acceptance.

#### Scenario: Schedule success without LinkedIn publication enabled

- **WHEN** the Flow A workflow completes a clean empty-ready or schedule no-op while LinkedIn publication is disabled
- **THEN** orchestration stops successfully without calling LinkedIn publication endpoints

#### Scenario: Workflow does not depend on LinkedIn enablement flag

- **WHEN** the Flow A workflow export and worker HTTP chain are inspected for LinkedIn publication enablement coupling
- **THEN** no workflow step requires `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` to be `true` for publish/package/schedule success
