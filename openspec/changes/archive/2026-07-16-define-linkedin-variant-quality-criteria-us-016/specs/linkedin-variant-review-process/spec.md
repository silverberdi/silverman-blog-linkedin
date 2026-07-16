## ADDED Requirements

### Requirement: Operator-visible LinkedIn variant quality and differentiation criteria artifact

The repository MUST provide an operator-facing criteria document at `docs/operations/linkedin-variant-quality-criteria.md` that defines Flow A LinkedIn variant **quality** and **differentiation** criteria for US-016 (BL-006 story 2).

The criteria artifact MUST be understandable to the content operator without requiring worker source code or n8n workflow inspection.

The criteria artifact MUST answer: whether a variant is **good enough and distinct enough** to publish for its intended audience and objective during the optional supervision window defined by US-015.

The criteria artifact MUST cross-link at least: `docs/operations/linkedin-variant-review-policy.md` (US-015), `docs/GLOSSARY.md`, `docs/product/user-stories.md` US-016, and `content-strategy/silverman-editorial-system.md` anchors `#audience-map`, `#linkedin-derivative-package`, `#no-redundancy-rules`, `#anti-ai-writing-rules`, and `#linkedin-distribution-strategy`.

The criteria artifact MUST NOT contradict US-015 strategy-driven publication defaults or convert Flow A into mandatory per-variant approval.

#### Scenario: Criteria artifact exists for operators

- **WHEN** an operator opens `docs/operations/linkedin-variant-quality-criteria.md`
- **THEN** the document states it defines quality and differentiation criteria for Flow A LinkedIn variants during the optional supervision window

#### Scenario: Criteria is findable from product story

- **WHEN** an operator reads US-016 in `docs/product/user-stories.md` after this capability is implemented
- **THEN** US-016 points to `docs/operations/linkedin-variant-quality-criteria.md` as the demonstrated criteria outcome (or CURRENT-STATE does equivalent linking)

### Requirement: Default variant audience and objective association

The criteria artifact MUST include a normative mapping table for default variant IDs that associates each variant with:

- a **primary audience lens** (from `#audience-map`),
- a **publication objective** (from `#linkedin-derivative-package` objective definitions),
- and **differentiation checks** relative to sibling variants in the same package.

The mapping MUST cover at minimum: `executive-recruiter`, `technical-architect`, `engineering-leadership`, and `short-provocative`.

Campaign `variants[]` metadata produced at package generation MUST include `audience` and `objective` for each default variant entry so the association is visible in campaign JSON without opening draft files.

#### Scenario: Operator reads variant audience and objective mapping

- **WHEN** an operator reads the default variant mapping section
- **THEN** each of the four default variant IDs lists a primary audience lens and a publication objective distinct from the other variants

#### Scenario: Campaign metadata exposes objective

- **WHEN** an operator inspects `metadata/campaigns/<campaign-id>.json` after Flow A package generation
- **THEN** each `variants[]` entry includes `audience` and `objective` fields for the generated variant

### Requirement: Quality criteria for supervision-window evaluation

The criteria artifact MUST define quality checks for Flow A LinkedIn derivatives, including at minimum:

- **Source fidelity** — facts and thesis derive from the canonical blog only; no invented metrics, companies, or URLs.
- **Voice and style fit** — senior, practical tone per `#voice-and-style`; no engagement bait, hashtags, or emoji by default.
- **Anti-AI editorial patterns** — generated derivatives follow `#anti-ai-writing-rules` **rewrite/blocking** posture (documented as criteria; not Flow A blog warning posture).
- **CTA and URL rules** — CTA placement and `source_public_url` usage per `#cta-rules` and publish-confirmed URL requirements.
- **Independent readability** — each variant stands alone without requiring the blog opening.

#### Scenario: Operator evaluates source fidelity

- **WHEN** an operator reads the quality criteria section
- **THEN** the section states variants MUST NOT invent facts not present in the source blog

#### Scenario: Anti-AI posture for derivatives is stated

- **WHEN** an operator reads the quality criteria section
- **THEN** the section states generated LinkedIn derivatives use rewrite/blocking anti-AI editorial posture, distinct from Flow A user-blog warnings

### Requirement: Differentiation criteria across package siblings

The criteria artifact MUST define differentiation requirements across variants in the same package, aligned with `#no-redundancy-rules`:

- unique opening hook (first 1–2 sentences),
- distinct primary objective angle,
- varied structure and narrative arc,
- distinct CTA phrasing (same URL allowed),
- no duplicate variant text with only audience label changed.

The criteria artifact MUST include a supervision-window checklist derived from the normative mapping and differentiation rules.

#### Scenario: Operator verifies sibling differentiation

- **WHEN** an operator supervises a multi-variant package using the differentiation section
- **THEN** the section requires unique hooks and objective angles across siblings

#### Scenario: Supervision checklist exists

- **WHEN** an operator reads the supervision-window checklist
- **THEN** a condensed pass/fail checklist is present for optional evaluation while `publish_state` is `pending`

### Requirement: Criteria failure and blocked states are communicated

The criteria artifact MUST distinguish:

- **Criteria failure** — variant does not meet quality or differentiation criteria; operator SHOULD edit, defer, or cancel during supervision (persistence deferred to US-017); this is **not** a new worker `publish_state` value in US-016.
- **Normal supervision** — `pending` before API queue per US-015; not a policy failure.
- **Technical blocks** — publication enablement off, integration `failed`, OAuth action-required — follow existing publication semantics.
- **Deferred capabilities** — US-017 override mechanics, supervision console, automated similarity checks — absence is not a worker defect for US-016.

The criteria artifact MUST NOT redefine US-015 strategy-driven publication defaults or `publish_state` enum values.

#### Scenario: Criteria failure is guidance not automatic queue block

- **WHEN** an operator reads the criteria-failure section
- **THEN** the section states criteria failure guides optional supervision actions and does not introduce a mandatory approval gate or new `publish_state` for US-016

#### Scenario: Technical blocks remain separate

- **WHEN** an operator reads the blocked-states section
- **THEN** technical publication blocks are distinguished from editorial criteria failure

### Requirement: No duplication of US-015 or publication guards

Applying this capability MUST NOT change US-015 strategy-driven publication defaults, Flow A ready-path completion, campaign lifecycle transitions, US-011 publication-guard semantics, or ADR-0001 (n8n → worker HTTP only).

This capability MUST NOT add worker HTTP endpoints, n8n LinkedIn publish workflows, or BL-007 auto-queue behavior.

This capability MUST NOT modify `linkedin_publication_flow.py` queue/publish/cancel behavior.

#### Scenario: US-015 defaults preserved

- **WHEN** this capability is applied
- **THEN** `docs/operations/linkedin-variant-review-policy.md` strategy-driven publication and optional supervision sections remain unchanged in substance (cross-link updates only)

#### Scenario: No new publication endpoints

- **WHEN** this capability is applied
- **THEN** no new worker LinkedIn publication routes are introduced
