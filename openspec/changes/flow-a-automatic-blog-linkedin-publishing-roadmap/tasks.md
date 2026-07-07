## 1. Umbrella Planning Artifacts (this change)

- [x] 1.1 Review and approve `proposal.md` — Flow A motivation, goals, non-goals, child change list
- [x] 1.2 Review and approve `design.md` — lifecycle, architecture, Flow A vs Flow B, dependency order
- [x] 1.3 Review and approve `specs/flow-a-automatic-publishing/spec.md` — target requirements
- [x] 1.4 Run `openspec validate flow-a-automatic-blog-linkedin-publishing-roadmap --strict` and fix any issues
- [ ] 1.5 Keep umbrella active while child changes are implemented; archive only after Flow A child changes are completed/validated or the roadmap is superseded (separate `/opsx-archive` when ready — not part of implementation)

> **Note:** Sections 2–9 are **child OpenSpec changes** tracked by this umbrella. Do not implement them under `/opsx-apply` for this change. Each slice gets its own change via `/opsx-propose`.

## Roadmap Progress

| # | Child change | Status | Canonical outputs |
|---|--------------|--------|-------------------|
| 1 | `editorial-canon-and-linkedin-distribution-strategy` | **completed** (archived) | Spec: `openspec/specs/editorial-canon/spec.md`; artifact: `content-strategy/silverman-editorial-system.md`; commit `ae3eb43` |
| 2 | `flow-a-lifecycle-and-duplicate-prevention` | **completed** (archived) | Spec: `openspec/specs/flow-a-lifecycle/spec.md`; worker: `src/silverman_blog_linkedin/campaign_lifecycle.py`; commit `aa48e6c` |
| 3 | `ready-post-editorial-validation` | **completed** (archived) | Spec: `openspec/specs/ready-post-editorial-validation/spec.md`; worker: `src/silverman_blog_linkedin/ready_post_validation.py`; tests: `tests/test_ready_post_validation.py` |
| 4 | `worker-blog-publishing-endpoint` | **completed** (archived) | Spec: `openspec/specs/worker-blog-publishing-endpoint/spec.md`; endpoint `POST /publish-blog-post`; service `src/silverman_blog_linkedin/blog_publish_flow.py`; HTTP `src/silverman_blog_linkedin/main.py`; tests `tests/test_blog_publish_flow.py`; commit `c9a0cb2` feat(flow-a): add blog publishing endpoint |
| 5 | `linkedin-derivative-package-generation` | **completed** (archived) | Spec: `openspec/specs/linkedin-derivative-package-generation/spec.md`; endpoint `POST /generate-linkedin-package`; service `src/silverman_blog_linkedin/linkedin_package_flow.py`; tests `tests/test_linkedin_package_generation.py` |
| 6 | `linkedin-distribution-scheduling-model` | **completed** (archived) | Spec: `openspec/specs/linkedin-distribution-scheduling-model/spec.md`; endpoint `POST /schedule-linkedin-distribution`; service `src/silverman_blog_linkedin/linkedin_distribution_schedule.py`; tests `tests/test_linkedin_distribution_scheduling.py`; commit `53708eb` |
| 7 | `n8n-flow-a-blog-publish-orchestration` | **completed** (archived) | Spec: `openspec/specs/n8n-flow-a-blog-publish-orchestration/spec.md`; Workflow: `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json`; tests: `tests/test_n8n_flow_a_publish_workflow.py` |
| 8 | `linkedin-publication-integration` | **deferred** | LinkedIn API publish; depends on integration constraints |

The umbrella remains **active**. Slices 1–7 are **completed** (archived); slice 8 is **deferred**.

## 2. Child Change: editorial-canon-and-linkedin-distribution-strategy

**Status:** **completed** (archived). Canonical spec: `openspec/specs/editorial-canon/spec.md`. Canonical artifact: `content-strategy/silverman-editorial-system.md`. Commit: `ae3eb43` docs(editorial): add Silverman editorial canon.

**Propose with:** `/opsx-propose editorial-canon-and-linkedin-distribution-strategy`

- [ ] 2.1 Create `content-strategy/silverman-editorial-system.md` with all required sections from design.md
- [ ] 2.2 Encode Flow A vs Flow B policy table in the artifact
- [ ] 2.3 Define operational cadence, audience, objective, CTA, and non-redundancy rules
- [ ] 2.4 Document anti-AI-writing rules (strong for generated content; blocking vs warning for user blog input)
- [ ] 2.5 Document how worker validation and prompts load the artifact
- [ ] 2.6 Add tests or lint that required sections exist

**Depends on:** umbrella approval

## 3. Child Change: flow-a-lifecycle-and-duplicate-prevention

**Status:** **completed** (archived). Canonical spec: `openspec/specs/flow-a-lifecycle/spec.md`. Worker module: `src/silverman_blog_linkedin/campaign_lifecycle.py`. Commit: `aa48e6c` feat(flow-a): add lifecycle metadata foundation.

**Propose with:** `/opsx-propose flow-a-lifecycle-and-duplicate-prevention`

- [ ] 3.1 Define `metadata/campaigns/<campaign-id>.json` schema
- [ ] 3.2 Implement lifecycle state machine transitions
- [ ] 3.3 Define idempotency keys for blog, draft, and publish slots
- [ ] 3.4 Define file-move vs mark-processed/mark-error behavior (avoid premature folder binding)
- [ ] 3.5 Ensure metadata excludes `markdown_content` and `generated_draft_content`
- [ ] 3.6 Add tests for state transitions and duplicate-prevention keys

**Depends on:** 2 (policy fields); umbrella. Foundational for slices 4–8.

## 4. Child Change: ready-post-editorial-validation

**Status:** **completed** (archived). Canonical spec: `openspec/specs/ready-post-editorial-validation/spec.md`. Worker module: `src/silverman_blog_linkedin/ready_post_validation.py`. Tests: `tests/test_ready_post_validation.py`.

**Propose with:** `/opsx-propose ready-post-editorial-validation`

- [x] 4.1 Implement `validate_ready_post()` library entry point (HTTP endpoint deferred to slice 7 orchestration)
- [x] 4.2 Validate `source_slug` and derived `public_slug` per umbrella slug rules
- [x] 4.3 Apply editorial rules from `silverman-editorial-system.md` (blocking vs warnings for anti-AI on user input)
- [x] 4.4 Return structured `ReadyPostValidationResult` (`ok`, `errors[]`, `warnings[]`, `campaign_id`, metadata fields)
- [x] 4.5 On failure: mark metadata-only error state via lifecycle metadata; physical file moves remain deferred to a later orchestration/operations slice
- [x] 4.6 Add unit and integration tests for validation scenarios (including canonical slug example)

**Depends on:** 2, 3 (may develop closely with lifecycle in parallel)

## 5. Child Change: worker-blog-publishing-endpoint

**Status:** **completed** (archived). Canonical spec: `openspec/specs/worker-blog-publishing-endpoint/spec.md`. Endpoint `POST /publish-blog-post`; service `src/silverman_blog_linkedin/blog_publish_flow.py`; HTTP `src/silverman_blog_linkedin/main.py`; tests `tests/test_blog_publish_flow.py`. Commit: `c9a0cb2` feat(flow-a): add blog publishing endpoint.

**Proposed with:** `/opsx-propose worker-blog-publishing-endpoint`

- [x] 5.1 Implement `POST /publish-blog-post` wrapping GitHub Pages CLI bridge
- [x] 5.2 Support dry-run and apply modes via request body
- [x] 5.3 Return publish-confirmed `source_public_url`, `source_slug`, `public_slug`, `publication_date`
- [x] 5.4 Implement idempotent `already_published` response
- [x] 5.5 Add HTTP tests; document n8n request/response contract

**Depends on:** umbrella (slug/URL rules); 2, 3 recommended

## 6. Child Change: linkedin-derivative-package-generation

**Status:** **completed** (archived). Canonical spec: `openspec/specs/linkedin-derivative-package-generation/spec.md`. Endpoint `POST /generate-linkedin-package`; service `src/silverman_blog_linkedin/linkedin_package_flow.py`; tests `tests/test_linkedin_package_generation.py`.

**Applied with:** `/opsx-apply linkedin-derivative-package-generation`

**Archived with:** `/opsx-archive linkedin-derivative-package-generation`

- [x] 6.1 Implement `POST /generate-linkedin-package` (multi-variant)
- [x] 6.2 Require publish-confirmed `source_public_url` for Flow A CTAs
- [x] 6.3 Apply anti-AI-writing rules strongly to generated variants
- [x] 6.4 Link variants to `campaign_id` in metadata
- [x] 6.5 Idempotent per `source_content_sha256` + `variant` + `flow_a`
- [x] 6.6 Add tests for package structure and fidelity rules

**Depends on:** 2, 3; 5 for confirmed URL

## 7. Child Change: linkedin-distribution-scheduling-model

**Status:** **completed** (archived). Canonical spec: `openspec/specs/linkedin-distribution-scheduling-model/spec.md`. Endpoint `POST /schedule-linkedin-distribution`; service `src/silverman_blog_linkedin/linkedin_distribution_schedule.py`; tests `tests/test_linkedin_distribution_scheduling.py`.

**Applied with:** `/opsx-apply linkedin-distribution-scheduling-model`

**Archived with:** `/opsx-archive linkedin-distribution-scheduling-model`

- [x] 7.1 Implement scheduling logic applying editorial distribution strategy (`flow_a_staggered` default)
- [x] 7.2 Persist per-variant `scheduled_at_utc` and `publish_state` (`pending` until API slice)
- [x] 7.3 Enforce cadence spacing and anti-simultaneous rules (variants staggered, ≥3 calendar days)
- [x] 7.4 Expose `POST /schedule-linkedin-distribution`
- [x] 7.5 Add tests for cadence, idempotency, and eligibility in `tests/test_linkedin_distribution_scheduling.py`

**Depends on:** 2, 3, 5 (linkedin-derivative-package-generation)

## 8. Child Change: n8n-flow-a-blog-publish-orchestration

**Status:** **completed** (archived). Canonical spec: `openspec/specs/n8n-flow-a-blog-publish-orchestration/spec.md`. Workflow: `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json`; tests: `tests/test_n8n_flow_a_publish_workflow.py`.

**Proposed with:** `/opsx-propose n8n-flow-a-blog-publish-orchestration`

**Applied with:** `/opsx-apply n8n-flow-a-blog-publish-orchestration`

**Archived with:** `/opsx-archive n8n-flow-a-blog-publish-orchestration`

- [x] 8.1 Extend or add n8n workflow JSON for Flow A full pipeline
- [x] 8.2 Chain: health → validate → publish → confirm URL → generate package → schedule
- [x] 8.3 HTTP-only; no Execute Command, filesystem, or direct LLM nodes
- [x] 8.4 Keep `"active": false` in export
- [x] 8.5 Update README and lightweight workflow validation tests
- [ ] 8.6 Manual trigger end-to-end test on Ubuntu server

**Depends on:** 4, 5, 6, 7

## 9. Child Change: linkedin-publication-integration (deferred)

**Status:** **deferred** — LinkedIn API publish; depends on credentials, API surface, and rate-limit constraints.

**Propose with:** `/opsx-propose linkedin-publication-integration` when integration constraints are documented

- [ ] 9.1 Document LinkedIn API credentials, rate limits, override policy
- [ ] 9.2 Implement worker endpoint for scheduled LinkedIn publish (automatic per Flow A policy)
- [ ] 9.3 Idempotent publish per campaign/variant/schedule slot
- [ ] 9.4 Update n8n workflow for publish step when schedule matures
- [ ] 9.5 Define rollback and manual override behavior

**Depends on:** 7; API constraints clarified. Implements deferred LinkedIn API publish; not immediate on generation.

## 10. Flow A Completion Verification (after child changes 2–8)

- [ ] 10.1 Place test blog post in `blog-posts/ready/` and run Flow A workflow manually
- [ ] 10.2 Verify validation, publish, confirmed URL, package, and scheduling metadata (`publish_state` `pending` until slice 9)
- [ ] 10.3 Re-run workflow and confirm no duplicate blog or LinkedIn artifacts
- [ ] 10.4 Verify error visibility for intentional failure cases (missing PNG, invalid public slug)
- [ ] 10.5 Confirm Flow B content cannot enter Flow A path
- [ ] 10.6 Run full test suite and `openspec validate --all --strict`
