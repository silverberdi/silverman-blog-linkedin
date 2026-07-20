# Silverman Editorial System

Operational editorial canon for the `silverman-blog-linkedin` content automation system. This document is the single source of truth for blog writing rules, LinkedIn derivative package rules, distribution strategy, Flow A vs Flow B policy, and consumption rules for future worker validation, prompt assembly, and scheduling logic.

**Umbrella reference (archived):** `openspec/changes/archive/2026-07-07-flow-a-automatic-blog-linkedin-publishing-roadmap/` — historical evidence only, not active requirements. **Current status:** [docs/CURRENT-STATE.md](../docs/CURRENT-STATE.md). **Authority:** [docs/CONTEXT-AUTHORITY.md](../docs/CONTEXT-AUTHORITY.md).

**Flow A vs Flow B approval:** Flow A automates publish/package/schedule after validation; LinkedIn variants follow distribution strategy with an optional pre-send supervision window (not mandatory per-variant approval). Flow B requires mandatory human approval of the **AI-generated blog** before Flow A eligibility; after that approval, LinkedIn follows Flow A (optional supervision only). See [GLOSSARY.md](../docs/GLOSSARY.md), [linkedin-variant-review-policy.md](../docs/operations/linkedin-variant-review-policy.md), and product backlog BL-016–BL-019.

---

## 1 Purpose {#purpose}

This canon defines enforceable editorial policy for:

- **Blog posts** — user-authored Markdown in `blog-posts/ready/`; canonical long-form content published to [silverman.pro](https://silverman.pro).
- **LinkedIn derivatives** — one or more distribution posts per blog, generated from the canonical blog, stored under `linkedin-posts/{review,approved,published}/`.
- **Distribution** — staggered publication of derivative variants per campaign metadata, not simultaneous blast.

**Scope boundaries:**

| In scope | Out of scope (this document only) |
|----------|-----------------------------------|
| Rules, anchors, examples | Runtime capability status (see CURRENT-STATE) |
| Validation / prompt / scheduling consumption map | HTTP endpoint implementation detail |
| Flow A vs Flow B policy encoding | Flow B generation automation beyond policy |
| Anti-AI and redundancy rules | LinkedIn API operational validation |

Blog post is canonical (ADR-0002). LinkedIn posts are derivative distribution assets. The worker remains the filesystem and LLM boundary; n8n orchestrates over HTTP only (ADR-0001).

---

## 2 Brand Positioning {#brand-positioning}

**Author:** Silverio Bernal  
**Site:** [silverman.pro](https://silverman.pro)  
**Professional identity:** Solutions Architect — practical architecture leadership, not influencer persona.

**Positioning statement (operational):**

- Lead with **domain-first design** and delivery discipline over tool hype.
- Write as a senior practitioner who has shipped systems, not as a commentator on news cycles.
- Favor concrete architectural decisions, trade-offs, and governance patterns over generic "digital transformation" language.
- Audience should infer: remote-capable senior architect, credible for staff/principal/architect roles and C-level advisory.

**Do not position as:** AI influencer, tool reviewer, motivational speaker, or news aggregator.

---

## 3 Business Goals {#business-goals}

Primary goals, in priority order for content decisions:

1. **Recruiter and hiring-manager attraction** — signal fit for remote senior architecture roles (target compensation above USD 6,000/month). Content must demonstrate judgment, scope ownership, and communication at executive and engineering-leadership levels.
2. **Thought leadership** — establish credibility in software architecture, domain-driven design, AI-assisted SDLC, spec-driven development, modernization, and engineering leadership.
3. **Blog traffic** — drive qualified readers to silverman.pro without engagement-bait or influencer tone. LinkedIn is a funnel to the blog, not a parallel content empire.

**Success signals (editorial, not analytics):**

- Recruiters and engineering leaders recognize consistent architectural point of view.
- Blog posts are cite-worthy in hiring conversations and architecture reviews.
- LinkedIn variants feel human, distinct, and worth reading—not templated reposts of the same paragraph.

---

## 4 Audience Map {#audience-map}

Six audience lenses. Each LinkedIn variant MUST map to one primary lens. Secondary lenses MAY inform tone but MUST NOT dilute the primary hook.

| Lens | Who they are | What they need from content | Default variant mapping |
|------|--------------|----------------------------|-------------------------|
| **Recruiters** | Technical recruiters, talent partners | Clear seniority signals, remote readiness, domain breadth, hireable narrative | `executive-recruiter` |
| **Engineering managers** | EM, VP Engineering, delivery leads | Team scaling, delivery risk, technical debt trade-offs, leadership judgment | `engineering-leadership` |
| **Software architects** | Staff/principal architects, solution architects | Design decisions, boundaries, patterns, failure modes, spec-driven practice | `technical-architect` |
| **Senior developers** | Senior/lead ICs | Actionable depth, "how I'd decide this" framing, career-relevant craft | `technical-architect` (secondary) or `short-provocative` |
| **C-level / executives** | CTO, CIO, product executives | Business outcome, risk reduction, modernization ROI, governance | `executive-recruiter` |
| **AI + architecture enthusiasts** | Practitioners exploring AI in SDLC | Practical AI-in-delivery patterns without hype; architecture guardrails | `short-provocative` or `technical-architect` |

**Variant mapping rule:** When generating a package, assign exactly one primary lens per variant. Document the lens in campaign metadata (`audience_lens` field — future child `flow-a-lifecycle-and-duplicate-prevention`).

---

## 5 Content Pillars {#content-pillars}

Seven allowed thematic pillars. Every blog post SHOULD anchor to at least one primary pillar. LinkedIn variants MAY emphasize different pillars from the same blog.

| Pillar | Operational definition |
|--------|------------------------|
| **Software architecture** | System structure, boundaries, integration patterns, quality attributes, evolutionary architecture. |
| **Domain-first design** | Modeling business domains before infrastructure; ubiquitous language; bounded contexts; resisting premature persistence/ORM decisions. |
| **AI-assisted SDLC** | Using AI in spec, design, implementation, and review workflows—with governance, not replacement of judgment. |
| **OpenSpec / spec-driven development** | Change proposals, specs, tasks, validation discipline; architecture decisions recorded before code. |
| **Modernization and technical debt** | Strangler patterns, incremental migration, debt triage, risk-aware rewrites. |
| **Engineering leadership** | Decision-making under uncertainty, team leverage, cross-functional alignment, delivery accountability. |
| **Practical delivery discipline** | Shipping, operational constraints, feedback loops, "good enough" architecture that ships. |

Posts that do not clearly connect to at least one pillar are weak candidates for publication.

---

## 6 Topic Boundaries {#topic-boundaries}

### Allowed (high value)

- Architecture decisions with explicit trade-offs and context.
- Domain modeling, bounded contexts, API design, integration boundaries.
- Spec-driven / OpenSpec workflow experience (this repo is a valid example).
- Modernization paths, technical debt governance, incremental delivery.
- AI in development workflows with guardrails (prompting, review, spec validation)—not model benchmarks.
- Engineering leadership and delivery judgment grounded in real constraints.
- Personal professional narrative **only** when tied to a concrete architectural lesson (not lifestyle content).

### Weak / deferred (publish only with strong angle)

- Tool tutorials without architectural framing.
- Framework version release notes or changelog commentary.
- Generic "lessons learned" lists without a specific decision story.
- Conference recap posts without original analysis.
- Comparisons of vendors/tools as the main thesis (see forbidden).

### Forbidden / low value (MUST NOT publish)

- News commentary or hot-take reactions to industry headlines.
- Tool-vs-tool comparison posts as primary content.
- Unsupported personal anecdotes (invented metrics, fake meetings, fabricated stakeholder quotes).
- Motivational or hustle culture content.
- Engagement bait ("Agree?", "Comment below", polls designed only for reach).
- Political, religious, or off-brand controversy.
- Unrelated side projects unless directly tied to the Silverman professional brand or architecture/AI delivery lessons.
- Content that reads as AI-generated filler (see `#anti-ai-writing-rules`).

---

## 7 Blog Post Rules {#blog-post-rules}

### File pair requirement

Each ready blog candidate MUST exist as a pair in `blog-posts/ready/`:

- `<source_slug>.md` — Markdown with YAML frontmatter.
- `<source_slug>.png` — companion hero/social image (same basename).

Missing either file blocks Flow A validation.

### Slug terminology

| Term | Definition | Example |
|------|------------|---------|
| `source_slug` | Basename of ready file without `.md`; MAY include numeric ordering prefix | `01-why-i-did-not-start-with-the-database` |
| `public_slug` | Published slug: strip leading `^\d+-` from `source_slug` | `why-i-did-not-start-with-the-database` |

Canonical mapping example:

- Source file: `blog-posts/ready/01-why-i-did-not-start-with-the-database.md`
- `source_slug`: `01-why-i-did-not-start-with-the-database`
- `public_slug`: `why-i-did-not-start-with-the-database`
- Public URL pattern: `https://silverman.pro/{YYYY}/{MM}/{DD}/{public_slug}/`

### Required YAML frontmatter

Minimum fields (validation MUST enforce):

| Field | Requirement |
|-------|-------------|
| `title` | Human-readable post title; becomes Jekyll/page title |
| `date` | Publication date (`YYYY-MM-DD` or datetime with timezone) |
| `description` | Summary for SEO/social (or equivalent `summary` field—normalize at publish) |
| `image` | Path relative to public site (e.g. `/assets/images/{public_slug}.png`) |

Optional fields MAY include `tags`, `categories`—do not require for Flow A.

### Structure and depth

- **Opening:** State the problem or decision within the first two paragraphs—no throat-clearing.
- **Body:** One central thesis; support with reasoning, constraints, and alternatives considered.
- **Depth:** Senior practitioner level—assume reader knows what a microservice is; explain *why this boundary*, not *what is a microservice*.
- **Argument style:** First-person acceptable when describing real decisions; avoid fabricated scenarios.
- **Length:** Typically 800–2,500 words; shorter only if the idea is complete.
- **Headings:** Use `##` / `###` for scanability; avoid single-sentence sections.

### Blog style rules

- Develop **one argument deeply**—do not try to cover every related topic in a single post.
- The **intro** MUST identify the architectural mistake, delivery pressure, or trade-off that motivates the piece.
- The **body** MUST show why the obvious or popular option is insufficient—not just what the better option is.
- The **ending** MUST land the architectural lesson without motivational language or false urgency.
- Avoid "key takeaways" sections unless they add genuine synthesis; prefer a closing paragraph that states the decision principle.
- Prefer **concrete architectural vocabulary** (bounded context, invariant, integration boundary, failure mode) over generic business language (synergy, transformation, empowerment).
- Do **not** write SEO-first content—write for readers with architectural judgment, not for keyword density.
- Do **not** add generic sections just to look complete (empty introductions, filler conclusions).
- Explain enough for clarity, but do **not** teach basic concepts to expert readers unless the concept is being reframed.
- Use deeper structured reasoning than LinkedIn: numbered steps, alternatives considered, and explicit trade-offs are welcome when they serve the argument.

### Blog-level CTA

- Blog body SHOULD NOT contain heavy self-promotion or "follow me" CTAs.
- Public URL is derived at publish time; do not hardcode future URLs in draft body.
- End with a concise takeaway, not a sales close.

### Forbidden in blog posts

Per `#topic-boundaries`. Validation MUST block structural violations; anti-AI heuristics on user blog input default to **warnings** only (see `#anti-ai-writing-rules`).

---

## 8 LinkedIn Derivative Package {#linkedin-derivative-package}

### Package concept

A **derivative package** is one or more LinkedIn posts linked to a single source blog via shared `campaign_id` in `metadata/campaigns/`. Each variant:

- Derives facts and thesis from the canonical blog only.
- Targets one primary audience lens (see `#audience-map`).
- Has distinct hook, objective, structure, and CTA phrasing (see `#no-redundancy-rules`).
- Is stored as a separate file under `linkedin-posts/review/` (Flow A pre-approved path) or `linkedin-posts/approved/` when lifecycle child finalizes folder semantics.

**Critical:** One or more variants does **not** mean simultaneous publication. See `#linkedin-distribution-strategy`.

### Variant count

| Rule | Value |
|------|-------|
| Minimum variants per package | **3** |
| Maximum variants per package | **4** (default cap) |
| Default trio | `executive-recruiter`, `technical-architect`, `short-provocative` |
| Fourth variant (when used) | `engineering-leadership` — recommended for posts with strong delivery/leadership angle |

### Variant definitions

| Variant ID | Primary lens | Objective | Structure sketch |
|------------|--------------|-----------|------------------|
| `executive-recruiter` | Recruiters + C-level | Signal seniority, scope, hireable judgment in 60-second read | Problem → decision → business outcome → soft or link CTA |
| `technical-architect` | Software architects | Teach the design move; name trade-offs | Constraint → pattern → what you'd do differently → link CTA |
| `engineering-leadership` | Engineering managers | Team/delivery implications of the architectural choice | Leadership stakes → decision → how to coach the team → link CTA |
| `short-provocative` | Senior ICs + enthusiasts | One sharp insight; pattern interrupt | Bold opening line → 3–5 short paragraphs → minimal CTA |

### Post-type recommendations

| Blog type | Recommended package |
|-----------|---------------------|
| Domain/design decision story | Default trio + optional `engineering-leadership` |
| AI-assisted SDLC / OpenSpec practice | Default trio; `technical-architect` leads with workflow detail |
| Modernization / debt | Add `engineering-leadership` as 4th variant |
| Short essay (&lt; 1,200 words) | Minimum 3; skip 4th unless leadership angle is strong |

### Relationship to source blog

- NEVER invent facts, metrics, companies, or URLs not in the blog.
- `source_public_url` MUST be publish-confirmed before link CTAs in Flow A (see `#cta-rules`).
- `source_relative_path`, `source_content_sha256`, and `public_slug` MUST trace in campaign metadata.

### LinkedIn style rules

- LinkedIn posts MUST feel like **compressed architectural arguments**, not blog summaries or table-of-contents reposts.
- Do **not** start every variant with a contrarian hook—vary opening strategy across the package.
- Do **not** repeat the blog title as the LinkedIn opening line.
- Do **not** use "I wrote a post about…" or "I wrote a blog post about…" as the default first sentence.
- The **first two lines** MUST create tension, decision context, or a concrete trade-off—the reader should know why this matters before the thesis lands.
- **One idea per paragraph**; keep paragraphs short (2–4 sentences typical).
- **No hashtags** by default.
- **No emoji** by default.
- **No engagement bait**—no polls, reaction prompts, or comment requests.
- Place the CTA **late and naturally**—after the argument is complete, not as the opening move.
- Each variant MUST be **independently readable** without the reader opening the blog.

---

## 9 LinkedIn Distribution Strategy {#linkedin-distribution-strategy}

### Core principle

**Stagger, don't blast.** Variants from the same campaign publish on separate calendar days with audience-aware sequencing.

### Cadence defaults (scheduling class)

| Parameter | Default | Notes |
|-----------|---------|-------|
| Minimum spacing between variants (same campaign) | **3 calendar days** | Hard default for scheduling child (schedule-intent stagger) |
| Maximum publications per campaign per calendar day | **1** | Never publish two variants same day |
| Simultaneous multi-variant publish | **Prohibited** | Unless operator manually overrides outside automation |
| Preferred days | Tuesday, Wednesday, Thursday | America/Bogota operator timezone |
| Preferred windows | 08:00–10:00 or 16:00–18:00 | Adjust in scheduling child if API limits require |

**Publish-time authority:** Schedule-intent stagger above is planning guidance for `scheduled_at` placement. At send time, the worker US-020 publish-time cadence guard (minimum **72 hours** between successful same-campaign `published` evidence) remains authoritative — see [linkedin-cadence-spacing-policy.md](../docs/operations/linkedin-cadence-spacing-policy.md) and [linkedin-publication-prerequisites.md](../docs/deployment/linkedin-publication-prerequisites.md#publish-time-sequence-and-cadence-guard-us-020). Do not treat this table as a second publish-time cadence engine.

### Audience sequencing (first publish order)

For default 3-variant packages:

1. **Day 0 (first slot):** `executive-recruiter` — widest professional reach; recruiter/C-level lens.
2. **Day 3+:** `technical-architect` — depth for architect network.
3. **Day 6+:** `short-provocative` OR `engineering-leadership` — depending on post type (see `#linkedin-derivative-package`).

When a 4th variant is included, insert `engineering-leadership` at position 2 or 3 based on post type; never same day as another variant.

### CTA mode per wave

- First variant MAY use softer CTA (insight-led) if blog URL not yet confirmed at generation time.
- Once `source_public_url` is publish-confirmed, subsequent variants SHOULD use direct link CTA (see `#cta-rules`).
- Regenerate or patch drafts if URL was missing at generation time and link CTA is required.

### Anti-simultaneous publish

Automation MUST NOT schedule all package variants at the same timestamp. Campaign metadata MUST record `scheduled_at` per variant with spacing ≥ 3 days.

---

## 10 No-Redundancy Rules {#no-redundancy-rules}

Across variants in the same package, the following MUST be unique per variant:

| Element | Uniqueness requirement |
|---------|------------------------|
| **Opening hook** | First 1–2 sentences MUST NOT be reused or lightly paraphrased across variants |
| **Primary objective** | Each variant optimizes for a different lens (see `#audience-map`) |
| **Central thesis angle** | Same blog fact, different emphasis—not copy-paste of the same takeaway |
| **Structure** | Vary paragraph count, list usage, and narrative arc |
| **CTA phrasing** | Different natural-language close; same URL allowed but phrasing MUST differ |
| **Closing line** | No shared "in conclusion" boilerplate |

**Forbidden:** Publishing the same LinkedIn text as two variants with only audience label changed.

**Validation (future):** Package generation child SHOULD run similarity check on hooks and CTA sentences; flag above ~0.85 n-gram overlap for rewrite.

---

## 11 Anti-AI-Writing Rules {#anti-ai-writing-rules}

### Anti-AI posture

This project does **not** detect authorship. It detects and rewrites **low-quality AI-sounding editorial patterns**.

| Rule | Requirement |
|------|-------------|
| No perfect detection claim | The system MUST NOT claim perfect AI-writing detection |
| No authorship verdict | The system MUST NOT use "AI detected" as a final verdict |
| Flow A user blogs | Anti-AI checks produce **warnings** by default—non-blocking |
| Generated LinkedIn derivatives | Anti-AI checks are **rewrite/blocking** rules |
| Future Flow B content | Anti-AI checks are **rewrite/blocking** rules at approval gate |
| Correct label | Use **"AI-sounding editorial pattern"**, not "AI-written content" |

Human review remains the final gate for edge cases. Heuristics flag editorial quality problems; they do not prove authorship.

### Source-informed rationale

- AI writing detectors are not reliable enough to be used as final editorial verdicts. Major providers have retired or limited classifier tools due to low accuracy.
- Detectors are style-sensitive, produce false positives, and can unfairly flag non-native English writing patterns.
- This project uses anti-AI rules as editorial quality rules, not authorship detection.
- The goal is **people-first, experience-based, useful writing**—content that demonstrates judgment, specificity, and a clear point of view for readers, not optimization for algorithms or generic virality.

### What "AI-sounding" means in this project

"AI-sounding" means writing that:

- makes broad claims without a specific architectural decision
- uses polished but empty phrasing
- repeats common LinkedIn templates
- introduces no trade-off, constraint, consequence, or example
- sounds like content marketing rather than senior architecture judgment
- summarizes instead of arguing
- uses generic transformations like "X is not just Y; it is Z" too often
- has uniform paragraph rhythm and predictable transitions
- avoids taking a position

The correct response is **rewrite**, not "flag as AI."

### Forbidden AI-sounding openings

MUST NOT open with:

- "In today's fast-paced world…"
- "In the ever-evolving landscape…"
- "In modern software development…"
- "In the digital age…"
- "As technology continues to evolve…"
- "Let's dive into…"
- "Here are X reasons why…"
- "Have you ever wondered…"
- "It's no secret that…"
- "Now more than ever…"
- Restating the blog title as the first sentence.
- "I wrote a post about…" or "I wrote a blog post about…" as the default opener.

**Rule:** Generated content MUST start from a specific tension, decision, trade-off, or mistake instead.

### Forbidden AI-sounding transitions

MUST NOT use:

- "Moreover"
- "Furthermore"
- "Additionally"
- "In conclusion"
- "It is important to note"
- "That being said"
- "At the end of the day"
- "Ultimately"
- "This highlights the importance of"
- "This underscores the need for"

**Rule:** Generated content SHOULD use natural transitions based on the argument, for example:

- "The problem is…"
- "That looks practical, but…"
- "The trade-off is…"
- "The mistake is not the database. The mistake is starting there."
- "What changes in a real system is…"

### Forbidden AI-sounding endings

MUST NOT close with:

- "What are your thoughts?"
- "Agree or disagree?"
- "Comment below."
- "Let me know in the comments."
- "The future belongs to…"
- "The possibilities are endless."
- "This is just the beginning."
- "Embrace the future of…"
- "In conclusion…"
- "Tag someone who needs this."
- "Follow for more insights."

**Rule:** Endings MUST land the architectural lesson, decision, or CTA without engagement bait.

### Forbidden AI-sounding vocabulary

Avoid unless technically justified in context:

- leverage, unlock, game-changer, revolutionize, transformative
- robust, seamless, cutting-edge, holistic, empower
- scalable solution, dynamic landscape, digital transformation journey
- mission-critical (unless actually necessary)
- best-in-class, next-generation, innovative solution
- paradigm shift, frictionless
- optimize workflows (unless concrete and specific)

**Rule:** Prefer concrete architectural words:

boundary, invariant, workflow, decision, trade-off, coupling, latency, ownership, migration, validation, failure mode, constraint, sequence, policy, model, behavior

### Structural patterns to avoid

- Same paragraph length across the whole post.
- Three-part LinkedIn list with no real argument.
- "X is not just Y; it is Z" as a repeated template.
- Hook → generic explanation → generic list → engagement question.
- Excessive bullet lists when the post needs argument.
- Summary of the blog instead of derivative argument.
- Repeating the blog title as the LinkedIn hook.
- Starting with "I wrote about…" as the default opening.
- Reusing the same CTA structure across variants.
- Over-polished sentence rhythm with no friction or specificity.
- Section headers that are rhetorical questions throughout the piece.
- "Introduction / Conclusion / Key Takeaways" scaffolding with no substance.
- Fake anecdotes: invented meetings, unnamed clients, fabricated metrics.
- Hashtag spam (default: **no hashtags** in Flow A derivatives).
- Redundant variant copy (see `#no-redundancy-rules`).

### Humanization rules

Generated content MUST include at least some of:

- a concrete architectural tension
- a decision the architect would or would not make
- a trade-off
- a constraint
- a failure mode
- a business or delivery consequence
- a boundary or ownership implication
- a specific phrase that sounds like Silverio's judgment

**Examples of acceptable Silverio-style judgment:**

- "I would not start there."
- "That looks practical, but it hides the real decision."
- "The database matters. But it should not be the first thing that defines the system."
- "The real problem is not persistence. The real problem is naming the business too late."
- "This is where architecture becomes a delivery discipline, not a diagram."

### Rewrite rules

When generated content sounds AI-like:

- Replace broad claims with specific architectural decisions.
- Replace abstract adjectives with constraints and consequences.
- Replace generic openings with tension.
- Replace engagement-bait endings with a lesson or natural CTA.
- Replace summaries with a point of view.
- Replace repeated transitions with argument-driven movement.
- Remove hashtags unless explicitly required by a future strategy update.
- Remove invented anecdotes, invented metrics, invented clients, or unsupported claims.

### Flow A blog warnings (non-blocking examples)

- Excessive em dash or colon lists typical of LLM output.
- Generic section titles ("Introduction", "Conclusion", "Key Takeaways") without substance.
- Overuse of "delve", "crucial", "robust", "landscape", "tapestry".

Warnings MUST surface in validation response `warnings[]`; they MUST NOT alone fail validation.

---

## 12 Voice and Style {#voice-and-style}

### Silverio writing style DNA

Write as a **senior practitioner**, not an influencer:

- **Direct but not rude** — state positions clearly without performative aggression.
- **Opinionated but reasoned** — every claim earns its place through constraint, trade-off, or consequence.
- **Architecture-first and business-aware** — technical decisions connect to delivery risk, cost, or organizational reality.
- **Practical and implementation-conscious** — ideas must survive contact with real systems and teams.
- **Comfortable challenging common instincts** — willing to say the obvious move is wrong for this context.
- **Comfortable using first person** when it signals real architectural judgment, not for faux intimacy.
- **English for public posts** — should not sound over-polished or corporate; non-native executive-professional English is acceptable if clear and natural.
- **Prefers trade-offs, boundaries, failure modes, and delivery consequences** over absolute claims and buzzwords.

**Concrete style rules (aligned with clear technical writing):**

- Lead with the important point—start from tension, mistake, decision, or trade-off.
- Use **active voice** by default.
- Prefer **plain, specific language**; avoid unnecessary modifiers and vague phrasing.
- Make the argument **progressively**—each paragraph advances the reasoning.
- Use **first person** when it signals real judgment ("I would not start there").
- Use **short paragraphs on LinkedIn**; use **deeper structured reasoning in blog posts**.
- Prefer **"what I would do / what I would avoid / why it matters"** over generic advice.
- Use **examples and concrete trade-offs** to support claims.

### Preferred argument patterns

Use these narrative arcs (adapt to context; do not formula-copy):

| Pattern | Shape |
|---------|-------|
| Common instinct → hidden cost → better architectural move | "Teams reach for X because… The hidden cost is… A better move is…" |
| What looks practical → why it fails in complex systems → what to do instead | "On paper, X is faster… In complex systems, it breaks because… Instead…" |
| Tool-first temptation → domain/business reality → architectural boundary | "The tool suggests Y… The business actually needs Z… Draw the boundary at…" |
| Delivery pressure → risk of shortcut → disciplined compromise | "The deadline pushes toward… The shortcut risks… A disciplined compromise is…" |
| Architecture principle → concrete system behavior → business consequence | "The principle is… In the system, that means… For the business, the effect is…" |
| Symptom in the team → architectural root cause → leadership action | "The team shows X… The root cause is an architectural gap… The leadership move is…" |

### Disallowed writing patterns

MUST NOT produce:

- Generic numbered lists without a point of view.
- "AI newsletter" tone—surveying a topic without taking a position.
- Motivational close disconnected from the argument.
- Exaggerated certainty ("always", "never", "the only way") without acknowledging context.
- Fake storytelling—invented scenes, meetings, or metrics.
- Vendor-style phrasing ("our platform enables…", "seamlessly integrates…").
- Repetitive rhetorical questions as a structural device.
- Comments or reactions as the main ending.
- Overusing "not just X, but Y" as a rhetorical template.
- Over-explaining basic software concepts to expert audiences.
- Overuse of: leverage, robust, scalable, seamless, unlock, transform, empower.

### Voice (summary)

- **Senior** — assume reader intelligence; no condescension, no over-explaining basics.
- **Practical** — prefer "here is the constraint and what I did" over abstract principles alone.
- **Direct** — short sentences mixed with longer explanatory ones; active voice default.
- **Human** — occasional first person; no corporate passive mush.

### Rhythm

- Vary sentence length. Avoid three identical paragraph shapes in a row.
- Prefer concrete nouns and verbs over adjective piles.
- One idea per paragraph on LinkedIn; blog may carry more depth.

### Avoid list

- Influencer cadence ("Here's the thing...", "Thread:", "🚀🚀🚀").
- False urgency ("You need to read this before it's too late").
- Humble-brag stacking.
- Listing every technology in the stack without architectural point.
- Rhetorical questions as section headers throughout.

---

## 13 CTA Rules {#cta-rules}

### Modes

| Mode | When to use | Example shape |
|------|-------------|----------------|
| **Direct link CTA** | `source_public_url` is publish-confirmed and blog is live | "I wrote the full breakdown here: {url}" |
| **Soft CTA** | URL not yet confirmed; or first variant in pipeline before publish | "More detail in the article—link coming once published" OR insight-only close with no URL |
| **No CTA** | `short-provocative` variant MAY end on the insight alone | — |

### Publish-confirmed URL requirement

- Flow A LinkedIn variants with direct link CTA MUST use `source_public_url` returned from blog publish step—not derived/expected URL alone.
- Expected URL derivation (n8n `Compute Source Public URL`) is acceptable for **generation hints** only until publish confirms.
- MUST NOT claim article is live with a URL that returns 404.

### CTA content rules

- Include URL **at most once** per post.
- Vary phrasing across variants (see `#no-redundancy-rules`).
- No engagement bait in CTA line.
- No "follow for more" as primary close.

### Blog vs LinkedIn

- Blog: minimal CTA (see `#blog-post-rules`).
- LinkedIn: CTA is allowed and encouraged when URL confirmed—LinkedIn is distribution.

---

## 14 Flow A vs Flow B {#flow-a-vs-flow-b}

Publication policy consistent with product backlog P4 (simplified Flow B) and Flow A roadmap. Normative ops policy: [flow-b-simplified-policy.md](../docs/operations/flow-b-simplified-policy.md).

| Dimension | Flow A | Flow B |
|-----------|--------|--------|
| **Content source** | User-provided blog in `blog-posts/ready/` | AI topic discovery (DeepSeek v1) + AI blog draft in `blog-posts/pending-approval/` |
| **Career / authority objective** | Same brand positioning | Discovery brief MUST favor senior leadership / architecture / transformation / AI authority (≥ ~USD 7,000); **referent**, not news spreader |
| **Pre-approval** | After automated validation passes | Blog draft never pre-approved |
| **Human review (core)** | **Not required** after validation for blog publish, package, or schedule | **Required** for the **blog draft** only (in **Silverman Authority Manager**) |
| **Human review (LinkedIn API)** | **Not mandatory** — optional supervision while `pending` before API send (edit, delay, cancel; mechanics US-017) | **Same as Flow A** after blog approval — optional supervision only |
| **Blog publish** | MAY proceed automatically | MUST NOT until recorded blog approval + promote to `ready/`; then MAY via Flow A |
| **LinkedIn package / schedule** | MAY generate automatically | MUST NOT until blog approval; then MAY via Flow A (spill algorithm A for surplus slots) |
| **LinkedIn publish** | Expected per `#linkedin-distribution-strategy` when integration and enablement allow; optional supervision | Same as Flow A after blog approval |
| **Calendar role** | Consumes scheduled variants | **Weekly gap sensor** (next local week; gap = 0 LinkedIn posts; typically Friday → following week; up to 2 drafts) may trigger Flow B (BL-019) |
| **Implementation status** | Active (console / publish path per CURRENT-STATE) | Backlog BL-016–BL-019 (US-074–US-082); not yet implemented |

### Flow A automatic path (operational)

1. User places `<source_slug>.md` + `.png` in `blog-posts/ready/` (including Flow B drafts promoted from `pending-approval/` after approval).
2. `POST /validate-ready-post` (future) passes structural + editorial checks.
3. Blog publishes to GitHub Pages; `source_public_url` confirmed.
4. Derivative package generated (≥3 variants).
5. Variants scheduled per `#linkedin-distribution-strategy` (`publish_state` `pending` = optional supervision window).
6. LinkedIn API queue/publish per strategy when integration, enablement, and automation (e.g. BL-007) allow — not blocked on mandatory per-variant human approval.

### Flow A LinkedIn supervision (optional)

While variants remain `pending` before API queue/send, the operator MAY edit, delay, or cancel. Non-intervention means publication proceeds per schedule. This is not a mandatory approval gate. Detail: [linkedin-variant-review-policy.md](../docs/operations/linkedin-variant-review-policy.md).

### Flow B path (simplified)

1. Trigger (weekly calendar gap sensor via n8n→HTTP and/or explicit operator/orchestration trigger).
2. AI (DeepSeek v1) discovers an authority-aligned thesis (not news); sources: brief + canon + soft anti-dup; hand-curated BL-020 backlog is optional, not required.
3. AI generates blog draft + image into **`blog-posts/pending-approval/`**; **no** auto-publish.
4. Operator **approves** or **rejects** the blog in **Silverman Authority Manager** (single hard gate; no revision CMS required in P4).
5. On approve: recorded approval + promote/move from `pending-approval/` to `blog-posts/ready/`.
6. From then on: identical to Flow A (including optional LinkedIn supervision and spill algorithm A for surplus LinkedIn slots).

### Flow B guardrail

Unapproved drafts in `blog-posts/pending-approval/` MUST NOT enter Flow A automatic publish paths. After recorded operator blog approval and promote to `ready/`, content MAY enter Flow A like other ready posts.

---

## 15 Machine-Readable Anchors {#machine-readable-anchors}

### Format

Level-2 headings use explicit anchor suffix:

```markdown
## {number} {Title} {#anchor-id}
```

### Parsing note (for future worker)

Extract sections with regex:

```text
^## .+ \{#([a-z0-9-]+)\}\s*$
```

Section body = lines after heading until next `^## ` heading. Trim whitespace; body MUST be non-empty.

If file missing or anchor not found, return structured error `editorial_canon_missing` or `editorial_canon_section_missing` — do not fall back to hardcoded defaults.

### Anchor registry

| Anchor ID | Title | Consumption classes |
|-----------|-------|---------------------|
| `purpose` | Purpose | validation, prompt |
| `brand-positioning` | Brand Positioning | prompt |
| `business-goals` | Business Goals | prompt |
| `audience-map` | Audience Map | prompt, scheduling |
| `content-pillars` | Content Pillars | validation, prompt |
| `topic-boundaries` | Topic Boundaries | validation, prompt |
| `blog-post-rules` | Blog Post Rules | validation |
| `linkedin-derivative-package` | LinkedIn Derivative Package | prompt |
| `linkedin-distribution-strategy` | LinkedIn Distribution Strategy | scheduling |
| `no-redundancy-rules` | No-Redundancy Rules | prompt, scheduling |
| `anti-ai-writing-rules` | Anti-AI-Writing Rules | validation, prompt |
| `voice-and-style` | Voice and Style | prompt |
| `cta-rules` | CTA Rules | prompt, scheduling |
| `flow-a-vs-flow-b` | Flow A vs Flow B | validation |
| `machine-readable-anchors` | Machine-Readable Anchors | validation |
| `validation-and-prompt-usage` | Validation and Prompt Usage | validation |
| `examples` | Examples | prompt |

---

## 16 Validation and Prompt Usage {#validation-and-prompt-usage}

### Consumption classes

| Class | Subsystem | Behavior |
|-------|-----------|----------|
| `validation` | `POST /validate-ready-post` (future) | Blocking checks; load sections marked validation |
| `prompt` | `linkedin-derivative-package-generation` (future) | Inject into LLM system/user context |
| `scheduling` | `linkedin-distribution-scheduling-model` (future) | Compute `scheduled_at` per variant |

### Section load map

| Child change | Anchors to load |
|--------------|-----------------|
| `ready-post-editorial-validation` | `blog-post-rules`, `topic-boundaries`, `anti-ai-writing-rules` (warnings), `flow-a-vs-flow-b` |
| `linkedin-derivative-package-generation` | `linkedin-derivative-package`, `anti-ai-writing-rules`, `voice-and-style`, `cta-rules`, `no-redundancy-rules`, `audience-map`, `content-pillars` |
| `linkedin-distribution-scheduling-model` | `linkedin-distribution-strategy`, `no-redundancy-rules`, `cta-rules`, `audience-map` |
| `flow-a-lifecycle-and-duplicate-prevention` | `flow-a-vs-flow-b` |
| Future Flow B review | `flow-a-vs-flow-b`, `anti-ai-writing-rules` (blocking), `topic-boundaries` |

### Loading rules

- Load only required anchors for the operation—do not inject full file into every prompt.
- On missing file: fail with `editorial_canon_missing`.
- On missing anchor: fail with `editorial_canon_section_missing`.
- Section-presence test in CI (`tests/test_editorial_canon.py`) guards anchor drift.

### Current state (this change)

Canon is documentation + CI presence test only. `linkedin_prompt.py` hardcoded fragments remain until `linkedin-derivative-package-generation` replaces them.

---

## 17 Examples {#examples}

### Worked example: Why I Did Not Start With the Database

| Field | Value |
|-------|-------|
| Source file | `blog-posts/ready/01-why-i-did-not-start-with-the-database.md` |
| `source_slug` | `01-why-i-did-not-start-with-the-database` |
| `public_slug` | `why-i-did-not-start-with-the-database` |
| Public URL | `https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/` |
| Primary pillars | Domain-first design, software architecture, practical delivery discipline |
| Thesis (blog) | Model the domain and boundaries before choosing persistence; the database is an implementation detail, not the starting blueprint. |

#### Variant 1: executive-recruiter

- **Hook:** "The most expensive refactor I avoided wasn't code—it was committing to a schema before we agreed what the business event actually was."
- **Objective:** Signal senior judgment and hireable architecture leadership to recruiters/C-level.
- **Angle:** Business risk of premature persistence; decision discipline under delivery pressure.
- **Structure:** Stakes → decision → outcome → link CTA.
- **CTA phrasing:** "Full write-up on domain-first delivery: {source_public_url}"

#### Variant 2: technical-architect

- **Hook:** "If your first artifact is an ERD, you've already chosen bounded contexts for the business."
- **Objective:** Teach architects the boundary-first move and naming trade-offs.
- **Angle:** Aggregate roots, invariants, and where ORM convenience distorts the model.
- **Structure:** Constraint → pattern → failure mode avoided → link CTA.
- **CTA phrasing:** "I broke down the modeling steps here: {source_public_url}"

#### Variant 3: engineering-leadership

- **Hook:** "Your team isn't slow because they lack ORM skill—they're debating domain language that should have been settled in week one."
- **Objective:** Help EMs recognize process smell and coach toward domain workshops before sprint velocity metrics.
- **Angle:** Team dynamics, backlog churn, and when to pause feature work for modeling.
- **Structure:** Team symptom → root cause → leadership action → link CTA.
- **CTA phrasing:** "How we reset the sprint around domain clarity: {source_public_url}"

#### Variant 4: short-provocative

- **Hook:** "Starting with the database is a confession that you let persistence design your product language."
- **Objective:** Pattern interrupt for senior ICs and architecture enthusiasts.
- **Angle:** One sharp claim; minimal setup; no tutorial tone.
- **Structure:** Bold line → 3 short paragraphs → optional single-line link CTA.
- **CTA phrasing:** "{source_public_url}" (minimal) OR no CTA if post stands alone.

**Redundancy check:** Four distinct hooks, four objectives, four structures, four CTA phrasings—compliant with `#no-redundancy-rules`.

**Distribution sketch:** Publish executive-recruiter Tuesday 09:00 → technical-architect Friday+3 09:00 → short-provocative Tuesday+6 17:00 → engineering-leadership Friday+9 09:00 (if 4-variant package). America/Bogota.

### Style transformation examples

Short before/after pairs illustrating `#voice-and-style` and `#anti-ai-writing-rules`.

#### Example A

**Bad:**

> In today's fast-paced world, databases are the backbone of every modern application.

**Better:**

> The database matters. But it should not be the first thing that defines the system.

#### Example B

**Bad:**

> Here are five reasons why domain-first design is a game-changer.

**Better:**

> Domain-first design is not a slogan. It is a way to avoid letting infrastructure decisions name the business.

#### Example C

**Bad:**

> Agree or disagree? Drop your thoughts in the comments.

**Better:**

> I wrote the full breakdown here: {source_public_url}

#### Example D

**Bad:**

> AI is revolutionizing software architecture.

**Better:**

> AI can accelerate architecture work, but only if the team already knows what decisions it is trying to make.

#### Example E

**Bad:**

> This architecture is robust, scalable, and future-proof.

**Better:**

> This design reduces coupling now, but it also creates a new ownership problem the team has to accept.

---

*Document version: editorial-canon-and-linkedin-distribution-strategy (child change 1). Git-tracked; worker runtime loading deferred.*
