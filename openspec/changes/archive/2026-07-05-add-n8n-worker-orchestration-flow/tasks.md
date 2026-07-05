## 1. Workflow JSON scaffold

- [x] 1.1 Create `n8n/workflows/` directory and `silverman-blog-linkedin-draft-generation.json` with Manual Trigger as entry node
- [x] 1.2 Add workflow variables (or documented Set node) for `worker_base_url` and `worker_api_key` with non-secret placeholders
- [x] 1.3 Name nodes clearly for operator debugging (`Health Check`, `Process Ready`, `Process File`, `Generate LinkedIn Draft`, etc.)

## 2. HTTP Request nodes (worker chain)

- [x] 2.1 Add HTTP Request node for `GET {{worker_base_url}}/health` (no auth required)
- [x] 2.2 Add optional IF branch on health response before processing
- [x] 2.3 Add HTTP Request node for `POST {{worker_base_url}}/process-ready` with `Authorization: Bearer {{worker_api_key}}` and JSON content type
- [x] 2.4 Add IF node: when `valid_count` is 0 or `valid_files` empty, route to clean stop (No Operation); otherwise continue
- [x] 2.5 Add IF node: when `process-ready` `status` is `failed`, stop with error context exposed

## 3. Per-candidate iteration and file read

- [x] 3.1 Add Split In Batches or Loop Over Items on `valid_files` from process-ready response
- [x] 3.2 Add HTTP Request node for `POST {{worker_base_url}}/process-file` with body `{ "relative_path": "<candidate.relative_path>" }` and Bearer auth
- [x] 3.3 Add IF node: proceed to generate only when process-file `status` is `completed` and `markdown_content` is present; otherwise branch to per-item failure output with `errors`

## 4. Draft generation and branching

- [x] 4.1 Add HTTP Request node for `POST {{worker_base_url}}/generate-linkedin-draft` with mapped body: `source_relative_path`, `markdown_content`, `source_content_sha256`, and static `tone` / `audience` / `variant` hints documented in README
- [x] 4.2 Add IF node branching on generate response `status` (`completed` vs `failed`)
- [x] 4.3 Completed branch: expose `draft_relative_path`, `metadata_path`, and optionally `generated_draft_content` via Set or output fields
- [x] 4.4 Failed branch: expose `errors` and `metadata_path` when available
- [x] 4.5 Confirm workflow contains no Execute Command, filesystem, LinkedIn publish, GitHub, or direct LLM provider HTTP nodes

## 5. Security and export hygiene

- [x] 5.1 Audit exported JSON for hardcoded secrets; ensure only placeholders or expressions remain
- [x] 5.2 Ensure all authenticated worker calls use Bearer header from variable/credential expression, not literal tokens

## 6. Documentation

- [x] 6.1 Update `README.md` with workflow import steps, variable/credential configuration, node flow summary, static editorial hints location, and constraints (no file moves, review-only output)
- [x] 6.2 Cross-reference ADR-0001 and existing worker endpoint documentation

## 7. Lightweight validation

- [x] 7.1 Add `tests/test_n8n_workflow.py` (or equivalent script) validating JSON parse, required node types, workflow file path, and absence of obvious secret patterns
- [x] 7.2 Wire validation into existing pytest suite

## 8. Validation

- [x] 8.1 Run full test suite (`pytest`) and ensure all tests pass
- [x] 8.2 Run `openspec validate add-n8n-worker-orchestration-flow`
- [x] 8.3 Run `openspec validate --all`
- [ ] 8.4 Manual smoke test (optional): import workflow into n8n, configure variables, run against local worker with a ready `.md` file and `DEEPSEEK_API_KEY` set; confirm draft in `linkedin-posts/review/` and source file unchanged in `blog-posts/ready/`
