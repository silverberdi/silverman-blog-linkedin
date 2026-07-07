## 1. Planning and Review

- [x] 1.1 Review and approve `proposal.md` — motivation, goals, non-goals, umbrella reference
- [x] 1.2 Review and approve `design.md` — repo vs running worker, Phase 0–4, Python CLI approach, failure modes
- [x] 1.3 Review and approve `specs/flow-a-deployment-readiness-and-smoke-test/spec.md` — readiness and smoke scenarios
- [x] 1.4 Run `openspec validate flow-a-deployment-readiness-and-smoke-test --strict` and fix any issues

> **Note:** Archive, commit, and push are **out of scope** for this change unless explicitly requested by the operator in a separate action.

## 2. Readiness Script Core

- [x] 2.1 Create `scripts/flow_a_readiness.py` CLI with `--repo-path`, `--worker-base-url`, `--n8n-base-url`, `--expected-commit` (repeatable), `--phase`, and `--json`
- [x] 2.2 Implement Phase 0 repository checks: `git rev-parse HEAD`, `git rev-parse origin/main`, expected commit ancestry, Flow A file manifest
- [x] 2.3 Implement Phase 0 worker checks: `GET /health`, `GET /openapi.json`, required OpenAPI path detection
- [x] 2.4 Implement Phase 0 workflow export checks: file exists, parse `"active": false`
- [x] 2.5 Implement optional worker container identity recording when docker/compose metadata is available
- [x] 2.6 Implement n8n reachability probe and `pending_import` status when workflow import cannot be confirmed
- [x] 2.7 Implement human-readable and JSON report models with overall pass/fail/pending summary
- [x] 2.8 Ensure no secrets are printed; report `configured: true/false` only for API keys

## 3. Smoke Phases

- [x] 3.1 Implement Phase 1 non-destructive worker contract smoke (authenticated `POST /process-ready`; no publish/package/schedule apply)
- [x] 3.2 Implement Phase 2 n8n configuration smoke (reachability + import pending checklist)
- [x] 3.3 Document Phase 3 manual Flow A n8n execution procedure (manual trigger only; workflow remains inactive in export)
- [x] 3.4 Document Phase 4 idempotent rerun verification checklist
- [x] 3.5 Enforce Phase 0 gate: Phases 1–4 do not proceed when Phase 0 fails (unless explicit `--force` for debugging)

## 4. Tests

- [x] 4.1 Add unit tests for OpenAPI required-path extraction
- [x] 4.2 Add unit tests for workflow `active` flag parsing
- [x] 4.3 Add unit tests for expected-commit ancestry logic
- [x] 4.4 Add unit tests for JSON report structure and overall status aggregation
- [x] 4.5 Add unit tests for stale-worker detection (repo pass + OpenAPI path fail)

## 5. Documentation

- [x] 5.1 Document Phase 0–4 operator workflow in README and/or `docs/deployment/ubuntu-server-worker-deployment.md`
- [x] 5.2 Document relationship to existing `deploy/server/smoke-worker.sh` (complementary; Flow A readiness is the pre-smoke gate)
- [x] 5.3 Document default expected commits (`79f5345`, `962ba2f`, `53708eb`) and how to override
- [x] 5.4 Document remediation hints for stale worker (rebuild/restart via `deploy/server/deploy-worker.sh` — manual operator action)

## 6. Validation

- [x] 6.1 Run `pytest` for new readiness tests
- [x] 6.2 Run `openspec validate flow-a-deployment-readiness-and-smoke-test --strict`
- [x] 6.3 Run `openspec validate --all --strict`
- [x] 6.4 Manual dry-run: execute Phase 0 locally against configured worker base URL and confirm pass/fail output (no commit)

## 7. Out of Scope (explicit)

- [x] 7.1 Do **not** implement LinkedIn API publication (slice 8 remains deferred)
- [x] 7.2 Do **not** set n8n workflow `"active": true` or add cron/webhook triggers
- [x] 7.3 Do **not** archive the umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`
- [x] 7.4 Do **not** commit or push as part of `/opsx-apply` for this change
- [x] 7.5 Do **not** add automatic deploy/restart behavior (future operational change if needed)

## 8. Deployment verification (post-apply refinement)

- [x] 8.1 Diagnose stale-worker failure mode: deploy on wrong host, Docker cache, missing OpenAPI verification
- [x] 8.2 Improve `deploy/server/deploy-worker.sh`: sync verification, `BUILD_REVISION`, `--force-recreate`, container identity output, integrated verification
- [x] 8.3 Add `deploy/server/verify-worker-deploy.sh`: target Flow A source files, container on `8010`, OpenAPI path checks
- [x] 8.4 Update `Dockerfile` / `silverman-worker.compose.yaml` with `BUILD_REVISION` build arg and pinned local image tag
- [x] 8.5 Strengthen `scripts/flow_a_readiness.py` stale-worker remediation text; update tests
- [x] 8.6 Document post-deploy OpenAPI requirement in `docs/deployment/ubuntu-server-worker-deployment.md` and README
- [x] 8.7 Refine `verify-worker-deploy.sh`: retry `/health` and `/openapi.json` after container recreate; update tests and docs

## 9. n8n Flow A import formalization (Ubuntu validation)

- [x] 9.1 Add `deploy/server/import-flow-a-n8n-workflow.sh` — locate real n8n container by image (`n8nio/n8n`), exclude nginx gateway
- [x] 9.2 Prepare workflow JSON with stable id `silvermanFlowAPublish01`, `active=false`, `worker_base_url`, `worker_api_key`; remove null `createdAt`/`updatedAt`/`versionId`
- [x] 9.3 Import via `docker exec … n8n import:workflow`; verify with `export:workflow` (26 nodes, inactive); never print API key
- [x] 9.4 Update `scripts/flow_a_readiness.py` pending-import wording to reference import script as manual verification evidence
- [x] 9.5 Add tests in `tests/test_server_deployment_artifacts.py` for import script behavior and safety constraints
- [x] 9.6 Document import procedure in README and `docs/deployment/ubuntu-server-worker-deployment.md`
- [x] 9.7 Update design/spec with gateway vs n8n container, stable workflow id requirement, and pending readiness semantics

## 10. Flow A post-smoke evidence collection (Ubuntu validation)

- [x] 10.1 Add `deploy/server/collect-flow-a-smoke-evidence.sh` — read-only; resolve base path from env/mounts/health/candidates; no secrets printed
- [x] 10.2 Collect worker `/health` + `/openapi.json` Flow A path evidence; latest metadata/campaign/generated artifacts; slug fragment blog publish files
- [x] 10.3 Export n8n workflows from real n8n container; confirm `silvermanFlowAPublish01` inactive with 26 nodes
- [x] 10.4 Implement `PASS` / `PENDING` / `FAIL` overall status semantics; optional `--json` output
- [x] 10.5 Add tests in `tests/test_server_deployment_artifacts.py` for script existence, safety, base path detection, worker/n8n checks, slug fragment, no secrets
- [x] 10.6 Document evidence collection in README and `docs/deployment/ubuntu-server-worker-deployment.md` (replace ad-hoc SSH heredocs)
- [x] 10.7 Update design/spec with fragile manual evidence failure reason and Phase 3/4 verification flow; slice 8 remains deferred; workflow inactive requirement unchanged
