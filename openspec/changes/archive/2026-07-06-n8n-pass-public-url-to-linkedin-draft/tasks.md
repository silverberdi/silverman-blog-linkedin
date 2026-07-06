## 1. Workflow JSON — Set Configuration

- [x] 1.1 Add `source_public_url` assignment to **Set Configuration** with default empty string (or safe placeholder per design)
- [x] 1.2 Add `topic_theme` assignment to **Set Configuration** with default empty string
- [x] 1.3 Update **Set Configuration** node notes to mention optional public URL fields after publish

## 2. Workflow JSON — Generate LinkedIn Draft

- [x] 2.1 Update **Generate LinkedIn Draft** `jsonBody` expression to keep required field mapping (`source_relative_path`, `markdown_content`, `source_content_sha256`, `tone`, `audience`, `variant`)
- [x] 2.2 Add conditional inclusion of `source_public_url` only when **Set Configuration** value is non-empty after trim
- [x] 2.3 Add conditional inclusion of `topic_theme` only when **Set Configuration** value is non-empty after trim
- [x] 2.4 Verify exported JSON contains no real secrets or hardcoded production URLs

## 3. Workflow JSON — Success / failure visibility

- [x] 3.1 Extend **Set Generate Success** to expose `source_public_url` and `topic_theme` from worker response when present
- [x] 3.2 Optionally extend failure branch output with echoed optional fields if useful (not required)

## 4. README

- [x] 4.1 Add `source_public_url` and `topic_theme` rows to **Configure before first run** table
- [x] 4.2 Document that `source_public_url` should be set after the article is published to https://silverman.pro
- [x] 4.3 State explicitly that this workflow does not publish to GitHub Pages (CLI bridge is separate)
- [x] 4.4 Note future orchestration may pass `public_url` automatically from a publishing step
- [x] 4.5 Update success outcome bullets to mention optional echoed `source_public_url` / `topic_theme`

## 5. Lightweight workflow tests

- [x] 5.1 Assert **Set Configuration** includes `source_public_url` and `topic_theme` in assignments
- [x] 5.2 Assert **Generate LinkedIn Draft** `jsonBody` references `source_public_url` and maps it conditionally
- [x] 5.3 Assert **Generate LinkedIn Draft** `jsonBody` references `topic_theme` and maps it conditionally
- [x] 5.4 Assert optional fields are not sent as unconditional empty string literals
- [x] 5.5 Confirm existing tests still pass: no forbidden nodes, no direct LLM URLs, no real secrets, Bearer from `worker_api_key`, HTTP-only worker endpoints

## 6. Validation

- [x] 6.1 Run `pytest tests/test_n8n_workflow.py -v`
- [x] 6.2 Run `openspec validate n8n-pass-public-url-to-linkedin-draft`
- [x] 6.3 Manual smoke (optional): import workflow, set valid `source_public_url`, run against deployed worker, confirm echoed fields and draft CTA
