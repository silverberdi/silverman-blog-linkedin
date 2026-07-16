## 1. Operator criteria artifact (US-016)

- [x] 1.1 Create `docs/operations/linkedin-variant-quality-criteria.md` with sections covering: purpose/scope (US-016 only), relationship to US-015 supervision window (criteria guide optional supervision — not mandatory approval), normative default variant mapping table (audience lens + objective + differentiation checks for `executive-recruiter`, `technical-architect`, `engineering-leadership`, `short-provocative`), quality criteria (source fidelity, voice/style, anti-AI rewrite/blocking posture for derivatives, CTA/URL rules, independent readability), differentiation criteria (`#no-redundancy-rules` sibling uniqueness), supervision-window checklist, criteria-failure vs technical-block vs deferred-states table, and explicit out-of-scope (US-017, BL-007, console, queue-time enforcement).
- [x] 1.2 Cross-link criteria doc to `docs/operations/linkedin-variant-review-policy.md`, `docs/GLOSSARY.md`, `docs/product/user-stories.md` US-016, and `content-strategy/silverman-editorial-system.md` anchors `#audience-map`, `#linkedin-derivative-package`, `#no-redundancy-rules`, `#anti-ai-writing-rules`, `#linkedin-distribution-strategy`, `#flow-a-vs-flow-b`.
- [x] 1.3 Update `docs/operations/linkedin-variant-review-policy.md` deferred/out-of-scope sections only: remove US-016 from deferred list; add pointer to criteria doc; preserve all US-015 strategy-driven and supervision substance unchanged.

## 2. Glossary alignment

- [x] 2.1 Update `docs/GLOSSARY.md` with terms for **variant publication objective** (distinct from voice `tone`) and **criteria failure** (editorial guidance during supervision, not a new `publish_state`) — cross-link criteria doc.
- [x] 2.2 Ensure glossary does not equate criteria failure with mandatory review or contradict US-015 supervision window language.

## 3. Minimal metadata alignment (design D6)

- [x] 3.1 Add `objective` (and optionally `audience_lens`) to `DEFAULT_VARIANT_EDITORIAL_MAP` in `src/silverman_blog_linkedin/linkedin_package_flow.py` per canon `#linkedin-derivative-package` variant definitions.
- [x] 3.2 Include `objective` in `_variant_metadata_entry()` output; keep existing `audience` and `tone` fields.
- [x] 3.3 Extend `_variant_summary()` to surface `objective` when present.
- [x] 3.4 Verify git diff does **not** include `linkedin_publication_flow.py`, BL-007 WIP paths, n8n publish-pending workflows, or deploy publish-pending scripts.

## 4. Presence / contract checks

- [x] 4.1 Add `tests/test_linkedin_variant_quality_criteria.py` mirroring `tests/test_linkedin_variant_review_policy.py`: file exists, required headings/phrases (quality criteria, differentiation, audience, objective, supervision checklist, criteria failure, US-015 cross-link, US-017 deferred, canon anchors).
- [x] 4.2 Extend package metadata tests to assert `objective` is present in generated `variants[]` entries for default variant IDs.
- [x] 4.3 Run targeted tests only (`test_linkedin_variant_quality_criteria.py` and touched package metadata tests); no LinkedIn API integration tests.

## 5. Status and product progress (after ACs demonstrated)

- [x] 5.1 Update `docs/CURRENT-STATE.md` to record US-016 / BL-006 story 2 as criteria defined (docs/spec + optional metadata); state US-017 enforcement and BL-006 closure remain open; do not claim BL-006 closed or BL-007 started.
- [x] 5.2 Update `docs/product/user-stories.md` US-016 acceptance criteria and status only when demonstrated; leave US-017 unchecked.
- [x] 5.3 Update `docs/product/progress-checklist.md` for US-016 demonstrated items only; keep BL-006 open until US-017 complete.
- [x] 5.4 Do not update `docs/RUNTIME-STATE.md` (no live flag changes in this change).

## 6. Explicit non-touch / regression guardrails

- [x] 6.1 Verify no new worker routes, no n8n LinkedIn publish workflow changes, and no change to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` defaults or US-011 guard semantics.
- [x] 6.2 Verify US-015 policy strategy-driven publication and optional supervision sections are unchanged in substance (cross-link edits only).
- [x] 6.3 Run `git diff --check` on touched paths.

## 7. Business validation (US-016)

- [x] 7.1 Walk US-016 acceptance criteria against criteria doc and metadata: (1) quality/differentiation criteria defined, (2) each default variant associated with audience + objective visible to operator, (3) outcome understandable, (4) criteria-failure vs blocked/deferred states clear, (5) no unintended change to US-015 / Flow A / publication guards.
- [x] 7.2 Confirm BL-006 remains open with US-017 still pending; confirm criteria do not add mandatory approval gate or BL-007 queue eligibility changes beyond US-015.
