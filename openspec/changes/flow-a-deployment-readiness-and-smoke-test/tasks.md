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

## 11. Public blog repo mount for Flow A publish (post-smoke remediation)

**Observed smoke failure (2026-07):** Flow A reached **Publish Blog Post**; validation passed; campaign metadata reached `validated`; publish failed only with `blog_publish_public_repo_not_configured` because the worker container lacked `SILVERMAN_GITHUB_PAGES_REPO_PATH` and the `/public-blog` mount.

- [x] 11.1 Update `deploy/server/silverman-worker.compose.yaml`: add `SILVERMAN_GITHUB_PAGES_REPO_PATH`, `SILVERMAN_SITE_URL`, and public blog repo host mount at `/public-blog`; keep editorial mount and port `8010` unchanged; no secrets
- [x] 11.2 Update `deploy/server/silverman-worker.env.example`: document `SILVERMAN_PUBLIC_BLOG_REPO_PATH` and `SILVERMAN_SITE_URL`
- [x] 11.3 Update `deploy/server/deploy-worker.sh`: verify public blog repo host path before `docker compose up`; remediation text; `SKIP_PUBLIC_BLOG_REPO_CHECK=1` escape hatch; no automatic clone
- [x] 11.4 Update `deploy/server/verify-worker-deploy.sh`: verify container env `/public-blog` and `_posts` / `assets/images` inside container
- [x] 11.5 Update `deploy/server/collect-flow-a-smoke-evidence.sh`: public blog repo readiness section; FAIL (not PENDING) when worker/n8n OK but public repo missing
- [x] 11.6 Add/update tests in `tests/test_server_deployment_artifacts.py` for compose, env example, deploy, verify, and evidence script public repo checks
- [x] 11.7 Update README and `docs/deployment/ubuntu-server-worker-deployment.md` with two required host paths and `blog_publish_public_repo_not_configured` remediation
- [x] 11.8 Update design/spec with observed smoke failure and public blog repo deployment readiness; slice 8 remains deferred; workflow inactive requirement unchanged

## 12. docker inspect stdin bug fix (post public-mount deploy)

**Observed (2026-07):** Public repo synced and container paths `_posts` / `assets/images` passed, but env `SILVERMAN_GITHUB_PAGES_REPO_PATH` and host mount checks failed because `docker inspect | python3 - <<'PY'` feeds the heredoc to stdin instead of inspect JSON.

- [x] 12.1 Fix `verify-worker-deploy.sh` and `collect-flow-a-smoke-evidence.sh` to use `docker_inspect_json_tmp` temp-file helper; update tests; note in design

## 13. Public blog artifact evidence path correction (post-smoke validation)

**Observed (2026-07):** `verify-worker-deploy.sh` passed public repo mount checks, but `collect-flow-a-smoke-evidence.sh` searched published `_posts` and `assets/images` under the editorial base path instead of the public GitHub Pages repo checkout.

- [x] 13.1 Update `collect-flow-a-smoke-evidence.sh`: separate Editorial artifacts from Public blog artifacts; search published files under `PUBLIC_BLOG_HOST_MOUNT` with container fallback; published blog matches informational only for PASS
- [x] 13.2 Update `tests/test_server_deployment_artifacts.py`: assert public blog artifact paths use `PUBLIC_BLOG_HOST_MOUNT`; assert editorial base path is not used for published blog search
- [x] 13.3 Update README, deployment doc, design, and spec with editorial vs public blog artifact distinction

## 14. Deterministic worker smoke and publish reconciliation (post-smoke validation)

**Observed (2026-07):** Public repo mount PASS; campaign stuck at `validated` with public blog files on disk; n8n fails at Publish Blog Post. Root cause: worker did not reconcile metadata when public targets already existed (`blog_publish_target_exists`). n8n workflow JSON verified correct.

- [x] 14.1 Diagnose n8n workflow JSON payloads and branch conditions after Process Ready / Publish / Package / Schedule — confirm field mappings; workflow remains inactive
- [x] 14.2 Fix worker `publish_blog_post` reconciliation when public targets exist and campaign is `validated` / `blog_publish_pending` / recoverable `error`
- [x] 14.3 Add `deploy/server/run-flow-a-worker-smoke.sh` — deterministic publish/package/schedule gate without n8n UI
- [x] 14.4 Extend `tests/test_n8n_flow_a_publish_workflow.py` static validation (HTTP methods, payloads, branch fields)
- [x] 14.5 Add tests in `tests/test_server_deployment_artifacts.py` for smoke script existence, safety, endpoint sequence, campaign checks
- [x] 14.6 Add unit tests for publish reconciliation in `tests/test_blog_publish_flow.py`
- [x] 14.7 Update README, `docs/deployment/ubuntu-server-worker-deployment.md`, design, and spec — worker smoke is diagnostic source of truth; manual n8n is orchestration validation only
- [x] 14.8 Run `openspec validate`, targeted pytest, and full `pytest`

## 15. Error-state publish reconciliation and evidence PASS semantics (post-smoke validation)

**Observed smoke failure (2026-07, commit `07ce499`):** `verify-worker-deploy.sh` and public blog mount PASS; public `_posts` and `assets/images` exist on disk. `run-flow-a-worker-smoke.sh` fails at `POST /publish-blog-post` with `blog_publish_invalid_campaign_state` because prior failed publish attempts left campaign metadata in `error`. `collect-flow-a-smoke-evidence.sh` incorrectly reported `OVERALL: PASS` when campaign metadata existed without `linkedin_package`, `linkedin_distribution`, or `distribution_scheduled`.

- [x] 15.1 Extend `publish_blog_post` reconciliation to safely recover from `error` when public artifacts match source/idempotency/hash
- [x] 15.2 Add unit tests for error-state reconciliation safety (match, hash mismatch, wrong path, stale error clearing)
- [x] 15.3 Fix `collect-flow-a-smoke-evidence.sh` PASS semantics — require `distribution_scheduled` or `linkedin_distribution`; `error` → FAIL; public blog informational only
- [x] 15.4 Update `run-flow-a-worker-smoke.sh` — campaign snapshot on publish failure; PASS only with `distribution_scheduled` + `linkedin_distribution`
- [x] 15.5 Update `tests/test_server_deployment_artifacts.py` for evidence and smoke PASS gating
- [x] 15.6 Update design, spec, README, and deployment docs with second root cause
- [x] 15.7 Run `openspec validate`, targeted pytest, and full `pytest`

## 16. Publish reconciliation ordering and diagnostics (post-smoke validation)

**Observed smoke failure (2026-07, commit `8b656b8`):** `verify-worker-deploy.sh` and public repo mount PASS; public `_posts` and `assets/images` exist on disk. `run-flow-a-worker-smoke.sh` still fails at `POST /publish-blog-post` with `blog_publish_target_exists`, `source_public_url: null` in the worker response, while campaign metadata already has `source_public_url` and `errors: ["blog_publish_target_exists"]` with `blog_publish.public_repo_path` unset. Root cause: safe reconciliation could be skipped when the initial public-target probe did not match disk state (e.g. campaign identity not merged into preflight on resume), allowing `run_publish` overwrite protection to return `blog_publish_target_exists` without attempting recovery or explaining why reconciliation was skipped.

- [x] 16.1 Fix `publish_blog_post` reconciliation ordering — attempt safe reconciliation before any `blog_publish_target_exists` return for `validated` / `blog_publish_pending` / `error`; retry reconciliation when `run_publish` refuses overwrite
- [x] 16.2 Enrich preflight from campaign metadata when resuming without validation; preserve/compute `source_public_url` on failed and skipped-reconciliation responses
- [x] 16.3 Add stable `blog_publish.reconciliation_skip_reason` diagnostics when reconciliation is skipped
- [x] 16.4 Add regression tests in `tests/test_blog_publish_flow.py` for exact error-state server scenario, ordering, skip reasons, and non-null `source_public_url`
- [x] 16.5 Update `run-flow-a-worker-smoke.sh` to print reconciliation skip diagnostics on publish failure
- [x] 16.6 Update design, spec, README, and deployment docs with third root cause; Flow A not complete until worker smoke reaches `distribution_scheduled`
- [x] 16.7 Run `openspec validate`, targeted pytest, and full `pytest`

## 17. Reconciliation canonical publish output comparison (post-smoke validation)

**Observed smoke failure (2026-07, commit `b8b7a7a`):** `verify-worker-deploy.sh` and public repo mount PASS; public `_posts` and `assets/images` exist; `POST /publish-blog-post` fails with `blog_publish_target_exists` and `blog_publish.reconciliation_skip_reason: blog_publish_reconciliation_skipped_public_content_mismatch` while `source_public_url` is present. Root cause: reconciliation content check did not share a single canonical render path with `apply_plan` / `run_publish`, and mismatch diagnostics were insufficient to distinguish post vs image drift.

- [x] 17.1 Extract `render_expected_public_post` in `github_pages_publish.py` and use in `apply_plan` and reconciliation comparison
- [x] 17.2 Compare public post bytes against canonical publish output (not raw ready markdown); separate image mismatch skip reason
- [x] 17.3 Add safe reconciliation diagnostic hashes/paths under `blog_publish` on content or image mismatch
- [x] 17.4 Add regression tests in `tests/test_blog_publish_flow.py` (canonical `run_publish` output reconciles; raw-ready mismatch fails with hashes; image mismatch fails safely)
- [x] 17.5 Update `run-flow-a-worker-smoke.sh` to print reconciliation hash diagnostics on publish failure
- [x] 17.6 Update design, spec, README, and deployment docs with fourth root cause
- [x] 17.7 Run `openspec validate`, targeted pytest, and full `pytest`

## 18. Public image adoption reconciliation (post-smoke validation)

**Observed smoke failure (2026-07):** Public post was already published to the real GitHub Pages repo; the operator manually corrected the public image afterward. Campaign metadata remained `error` with `blog_publish_target_exists` and `blog_publish.reconciliation_skip_reason: blog_publish_reconciliation_skipped_public_image_mismatch` while public post hash matched canonical publish output and public image existed at the expected path but differed from `blog-posts/ready/...png`. Root cause: reconciliation treated ready-image drift as unsafe and refused recovery; copying the ready image over the public asset would destroy the official published image.

- [x] 18.1 Update `publish_blog_post` reconciliation to adopt existing public image when canonical post matches, public image exists at expected path, and ready image differs — never overwrite public image
- [x] 18.2 Add regression tests for image adoption, post mismatch rejection, missing image rejection, and campaign beyond blog publish
- [x] 18.3 Update `run-flow-a-worker-smoke.sh` to print adoption metadata on publish success
- [x] 18.4 Update evidence collector to show `public_image_adopted` in campaign summary when present
- [x] 18.5 Update design, spec, README, and deployment docs with fifth root cause
- [x] 18.6 Run `openspec validate`, targeted pytest, and full `pytest`
