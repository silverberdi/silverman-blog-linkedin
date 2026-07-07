## Context

### Current State

Flow A core implementation is complete through umbrella child slice 7:

| Milestone | Commit | Capability |
|-----------|--------|------------|
| LinkedIn distribution scheduling | `53708eb` | `POST /schedule-linkedin-distribution` |
| n8n Flow A orchestration workflow | `962ba2f` | `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` |
| Umbrella docs updated | `79f5345` | Core orchestration marked complete through slice 7 |

The Ubuntu server runs the worker in an isolated Docker Compose project (`deploy/server/silverman-worker.compose.yaml`, host port `8010`). n8n runs in separate `local-ai-stack`. Existing `deploy/server/smoke-worker.sh` validates basic deployment (`GET /health`, `POST /process-ready`) but does **not**:

- Compare repository HEAD to `origin/main` or expected Flow A commits.
- Inspect `GET /openapi.json` for Flow A endpoint paths.
- Verify Flow A workflow export exists and `"active": false`.
- Distinguish stale running worker from current checkout.
- Gate phased Flow A smoke execution on deployment readiness.

### Problem: Repository State ≠ Running Worker State

```
┌─────────────────────┐         ┌──────────────────────────────┐
│  Git checkout       │         │  Running worker container     │
│  (Mac or server)    │   ≠     │  (built image + old code?)    │
│  HEAD = 962ba2f     │         │  OpenAPI missing /publish-*   │
└─────────────────────┘         └──────────────────────────────┘
```

Common failure: operator pulls latest `main` on the server editorial mount or build context but **does not rebuild/restart** the worker container. `git rev-parse HEAD` passes while `/openapi.json` still reflects a pre–Flow A image.

**Observed deployment failure (2026-07):** `deploy-worker.sh` ran from Mac targeting `/home/silverman/silverman-blog-linkedin-worker`; `GET /health` on `192.168.0.194:8010` returned HTTP 200 but `/openapi.json` still lacked Flow A paths. Root causes:

1. **Wrong host** — deploy syncs to `TARGET_DIR` on the machine where the script runs; Mac deploy does not update the Ubuntu server worker unless run over SSH on the server.
2. **Stale Docker image** — the worker runs `pip install .` at image build time; `docker compose up -d --build` may reuse cached layers or skip container recreation.
3. **No post-deploy OpenAPI verification** — `smoke-worker.sh` only checks `/health` and `/process-ready`, so a stale image can pass smoke while Flow A endpoints are absent.

**Remediation applied in this change:**

- `deploy-worker.sh` warns when target is a server path on a non-Linux host; verifies synced Flow A source files; builds with `BUILD_REVISION`; uses `--force-recreate`; prints container/image identity; runs `verify-worker-deploy.sh`.
- `verify-worker-deploy.sh` confirms target source files, container on port `8010`, and required OpenAPI paths.
- `DEPLOY_FORCE_REBUILD=1` triggers `docker compose build --no-cache`.

### Stakeholders and Constraints

- **Operator**: Needs one command to answer “Is the environment safe to run Flow A smoke?”
- **n8n**: HTTP-only orchestration (ADR-0001); workflow export MUST stay `"active": false` until a future operational change.
- **Worker**: Must not expose secrets; readiness uses read-only HTTP and local file checks.
- **CI**: Parser/check logic unit-testable without live Ubuntu server.
- **Umbrella**: Slice 8 (`linkedin-publication-integration`) remains deferred; umbrella archive blocked until this child completes.

## Goals / Non-Goals

**Goals:**

- Provide `scripts/flow_a_readiness.py` as the primary repeatable verification entry point.
- Implement Phase 0 deployment readiness checks (see below) with clear pass/fail and remediation hints.
- Define Phases 1–4 smoke procedures (some automated checks, some operator-guided) gated on Phase 0.
- Emit human-readable terminal output and optional `--json` machine-readable report.
- Never print API keys, tokens, or env secret values.
- Never perform destructive operations or automatic deploy/restart.

**Non-Goals:**

- LinkedIn API calls or slice 8 implementation.
- Activating n8n workflow, cron, or webhooks.
- Replacing `deploy/server/deploy-worker.sh` or auto-restarting containers.
- A worker diagnostic HTTP endpoint (defer unless operator feedback demands it).
- Archiving umbrella or committing/pushing as part of this change.

## Deployment Readiness Checks (Phase 0)

| Check | Source | Pass criteria | Typical failure |
|-------|--------|---------------|-----------------|
| Repo path | CLI arg / cwd | Path exists and is git repo | Wrong directory |
| `git rev-parse HEAD` | local git | Succeeds; recorded in report | Not a git checkout |
| `git rev-parse origin/main` | local git | Succeeds; recorded | No `origin/main` fetch |
| Expected commits present | `git merge-base --is-ancestor` | Each configured commit is ancestor of HEAD | Branch behind expected Flow A commits |
| Required Flow A files exist | filesystem | Paths from manifest (see below) | Incomplete checkout |
| Worker process/container identity | optional docker/compose | Container name/image id recorded when available | Cannot identify running worker |
| `GET /health` | HTTP | HTTP 200, structured JSON | Worker down, wrong port |
| `GET /openapi.json` | HTTP | HTTP 200, parseable OpenAPI | Stale worker, wrong base URL |
| Required OpenAPI paths | parsed paths | `/health`, `/process-ready`, `/publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution` present | **Stale worker** after code merge |
| n8n reachable | HTTP TCP/connect | Configured n8n base URL responds | n8n down, wrong host |
| Flow A workflow JSON in checkout | filesystem | `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` exists | Missing workflow export |
| Workflow `active` flag | JSON parse | `"active": false` | Accidental activation in export |

**Required Flow A files (checkout manifest):**

- `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json`
- `content-strategy/silverman-editorial-system.md`
- `src/silverman_blog_linkedin/blog_publish_flow.py`
- `src/silverman_blog_linkedin/linkedin_package_flow.py`
- `src/silverman_blog_linkedin/linkedin_distribution_schedule.py`
- `src/silverman_blog_linkedin/ready_post_validation.py`

**Default expected commits** (override via CLI flags):

- `79f5345` — docs(flow-a): mark core orchestration complete through slice 7
- `962ba2f` — feat(flow-a): add n8n publish orchestration workflow
- `53708eb` — feat(flow-a): add linkedin distribution scheduling model

## Expected Failure Modes

| Failure | Detection | Report severity | Remediation hint |
|---------|-----------|-----------------|------------------|
| Repo current, worker stale | HEAD has commits; OpenAPI missing Flow A paths | **fail** | Rebuild/recreate on server (`deploy-worker.sh`, `verify-worker-deploy.sh`; `DEPLOY_FORCE_REBUILD=1` if needed) |
| Deploy ran on wrong host | Mac deploy; server worker unchanged | **fail** | Run deploy on Ubuntu server; verify `TARGET_DIR` |
| Worker running old installed package | health OK; openapi paths incomplete | **fail** | `docker compose build --no-cache` + `--force-recreate` |
| Wrong port / base URL | connection refused or 404 on `/health` | **fail** | Check `WORKER_BASE_URL` / `8010` |
| Wrong environment/base path | health OK but editorial paths wrong in health payload | **warn/fail** | Verify `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` mount |
| n8n not imported yet | n8n reachable; optional API/workflow name check inconclusive | **pending** | Run `deploy/server/import-flow-a-n8n-workflow.sh` on Ubuntu server; confirm `OVERALL: PASS` |
| API key mismatch | Phase 1 authenticated probe returns 401 | **fail** (Phase 1) | Align n8n `worker_api_key` with server `.env` |
| Workflow export `active: true` | JSON parse | **fail** | Reset export to `"active": false` before merge |
| Public blog repo not mounted | publish validation passes; `blog_publish_public_repo_not_configured` on apply | **fail** | Clone/sync `silverberdi.github.io` to host; ensure `_posts/` and `assets/images/`; redeploy with public mount; `verify-worker-deploy.sh` |

## Smoke-Test Phases

```
Phase 0: Deployment readiness     ← automated; MUST pass before later phases
Phase 1: Worker endpoint contract ← lightweight HTTP probes (auth where required)
Phase 2: n8n import/configuration ← reachability + operator checklist / optional API probe
Phase 3: Full manual Flow A       ← operator runs n8n manual trigger (documented steps)
Phase 4: Idempotent rerun         ← operator re-runs; verify already_* / no duplicates
```

**Gating rule:** Phases 1–4 MUST NOT start unless Phase 0 reports `overall: pass`. CLI exits non-zero on Phase 0 failure when invoked with default `--phase 0` or `--phase all` stopping at first failure.

Phase 1 contract smoke (non-destructive):

- `GET /health` — no auth
- `GET /openapi.json` — verify paths (already in Phase 0)
- `POST /process-ready` — Bearer auth; expect 200 (empty ready is OK)
- Optional HEAD/OPTIONS or dry-run probes for publish/package/schedule if endpoints support safe no-op modes; otherwise document manual Phase 3 only

Phase 2 n8n smoke:

- TCP/HTTP reachability to configured n8n URL (e.g. `http://192.168.0.194:5678` or documented gateway)
- Workflow import: if n8n API credentials not configured, emit **pending_import** with manual checklist (not fail)
- Verify workflow export in repo has `"active": false` (Phase 0)

Phase 3–4: Documented operator procedures referencing README; not fully automatable without test fixtures and risk of real publish — out of scope for automated script except reporting checklist status.

## Implementation Approach

### D1: Python CLI under `scripts/` (primary)

**Decision:** Implement `scripts/flow_a_readiness.py` using Python 3.11+ (matches project).

**Rationale:**

- OpenAPI JSON parsing, structured report models, and unit tests align with existing `tests/` patterns.
- `pyproject.toml` already defines project dependencies; can use `httpx` or stdlib `urllib` for HTTP.
- Machine-readable `--json` output is straightforward with `dataclasses` + `json`.

**Alternatives considered:**

- **Shell only** — matches `deploy/server/smoke-worker.sh` but weak for OpenAPI parsing and testability; may add thin wrapper `deploy/server/flow-a-readiness.sh` calling Python.
- **Worker diagnostic endpoint** — couples readiness to deployment cycle; rejected for v1.

### D2: Complement, not replace, `smoke-worker.sh`

**Decision:** Keep `deploy/server/smoke-worker.sh` for minimal server post-deploy checks; Flow A readiness script is the pre-smoke gate with broader checks.

### D3: Configuration via CLI flags and env vars

| Input | Default | Purpose |
|-------|---------|---------|
| `--repo-path` | cwd | Git checkout to verify |
| `--worker-base-url` | `http://localhost:8010` | Running worker |
| `--n8n-base-url` | optional | n8n reachability |
| `--expected-commit` | repeatable; defaults to Flow A trio | Commit ancestry checks |
| `--api-key-env` | `SILVERMAN_BLOG_LINKEDIN_API_KEY` | Phase 1 auth; load from env file path, never print value |
| `--phase` | `0` | `0`, `1`, `2`, `all` |
| `--json` | off | Machine-readable report on stdout |

### D4: Output format

**Human-readable:**

```
==> Flow A deployment readiness (Phase 0)
PASS  repo_path: /path/to/repo
PASS  git_head: 79f5345
PASS  git_origin_main: 79f5345
PASS  expected_commits_present: 79f5345, 962ba2f, 53708eb
PASS  file_manifest: 6/6
PASS  worker_health: HTTP 200
PASS  openapi_paths: 5/5 required
PASS  workflow_export_active_false: true
WARN  n8n_workflow_import: pending (manual import required)

OVERALL: PASS (ready for Phase 1)
```

**JSON report** (`--json`): `{ "phase": 0, "overall": "pass"|"fail"|"pending", "checks": [ { "id", "status", "message" } ], "remediation": [] }`

Secrets: API key presence reported as `configured: true/false` only.

### D5: No automatic deploy/restart

Readiness reports failure with remediation text pointing to `deploy/server/deploy-worker.sh` and `deploy/server/verify-worker-deploy.sh`; does not invoke them.

### D6: Post-deploy verification companion

**Decision:** Add `deploy/server/verify-worker-deploy.sh` and integrate it into `deploy-worker.sh` so operators can confirm Flow A OpenAPI surface without ad-hoc curl inspection.

**Rationale:** `smoke-worker.sh` predates Flow A and does not inspect OpenAPI. Stale images can pass health/process-ready while missing `/publish-blog-post` and related paths.

### D7: Repeatable n8n Flow A import script

**Decision:** Add `deploy/server/import-flow-a-n8n-workflow.sh` for Ubuntu server operators. The script selects the **real n8n application container** by Docker image (`docker.n8n.io/n8nio/n8n` or `n8nio/n8n`), not the **nginx gateway** container (`local-ai-stack-n8n-gateway-1`).

**Observed Ubuntu validation (2026-07):**

| Item | Value |
|------|-------|
| Real n8n container | `local-ai-stack-n8n-1` (image `docker.n8n.io/n8nio/n8n:2.21.7`) |
| Gateway (do not use for CLI) | `local-ai-stack-n8n-gateway-1` (nginx) |
| Failed import cause | Workflow JSON missing/null top-level `id` → Postgres `workflow_entity.id` NOT NULL violation |
| Successful stable id | `silvermanFlowAPublish01` |
| Imported workflow | name `Silverman Blog LinkedIn Flow A Publish`, `active: false`, 26 nodes |
| Worker config | `worker_base_url` `http://192.168.0.194:8010`; `worker_api_key` from server `.env` (never printed) |

**Import preparation:** Set stable `id`, `name`, `active: false`; update **Set Configuration** `worker_base_url` and `worker_api_key`; remove null `createdAt`, `updatedAt`, `versionId` if present. Import via `docker exec <n8n-container> n8n import:workflow`; verify with `export:workflow` (matching id/name, `active: false`, 26 nodes). Do **not** activate workflow or add cron/webhook triggers.

**Readiness interaction:** Phase 0 `n8n_workflow_import` may remain **pending** when HTTP reachability alone cannot confirm import (no n8n API credentials required). A successful `import-flow-a-n8n-workflow.sh` run with `OVERALL: PASS` satisfies manual import verification evidence.

### D8: Repeatable Flow A post-smoke evidence collection

**Decision:** Add `deploy/server/collect-flow-a-smoke-evidence.sh` for Ubuntu server operators to collect Phase 3/4 verification evidence without ad-hoc SSH heredocs.

**Observed failure (2026-07):** Manual post-smoke evidence commands failed due to fragile shell quoting around `docker inspect --format`. Operators also assumed `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` exists in `/home/silverman/silverman-blog-linkedin-worker/.env`, but the server `.env` may contain only `SILVERMAN_BLOG_LINKEDIN_API_KEY`. The editorial root must be resolved from container env, Docker mounts, `GET /health`, or known host candidates.

**Script behavior:** Read-only; no secrets printed; no n8n activation; no LinkedIn API calls; no deploy/restart. Resolves base path with explicit source reporting; checks worker `/health` and `/openapi.json` Flow A paths; lists latest `metadata/runs/`, `metadata/campaigns/`, `linkedin-posts/generated/` artifacts and published blog files matching `POST_SLUG_FRAGMENT`; exports n8n workflows and confirms `silvermanFlowAPublish01` is inactive with 26 nodes. Overall `PASS` / `PENDING` / `FAIL` semantics gate on worker health, n8n inactive state, and presence of smoke artifacts.

**Slice 8 remains deferred.** Workflow must stay inactive until a future operational change.

### D9: Public GitHub Pages repo mount for Flow A publish

**Decision:** Extend `silverman-worker.compose.yaml` with a second volume mount for the public blog repo checkout and container env `SILVERMAN_GITHUB_PAGES_REPO_PATH=/public-blog`, plus `SILVERMAN_SITE_URL` (default `https://silverman.pro`).

**Observed smoke failure (2026-07):** Flow A n8n execution reached **Publish Blog Post**; publish validation passed; campaign metadata reached `validated`; publish failed only with `blog_publish_public_repo_not_configured`. Investigation showed the worker compose mounted only the editorial workspace (`/data/silverman-blog-linkedin`) and did not set `SILVERMAN_GITHUB_PAGES_REPO_PATH` or mount the `silverberdi.github.io` checkout. The Ubuntu server had no public blog repo under `/home/silverman` at deploy time.

**Two required host paths on Ubuntu server:**

| Purpose | Default host path | Container path |
|---------|-------------------|----------------|
| Editorial workspace | `/home/silverman/compartido_mac/silverman-blog-linkedin` | `/data/silverman-blog-linkedin` |
| Public GitHub Pages repo | `/home/silverman/silverberdi.github.io` | `/public-blog` |

The public checkout must contain `_posts/` and `assets/images/`. `deploy-worker.sh` verifies the host path before `docker compose up` (fails by default; `SKIP_PUBLIC_BLOG_REPO_CHECK=1` for non-publishing deploys). The deploy script does **not** clone the repo automatically.

`verify-worker-deploy.sh` and `collect-flow-a-smoke-evidence.sh` verify `/public-blog` layout inside the running container. Evidence collection reports `FAIL` (not `PENDING`) when worker and n8n are OK but the public repo is missing — publish would fail with `blog_publish_public_repo_not_configured`, which is a worker deployment issue, not an n8n failure.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| n8n import status hard to detect without API token | Report `pending_import` with checklist; successful `import-flow-a-n8n-workflow.sh` satisfies manual evidence |
| Phase 3–4 remain operator-heavy | Document clearly; automate only safe read-only checks |
| False pass if worker URL points to dev machine | Require explicit `--worker-base-url`; document server default |
| Commit pins become stale | Configurable `--expected-commit`; default tied to umbrella baseline |

## Migration Plan

1. **Propose** (this change): artifacts only; umbrella updated.
2. **Apply**: implement `scripts/flow_a_readiness.py`, tests, docs.
3. **Operator adoption**: run Phase 0 on Mac against local worker and on Ubuntu server against `8010` after each deploy.
4. **Umbrella archive**: only after this child is applied, validated, and archived — slice 8 remains deferred.

Rollback: script is read-only; removal does not affect worker or n8n.

## Open Questions

1. Should Phase 2 probe n8n REST API when `N8N_API_KEY` is available, or stay checklist-only?
2. Should `deploy/server/smoke-worker.sh` delegate to Phase 0 after Flow A apply?
3. Exact n8n health URL for reachability (direct port vs gateway)?
