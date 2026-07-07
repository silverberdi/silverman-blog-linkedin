# editorial-canon

## Purpose

Canonical editorial rules for the `silverman-blog-linkedin` content automation system: brand positioning, blog post rules, LinkedIn derivative package and distribution strategy, anti-AI-writing posture, Flow A vs Flow B publication policy, and machine-readable anchors for future worker validation and prompt assembly.

## Requirements

### Requirement: Canonical editorial artifact path

The repository SHALL define the canonical editorial artifact at `content-strategy/silverman-editorial-system.md`.

The artifact MUST be version-controlled Markdown readable by future worker validation, LLM prompt assembly, and distribution scheduling logic.

The artifact MUST NOT be decorative marketing copy only; it MUST encode operational rules the system can enforce or inject.

This child change implements the artifact requirement referenced by umbrella change `flow-a-automatic-blog-linkedin-publishing-roadmap` and target spec `flow-a-automatic-publishing`.

#### Scenario: Canonical path exists after apply

- **WHEN** change `editorial-canon-and-linkedin-distribution-strategy` is applied
- **THEN** file `content-strategy/silverman-editorial-system.md` exists and is non-empty

#### Scenario: Missing artifact is detectable

- **WHEN** future worker validation or generation logic cannot read `content-strategy/silverman-editorial-system.md`
- **THEN** the system reports a structured error (for example `editorial_canon_missing`) rather than proceeding with implicit defaults

### Requirement: Required editorial sections

The canonical artifact MUST include all of the following sections with operational content:

1. Purpose of the editorial canon (`#purpose`)
2. Brand positioning (`#brand-positioning`)
3. Primary business goals (`#business-goals`)
4. Audience map covering recruiters, engineering managers, software architects, senior developers, C-level/executives, and AI + architecture enthusiasts (`#audience-map`)
5. Content pillars: software architecture, domain-first design, AI-assisted SDLC, OpenSpec/spec-driven development, modernization and technical debt, engineering leadership, practical delivery discipline (`#content-pillars`)
6. Topic boundaries: allowed, weak/deferred, and forbidden or low-value topics (`#topic-boundaries`)
7. Blog post rules: frontmatter, title, structure, argument style, depth, CTA behavior (`#blog-post-rules`)
8. LinkedIn derivative package rules: package concept, min/max variants, recommended variants by post type, variant definitions, relationship to source blog (`#linkedin-derivative-package`)
9. LinkedIn distribution strategy: cadence, spacing, audience sequencing, link-in-body vs soft CTA, anti-simultaneous publish, scheduling rules (`#linkedin-distribution-strategy`)
10. No-redundancy rules across variants (`#no-redundancy-rules`)
11. Anti-AI-writing rules: editorial-quality enforcement targeting AI-sounding patterns (not authorship detection); warning posture for Flow A user blog; rewrite/blocking for generated LinkedIn and future Flow B content (`#anti-ai-writing-rules`)
12. Voice and style rules (`#voice-and-style`)
13. CTA rules (`#cta-rules`)
14. Flow A vs Flow B publication policy (`#flow-a-vs-flow-b`)
15. Machine-readable anchors registry (`#machine-readable-anchors`)
16. Validation and prompt usage rules (`#validation-and-prompt-usage`)
17. Examples including `Why I Did Not Start With the Database` with variant strategy sketches (`#examples`)

#### Scenario: Section anchors present

- **WHEN** automated section-presence validation runs against `content-strategy/silverman-editorial-system.md`
- **THEN** all required `#anchor-id` headings listed in this requirement are found and have non-empty body content

#### Scenario: Audience map covers six lenses

- **WHEN** an operator reads `#audience-map`
- **THEN** the section defines distinct lenses for recruiters, engineering managers, software architects, senior developers, C-level/executives, and AI + architecture enthusiasts

### Requirement: Machine-readable section anchors

Each required major section MUST use a level-2 Markdown heading with an explicit anchor ID suffix in the form `## {title} {#anchor-id}`.

The artifact MUST include a `#machine-readable-anchors` section listing all anchor IDs and their consumption class (`validation`, `prompt`, `scheduling`, or combinations).

Future worker logic MUST be able to locate sections by anchor ID without hardcoding full section titles.

#### Scenario: Anchor format is consistent

- **WHEN** section-presence validation inspects required headings
- **THEN** each required section heading matches the pattern containing `{#anchor-id}` with the expected anchor slug

#### Scenario: Consumption classes documented

- **WHEN** an implementer reads `#validation-and-prompt-usage`
- **THEN** each major anchor is mapped to at least one consumption class

### Requirement: Flow A vs Flow B publication policy

The artifact MUST explicitly encode Flow A and Flow B publication policy consistent with umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`:

- **Flow A:** User-provided blog post in `blog-posts/ready/`; after automated validation passes, content is pre-approved; blog and LinkedIn derivative package MAY proceed automatically; LinkedIn publication MAY be automatic per distribution strategy when integration exists; no human approval after validation.
- **Flow B:** System-generated ideas/drafts; not pre-approved; human review required before publication; implementation deferred but policy MUST be encoded now.

The artifact MUST state that Flow B content MUST NOT enter Flow A automatic publish paths.

#### Scenario: Flow A automatic path documented

- **WHEN** an operator reviews `#flow-a-vs-flow-b`
- **THEN** the section states that Flow A requires no human approval after validation passes

#### Scenario: Flow B deferred but encoded

- **WHEN** an operator reviews `#flow-a-vs-flow-b`
- **THEN** the section states Flow B requires human approval and is deferred for implementation

### Requirement: LinkedIn derivative package and distribution rules

The artifact MUST define a **derivative package** as one or more LinkedIn posts linked to a single source blog post via campaign metadata.

The artifact MUST state that one or more variants does NOT mean simultaneous publication.

The artifact MUST define:

- minimum default of three variants per package (executive/recruiter, technical architect, short provocative) unless narrowed by post type
- maximum of four variants per package by default
- minimum spacing between scheduled variants (default at least 3 calendar days)
- maximum one derivative publication per calendar day per campaign
- distinct primary hook, objective, and CTA phrasing per variant (`#no-redundancy-rules`)
- when to use direct blog link CTA vs softer CTA (`#cta-rules`)
- requirement for publish-confirmed `source_public_url` before link CTAs in Flow A

#### Scenario: Non-simultaneous publication encoded

- **WHEN** an operator reads `#linkedin-distribution-strategy`
- **THEN** the section prohibits publishing all variants at once by default and defines spacing rules

#### Scenario: Package minimum variants

- **WHEN** an operator reads `#linkedin-derivative-package`
- **THEN** the section specifies at least three default variant types and their audience lenses

### Requirement: Anti-AI-writing posture

The artifact MUST define anti-AI-writing rules as **editorial-quality rules**, not authorship detection.

The system MUST NOT detect authorship. The system MUST NOT use "AI detected" as a final verdict. The correct label is **"AI-sounding editorial pattern"**, not "AI-written content". The system MUST target AI-sounding editorial patterns for rewrite or blocking—not claim reliable AI authorship detection.

Anti-AI rules MUST prohibit generic AI-sounding prose, buzzword stacking, fake anecdotes, empty motivational closings, engagement bait, and redundant variant copy.

**Enforcement posture:**

- **Flow A user-provided blog input:** automatable anti-AI checks MUST default to **warnings** (non-blocking) unless a future child spec marks a specific rule as blocking.
- **Generated LinkedIn derivatives:** anti-AI checks MUST use **rewrite/blocking** posture.
- **Future Flow B generated content:** anti-AI checks MUST use **rewrite/blocking** posture at approval gate.

The artifact MUST explicitly state the system MUST NOT claim perfect AI-writing detection. The artifact MUST include source-informed rationale that AI writing detectors are not reliable enough for final editorial verdicts and that non-native English patterns can be unfairly flagged.

The `#anti-ai-writing-rules` section MUST include operational subsections:

1. Anti-AI posture
2. Source-informed rationale
3. What "AI-sounding" means in this project
4. Forbidden AI-sounding openings
5. Forbidden AI-sounding transitions
6. Forbidden AI-sounding endings
7. Forbidden AI-sounding vocabulary
8. Structural patterns to avoid
9. Humanization rules
10. Rewrite rules

#### Scenario: Anti-AI rules are editorial quality not authorship detection

- **WHEN** an operator reads `#anti-ai-writing-rules`
- **THEN** the section states anti-AI rules are editorial-quality rules, not authorship detection
- **AND** the section states the system MUST NOT use "AI detected" as a final verdict

#### Scenario: Generated content rewrite/blocking posture

- **WHEN** an operator reads `#anti-ai-writing-rules`
- **THEN** the section states generated LinkedIn derivatives and future Flow B content use rewrite/blocking posture for AI-sounding editorial patterns

#### Scenario: User blog warning posture

- **WHEN** an operator reads `#anti-ai-writing-rules`
- **THEN** the section states Flow A user-provided blog posts receive warnings not blocks for anti-AI heuristics by default

#### Scenario: Operational anti-AI subsections present

- **WHEN** automated section-presence validation runs against `#anti-ai-writing-rules`
- **THEN** all required operational subsections listed in this requirement are found with non-empty content

#### Scenario: AI-sounding definition is operational

- **WHEN** an operator reads What "AI-sounding" means in this project
- **THEN** the subsection defines AI-sounding as polished empty phrasing, template repetition, and lack of trade-offs—not authorship probability

### Requirement: Blog post operational rules

The artifact MUST define blog rules including:

- required YAML frontmatter fields (at minimum `title`, `date`, `description` or equivalent summary field, `image` path relative to public site)
- `source_slug` vs `public_slug` behavior aligned with umbrella slug rules (numeric ordering prefix strip)
- companion PNG requirement under `blog-posts/ready/<source-slug>.png`
- title behavior, structure, argument style, expected depth
- forbidden content types per `#topic-boundaries`
- blog-level CTA behavior (minimal or absent in body; public URL derived at publish time)

#### Scenario: Slug rules align with umbrella

- **WHEN** an operator reads `#blog-post-rules`
- **THEN** the section documents `source_slug` `01-why-i-did-not-start-with-the-database` maps to `public_slug` `why-i-did-not-start-with-the-database`

#### Scenario: Frontmatter requirements listed

- **WHEN** future validation loads `#blog-post-rules`
- **THEN** required frontmatter fields are explicitly named

### Requirement: Worked example for database post

The `#examples` section MUST include at least one worked example for blog post **Why I Did Not Start With the Database** using:

- source file `blog-posts/ready/01-why-i-did-not-start-with-the-database.md`
- `source_slug` `01-why-i-did-not-start-with-the-database`
- `public_slug` `why-i-did-not-start-with-the-database`
- example public URL `https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/`

The example MUST sketch LinkedIn derivative strategies (not necessarily full post text) for:

- executive/recruiter variant
- technical architect variant
- engineering leadership variant
- short provocative variant

Each sketch MUST differ in hook, objective, structure, and CTA phrasing per `#no-redundancy-rules`.

#### Scenario: Example includes four variant sketches

- **WHEN** an operator reads `#examples`
- **THEN** four distinct variant strategy sketches exist for the database post with differing hooks and objectives

### Requirement: Section presence validation

The repository SHALL include an automated test or lint that verifies `content-strategy/silverman-editorial-system.md` contains all required anchor IDs and non-empty section bodies.

The check MUST fail CI or local test runs when a required anchor is missing or empty.

#### Scenario: Test passes on complete canon

- **WHEN** all required sections exist in the canonical artifact
- **THEN** the editorial canon presence test passes

#### Scenario: Test fails on missing anchor

- **WHEN** a required `#anchor-id` heading is removed from the canonical artifact
- **THEN** the editorial canon presence test fails

### Requirement: No runtime worker changes in this change

Applying change `editorial-canon-and-linkedin-distribution-strategy` MUST NOT add or modify worker HTTP endpoints, n8n workflow JSON, LinkedIn API integration, or Flow B generation logic.

Worker loading of the canon at runtime is deferred to downstream child changes cited by the umbrella.

#### Scenario: Apply scope is documentation only

- **WHEN** this change is applied
- **THEN** deliverables are limited to `content-strategy/silverman-editorial-system.md`, editorial canon tests/lint, and optional README pointer
