## Context

Flow A blog publish already validates editorial content, hands off `_posts/` and `assets/images/` files to the mounted public checkout (`SILVERMAN_GITHUB_PAGES_REPO_PATH=/public-blog`), and records `source_public_url` in campaign metadata. Operators must still SSH to the server (or use the host checkout) to `git commit` and `git push` — documented in `docs/workflows/blog-publishing-bridge.md` and `docs/CURRENT-STATE.md` as a manual step.

Canonical specs currently forbid Git operations in `worker-blog-publishing-endpoint` and `github-pages-blog-publishing`. This change introduces guarded Git publication for **US-001** only, leaving **US-002** (remote reconciliation, live-site confirmation, divergence handling, advanced duplicate prevention) for a follow-up change.

Constraints:

- ADR-0001: n8n orchestrates via HTTP only; Git runs inside the worker process, not n8n Execute Command.
- Fail closed when disabled (pattern mirrors `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`).
- No secrets in HTTP responses, campaign metadata, logs, examples, or versioned files.
- Develop on Mac; deploy Docker on `192.168.0.194` with public blog mount at `/public-blog`.

## Goals / Non-Goals

**Goals:**

- Automate controlled `git add` (scoped paths), `git commit`, and `git push` after successful blog handoff when explicitly enabled and opted in.
- Expose opt-in on both `POST /publish-blog-post` and calendar Flow A execution (`POST /editorial-calendar/execute-flow-a-due`).
- Reuse existing publish validation and artifact paths from `BlogPublishResult` / `blog_publish` metadata.
- Persist `blog_git_publication` evidence on campaigns.
- Return structured JSON for n8n branching, including `partial` when handoff succeeds but Git fails.
- Unit-test with injectable Git runner fakes.
- Install and verify `git` in the worker Docker image.
- Document deploy-key operator setup as an operational prerequisite.

**Non-Goals (US-002):**

- HTTP probes to `source_public_url` or GitHub Pages deploy APIs.
- `git fetch` / `git pull` / rebase / merge / conflict resolution before or after push.
- Force-push or branch creation.
- Cross-campaign duplicate commit detection; equivalent commits after amend or rebase; remote-history divergence reconciliation.
- GitHub Pages deployment confirmation; live URL reachability.
- n8n workflow activation or scheduling changes.
- Automatic Git for the operator CLI `github_pages_publish` module.

## Decisions

### 1. Integrate Git publication into `publish_blog_post` as optional final step

**Choice:** Extend `publish_blog_post(..., git_publication: bool = False)` and `POST /publish-blog-post` with `git_publication` rather than a mandatory separate endpoint.

**Rationale:** US-001 happy path is validate → handoff → commit → push in one operator action. Keeps orchestration simple while preserving handoff-only behavior when flag is false.

**Alternative considered:** Separate `POST /commit-blog-git-publication` — rejected as primary path to avoid an extra HTTP call for US-001; may add later if operators want decoupled retry without re-running handoff.

### 2. Dual guard: env enablement + per-request opt-in

**Choice:**

- `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true` (default false)
- Request body `git_publication: true` on publish or calendar execution

Both required to run Git. Environment enablement alone MUST NOT trigger Git publication.

**Rationale:** Matches LinkedIn publication guard pattern; prevents accidental push in dev/smoke environments even if a workflow sends `git_publication: true`.

### 3. Calendar execution connector passes opt-in to publish

**Choice:** Extend `execute_due_editorial_calendar_flow_a(..., git_publication: bool = False)` and `POST /editorial-calendar/execute-flow-a-due` request body with optional `git_publication` (default `false`). During real execution, pass the value to `publish_blog_post`.

**Rationale:** US-001 must not be limited to manual curl or the direct publish endpoint. Calendar Flow A is a first-class execution path. n8n activation and scheduling remain out of scope.

**Scope limit:** Update calendar connector service, HTTP request model, and tests only as needed for opt-in passthrough; no n8n or cron changes.

### 4. New module `github_pages_git_publication.py`

**Choice:** Isolate subprocess Git logic in a dedicated module with injectable `GitRunner` protocol for tests.

**Rationale:** Keeps `blog_publish_flow.py` orchestration readable; avoids embedding subprocess calls in `github_pages_publish.py` bridge (CLI remains Git-free).

### 5. Scoped staging only

**Choice:** `git add -- <post_relative_path> <image_relative_path>` for exactly the two paths from publish result.

**Rationale:** Satisfies US-001 "no unintentional changes"; avoids committing unrelated dirty files in a shared checkout. Unrelated files MUST NOT be staged, committed, reverted, or overwritten.

### 6. US-001 idempotency boundary

**Choice:** When campaign metadata records successful Git publication (`blog_git_publication.status` `pushed`) for the same `blog_publish.idempotency_key` with matching `commit_sha` and scoped artifact paths, and the working tree shows no changes for those paths, a repeat request MUST:

- return `blog_git_publication.status` `already_published`;
- NOT create another commit;
- NOT perform an unnecessary push;
- NOT overwrite prior successful Git evidence with weaker or ambiguous state.

**Deferred to US-002:**

- Remote-history divergence reconciliation.
- Equivalent commits after amend or rebase.
- Cross-campaign duplicate detection.
- Automatic fetch, pull, merge, or rebase.
- GitHub Pages deployment confirmation.
- Live URL reachability.

### 7. Push without fetch

**Choice:** Run `git push <remote> <branch>` directly; on non-fast-forward failure return `blog_git_publication_push_failed`.

**Rationale:** US-002 explicitly owns divergence handling; attempting auto-pull risks unintended merges in production.

### 8. Partial-result semantics when handoff succeeds but Git fails

**Choice:** When `git_publication` was requested and blog handoff succeeded but commit or push fails:

- overall publish `status` MUST be `partial` (not `failed`);
- `blog_publish` MUST preserve successful `published` or `already_published` evidence;
- `blog_git_publication.status` MUST be `failed` with a stable `error_code`;
- response MUST state that files were written to the checkout but remote Git publication did not complete;
- `errors[]` MUST include an actionable recovery message without secrets.

Complete failure before successful handoff continues to use `status: failed`.

**Rationale:** Distinguishes recoverable partial success from total publish failure; aligns with calendar connector `partial` vocabulary.

### 9. Git credential model — dedicated deploy key

**Choice:** Use a dedicated GitHub deploy key with repository-scoped access to the public GitHub Pages repository. Mount the private key read-only from the worker secrets directory into the container. Configure Git in the container to use that key for push (e.g. `GIT_SSH_COMMAND` or `core.sshCommand` pointing at the mounted key path).

**Requirements:**

- Write permission only where required for push to the target branch.
- No reuse of a personal interactive credential.
- No key, token, credential path content, or authorization data in HTTP responses, campaign metadata, logs, examples, or versioned files.
- Operator documentation describes setup steps without embedding secrets.

**Rationale:** Least-privilege, automation-safe credential isolated from operator personal accounts.

**Operational prerequisite:** Git publication validation MUST NOT proceed on the server until deploy key is configured and push succeeds in a controlled test. Implementation may surface a readiness error when credentials are missing, but MUST NOT leak credential material.

### 10. Git binary in worker Docker image

**Choice:** The current `python:3.11-slim` base image does not include Git. This change MUST add `git` package installation to `Dockerfile` and verify `git` is available in the built container (e.g. `git --version` in image build or deploy verification step).

**Rationale:** Git publication cannot run without the binary; this is mandatory, not optional.

### 11. Configuration surface

| Variable | Purpose | Default |
|----------|---------|---------|
| `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED` | Master enablement | false |
| `SILVERMAN_BLOG_GIT_PUBLICATION_BRANCH` | Target branch | `main` |
| `SILVERMAN_BLOG_GIT_PUBLICATION_REMOTE` | Target remote | `origin` |
| `SILVERMAN_BLOG_GIT_COMMIT_MESSAGE_TEMPLATE` | Optional commit message | `Add blog post: {public_slug} ({campaign_id})` |

Deploy key path and SSH configuration are operator-managed via container mount and documented setup; not exposed via HTTP.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Push fails when remote advanced | Fail with `blog_git_publication_push_failed`; return `partial` when handoff succeeded; document manual reconciliation (US-002) |
| Container lacks deploy key | Document as operational prerequisite; controlled validation blocked until configured |
| Container lacks `git` binary | Install in Dockerfile; verify in build/deploy |
| Unrelated dirty files in checkout | Scoped `git add` only; never `git add -A` |
| Accidental production push in dev | Default disabled; dual guard |
| Subprocess `git` hangs | Configurable timeout on Git runner; surface timeout error code |
| Credential leakage in stderr | Sanitize error messages; log stderr at warning level without echoing to HTTP |

## Migration Plan

1. Implement behind `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=false` (no behavior change on deploy).
2. Update Dockerfile to install `git`; rebuild and verify binary in container.
3. Operator configures deploy key on Ubuntu server and mounts from worker secrets directory.
4. Enable flag in worker `.env` on server after controlled validation with one test post via direct publish or calendar execution with `git_publication: true`.
5. Rollback: set enablement false; manual Git remains documented fallback.

## Resolved Questions

All planning questions from the initial design are closed:

| Topic | Resolution |
|-------|------------|
| Git availability | Install `git` in worker Docker image; verify in built container |
| Credential model | Dedicated repository-scoped deploy key mounted read-only from worker secrets directory |
| Calendar connector scope | Extend execution request with `git_publication`; pass through to `publish_blog_post`; n8n activation out of scope |
| Partial-result semantics | Overall `partial` when handoff succeeds and Git fails; preserve `blog_publish` success evidence |
