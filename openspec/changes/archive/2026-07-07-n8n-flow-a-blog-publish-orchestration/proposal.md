## Why

The active Flow A umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` has completed worker slices 1–6: editorial validation (library), blog publish (`POST /publish-blog-post`), multi-variant package generation (`POST /generate-linkedin-package`), and distribution scheduling (`POST /schedule-linkedin-distribution`). n8n still only orchestrates the legacy single-draft workflow (`silverman-blog-linkedin-draft-generation.json`), which targets human review in `linkedin-posts/review/` and does not chain publish → package → schedule. Without slice 7, Flow A cannot run end-to-end over HTTP (ADR-0001); operators must invoke worker steps manually or piecemeal.

## Goals

- Add a dedicated Flow A n8n orchestration workflow that chains worker endpoints in lifecycle order without human approval after validation.
- Discover ready candidates via `POST /process-ready`, then for each candidate invoke publish → package → schedule with structured branching on `status` and `errors[]`.
- Pass `campaign_id` and `source_relative_path` between steps using worker response fields.
- Keep the workflow export inactive (`"active": false`) and manual-trigger only (no production cron).
- Preserve Flow B separation by leaving the existing single-draft workflow unchanged.
- Prepare an operator-run end-to-end smoke test path on the Ubuntu server worker.

## Non-Goals

- LinkedIn API publication (deferred to slice 8 `linkedin-publication-integration`).
- Activating production scheduling (cron/webhook) in the exported workflow JSON.
- Modifying `n8n/workflows/silverman-blog-linkedin-draft-generation.json` (Flow B / manual review path).
- New worker HTTP endpoints or changes to publish/package/schedule contracts.
- Moving source blog files between editorial folders from n8n.
- Git commit, git push, or public-repo operations from n8n.
- Archiving the umbrella or this child change.
- Committing or pushing repository changes as part of this proposal.

## What Changes

- Add child OpenSpec change `n8n-flow-a-blog-publish-orchestration` under active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 7).
- Introduce capability spec `n8n-flow-a-blog-publish-orchestration` covering a new importable workflow artifact, HTTP-only orchestration, worker endpoint chaining, error branching, idempotent rerun behavior, API-key handling, and inactive export defaults.
- Add new workflow export `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` (name finalized at apply) — separate from the existing draft-generation workflow.
- Extend or add lightweight workflow validation tests following `tests/test_n8n_workflow.py` patterns.
- Update README with Flow A orchestration import/configuration and end-to-end smoke-test steps.
- Update umbrella roadmap progress to mark slice 7 as **proposed/active**.

No worker Python changes, LinkedIn API calls, source file moves, or git operations are included.

## Capabilities

### New Capabilities

- `n8n-flow-a-blog-publish-orchestration`: Importable n8n workflow JSON that orchestrates Flow A over HTTP only — health → process-ready → per-candidate `POST /publish-blog-post` → `POST /generate-linkedin-package` → `POST /schedule-linkedin-distribution` — with structured error branching, idempotent rerun support, configurable worker base URL and API key placeholder, and inactive manual-trigger export.

### Modified Capabilities

<!-- No existing main spec requirements change. The legacy n8n-worker-orchestration-flow spec remains scoped to silverman-blog-linkedin-draft-generation.json. -->

## Impact

- **Umbrella reference**: This change MUST cite `flow-a-automatic-blog-linkedin-publishing-roadmap` for Flow A policy, lifecycle, and child sequencing. The umbrella remains active.
- **Worker endpoints consumed**: `GET /health`, `POST /process-ready`, `POST /publish-blog-post`, `POST /generate-linkedin-package`, `POST /schedule-linkedin-distribution` (all existing; no contract changes).
- **Canonical specs referenced**: `ready-post-editorial-validation`, `worker-blog-publishing-endpoint`, `linkedin-derivative-package-generation`, `linkedin-distribution-scheduling-model`, `flow-a-lifecycle`, `editorial-canon`, `n8n-worker-orchestration-flow` (patterns only; no delta).
- **OpenSpec**: New change directory `openspec/changes/n8n-flow-a-blog-publish-orchestration/` with proposal, design, tasks, and `specs/n8n-flow-a-blog-publish-orchestration/spec.md`.
- **n8n**: New workflow JSON file; operators re-import after merge; workflow remains inactive in export.
- **Tests**: New or extended lightweight workflow structure tests; no live n8n runtime required in CI.
- **Future children**: Slice 8 (`linkedin-publication-integration`) may extend this workflow with a publish step when API constraints are documented.
