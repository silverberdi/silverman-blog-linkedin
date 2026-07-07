## 1. Planning Review

- [x] 1.1 Review and approve `proposal.md` — Flow A orchestration motivation, goals, non-goals, umbrella citation
- [x] 1.2 Review and approve `design.md` — baseline workflow, node sequence, HTTP payloads, identifier flow, error branching, idempotency, API key handling
- [x] 1.3 Review and approve `specs/n8n-flow-a-blog-publish-orchestration/spec.md` — inactive export, endpoint chaining, failure branches, no LinkedIn API
- [x] 1.4 Run `openspec validate n8n-flow-a-blog-publish-orchestration --strict` and fix any issues

> **Out of scope for this change:** git commit, git push, archiving the umbrella, archiving this child, activating production cron, LinkedIn API publication.

## 2. Flow A Workflow JSON

- [x] 2.1 Create `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` as a separate artifact (do not modify `silverman-blog-linkedin-draft-generation.json`)
- [x] 2.2 Implement node sequence: Manual Trigger → Set Configuration → Health Check → IF Health Ready → Process Ready → candidate iteration → Publish Blog Post → IF Publish Completed → Generate LinkedIn Package → IF Package Completed → Schedule LinkedIn Distribution → IF Schedule Completed → success/failure Set nodes
- [x] 2.3 Wire `POST /publish-blog-post` with `source_relative_path` from `valid_files[].relative_path`; branch on `status` and expose `errors[]`
- [x] 2.4 Wire `POST /generate-linkedin-package` with `campaign_id` (fallback `source_relative_path`) from publish response; branch on `status`
- [x] 2.5 Wire `POST /schedule-linkedin-distribution` with `campaign_id` from package response; branch on `status`; expose `variant_schedules[]` with `publish_state` `pending`
- [x] 2.6 Use Bearer `Authorization` expressions referencing **Set Configuration** `worker_api_key` placeholder — no production secrets in export
- [x] 2.7 Set `"active": false`; Manual Trigger only — no Cron/Webhook/Schedule Trigger nodes
- [x] 2.8 Confirm workflow contains no Execute Command, SSH, filesystem, GitHub, LinkedIn, or direct LLM provider nodes

## 3. Tests and Documentation

- [x] 3.1 Add or extend lightweight workflow validation tests (follow `tests/test_n8n_workflow.py` patterns) for `silverman-blog-linkedin-flow-a-publish.json`: parse, inactive export, endpoint fragments (`/publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution`), forbidden nodes, secret patterns, API key expression
- [x] 3.2 Assert draft-generation workflow tests in `tests/test_n8n_workflow.py` remain unchanged and passing
- [x] 3.3 Update README with Flow A workflow import path, configuration fields, distinction from draft-generation workflow, inactive export note, and end-to-end smoke test steps

## 4. Verification

- [x] 4.1 Run `pytest tests/test_n8n_workflow.py` and new Flow A workflow tests locally
- [x] 4.2 Run `openspec validate n8n-flow-a-blog-publish-orchestration --strict`
- [x] 4.3 Run `openspec validate --all --strict`
- [ ] 4.4 Manual smoke test on Ubuntu server: import workflow, set API key, place test post in `blog-posts/ready/`, execute manually, verify campaign metadata and generated artifacts; re-run and confirm idempotent worker responses

## 5. Explicitly Out of Scope

- [ ] 5.1 Git commit — not part of this change implementation unless operator requests separately
- [ ] 5.2 Git push — not part of this change
- [ ] 5.3 Archive umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` — remains active
- [ ] 5.4 Archive this child change — separate `/opsx-archive` after apply and verification
- [ ] 5.5 LinkedIn API publication — deferred to slice 8
- [ ] 5.6 Production cron/workflow activation — deferred to future operational change
- [ ] 5.7 Source blog file moves between editorial folders — not proposed in this slice
