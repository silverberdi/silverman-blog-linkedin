## Why

Flow A already writes validated blog posts and images to the public GitHub Pages checkout (`/public-blog`), but **site published/live** still requires a manual operator `git commit` and `git push`. That gap blocks unattended Flow A and is the first operational step in backlog item **BL-001**. This change automates the controlled Git publication step for **US-001** so validated publication artifacts can be committed and pushed to the remote repository without manual Git intervention.

## Goals

- Satisfy **US-001**: validated publication artifacts are committed and pushed safely without manual Git intervention — reuse existing publish validation, create a controlled commit in `silverberdi.github.io`, push the approved commit to the remote, surface clear outcomes and failures, and avoid unintentional changes to unrelated files.
- Expose Git publication through **both** `POST /publish-blog-post` and the editorial calendar Flow A execution connector (`POST /editorial-calendar/execute-flow-a-due`) with per-request opt-in.
- Keep Git operations inside the worker HTTP boundary (ADR-0001) — n8n calls worker endpoints only, never Execute Command for `git`.
- Fail closed when Git publication is disabled or prerequisites are not met; environment enablement alone MUST NOT trigger Git publication.
- Record Git publication evidence in campaign metadata for operator traceability.
- Treat Git credential setup (dedicated deploy key) and Git binary availability in the worker image as operational prerequisites documented for operators.

## Non-Goals

- **US-002 is explicitly out of scope** for this change:
  - Reconciling the pushed publication against remote history and confirming it is live on the public site (HTTP probe, GitHub Pages deploy status, or URL reachability checks).
  - Remote-history divergence reconciliation; equivalent commits after amend or rebase; cross-campaign duplicate detection; automatic fetch, pull, merge, or rebase.
- n8n workflow activation, cron triggers, or unattended scheduling (BL-004).
- LinkedIn API publication changes.
- Modifying editorial source lifecycle moves or blog handoff bridge semantics.
- Operator CLI `github_pages_publish` automatic Git push (CLI remains handoff-only unless separately proposed).

## What Changes

- Introduce a guarded worker capability to **commit and push** only the blog publication artifacts for a campaign after successful blog handoff.
- Integrate optional Git publication into `publish_blog_post(..., git_publication: bool = False)` and `POST /publish-blog-post` with `git_publication` (default `false`).
- Extend `execute_due_editorial_calendar_flow_a(..., git_publication: bool = False)` and `POST /editorial-calendar/execute-flow-a-due` with the same opt-in; the calendar connector passes it through to `publish_blog_post`.
- Dual guard (both required): `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true` **and** request `git_publication=true`.
- Add configuration and enablement flag (fail closed when disabled).
- Install the `git` binary in the worker Docker image and verify it in the built container.
- Document operator deploy-key setup (repository-scoped, mounted from worker secrets directory) without embedding secrets.
- Extend campaign metadata with `blog_git_publication` recording commit hash, branch, push status, and structured errors.
- Return `status: partial` when blog handoff succeeds but Git commit or push fails; preserve successful `blog_publish` evidence and surface actionable recovery without secrets.
- Expose results in worker HTTP JSON responses suitable for n8n branching.
- Add automated tests with injectable Git subprocess fakes — no real remote calls in unit tests.
- Update operator documentation and `docs/CURRENT-STATE.md` when capability is implemented and validated.

No **BREAKING** changes to existing `POST /publish-blog-post` or calendar execution default behavior when Git publication is disabled or not opted in.

## User story mapping

| Story | Business interpretation | Scope in this change |
|-------|---------------------------|----------------------|
| **US-001** | Validated publication artifacts are committed and pushed safely without manual Git intervention. | **In scope** — validation (existing), controlled commit, push, visible outcome, failure communication, scoped idempotency, no unintentional file changes; reachable via direct publish endpoint and calendar execution connector |
| **US-002** | The pushed publication is reconciled against remote history and confirmed live on the public site. | **Excluded** — remote reconciliation, live-site confirmation, divergence handling, advanced duplicate prevention |

**BL-001** remains open after this change. US-001 progress may be recorded when acceptance criteria are demonstrated with real remote push evidence; **do not claim BL-001 complete** until US-002 is delivered separately.

## Capabilities

### New Capabilities

- `github-pages-git-publication`: Guarded worker Git commit and push for validated blog publication artifacts in the configured public checkout — controlled file scope, structured outcomes, campaign metadata, fail-closed enablement, deploy-key operational prerequisite, and Git binary in worker image.

### Modified Capabilities

- `worker-blog-publishing-endpoint`: Integrate optional Git publication step after successful blog handoff; update non-goals that currently forbid `git commit`/`git push`; extend publish result and campaign metadata with Git publication evidence; define `partial` overall status when handoff succeeds but Git fails.
- `flow-a-automatic-publishing`: Clarify that blog handoff plus guarded Git publication satisfies the US-001 automatic publish path; site published/live confirmation remains US-002.
- `editorial-calendar-flow-a-execution-connector`: Extend service and HTTP execution request with optional `git_publication` (default `false`); pass opt-in to `publish_blog_post` during real execution.

## Impact

- **Worker modules**: new Git publication service (e.g. `github_pages_git_publication.py`), updates to `blog_publish_flow.py`, `editorial_calendar_flow_a_execute.py`, and `main.py` for HTTP surface.
- **Docker image**: install `git` package in `Dockerfile`; add build or deploy verification that `git` is available in the built container.
- **Configuration**: new env vars for Git publication enablement, remote/branch defaults, and optional commit message template; deploy key mounted from worker secrets directory (operator setup); no secrets in responses.
- **Campaign metadata**: `metadata/campaigns/<id>.json` gains Git publication fields.
- **Tests**: new unit tests with faked `git` subprocess; extend publish-flow, HTTP, and calendar-connector tests for opt-in and partial semantics.
- **Documentation**: `docs/workflows/blog-publishing-bridge.md`, deployment docs, `docs/CURRENT-STATE.md`, deploy-key operator setup (no secrets in versioned files).
- **Operations**: Ubuntu server worker container requires deploy key and `git` binary before Git publication can be validated; documented as operator prerequisites, not committed.
- **n8n**: out of scope for activation and scheduling; operators may call existing HTTP endpoints with `git_publication: true` when approved.
