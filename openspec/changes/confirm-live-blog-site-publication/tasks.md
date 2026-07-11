## 1. Inspect and configuration

- [x] 1.1 Read `github_pages_git_publication.py`, `blog_publish_flow.py`, `main.py`, `editorial_calendar_flow_a_execute.py`, and `github_pages_git_config.py` — confirm actual signatures before coding
- [x] 1.2 Add live-site confirmation settings to config module (`SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED`, probe timeout/retry env vars, host allowlist from site base URL)
- [x] 1.3 Add Git fetch timeout setting (`SILVERMAN_BLOG_GIT_FETCH_TIMEOUT_SECONDS`) alongside existing Git publication config

## 2. Git remote reconciliation (US-002)

- [x] 2.1 Extend `GitRunner` / `FakeGitRunner` with fetch and ff-only pull call tracking
- [x] 2.2 Implement `git fetch` before push in `github_pages_git_publication.py`
- [x] 2.3 Implement fast-forward-only reconciliation when local branch is behind remote (treat "unrelated dirty files" as changes outside scoped `staged_paths` in working tree or index)
- [x] 2.4 Return `blog_git_publication_remote_diverged` (partial after handoff) when ff-only is not possible
- [x] 2.5 Implement cross-campaign duplicate artifact detection before commit (`blog_git_publication_duplicate_artifacts`)
- [x] 2.6 Extend Git publication unit tests: fetch before push, ff-only success, divergence failure, duplicate artifacts blocked

## 3. Live-site confirmation module

- [x] 3.1 Create `blog_live_site_confirmation.py` with injectable `HttpProbeClient` protocol and production stdlib implementation
- [x] 3.2 Implement guarded enablement, git-required guard, host allowlist validation, and slug body marker check
- [x] 3.3 Implement bounded retry probe with configurable timeout, attempts, and delay
- [x] 3.4 Persist `blog_live_site_publication` campaign metadata (`confirmed`, `failed`, `already_confirmed`, evidence fields)
- [x] 3.5 Return structured result for publish flow (`partial` when push succeeded but probe failed)
- [x] 3.6 Add unit tests with HTTP fakes: disabled guard, git-required, success, retry, exhausted failures, idempotent `already_confirmed`, invalid host

## 4. Publish flow and HTTP integration

- [x] 4.1 Extend `publish_blog_post(..., live_site_confirmation: bool = False)` to orchestrate live confirmation after Git push evidence
- [x] 4.2 Add `live_site_confirmation` to `POST /publish-blog-post` request model and response serialization
- [x] 4.3 Extend publish error codes and recovery messages for live confirmation failures
- [x] 4.4 Add HTTP tests for live confirmation opt-in, partial probe failure, and disabled guard

## 5. Calendar connector passthrough

- [x] 5.1 Extend `execute_due_editorial_calendar_flow_a(..., live_site_confirmation: bool = False)` and pass through to `publish_blog_post`
- [x] 5.2 Add `live_site_confirmation` to `POST /editorial-calendar/execute-flow-a-due` request model (default `false`, `extra="forbid"`)
- [x] 5.3 Surface partial item results when push succeeds but live confirmation fails
- [x] 5.4 Add calendar connector tests for live confirmation passthrough and partial item results

## 6. Verification and documentation

- [x] 6.1 Run targeted pytest for touched modules; then full pytest suite
- [x] 6.2 Run `git diff --check` and secrets audit on changed files
- [x] 6.3 Add operational smoke script `deploy/server/run-us002-live-site-confirmation-smoke.sh` (or extend US-001 script) for controlled validation on `192.168.0.194` — include container egress precheck to `https://silverman.pro` and assert `public_slug` appears in the probed page body
- [x] 6.4 Document smoke procedure and record evidence in `docs/operations/phase3-us002-live-site-confirmation-validation-YYYY-MM-DD.md` after real validation — include HTTP status, final URL, slug marker check outcome, probe attempt count, and egress precheck result
- [x] 6.5 Update `docs/GLOSSARY.md` (blog handoff vs blog Git publication vs live-site confirmation vs site published/live), `docs/CURRENT-STATE.md`, and `docs/RUNTIME-STATE.md` when operational validation completes
- [x] 6.6 Update `docs/product/progress-checklist.md` and US-002 in `docs/product/user-stories.md` only when acceptance criteria are demonstrated with real HTTP evidence — do not claim BL-001 complete until all US-002 criteria pass

> **Implementation note (apply):** Before coding, inspect `github_pages_git_publication.py`, `blog_publish_flow.py`, `main.py`, `editorial_calendar_flow_a_execute.py`, and `github_pages_git_config.py`. Use actual signatures; do not invent APIs. Live confirmation requires prior Git push evidence — do not probe on handoff-only publishes.
