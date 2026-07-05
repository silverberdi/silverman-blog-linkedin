# OpenAI Content Generation Context

## Role in the System

The worker uses an LLM (expected: OpenAI API) to transform Markdown blog posts into LinkedIn draft variants. Generation is **downstream of canonical blog content**—the model rewrites and reframes; it does not replace editorial ownership of the original article.

## Expected Generation Behavior

For each input blog post:

1. Read Markdown from `blog-posts/ready/` (or specified file for `/process-file`).
2. Load prompt templates from `prompts/` (exact template structure defined in implementation change).
3. Generate at least three LinkedIn variants per post (see editorial-operating-model.md).
4. Write drafts as files under `linkedin-posts/review/` with naming that links back to the source blog post.
5. Record generation metadata (model, timestamps, variant types) in run/campaign metadata.

Generation must be deterministic enough for review: consistent structure, identifiable variant type, traceable source filename.

## LinkedIn Generation Rules

Each variant must:

- Stay faithful to claims and examples in the source blog post
- Use English
- Match the variant intent (executive, technical leadership, short provocative)
- Respect LinkedIn length conventions (short variant especially tight)
- Avoid hashtags spam and engagement bait clichés unless the prompt template explicitly allows restrained use

Each variant must **not**:

- Introduce facts, metrics, client names, or project details absent from the blog
- Present tool comparisons or vendor rankings
- Comment on breaking news or industry headlines unrelated to the article
- Read like generic AI marketing copy

## Positioning Rules

Generated content should reinforce positioning as a senior Solutions Architect who connects:

- Technology decisions ↔ business value
- Architecture ↔ cost and risk reduction
- Delivery ↔ governance and operational efficiency

The voice is practical and executive-friendly—credible to recruiters and C-level readers evaluating remote senior roles (~USD 7k/month target band).

## Phase 1 Exclusions

| Exclusion | Note |
|-----------|------|
| Dairector content | Out of scope for phase 1; no prompts or outputs for Dairector |
| Auto-publish to LinkedIn | Human review required; drafts land in `review/` only |
| GitHub blog sync | Blog posts are placed manually in phase 1 |

## Personal Stories and Claims

**Do not invent unsupported personal stories.**

If the blog post does not describe a specific experience, the generated LinkedIn text must not fabricate one. Prefer:

- Paraphrasing the article's stated experience
- Abstracting to general architectural principles when the blog is principle-focused
- Omitting personal anecdote rather than inventing it

Reviewers in `linkedin-posts/review/` remain the final gate; generation rules exist to reduce editorial cleanup and reputational risk.

## Prompt and Model Configuration

Prompt templates live in `prompts/` and should be versioned in the repository. Model name, temperature, and token limits are environment-configurable. API keys must never appear in generated files, HTTP responses, or committed configuration.

Implementation details (exact prompt files, Pydantic schemas, retry logic) belong in approved OpenSpec changes, not in this context document.
