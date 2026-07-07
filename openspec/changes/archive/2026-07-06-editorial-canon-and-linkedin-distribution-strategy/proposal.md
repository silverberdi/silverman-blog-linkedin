## Why

The active Flow A umbrella change `flow-a-automatic-blog-linkedin-publishing-roadmap` defines lifecycle, policy, and child sequencing for automatic blog-to-LinkedIn publishing, but worker validation, LLM prompt assembly, and distribution scheduling have no operational editorial source of truth. Hardcoded prompt fragments in `linkedin_prompt.py` and implicit editorial assumptions cannot enforce Flow A pre-approval rules, anti-AI-writing constraints, variant non-redundancy, or staggered LinkedIn distribution. This child change is the first slice under the umbrella and creates the canonical artifact that all subsequent Flow A children MUST reference.

## Goals

- Create `content-strategy/silverman-editorial-system.md` as the single operational editorial canon for blog rules, LinkedIn derivative generation, and distribution strategy.
- Encode Flow A vs Flow B publication policy, editorial-quality anti-AI rules (pattern-based, not authorship detection), audience targeting, CTA behavior, cadence/spacing, and no-redundancy rules in enforceable form.
- Define machine-readable section anchors so future worker validation, prompt assembly, and scheduling logic can locate rules reliably.
- Introduce the `editorial-canon` capability spec with testable requirements aligned to the umbrella's canonical artifact requirements.
- Remain scoped to documentation and section validation only—no worker endpoints, n8n workflows, or scheduling implementation.

## Non-Goals

- Implementing worker code, HTTP endpoints, or LLM prompt loading from the canon (deferred to `ready-post-editorial-validation`, `linkedin-derivative-package-generation`, and related children).
- Implementing n8n workflow JSON changes, LinkedIn API publishing, or Flow B content generation.
- Modifying the umbrella change `flow-a-automatic-blog-linkedin-publishing-roadmap` or archiving it.
- Archiving this child change after planning artifact creation.
- Committing or pushing repository changes.

## What Changes

- Add child OpenSpec change `editorial-canon-and-linkedin-distribution-strategy` under the active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`.
- Create `content-strategy/silverman-editorial-system.md` with 17 required operational sections (purpose, positioning, audiences, pillars, boundaries, blog rules, LinkedIn package rules, distribution strategy, no-redundancy, anti-AI-writing, voice/style, CTA, Flow A vs Flow B policy, machine-readable anchors, validation/prompt usage rules, and examples).
- Add new capability spec `editorial-canon` defining artifact path, required sections, anchor conventions, and consumption rules for validation vs prompt vs scheduling.
- Add tests or lint verifying required sections and anchors exist in the canonical artifact.
- Update README or docs only if needed to point operators at the canon path.

No runtime worker behavior, n8n exports, or metadata schema changes are included in this change.

## Capabilities

### New Capabilities

- `editorial-canon`: Canonical editorial artifact at `content-strategy/silverman-editorial-system.md`—required sections, machine-readable anchors, Flow A vs Flow B policy, blog and LinkedIn derivative rules, distribution strategy dimensions, editorial-quality anti-AI rules (targeting AI-sounding patterns, not authorship detection), and consumption rules for future validation, prompt assembly, and scheduling logic.

### Modified Capabilities

<!-- No existing main specs are modified. Flow A target requirements remain in the umbrella spec `flow-a-automatic-publishing`; this child implements the editorial artifact the umbrella references. -->

## Impact

- **Umbrella reference**: This change MUST cite `flow-a-automatic-blog-linkedin-publishing-roadmap` for Flow A policy, lifecycle, child sequencing, and publication strategy. The umbrella remains active.
- **OpenSpec**: New change directory `openspec/changes/editorial-canon-and-linkedin-distribution-strategy/` with proposal, design, tasks, and `specs/editorial-canon/spec.md`.
- **Documentation**: New `content-strategy/silverman-editorial-system.md` (primary deliverable).
- **Tests**: New section-presence test or lint script for required anchors (no worker endpoint tests).
- **Future children** (not implemented here): `ready-post-editorial-validation`, `linkedin-derivative-package-generation`, `linkedin-distribution-scheduling-model`, and Flow B review flows will load applicable canon sections.
- **Worker API**: No endpoint changes.
- **n8n**: No workflow changes.
