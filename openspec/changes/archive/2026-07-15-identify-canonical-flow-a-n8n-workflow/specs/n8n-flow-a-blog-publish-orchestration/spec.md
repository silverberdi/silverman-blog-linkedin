# n8n-flow-a-blog-publish-orchestration (delta)

## ADDED Requirements

### Requirement: Canonical workflow identity documented in README

The repository README Flow A section SHALL document the canonical workflow identity table:

| Attribute | Value |
|-----------|-------|
| Export path | `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` |
| Workflow name | `Silverman Blog LinkedIn Flow A Publish` |
| Stable n8n id | `silvermanFlowAPublish01` |
| Node count | `26` |
| Distinction from Flow B | `silverman-blog-linkedin-draft-generation.json` is draft review only |

#### Scenario: README identifies canonical Flow A workflow

- **WHEN** an operator reads README Flow A orchestration section
- **THEN** they find canonical path, stable id, and explicit note that Flow B draft workflow is not Flow A orchestration

### Requirement: Proposed execution frequency documented without activation

The repository README and deployment documentation SHALL document the **proposed** Flow A n8n scheduled execution frequency:

- Daily at 09:00 UTC (Schedule Trigger to be added in US-010 activation change).
- Editorial calendar remains the policy authority for due items; n8n scheduling is the orchestration timer proposal only.

Documentation MUST state that the repository export remains `"active": false` and contains no Cron, Webhook, or Schedule Trigger nodes until US-010.

#### Scenario: README labels frequency as proposed not active

- **WHEN** an operator reads proposed execution frequency in documentation
- **THEN** text explicitly states scheduling is not enabled and points to US-010 for activation

#### Scenario: Export unchanged for schedule triggers

- **WHEN** this change is applied under US-009 scope
- **THEN** `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` does not contain Cron, Webhook, or Schedule Trigger node types

### Requirement: US-009 identification defers activation

This capability change under US-009 MUST NOT modify the requirement that exported workflow JSON keeps `"active": false` or add production scheduling triggers. Activation and concurrency controls belong to US-010.

#### Scenario: US-009 apply does not activate export

- **WHEN** US-009 implementation completes
- **THEN** workflow export `active` field remains `false` and no schedule trigger nodes are added
