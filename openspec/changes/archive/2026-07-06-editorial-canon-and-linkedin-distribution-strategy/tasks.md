## 1. Editorial canon artifact

- [x] 1.1 Create `content-strategy/` directory and `content-strategy/silverman-editorial-system.md`
- [x] 1.2 Write `#purpose` — operational scope; cite umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`; blog canonical, LinkedIn derivative
- [x] 1.3 Write `#brand-positioning` — Silverio Bernal / silverman.pro; Solutions Architect; domain-first; practical architecture leadership
- [x] 1.4 Write `#business-goals` — recruiter attraction (remote senior > USD 6000/month); thought leadership; blog traffic without influencer tone
- [x] 1.5 Write `#audience-map` — six lenses with variant mapping hints
- [x] 1.6 Write `#content-pillars` — seven pillars with brief operational definitions
- [x] 1.7 Write `#topic-boundaries` — allowed, weak/deferred, forbidden/low-value lists
- [x] 1.8 Write `#blog-post-rules` — frontmatter, slugs, PNG pair, structure, depth, argument style, blog CTA
- [x] 1.9 Write `#linkedin-derivative-package` — package concept, min 3 / max 4 variants, variant definitions, post-type recommendations
- [x] 1.10 Write `#linkedin-distribution-strategy` — cadence (min 3 days), max 1/day/campaign, audience sequencing, scheduling windows, anti-simultaneous publish
- [x] 1.11 Write `#no-redundancy-rules` — hooks, objectives, thesis, CTA language, structure uniqueness
- [x] 1.12 Write `#anti-ai-writing-rules` — forbidden patterns; strong for generated; warning for Flow A user blog; no perfect-detection claim
- [x] 1.13 Write `#voice-and-style` — senior, practical, direct, human; rhythm and avoid list
- [x] 1.14 Write `#cta-rules` — direct link vs soft CTA; publish-confirmed URL requirement; no engagement bait
- [x] 1.15 Write `#flow-a-vs-flow-b` — policy table matching umbrella; Flow B deferred note
- [x] 1.16 Write `#machine-readable-anchors` — anchor registry and parsing note
- [x] 1.17 Write `#validation-and-prompt-usage` — map anchors to validation / prompt / scheduling consumption
- [x] 1.18 Write `#examples` — `Why I Did Not Start With the Database` with four variant strategy sketches (executive, technical architect, engineering leadership, short provocative)

## 2. Automated section checks

- [x] 2.1 Add `tests/test_editorial_canon.py` (or equivalent) asserting all required `#anchor-id` headings exist with non-empty bodies
- [x] 2.2 Run pytest for editorial canon test and fix any missing sections

## 3. Documentation and validation

- [x] 3.1 Update README with pointer to `content-strategy/silverman-editorial-system.md` only if not already documented
- [x] 3.2 Run `openspec validate editorial-canon-and-linkedin-distribution-strategy --strict`
- [x] 3.3 Run `openspec validate --all --strict`

## 4. Deferred to future child changes (reference only — do not implement here)

> These items are tracked under umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` sections 3–9. Cite this canon from those changes; do not implement under `/opsx-apply` for this change.

- [ ] 4.1 `flow-a-lifecycle-and-duplicate-prevention` — campaign metadata schema and state machine
- [ ] 4.2 `ready-post-editorial-validation` — `POST /validate-ready-post`; load `#blog-post-rules`, `#topic-boundaries`
- [ ] 4.3 `worker-blog-publishing-endpoint` — `POST /publish-blog-post`
- [ ] 4.4 `linkedin-derivative-package-generation` — multi-variant package; replace hardcoded prompt fragments with canon sections
- [ ] 4.5 `linkedin-distribution-scheduling-model` — apply `#linkedin-distribution-strategy` defaults
- [ ] 4.6 `n8n-flow-a-blog-publish-orchestration` — full Flow A HTTP chain
- [ ] 4.7 `linkedin-publication-integration` — deferred LinkedIn API publish
