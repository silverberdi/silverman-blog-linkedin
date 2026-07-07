## Context

### Umbrella and sequencing

This is **child change 1** under the active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`. The umbrella defines Flow A lifecycle, slug terminology (`source_slug` vs `public_slug`), derivative package model, distribution strategy dimensions, and dependency order for slices 2–8. This child implements the editorial artifact the umbrella specifies at `content-strategy/silverman-editorial-system.md` but deliberately deferred authoring.

### Current state

| Component | Editorial behavior today |
|-----------|-------------------------|
| `linkedin_prompt.py` | Hardcoded system prompt and inline CTA instructions; no canon file load |
| `POST /generate-linkedin-draft` | Single variant per call; hints via request body (`tone`, `audience`, `variant`) |
| Validation | Structural/slug checks only; no editorial canon gate |
| Distribution | No scheduling model; no package-level strategy |
| Flow A policy | Documented in umbrella only; not operationalized in repo artifact |

The worker remains the filesystem and LLM boundary (ADR-0001). n8n orchestrates over HTTP only. Blog posts are canonical (ADR-0002); LinkedIn posts are distribution derivatives.

### Stakeholders

- **Author/operator**: Writes user-provided blog posts; expects Flow A automation after validation.
- **Future worker logic**: Will read canon sections for blocking validation, prompt injection, and schedule computation.
- **Future Flow B reviewer**: Will use canon for approval criteria when Flow B is implemented.

## Goals / Non-Goals

**Goals:**

- Author `content-strategy/silverman-editorial-system.md` as operational policy—not marketing prose.
- Encode all 17 required sections with stable `## anchor-id` headings for machine lookup.
- Document which sections feed validation (blocking), prompt assembly (generation), and scheduling (cadence/spacing).
- Encode Flow A vs Flow B policy table matching the umbrella.
- Encode LinkedIn derivative package rules: one or more variants per blog, staggered publication per strategy (not simultaneous).
- Include strategy examples for `Why I Did Not Start With the Database` (`01-why-i-did-not-start-with-the-database` → public slug `why-i-did-not-start-with-the-database`).
- Add automated check that required sections/anchors exist.

**Non-Goals:**

- Worker code to load or parse the canon at runtime.
- `POST /validate-ready-post`, `POST /generate-linkedin-package`, `POST /schedule-linkedin-package`.
- n8n workflow JSON, LinkedIn API integration, Flow B generation.
- Campaign metadata schema (child change `flow-a-lifecycle-and-duplicate-prevention`).
- Replacing or archiving the umbrella.

## Artifact structure

### Path and format

- **Path:** `content-strategy/silverman-editorial-system.md`
- **Format:** Markdown with level-2 headings using explicit anchor IDs: `## {numeric-prefix} {title} {#anchor-id}`
- **Versioning:** Git-tracked in this repository; worker reads from editorial root at runtime in future children.

### Machine-readable anchors

Each major section uses a stable `{#anchor-id}` suffix on the `##` heading. Future worker code will extract sections by anchor (regex or lightweight parser). Required anchors:

| Anchor | Purpose |
|--------|---------|
| `#purpose` | Canon purpose and scope |
| `#brand-positioning` | Positioning statement |
| `#business-goals` | Primary business goals |
| `#audience-map` | Audience lenses per variant |
| `#content-pillars` | Allowed thematic pillars |
| `#topic-boundaries` | Allowed/deferred/forbidden topics |
| `#blog-post-rules` | Frontmatter, structure, depth, blog CTA |
| `#linkedin-derivative-package` | Package concept, variant min/max, definitions |
| `#linkedin-distribution-strategy` | Cadence, spacing, sequencing, CTA modes |
| `#no-redundancy-rules` | Cross-variant uniqueness rules |
| `#anti-ai-writing-rules` | Editorial-quality rules targeting AI-sounding patterns; warning vs rewrite/blocking |
| `#voice-and-style` | Sentence rhythm, directness, avoid list |
| `#cta-rules` | Blog link vs soft CTA |
| `#flow-a-vs-flow-b` | Publication policy table |
| `#machine-readable-anchors` | Anchor registry (self-describing) |
| `#validation-and-prompt-usage` | Which sections for which subsystem |
| `#examples` | Worked examples including database post |

Subsections under anchors MAY use `###` headings without separate anchor IDs unless a future child needs them.

### Consumption map (future children)

```
content-strategy/silverman-editorial-system.md
        │
        ├── ready-post-editorial-validation
        │     └── #blog-post-rules, #topic-boundaries, #anti-ai-writing-rules (warnings for user blog)
        │
        ├── linkedin-derivative-package-generation
        │     └── #linkedin-derivative-package, #anti-ai-writing-rules, #voice-and-style,
        │         #cta-rules, #no-redundancy-rules, #audience-map
        │
        ├── linkedin-distribution-scheduling-model
        │     └── #linkedin-distribution-strategy, #no-redundancy-rules, #cta-rules
        │
        ├── flow-a-lifecycle-and-duplicate-prevention
        │     └── #flow-a-vs-flow-b (flow field semantics)
        │
        └── future Flow B review flow
              └── #flow-a-vs-flow-b, #anti-ai-writing-rules (rewrite/blocking), #topic-boundaries
```

## Decisions

### D1: Markdown file with explicit anchor IDs (not YAML-only config)

**Decision:** Single Markdown file with `{#anchor-id}` on `##` headings.

**Rationale:** Human-readable for author review; prompt-friendly for LLM injection; git-diffable; matches umbrella D6.

**Alternatives:** Separate YAML rules file—rejected; splits prose rules from structure and duplicates maintenance.

### D2: Three consumption classes in canon

**Decision:** Label each major section in `#validation-and-prompt-usage` as `validation`, `prompt`, `scheduling`, or combinations.

**Rationale:** Future worker can load only applicable slices; avoids injecting scheduling rules into blog validation prompts.

### D3: Anti-AI rules—editorial quality enforcement, not authorship detection

**Decision:** Canon defines anti-AI rules as editorial-quality enforcement targeting **AI-sounding editorial patterns**, not authorship detection. The system MUST NOT use "AI detected" as a final verdict and MUST NOT claim perfect AI-writing detection.

**Enforcement posture:**

- **Generated LinkedIn derivatives and future Flow B content:** rewrite/blocking posture when AI-sounding patterns are found.
- **Flow A user-provided blog input:** warnings by default; MUST NOT block unless a future child spec marks a specific rule as blocking.

**Rationale:** Research shows AI-text detectors are unreliable, style-sensitive, and can produce false positives—including bias risk against non-native English. The goal is people-first, experience-based writing quality, not algorithmic authorship classification. Matches umbrella editorial artifact requirements and realistic automation limits.

### D4: Minimum three LinkedIn variants per package (default)

**Decision:** Default package includes executive/recruiter, technical architect, and short provocative variants; engineering leadership variant recommended for leadership-angle posts. Maximum four variants per package unless canon narrows for a post type.

**Rationale:** Aligns with ADR-0002 editorial rules and umbrella minimum-three requirement.

### D5: Distribution defaults encoded numerically

**Decision:** Canon specifies concrete defaults future scheduling can implement without reinterpretation:

- Minimum 3 days between variant publications (same campaign).
- Maximum one LinkedIn derivative per calendar day per campaign.
- Preferred publish windows: Tue–Thu, 08:00–10:00 or 16:00–18:00 America/Bogota (operator timezone).
- First variant: executive/recruiter lens; second: technical architect; third: short provocative or engineering leadership depending on post type.

**Rationale:** Scheduling child needs operational numbers, not "use good judgment" only.

### D6: Section-presence test, not full semantic validation

**Decision:** This change adds a test that required anchors exist and are non-empty; semantic rule enforcement deferred to validation/generation children.

**Rationale:** Keeps slice 1 deliverable focused; prevents drift without implementing a rules engine.

### D7: Examples use umbrella canonical slug example

**Decision:** `#examples` uses `01-why-i-did-not-start-with-the-database` / `why-i-did-not-start-with-the-database` / `https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/` with variant strategy sketches—not full generated posts.

**Rationale:** Consistent with umbrella slug terminology; demonstrates domain-first design thesis angles.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Canon too verbose for prompt token limits | Consumption map loads section subsets; generation child may summarize anchors |
| Rules drift from umbrella | Proposal and design explicitly cite umbrella; spec scenarios cross-check policy |
| Over-specified cadence misfits LinkedIn API limits | Slice 8 may adjust; canon documents defaults as `scheduling` class, modifiable |
| Anchor parsing brittle | Document regex pattern in `#machine-readable-anchors`; test anchor presence |

## Migration Plan

1. Create `content-strategy/` directory and `silverman-editorial-system.md` with all sections.
2. Add `tests/test_editorial_canon.py` (or equivalent) asserting required anchors exist.
3. Optionally add one-line pointer in README to canon path.
4. Run `openspec validate editorial-canon-and-linkedin-distribution-strategy --strict`.
5. Future children replace hardcoded `linkedin_prompt.py` fragments with canon-loaded sections incrementally.

Rollback: delete artifact and test; no runtime dependency until validation child ships.

## Open Questions

1. Should `linkedin_prompt.py` be updated in this change to read canon, or left for `linkedin-derivative-package-generation`? **Default:** leave for package-generation child.
2. Should Flow A auto-approved drafts use `linkedin-posts/approved/` or a dedicated subfolder? **Default:** document both as acceptable in canon; lifecycle child finalizes.
3. Exact rewrite/blocking anti-AI heuristics for generated content—defer rule engine to `linkedin-derivative-package-generation` and `ready-post-editorial-validation` children; canon lists patterns and operational subsections only.
