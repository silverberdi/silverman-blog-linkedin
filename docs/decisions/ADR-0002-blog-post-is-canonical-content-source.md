# ADR-0002: Blog Post Is Canonical Content Source

## Status

Accepted

## Context

The content automation system produces both long-form blog articles and shorter LinkedIn posts. Without an explicit rule, tooling or prompts might treat LinkedIn as co-equal authoring targets, leading to inconsistent messaging, fabricated anecdotes, or duplicated editorial effort.

## Decision

**Markdown blog posts are the canonical content source.** LinkedIn posts are **generated distribution assets** derived from blog posts. The worker reads from `blog-posts/` and writes LinkedIn drafts to `linkedin-posts/`.

For each blog post, the system should eventually produce at least three LinkedIn variants:

1. Executive / recruiter version
2. Technical leadership version
3. Short provocative version

## Rationale

- One authoritative article reduces drift between channels
- Reviewers can trace every LinkedIn draft back to a source file
- Generation prompts can enforce fidelity to the blog rather than inventing standalone narratives
- Aligns with business goal: blog demonstrates depth; LinkedIn extends reach

## Consequences

### Positive

- Clear folder semantics (`ready` → process → `review`)
- Metadata can link variants to source blog filename/campaign
- Editorial review focuses on reframing quality, not fact-checking against unknown sources

### Negative

- LinkedIn-only ideas require writing a blog post first (or a future exception process not in phase 1)

### Neutral

- Human reviewers may edit LinkedIn drafts in `review/` before approval; canonical rule applies to generation inputs, not minor post-generation edits
- Dairector and other content types remain out of phase 1 scope

## Related Documents

- [docs/CURRENT-STATE.md](../CURRENT-STATE.md)
- [docs/CONTEXT-AUTHORITY.md](../CONTEXT-AUTHORITY.md)
- [docs/GLOSSARY.md](../GLOSSARY.md)
- `docs/context/editorial-operating-model.md`
- `docs/context/openai-content-generation-context.md`
