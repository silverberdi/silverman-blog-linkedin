## ADDED Requirements

### Requirement: Ready-path HTTP may invoke lifecycle completion

The Python entry point `complete_flow_a_source_lifecycle` MUST remain the sole filesystem lifecycle implementation used by authenticated HTTP ready-path completion (`POST /complete-flow-a-ready-path` per capability `flow-a-ready-path-completion`) after successful distribution scheduling on the ready-folder n8n path.

When invoked that way, lifecycle semantics MUST match this capability (including legacy `blog-posts/ready/` fallback). Calendar mutation MUST remain outside `complete_flow_a_source_lifecycle` itself and MUST be owned by the ready-path completion wrapper when requested.

#### Scenario: HTTP ready-path uses the same lifecycle entry point

- **WHEN** `POST /complete-flow-a-ready-path` runs for an eligible `distribution_scheduled` campaign whose Markdown is still under `blog-posts/ready/`
- **THEN** `complete_flow_a_source_lifecycle` performs the physical move to `blog-posts/processed/` and transitions campaign state to `flow_a_complete` on success

#### Scenario: Lifecycle entry point still does not write calendar.json

- **WHEN** `complete_flow_a_source_lifecycle` runs successfully
- **THEN** it does not itself modify `editorial-calendar/calendar.json` (calendar updates remain a separate ready-path completion concern)
