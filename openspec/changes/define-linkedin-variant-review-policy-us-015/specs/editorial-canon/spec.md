## MODIFIED Requirements

### Requirement: Flow A vs Flow B publication policy

The artifact MUST explicitly encode Flow A and Flow B publication policy consistent with Flow A automatic publishing requirements and the LinkedIn variant review process:

- **Flow A (blog + package + schedule):** User-provided blog post in `blog-posts/ready/`; after automated validation passes, content is pre-approved for Flow A core; blog publish/handoff and LinkedIn derivative package generation and distribution scheduling MAY proceed automatically; no human approval is required for those Flow A core steps after validation.
- **Flow A (LinkedIn API queue/publish):** LinkedIn variants scheduled per `#linkedin-distribution-strategy` are expected to publish at their scheduled times when publication integration and enablement allow. Human review is **not mandatory** before LinkedIn API queue or publish. The operator MAY supervise variants during the `pending` pre-send window (edit, delay, cancel — mechanics deferred to US-017). Automated queue/publish MAY exist later (for example BL-007) for scheduled variants not operator-cancelled or deferred. Policy detail: `docs/operations/linkedin-variant-review-policy.md` (capability `linkedin-variant-review-process`).
- **Flow B:** System-generated ideas/drafts; not pre-approved; human review **required** before any publication; implementation deferred but policy MUST be encoded now.

The artifact MUST state that Flow B content MUST NOT enter Flow A automatic publish paths.

The artifact MUST NOT require mandatory per-variant human approval for Flow A LinkedIn API publication.

#### Scenario: Flow A core path documented without mandatory LinkedIn review

- **WHEN** an operator reviews `#flow-a-vs-flow-b`
- **THEN** the section states that Flow A requires no human approval after validation for blog publish, package, schedule, or LinkedIn API publication

#### Scenario: Flow A LinkedIn follows strategy with optional supervision

- **WHEN** an operator reviews `#flow-a-vs-flow-b`
- **THEN** the section states that Flow A LinkedIn variants publish per distribution strategy with an optional operator supervision window while `pending`, not a mandatory approval gate

#### Scenario: Flow B deferred but encoded

- **WHEN** an operator reviews `#flow-a-vs-flow-b`
- **THEN** the section states Flow B requires mandatory human approval before any publish and is deferred for implementation
