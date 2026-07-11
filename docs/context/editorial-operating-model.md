# Editorial Operating Model

Terminology: [GLOSSARY.md](../GLOSSARY.md). Flow A vs Flow B: [flow-a-target-flow.md](../workflows/flow-a-target-flow.md), [linkedin-draft-review-flow.md](../workflows/linkedin-draft-review-flow.md).

## Canonical Content Rule

**The blog post is the canonical content source.**

Every LinkedIn variant must be derived from an existing Markdown blog post. The worker does not invent standalone LinkedIn narratives disconnected from blog content. Edits during review may refine tone and length, but the underlying claims, examples, and positioning must trace back to the source article.

## LinkedIn as Distribution

LinkedIn posts are **generated distribution assets**, not primary authoring targets. They exist to:

- Reach recruiters and executives in a native feed format
- Repackage blog insights for different audience lenses
- Support a repeatable pipeline from one article to multiple outbound messages

## Content Pillars

Content should connect technology decisions with:

- Business value
- Cost reduction
- Risk reduction
- Delivery discipline
- Governance
- Operational efficiency

Topics may include AI, software architecture, digital transformation, agility, and technology efficiency—but always anchored in practical, senior-level experience rather than abstract commentary.

## Tone Rules

- Practical and senior
- Clear and executive-friendly
- Grounded in real software architecture work
- Direct; avoid hype and buzzword stacking
- English as the primary language

Write for someone who evaluates whether this person can lead architecture decisions, not someone looking for tool tutorials.

## Forbidden Content Types

Do **not** produce content that is:

| Type | Why |
|------|-----|
| News commentary | Dates quickly; does not demonstrate enduring architecture judgment |
| Tool comparisons | Shifts focus from decisions and outcomes to vendor features |
| Generic AI hype | Undermines credibility with senior audiences |
| Unsupported personal stories | Fabricated anecdotes damage trust; only use what the source blog supports |

## LinkedIn Variants

For each blog post, the worker should eventually generate **at least three** LinkedIn variants:

1. **Executive / recruiter version** — Outcomes, business impact, leadership signals. Accessible to non-technical readers.
2. **Technical leadership version** — Architecture trade-offs, delivery discipline, governance, and engineering judgment.
3. **Short provocative version** — A sharp hook or contrarian framing that invites engagement without sacrificing accuracy.

All variants must remain faithful to the blog post. They differ in emphasis and length, not in factual basis.

## Review and Approval Flow (Flow B–adjacent)

```
blog-posts/ready/
        │
        ▼  (worker draft generation or Flow A package)
linkedin-posts/review/
        │
        ▼  (human review)
linkedin-posts/approved/
        │
        ▼  (manual publish or future guarded API)
linkedin-posts/published/
```

> **Historical note:** Early Phase 1 language described stopping at review only. Flow A now automates publish/package/schedule with human Git and LinkedIn publish remaining manual. See [CURRENT-STATE.md](../CURRENT-STATE.md) completion layers.

Flow A automatic path does not replace human review for Flow B drafts in `review/`. Campaign metadata in `metadata/campaigns/` is traceability authority for Flow A lifecycle.
