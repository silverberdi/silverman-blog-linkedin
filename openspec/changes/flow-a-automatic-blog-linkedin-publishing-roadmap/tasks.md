## 1. Umbrella Planning Artifacts (this change)

- [x] 1.1 Review and approve `proposal.md` — Flow A motivation, goals, non-goals, child change list
- [x] 1.2 Review and approve `design.md` — lifecycle, architecture, Flow A vs Flow B, dependency order
- [x] 1.3 Review and approve `specs/flow-a-automatic-publishing/spec.md` — target requirements
- [x] 1.4 Run `openspec validate flow-a-automatic-blog-linkedin-publishing-roadmap --strict` and fix any issues
- [x] 1.5 Flow A Core complete — umbrella **ready to archive** (slice 8 deferred to follow-up change; archive via `/opsx-archive` when operator confirms)

> **Note:** Sections 2–10 are **child OpenSpec changes** tracked by this umbrella. Implementation was done under each child change's own `/opsx-apply`. Slice 8 is **not** part of umbrella closure.

## Roadmap Progress — Flow A Core Complete (2026-07)

| # | Child change | Status | Canonical outputs |
|---|--------------|--------|-------------------|
| 1 | `editorial-canon-and-linkedin-distribution-strategy` | **completed** (archived) | Spec: `openspec/specs/editorial-canon/spec.md`; artifact: `content-strategy/silverman-editorial-system.md`; commit `ae3eb43` |
| 2 | `flow-a-lifecycle-and-duplicate-prevention` | **completed** (archived) | Spec: `openspec/specs/flow-a-lifecycle/spec.md`; worker: `campaign_lifecycle.py`; commit `aa48e6c` |
| 3 | `ready-post-editorial-validation` | **completed** (archived) | Spec: `openspec/specs/ready-post-editorial-validation/spec.md`; worker: `ready_post_validation.py`; tests: `tests/test_ready_post_validation.py` |
| 4 | `worker-blog-publishing-endpoint` | **completed** (archived) | Spec: `openspec/specs/worker-blog-publishing-endpoint/spec.md`; endpoint `POST /publish-blog-post`; commit `c9a0cb2` |
| 5 | `linkedin-derivative-package-generation` | **completed** (archived) | Spec: `openspec/specs/linkedin-derivative-package-generation/spec.md`; endpoint `POST /generate-linkedin-package` |
| 6 | `linkedin-distribution-scheduling-model` | **completed** (archived) | Spec: `openspec/specs/linkedin-distribution-scheduling-model/spec.md`; endpoint `POST /schedule-linkedin-distribution`; commit `53708eb` |
| 7 | `n8n-flow-a-blog-publish-orchestration` | **completed** (archived) | Spec: `openspec/specs/n8n-flow-a-blog-publish-orchestration/spec.md`; workflow inactive, 26 nodes; commit `962ba2f` |
| — | `flow-a-deployment-readiness-and-smoke-test` | **completed** (archived) | Spec: `openspec/specs/flow-a-deployment-readiness-and-smoke-test/spec.md`; worker smoke + evidence; commit `1457af0` |
| 8 | `linkedin-publication-integration` | **deferred** (follow-up change) | LinkedIn API publish; propose **after** umbrella archive |

**Flow A Core boundary:** Generated LinkedIn artifacts → scheduled distribution metadata → `publish_state: pending` → campaign state `distribution_scheduled`. No LinkedIn API, no n8n activation, no cron/webhook triggers.

**Umbrella status:** **Ready to archive.** Slice 8 is explicitly **out of scope** for umbrella closure.

## 2. Child Change: editorial-canon-and-linkedin-distribution-strategy

**Status:** **completed** (archived). Canonical spec: `openspec/specs/editorial-canon/spec.md`. Canonical artifact: `content-strategy/silverman-editorial-system.md`. Commit: `ae3eb43`.

- [x] 2.1 Create `content-strategy/silverman-editorial-system.md` with all required sections from design.md
- [x] 2.2 Encode Flow A vs Flow B policy table in the artifact
- [x] 2.3 Define operational cadence, audience, objective, CTA, and non-redundancy rules
- [x] 2.4 Document anti-AI-writing rules (strong for generated content; blocking vs warning for user blog input)
- [x] 2.5 Document how worker validation and prompts load the artifact
- [x] 2.6 Add tests or lint that required sections exist

## 3. Child Change: flow-a-lifecycle-and-duplicate-prevention

**Status:** **completed** (archived). Canonical spec: `openspec/specs/flow-a-lifecycle/spec.md`. Worker module: `campaign_lifecycle.py`. Commit: `aa48e6c`.

- [x] 3.1 Define `metadata/campaigns/<campaign-id>.json` schema
- [x] 3.2 Implement lifecycle state machine transitions
- [x] 3.3 Define idempotency keys for blog, draft, and publish slots
- [x] 3.4 Define file-move vs mark-processed/mark-error behavior (avoid premature folder binding)
- [x] 3.5 Ensure metadata excludes `markdown_content` and `generated_draft_content`
- [x] 3.6 Add tests for state transitions and duplicate-prevention keys

## 4. Child Change: ready-post-editorial-validation

**Status:** **completed** (archived). Canonical spec: `openspec/specs/ready-post-editorial-validation/spec.md`. Worker module: `ready_post_validation.py`.

- [x] 4.1 Implement `validate_ready_post()` library entry point (HTTP endpoint deferred to slice 7 orchestration)
- [x] 4.2 Validate `source_slug` and derived `public_slug` per umbrella slug rules
- [x] 4.3 Apply editorial rules from `silverman-editorial-system.md` (blocking vs warnings for anti-AI on user input)
- [x] 4.4 Return structured `ReadyPostValidationResult` (`ok`, `errors[]`, `warnings[]`, `campaign_id`, metadata fields)
- [x] 4.5 On failure: mark metadata-only error state via lifecycle metadata; physical file moves remain deferred to a later orchestration/operations slice
- [x] 4.6 Add unit and integration tests for validation scenarios (including canonical slug example)

## 5. Child Change: worker-blog-publishing-endpoint

**Status:** **completed** (archived). Canonical spec: `openspec/specs/worker-blog-publishing-endpoint/spec.md`. Commit: `c9a0cb2`.

- [x] 5.1 Implement `POST /publish-blog-post` wrapping GitHub Pages CLI bridge
- [x] 5.2 Support dry-run and apply modes via request body
- [x] 5.3 Return publish-confirmed `source_public_url`, `source_slug`, `public_slug`, `publication_date`
- [x] 5.4 Implement idempotent `already_published` response
- [x] 5.5 Add HTTP tests; document n8n request/response contract

## 6. Child Change: linkedin-derivative-package-generation

**Status:** **completed** (archived). Canonical spec: `openspec/specs/linkedin-derivative-package-generation/spec.md`.

- [x] 6.1 Implement `POST /generate-linkedin-package` (multi-variant)
- [x] 6.2 Require publish-confirmed `source_public_url` for Flow A CTAs
- [x] 6.3 Apply anti-AI-writing rules strongly to generated variants
- [x] 6.4 Link variants to `campaign_id` in metadata
- [x] 6.5 Idempotent per `source_content_sha256` + `variant` + `flow_a`
- [x] 6.6 Add tests for package structure and fidelity rules

## 7. Child Change: linkedin-distribution-scheduling-model

**Status:** **completed** (archived). Canonical spec: `openspec/specs/linkedin-distribution-scheduling-model/spec.md`. Commit: `53708eb`.

- [x] 7.1 Implement scheduling logic applying editorial distribution strategy (`flow_a_staggered` default)
- [x] 7.2 Persist per-variant `scheduled_at_utc` and `publish_state` (`pending` until API slice)
- [x] 7.3 Enforce cadence spacing and anti-simultaneous rules (variants staggered, ≥3 calendar days)
- [x] 7.4 Expose `POST /schedule-linkedin-distribution`
- [x] 7.5 Add tests for cadence, idempotency, and eligibility in `tests/test_linkedin_distribution_scheduling.py`

## 8. Child Change: n8n-flow-a-blog-publish-orchestration

**Status:** **completed** (archived). Canonical spec: `openspec/specs/n8n-flow-a-blog-publish-orchestration/spec.md`. Commit: `962ba2f`.

- [x] 8.1 Extend or add n8n workflow JSON for Flow A full pipeline
- [x] 8.2 Chain: health → validate → publish → confirm URL → generate package → schedule
- [x] 8.3 HTTP-only; no Execute Command, filesystem, or direct LLM nodes
- [x] 8.4 Keep `"active": false` in export
- [x] 8.5 Update README and lightweight workflow validation tests
- [x] 8.6 End-to-end verification on Ubuntu server (worker smoke `OVERALL: PASS`; n8n workflow inactive, 26 nodes)

## 9. Child Change: linkedin-publication-integration (deferred — follow-up change)

**Status:** **deferred** — NOT part of umbrella closure. Propose as a **new OpenSpec change** after umbrella archive.

**Propose with:** `/opsx-propose linkedin-publication-integration` when integration constraints are documented

- [ ] 9.1 Document LinkedIn API credentials, rate limits, override policy
- [ ] 9.2 Implement worker endpoint for scheduled LinkedIn publish (automatic per Flow A policy)
- [ ] 9.3 Idempotent publish per campaign/variant/schedule slot
- [ ] 9.4 Update n8n workflow for publish step when schedule matures
- [ ] 9.5 Define rollback and manual override behavior

**Depends on:** Flow A Core complete (slices 1–7 + OV). Implements deferred LinkedIn API publish; not immediate on generation.

## 10. Child Change: flow-a-deployment-readiness-and-smoke-test (operational verification)

**Status:** **completed** (archived). Canonical spec: `openspec/specs/flow-a-deployment-readiness-and-smoke-test/spec.md`. Commit: `1457af0`.

- [x] 10.1 Review planning artifacts (proposal, design, spec, tasks)
- [x] 10.2 Implement Phase 0 deployment readiness script/command
- [x] 10.3 Implement Phases 1–2 smoke checks and document Phases 3–4 operator procedures
- [x] 10.4 Add unit tests for readiness parsers/checks
- [x] 10.5 Document phased smoke workflow in README or `docs/deployment/`
- [x] 10.6 Run validation and manual Phase 0 dry-run on target environment

## 11. Flow A Core Completion Verification (umbrella checklist)

Verified on Ubuntu server (2026-07):

- [x] 11.1 Canonical test post in `blog-posts/ready/`; worker smoke exercises full pipeline
- [x] 11.2 Validation, publish (`blog_published`, public image adopted), confirmed URL, package (`derivatives_generated`), scheduling metadata (`publish_state: pending`, state `distribution_scheduled`)
- [x] 11.3 Re-run confirms idempotent worker responses; no duplicate blog or LinkedIn artifacts
- [x] 11.4 Error visibility verified during smoke development (reconciliation, skip reasons, diagnostics)
- [x] 11.5 Flow B blocked from Flow A path (policy + worker guards)
- [x] 11.6 Full test suite and `openspec validate --all --strict` pass

## 12. Umbrella Closure (this change)

- [x] 12.1 Update proposal/design/tasks to mark Flow A Core complete through all in-scope child changes
- [x] 12.2 Explicitly defer `linkedin-publication-integration` to follow-up change outside umbrella closure
- [x] 12.3 Document Flow A Core boundary: generated artifacts + scheduled metadata + `publish_state: pending`
- [x] 12.4 Confirm no LinkedIn API, n8n activation, or cron/webhook triggers in closure scope
- [x] 12.5 Run `openspec validate flow-a-automatic-blog-linkedin-publishing-roadmap --strict`
- [x] 12.6 Run `openspec validate --all --strict` and `pytest -q`

> **Next operator action:** Archive this umbrella with `/opsx-archive flow-a-automatic-blog-linkedin-publishing-roadmap` (not done in this apply). Then propose `linkedin-publication-integration` as slice 8 follow-up when ready.
