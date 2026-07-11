## 1. Docker image and Git binary

- [x] 1.1 Add `git` package installation to `Dockerfile` (mandatory; not optional)
- [x] 1.2 Add build-time or deploy verification that `git --version` succeeds in the built worker container
- [x] 1.3 Document Git binary requirement in deployment docs

## 2. Configuration, credentials, and module scaffold

- [x] 2.1 Add `github_pages_git_config.py` (or equivalent) parsing `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED`, branch, remote, and commit message template with safe defaults
- [x] 2.2 Create `github_pages_git_publication.py` with `GitRunner` protocol, subprocess implementation, and injectable fake for tests
- [x] 2.3 Document deploy-key operator setup: repository-scoped GitHub deploy key mounted read-only from worker secrets directory; no secrets in versioned files, HTTP responses, metadata, logs, or examples

## 3. Core Git publication service

- [x] 3.1 Implement artifact path resolution from publish result (`_posts/YYYY-MM-DD-<public-slug>.md`, `assets/images/<public-slug>.png`) with repo confinement checks
- [x] 3.2 Implement scoped `git add` for exactly two artifact paths (reject broad staging; leave unrelated dirty files untouched)
- [x] 3.3 Implement controlled `git commit` with template-based message (`public_slug`, `campaign_id`, `publication_date`)
- [x] 3.4 Implement `git push` to configured remote/branch without fetch/pull/rebase; map failures to `blog_git_publication_push_failed`
- [x] 3.5 Implement US-001 idempotency: repeat same-campaign successful push returns `already_published` without new commit or unnecessary push; preserve prior successful Git evidence
- [x] 3.6 Implement enablement guard (`blog_git_publication_disabled`) and Flow B rejection (`blog_git_publication_flow_b_not_allowed`)

## 4. Publish flow integration

- [x] 4.1 Extend `publish_blog_post(..., git_publication: bool = False)` to invoke Git publication after successful bridge apply when opted in and enabled
- [x] 4.2 Persist `blog_git_publication` metadata on campaigns (status, commit_sha, remote, branch, staged_paths, timestamps, error_code)
- [x] 4.3 Extend `BlogPublishResult` and HTTP serialization with `blog_git_publication` object; surface stable error codes in `errors[]`
- [x] 4.4 Extend `POST /publish-blog-post` request model with optional `git_publication` boolean (default false)
- [x] 4.5 Implement partial-failure semantics: handoff success + Git failure returns overall `status: partial` (not `failed`); preserve `blog_publish` success evidence; include actionable recovery message without secrets

## 5. Calendar execution connector integration

- [x] 5.1 Extend `execute_due_editorial_calendar_flow_a(..., git_publication: bool = False)` and pass opt-in to `publish_blog_post` during real execution
- [x] 5.2 Extend `POST /editorial-calendar/execute-flow-a-due` request model with optional `git_publication` boolean (default false)
- [x] 5.3 Ensure environment-only enablement does not trigger Git publication on calendar path
- [x] 5.4 Surface publish `partial` status and Git error codes in calendar item results when handoff succeeds but Git fails

## 6. Automated tests

- [x] 6.1 Add `tests/test_github_pages_git_publication.py` covering: disabled guard, environment-only enablement without opt-in, scoped staging, commit+push success, push failure returns partial, missing artifacts, idempotent `already_published` rerun, unrelated dirty files untouched, Flow B block
- [x] 6.2 Extend `tests/test_blog_publish_flow.py` for integrated publish with `git_publication: true` using Git runner fake; verify partial semantics
- [x] 6.3 Extend HTTP tests for `POST /publish-blog-post` with `git_publication` opt-in, environment-only no-publish, partial response, and auth behavior unchanged
- [x] 6.4 Extend `tests/test_editorial_calendar_flow_a_execute.py` for calendar `git_publication` opt-in passthrough, environment-only no-publish, and partial publish item results
- [x] 6.5 Run targeted pytest for touched modules; ensure zero new warnings attributable to this change

## 7. Documentation and operational context

- [x] 7.1 Update `docs/workflows/blog-publishing-bridge.md` — automatic Git when enabled and opted in, manual fallback, deploy-key setup (no secrets)
- [x] 7.2 Update `docs/deployment/ubuntu-server-worker-deployment.md` with Git publication env vars, deploy-key mount prerequisites, and Git binary verification
- [x] 7.3 Update `docs/CURRENT-STATE.md` — Git publication implemented vs operationally validated; adjust manual-steps and completion-layer table for US-001 scope
- [ ] 7.4 Update `docs/RUNTIME-STATE.md` if live enablement flag is set during validation

## 8. Business validation (US-001 only)

- [ ] 8.1 Configure deploy key on Ubuntu server (operational prerequisite) before validation
- [ ] 8.2 Controlled validation via `POST /publish-blog-post` **or** `POST /editorial-calendar/execute-flow-a-due` with `git_publication: true` after enablement; verify remote receives commit with only expected two files
- [ ] 8.3 Confirm response and campaign metadata show `blog_git_publication.status` `pushed` with `commit_sha` from real remote push evidence — do not claim live-site reachability (US-002 deferred)
- [ ] 8.4 Verify repeat same-campaign request returns `already_published` without duplicate commit
- [ ] 8.5 Verify handoff success + simulated or real push failure returns `partial` with preserved `blog_publish` evidence
- [ ] 8.6 Update `docs/product/progress-checklist.md` for US-001 only when acceptance criteria are demonstrated with real remote push evidence; leave US-002 and BL-001 unchecked

## 9. Verification gate

- [ ] 9.1 Run `/opsx-verify` for this change before commit approval
- [x] 9.2 Run `git diff --check` and secrets audit on modified files
