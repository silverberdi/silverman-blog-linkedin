## ADDED Requirements

### Requirement: Real-ready unattended path remains independent of LinkedIn publication

Flow A n8n orchestration of real ready-folder content through Manual Trigger or Schedule Trigger (publish → package → schedule) MUST remain valid evidence for unattended Flow A without calling LinkedIn publication APIs. Real-ready success for BL-005 is documented under capability `flow-a-unattended-e2e-validation`.

#### Scenario: Real ready Manual success without LinkedIn publication endpoints

- **WHEN** Flow A Manual Trigger processes a single real ready post through publish → package → schedule
- **THEN** orchestration does not call `/queue-linkedin-publication`, `/publish-linkedin-due-variants`, or `/cancel-linkedin-publication`

#### Scenario: Real ready Schedule success without LinkedIn publication endpoints

- **WHEN** Flow A Schedule Trigger processes a single real ready post through publish → package → schedule
- **THEN** orchestration does not call LinkedIn publication endpoints and does not require `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` for Flow A success
