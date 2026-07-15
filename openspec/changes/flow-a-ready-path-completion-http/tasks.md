## 1. Worker ready-path completion HTTP

- [x] 1.1 Add service helper that runs `complete_flow_a_source_lifecycle` then optional calendar upsert/reconcile from campaign (match by `campaign_id` / source path; insert completed item when no match; `skipped_calendar_absent` when calendar missing)
- [x] 1.2 Expose authenticated `POST /complete-flow-a-ready-path` in `main.py` with request fields `campaign_id`, optional `source_relative_path`, `update_calendar` (default true)
- [x] 1.3 Map overall response `status` to `completed` | `partial` | `failed` | `skipped` per `flow-a-ready-path-completion` spec; never invoke LinkedIn publication endpoints
- [x] 1.4 Add unit/API tests: auth failure, premature lifecycle, successful ready→processed, idempotent skip, calendar insert, calendar match-complete, calendar absent skip, calendar failure → partial

## 2. n8n Flow A orchestration export

- [x] 2.1 Extend Set Configuration with `git_publication` and `live_site_confirmation` (export defaults false)
- [x] 2.2 Update Publish Blog Post body to forward those opt-ins when true
- [x] 2.3 Add post-schedule HTTP node `POST /complete-flow-a-ready-path` with IF branching (failed / partial / success) before lock release
- [x] 2.4 Update lightweight workflow validation tests and README Flow A node-flow / config docs

## 3. Docs and context

- [x] 3.1 Update `docs/CURRENT-STATE.md` for ready-path completion capability (implemented vs validated once evidenced)
- [x] 3.2 Cross-link BL-005 ops note that Manual FAIL root cause is addressed by this change (no claim BL-005 closed)

## 4. Verify and handoff to BL-005

- [x] 4.1 Run targeted pytest for new/changed modules; `openspec validate flow-a-ready-path-completion-http --strict`; `git diff --check`
- [x] 4.2 Prepare `/opsx-verify` (exclude BL-007 WIP from commits)
- [x] 4.3 Business validation handoff: after explicit deploy + n8n re-import/activate + server Set Configuration git/live true, resume `/opsx-apply run-fully-unattended-flow-a-test-bl-005` for Manual revalidation then Schedule — do not mark US-012–US-014 complete in this change alone
