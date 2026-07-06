## Why

The public blog at https://silverman.pro is live and the GitHub Pages publishing bridge is operational—a real article is already published (for example `https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/`). LinkedIn draft generation works from internal Markdown, but generated drafts do not point readers back to the canonical public article. That gap blocks the core distribution workflow: LinkedIn posts should drive traffic to the blog once a post is published, without manual copy-paste of URLs into every draft.

## Goals

- Accept an optional public blog URL on `POST /generate-linkedin-draft` and instruct DeepSeek to include it once as a natural end-of-post call to action.
- Accept an optional `topic_theme` editorial hint to support varied CTA wording (for example "Read the full {topic_theme} story here: {url}").
- Validate `source_public_url` as an `http` or `https` URL when provided; reject invalid URLs with HTTP `422`.
- Persist `source_public_url` and `topic_theme` in run metadata when provided; never store generated draft content or secrets.
- Echo `source_public_url` and `topic_theme` in the HTTP response when provided, consistent with optional editorial hints today.
- Preserve backward compatibility: requests without the new fields behave as today.

## Non-Goals

- LinkedIn API integration or auto-publishing to LinkedIn.
- Changing blog publishing behavior or triggering git operations.
- n8n Execute Command usage.
- `cta_style` or other CTA configuration knobs beyond `topic_theme` (defer to a later change if needed).
- Hashtags in generated drafts.
- Inferring or constructing public URLs inside the worker (n8n or the caller supplies the URL after publish).

## What Changes

- Extend `POST /generate-linkedin-draft` request body with optional `source_public_url` and `topic_theme` string fields.
- Add Pydantic validation for `source_public_url`: must be a valid `http` or `https` URL when present; continue rejecting unexpected extra fields with HTTP `422`.
- Extend `linkedin_prompt.build_chat_messages()` to include public URL and topic theme instructions only when provided, guiding the model to use the URL exactly once near the end as a natural, non-spammy CTA with varied wording.
- Extend `run_metadata` builders to include `source_public_url` and `topic_theme` when provided in the request.
- Extend HTTP response builders to echo `source_public_url` and `topic_theme` when provided.
- Add prompt, endpoint, metadata, and backward-compatibility tests.
- Update README with the new optional request fields and n8n orchestration note (pass public URL after GitHub Pages publish).

## Why a Dedicated HTTP Worker (Not n8n Execute Command)

Public URL validation, prompt construction, metadata persistence, and DeepSeek orchestration belong in the version-controlled worker. n8n should pass the published article URL from the GitHub Pages publish step via an HTTP Request node—never shell out to validate URLs or build LLM prompts on the server host.

## Capabilities

### New Capabilities

_None. This change extends an existing capability rather than introducing a new spec._

### Modified Capabilities

- `deepseek-linkedin-draft-generation`: Extend request body, prompt behavior, run metadata, HTTP response, and tests to support optional `source_public_url` and `topic_theme` for a single natural blog CTA in generated LinkedIn drafts.

## Impact

- **Repository**: `src/silverman_blog_linkedin/main.py` (request model), `linkedin_prompt.py`, `run_metadata.py`; tests in `tests/test_linkedin_prompt.py`, `tests/test_generate_linkedin_draft.py`, `tests/test_run_metadata.py`; README endpoint documentation.
- **APIs**: `POST /generate-linkedin-draft` gains two optional request/response fields; no new endpoints; existing endpoints unchanged.
- **n8n**: Workflows that publish to GitHub Pages can forward the resulting public URL into `POST /generate-linkedin-draft` without workflow script changes beyond mapping the new field.
- **Editorial data**: Run metadata may include `source_public_url` and `topic_theme`; draft files and metadata still exclude generated content bodies and secrets.
- **Security**: URL validation limits scheme to `http`/`https`; no secrets in responses or metadata.
