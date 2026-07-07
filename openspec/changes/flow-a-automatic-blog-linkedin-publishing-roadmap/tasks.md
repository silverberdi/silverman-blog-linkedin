## 1. Umbrella Planning Artifacts (this change)

- [x] 1.1 Review and approve `proposal.md` — Flow A motivation, goals, non-goals, child change list
- [x] 1.2 Review and approve `design.md` — lifecycle, architecture, Flow A vs Flow B, dependency order
- [x] 1.3 Review and approve `specs/flow-a-automatic-publishing/spec.md` — target requirements
- [x] 1.4 Run `openspec validate flow-a-automatic-blog-linkedin-publishing-roadmap --strict` and fix any issues
- [ ] 1.5 Keep umbrella active while child changes are implemented; archive only after Flow A child changes are completed/validated or the roadmap is superseded (separate `/opsx-archive` when ready — not part of implementation)

> **Note:** Sections 2–9 are **future child OpenSpec changes**, not tasks for this umbrella. Do not implement them under `/opsx-apply` for this change. Each slice gets its own change via `/opsx-propose`.

## 2. Child Change: editorial-canon-and-linkedin-distribution-strategy

**Propose with:** `/opsx-propose editorial-canon-and-linkedin-distribution-strategy`

- [ ] 2.1 Create `content-strategy/silverman-editorial-system.md` with all required sections from design.md
- [ ] 2.2 Encode Flow A vs Flow B policy table in the artifact
- [ ] 2.3 Define operational cadence, audience, objective, CTA, and non-redundancy rules
- [ ] 2.4 Document anti-AI-writing rules (strong for generated content; blocking vs warning for user blog input)
- [ ] 2.5 Document how worker validation and prompts load the artifact
- [ ] 2.6 Add tests or lint that required sections exist

**Depends on:** umbrella approval

## 3. Child Change: flow-a-lifecycle-and-duplicate-prevention

**Propose with:** `/opsx-propose flow-a-lifecycle-and-duplicate-prevention`

- [ ] 3.1 Define `metadata/campaigns/<campaign-id>.json` schema
- [ ] 3.2 Implement lifecycle state machine transitions
- [ ] 3.3 Define idempotency keys for blog, draft, and publish slots
- [ ] 3.4 Define file-move vs mark-processed/mark-error behavior (avoid premature folder binding)
- [ ] 3.5 Ensure metadata excludes `markdown_content` and `generated_draft_content`
- [ ] 3.6 Add tests for state transitions and duplicate-prevention keys

**Depends on:** 2 (policy fields); umbrella. Foundational for slices 4–8.

## 4. Child Change: ready-post-editorial-validation

**Propose with:** `/opsx-propose ready-post-editorial-validation`

- [ ] 4.1 Implement `POST /validate-ready-post` (or equivalent) on worker
- [ ] 4.2 Validate `source_slug` and derived `public_slug` per umbrella slug rules
- [ ] 4.3 Apply editorial rules from `silverman-editorial-system.md` (blocking vs warnings for anti-AI on user input)
- [ ] 4.4 Return structured JSON (`status`, `errors[]`, `warnings[]`, `campaign_id`)
- [ ] 4.5 On failure: move to `blog-posts/error/` or mark error per lifecycle child spec
- [ ] 4.6 Add unit and integration tests for validation scenarios (including canonical slug example)

**Depends on:** 2, 3 (may develop closely with lifecycle in parallel)

## 5. Child Change: worker-blog-publishing-endpoint

**Propose with:** `/opsx-propose worker-blog-publishing-endpoint`

- [ ] 5.1 Implement `POST /publish-blog-post` wrapping GitHub Pages CLI bridge
- [ ] 5.2 Support dry-run and apply modes via request body
- [ ] 5.3 Return publish-confirmed `source_public_url`, `source_slug`, `public_slug`, `publication_date`
- [ ] 5.4 Implement idempotent `already_published` response
- [ ] 5.5 Add HTTP tests; document n8n request/response contract

**Depends on:** umbrella (slug/URL rules); 2, 3 recommended

## 6. Child Change: linkedin-derivative-package-generation

**Propose with:** `/opsx-propose linkedin-derivative-package-generation`

- [ ] 6.1 Implement `POST /generate-linkedin-package` (multi-variant)
- [ ] 6.2 Require publish-confirmed `source_public_url` for Flow A CTAs
- [ ] 6.3 Apply anti-AI-writing rules strongly to generated variants
- [ ] 6.4 Link variants to `campaign_id` in metadata
- [ ] 6.5 Idempotent per `source_content_sha256` + `variant` + `flow_a`
- [ ] 6.6 Add tests for package structure and fidelity rules

**Depends on:** 2, 3; 5 for confirmed URL

## 7. Child Change: linkedin-distribution-scheduling-model

**Propose with:** `/opsx-propose linkedin-distribution-scheduling-model`

- [ ] 7.1 Implement scheduling logic applying editorial distribution strategy
- [ ] 7.2 Persist per-variant `schedule_at` and `publish_state` (`pending` until API slice)
- [ ] 7.3 Enforce cadence spacing and non-redundancy rules (variants not simultaneous)
- [ ] 7.4 Expose `POST /schedule-linkedin-package` (or equivalent)
- [ ] 7.5 Add tests for cadence and redundancy prevention

**Depends on:** 2, 3, 6

## 8. Child Change: n8n-flow-a-blog-publish-orchestration

**Propose with:** `/opsx-propose n8n-flow-a-blog-publish-orchestration`

- [ ] 8.1 Extend or add n8n workflow JSON for Flow A full pipeline
- [ ] 8.2 Chain: health → validate → publish → confirm URL → generate package → schedule
- [ ] 8.3 HTTP-only; no Execute Command, filesystem, or direct LLM nodes
- [ ] 8.4 Keep `"active": false` in export
- [ ] 8.5 Update README and lightweight workflow validation tests
- [ ] 8.6 Manual trigger end-to-end test on Ubuntu server

**Depends on:** 4, 5, 6, 7

## 9. Child Change: linkedin-publication-integration (deferred)

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
