# Editorial Operating Model

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

## Review and Approval Flow

```
blog-posts/ready/
        │
        ▼  (worker processing)
linkedin-posts/review/
        │
        ▼  (human review)
linkedin-posts/approved/
        │
        ▼  (manual or future automated publish)
linkedin-posts/published/
```

Phase 1 stops at **review**. A human reviews drafts in `linkedin-posts/review/`, moves acceptable drafts to `approved/`, and publishes manually. Automatic publishing is a future phase.

Campaign and run metadata in `metadata/campaigns/` and `metadata/runs/` support traceability: which blog post produced which variants, when processing ran, and what outcomes occurred.
