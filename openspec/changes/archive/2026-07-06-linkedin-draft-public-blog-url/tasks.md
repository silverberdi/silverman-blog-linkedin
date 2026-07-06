## 1. Request model and validation

- [x] 1.1 Add optional `source_public_url: str | None = None` and `topic_theme: str | None = None` to `GenerateLinkedinDraftRequest` in `main.py` with `extra="forbid"` unchanged
- [x] 1.2 Add `@field_validator` for `source_public_url`: reject empty/whitespace; require parseable URL with scheme `http` or `https` and non-empty `netloc`
- [x] 1.3 Add `@field_validator` for `topic_theme`: reject empty/whitespace when provided

## 2. Prompt builder

- [x] 2.1 Extend `build_chat_messages()` in `linkedin_prompt.py` with optional `source_public_url` and `topic_theme` parameters
- [x] 2.2 When `source_public_url` is set, append user-prompt section with exact URL, single-use natural CTA instructions, varied wording examples, anti-spam/repeat/invent rules, and no hashtags
- [x] 2.3 When `topic_theme` is set, include it in prompt (editorial hint when URL absent; CTA phrasing hint when URL present)
- [x] 2.4 When `source_public_url` is omitted, keep prompt output unchanged from current behavior

## 3. Route orchestration

- [x] 3.1 Pass `body.source_public_url` and `body.topic_theme` from `/generate-linkedin-draft` handler into `build_chat_messages()`
- [x] 3.2 Pass both fields into `build_generate_linkedin_draft_metadata_payload()` and `build_generate_linkedin_draft_response()` at all call sites

## 4. Metadata and response helpers

- [x] 4.1 Extend `build_generate_linkedin_draft_metadata_payload()` in `run_metadata.py` to accept and conditionally include `source_public_url` and `topic_theme`
- [x] 4.2 Extend `build_generate_linkedin_draft_response()` to accept and conditionally include `source_public_url` and `topic_theme` in the response dict

## 5. Tests — prompt

- [x] 5.1 Add test: `source_public_url` appears in user prompt when provided
- [x] 5.2 Add test: `source_public_url` absent from user prompt when omitted
- [x] 5.3 Add test: `topic_theme` appears in user prompt when provided
- [x] 5.4 Add test: prompt instructs single-use natural CTA with varied wording (not one fixed phrase)
- [x] 5.5 Add test: prompt without `source_public_url` has no CTA URL instructions

## 6. Tests — endpoint and metadata

- [x] 6.1 Add test: valid `https` `source_public_url` accepted past body validation
- [x] 6.2 Add test: invalid URL and disallowed schemes return HTTP `422`
- [x] 6.3 Add test: unexpected extra fields (including `cta_style`) still return HTTP `422`
- [x] 6.4 Add test: metadata includes `source_public_url`/`topic_theme` when provided and excludes `markdown_content`/`generated_draft_content`
- [x] 6.5 Add test: response echoes `source_public_url`/`topic_theme` when provided and omits keys when not
- [x] 6.6 Add backward-compatibility test: existing generation request without new fields still passes

## 7. Documentation and validation

- [x] 7.1 Update README `POST /generate-linkedin-draft` section with optional `source_public_url` and `topic_theme` fields and n8n note to pass URL after GitHub Pages publish
- [x] 7.2 Run `pytest` for affected test modules and confirm all pass
- [x] 7.3 Run `openspec validate linkedin-draft-public-blog-url` and `openspec validate --all`
