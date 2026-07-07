## Why

The Silverman Blog LinkedIn automation project has implemented foundational capabilities—worker HTTP endpoints, ready-folder scanning, LinkedIn draft generation, GitHub Pages publishing bridge, and an n8n orchestration workflow—but these pieces operate as disconnected steps with manual operator intervention and no unified editorial policy for automatic publication. Flow A (user-provided, pre-approved blog posts published automatically with a scheduled LinkedIn derivative package) requires a single organizing source of truth that defines lifecycle, policy boundaries, distribution strategy, and the child changes needed to complete end-to-end automation without re-litigating strategy in every slice.

## Goals

- Define Flow A as the automatic publishing path for user-provided blog posts after automated validation passes.
- Reserve Flow B (system-generated content requiring human review) as a distinct, deferred policy.
- Specify the canonical editorial artifact requirements that govern all generated text and publishing decisions.
- Decompose Flow A into implementable child OpenSpec changes with clear dependencies and non-overlapping scope.
- Establish target requirements, lifecycle states, idempotency rules, and success criteria for completed Flow A.
- Serve as the reference umbrella that future slices cite instead of re-deriving architecture.
- Record **Flow A Core Complete** when child slices 1–7 and operational verification (`flow-a-deployment-readiness-and-smoke-test`) are implemented, archived, and server-validated — with LinkedIn API publication explicitly deferred to a separate follow-up change (`linkedin-publication-integration`).
- Remain an active OpenSpec change until explicitly archived after Flow A Core closure; slice 8 is **not** part of umbrella closure scope.

## Non-Goals

- Implementing worker code, n8n workflow JSON changes, or new HTTP endpoints in this change.
- Creating the actual `content-strategy/silverman-editorial-system.md` file (only specifying its intended path and required sections).
- Flow B content generation, review workflows, or approval bypass.
- Runtime LinkedIn API integration in this umbrella (Flow A *policy* allows automatic LinkedIn publication after validation and scheduling; actual API publish is deferred to `linkedin-publication-integration` until credentials, API, and rate-limit constraints are known).
- n8n Execute Command, SSH nodes, direct filesystem access from n8n, or direct LLM calls from n8n.
- Archiving this change before Flow A Core child changes and operational verification are complete, validated, and archived.
- Including `linkedin-publication-integration` (slice 8) in umbrella closure — that slice is deferred to a **new follow-up OpenSpec change** after umbrella archive.
- Committing/pushing repository changes as part of this umbrella update.

## What Changes

- Add an umbrella OpenSpec change `flow-a-automatic-blog-linkedin-publishing-roadmap` with proposal, design, tasks, and spec delta. This change remains **active** as the organizing roadmap while child changes (sections 2–9 in `tasks.md`) are proposed, applied, and archived; it is not archived immediately after stakeholder approval of planning artifacts.
- Introduce a new capability spec `flow-a-automatic-publishing` describing target end-state requirements for Flow A.
- Document the full Flow A lifecycle: input → validation → blog publish → confirmed public URL → LinkedIn derivative package → distribution scheduling (variants staggered per strategy, not simultaneous) → metadata and state tracking → error handling and duplicate prevention. **Flow A Core stops here** with generated LinkedIn artifacts, scheduled distribution metadata, and `publish_state: pending`. LinkedIn API publication is deferred to `linkedin-publication-integration` (slice 8), a separate follow-up change outside this umbrella closure.
- Document slug terminology (`source_slug` vs `public_slug`) and validation rules aligned with `github-pages-blog-publishing`.
- Document Flow A vs Flow B policy distinction and automatic-vs-approval-required rules.
- Define the canonical editorial artifact at `content-strategy/silverman-editorial-system.md` (path and required contents only).
- Enumerate child changes/slices with dependencies, scope boundaries, and sequencing.
- Define guardrails (HTTP-only n8n, worker as filesystem/LLM boundary, idempotent publication, metadata traceability without storing full generated content).
- Define success criteria for **Flow A Core Complete** (through scheduling metadata) and for the deferred LinkedIn API end-state (slice 8).

No runtime code, workflow JSON, worker endpoints, or editorial file content is modified by this change.

## Capabilities

### New Capabilities

- `flow-a-automatic-publishing`: End-to-end automatic publishing for user-provided blog posts and their LinkedIn derivative package—lifecycle, policy (Flow A vs Flow B), editorial canon requirements, distribution strategy, metadata/state model, idempotency, error handling, and success criteria.

### Modified Capabilities

<!-- No existing spec requirements change in this umbrella. Child changes will modify n8n-worker-orchestration-flow, github-pages-blog-publishing, deepseek-linkedin-draft-generation, and related specs as needed. -->

## Impact

- **OpenSpec**: New change directory under `openspec/changes/flow-a-automatic-blog-linkedin-publishing-roadmap/`; new target spec `flow-a-automatic-publishing` (delta until archived).
- **Documentation**: Future child changes will update `docs/context/`, `docs/workflows/`, and create `content-strategy/silverman-editorial-system.md`.
- **Worker API**: No changes now; child change `worker-blog-publishing-endpoint` will add HTTP endpoint wrapping the existing CLI bridge.
- **n8n**: No workflow JSON changes now; child change `n8n-flow-a-blog-publish-orchestration` will extend orchestration.
- **Editorial folders**: Lifecycle state model may extend metadata under `metadata/campaigns/`, `metadata/runs/`, and LinkedIn folder usage; no folder layout changes in this umbrella.
- **Dependencies**: Child changes depend on this umbrella for policy and sequencing. **Flow A Core is complete** (slices 1–7 + operational verification archived). The umbrella is **ready to archive**. Slice 8 (`linkedin-publication-integration`) is deferred to a new follow-up change. See design.md and tasks.md.
