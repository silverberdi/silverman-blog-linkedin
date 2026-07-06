## Context

`POST /generate-linkedin-draft` is implemented and archived under `deepseek-linkedin-draft-generation`. It accepts blog Markdown in the request body, calls DeepSeek, writes one draft to `linkedin-posts/review/`, and records run metadata. The GitHub Pages publishing bridge is also implemented and archived; the public blog at https://silverman.pro serves canonical articles.

n8n orchestration typically chains: read blog post → publish to GitHub Pages → generate LinkedIn draft. After publish, the workflow knows the public article URL (for example `https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/`). Today that URL is not passed into draft generation, so LinkedIn drafts lack a blog call to action.

This change is a narrow extension: two optional request fields, prompt instructions, metadata/response echo, and tests. No new endpoints, no publishing changes, no LinkedIn API.

## Goals / Non-Goals

**Goals:**

- Add optional `source_public_url` and `topic_theme` to `GenerateLinkedinDraftRequest` with strict `extra="forbid"` preserved.
- Validate `source_public_url` at request time: non-empty string, parseable URL, scheme `http` or `https` only; HTTP `422` on failure.
- Pass both fields into `build_chat_messages()` only when provided.
- Instruct DeepSeek to include the public URL exactly once near the end as a natural CTA; allow varied wording; forbid inventing or modifying the URL; forbid repeating the URL; forbid hashtags.
- Persist and echo optional fields in metadata and HTTP response when provided.
- Keep backward compatibility for requests omitting both fields.

**Non-Goals:**

- `cta_style` or prompt-template configuration (MVP uses model variation plus optional `topic_theme` only).
- Worker-side URL construction from slug, date, or filesystem paths.
- LinkedIn publishing, blog publishing changes, git operations, n8n workflow JSON updates in this change.
- Storing generated draft content in metadata.

## Decisions

### 1. Extend existing request model rather than a new endpoint

**Decision:** Add `source_public_url: str | None = None` and `topic_theme: str | None = None` to `GenerateLinkedinDraftRequest` in `main.py`.

**Rationale:** Same orchestration step, same auth, same pre-checks. n8n already calls this endpoint after publish; forwarding one more field is simpler than a separate "enrich draft" endpoint.

**Alternatives considered:**

- **New `POST /enrich-linkedin-draft` endpoint:** Rejected—extra round trip and duplicate auth/pre-checks for a prompt-only concern.
- **Infer URL from `slug_hint`:** Rejected—publish path/date segments are owned by the GitHub Pages bridge; worker should not duplicate URL rules.

### 2. URL validation via Pydantic field validator

**Decision:** Use a `@field_validator` on `source_public_url` that:

- Returns `None` unchanged when the field is omitted or null.
- Rejects empty or whitespace-only strings with `ValueError` (HTTP `422`).
- Parses with `urllib.parse.urlparse` and requires `scheme` in `("http", "https")` and a non-empty `netloc`.
- Rejects `javascript:`, `file:`, scheme-relative URLs, and other non-http(s) schemes.

**Rationale:** Matches existing Pydantic validation style (`markdown_content`, `source_relative_path`). Fails fast before DeepSeek or directory pre-checks.

**Alternatives considered:**

- **Regex-only validation:** Rejected—`urlparse` is clearer for scheme/netloc checks.
- **Allow any scheme:** Rejected—business requirement limits to http/https.

### 3. Prompt changes in `linkedin_prompt.py` only when URL provided

**Decision:** Extend `build_chat_messages()` signature with optional `source_public_url` and `topic_theme`. When `source_public_url` is set, append a dedicated user-prompt section that:

- States the exact public article URL the model MUST use verbatim.
- Instructs use exactly once near the end as a natural CTA.
- Gives example phrasings (not fixed templates), including topic-themed variant when `topic_theme` is provided.
- Explicitly forbids spammy tone, URL repetition, URL invention/modification, and hashtags.

When `source_public_url` is omitted, prompt output is unchanged from current behavior.

When `topic_theme` is provided without `source_public_url`, include `topic_theme` as an editorial hint only (same pattern as `title`/`tone`); no CTA URL instructions.

**Rationale:** Minimal diff; backward compatible; keeps CTA logic conditional on the business trigger (published URL known).

### 4. Metadata and response echo pattern

**Decision:** Mirror existing optional editorial hints (`title`, `slug_hint`, `tone`, `audience`, `variant`):

- `build_generate_linkedin_draft_metadata_payload()` and `build_generate_linkedin_draft_response()` accept optional `source_public_url` and `topic_theme`.
- Include keys in JSON only when values are not `None` (omit when absent).
- Never add `markdown_content` or `generated_draft_content` to metadata.

**Rationale:** Consistent with established helpers in `run_metadata.py`; n8n can branch on echoed fields.

### 5. No `cta_style` in MVP

**Decision:** Defer `cta_style` enum or similar. Rely on model variation plus example phrasings in the prompt and optional `topic_theme`.

**Rationale:** User requested small MVP; additional configuration adds API surface without proven need.

### 6. Route wiring

**Decision:** In `main.py` `/generate-linkedin-draft` handler, pass `body.source_public_url` and `body.topic_theme` into `build_chat_messages()`, metadata builder, and response builder. No other route changes.

## Risks / Trade-offs

- **[Model may still repeat or omit URL]** → Mitigate with explicit prompt rules; human review remains mandatory (`linkedin-posts/review/`).
- **[Invalid URL accepted by loose parser]** → Require `http`/`https` and non-empty `netloc`; test edge cases (`not-a-url`, `javascript:alert(1)`).
- **[topic_theme without URL could confuse CTA expectations]** → Only emit URL CTA instructions when `source_public_url` is present; `topic_theme` alone stays editorial.
- **[n8n must supply correct URL]** → Document in README; worker does not verify URL resolves or matches slug.

## Migration Plan

1. Deploy updated worker container to Ubuntu server (same Docker pattern as prior changes).
2. Update n8n workflow to map GitHub Pages publish response public URL into `source_public_url` on `POST /generate-linkedin-draft` (workflow change outside this repo scope).
3. Rollback: redeploy previous worker image; requests without new fields continue to work on either version.

## Open Questions

_None for MVP. Revisit `cta_style` if editorial review shows insufficient CTA variety._
