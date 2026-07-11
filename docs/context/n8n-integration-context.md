# n8n Integration Context

Status: [CURRENT-STATE.md](../CURRENT-STATE.md). Live n8n state: [RUNTIME-STATE.md](../RUNTIME-STATE.md).

## Why Execute Command Is Not Used

n8n Execute Command runs arbitrary shell commands on the host. **Decision:** Use HTTP worker only. See ADR-0001.

## n8n as Orchestrator

n8n responsibilities:

- Trigger processing (manual, cron, or calendar-driven when activated)
- Call worker HTTP endpoints
- Branch on worker JSON responses

n8n does **not** own filesystem generation logic, shell-based processing, or LLM calls directly.

## Implemented vs imported vs active

| State | Meaning at last baseline |
|-------|--------------------------|
| **Implemented** | Worker endpoints and workflow JSON exist in repo |
| **Imported** | Flow A workflow present in n8n (`silvermanFlowAPublish01`) |
| **Tested** | Manual execution and worker smoke validated |
| **Active** | **No** — workflow export keeps `active: false`; not unattended automation |

Draft-generation workflow (`silverman-blog-linkedin-draft-generation.json`) is a separate Flow B–adjacent path.

## Worker Integration: HTTP Request Nodes Only

| Workflow | Primary HTTP calls |
|----------|-------------------|
| Flow A publish | `GET /health`, `POST /publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution` |
| Draft generation | `GET /health`, `POST /process-ready`, `/process-file`, `/generate-linkedin-draft` |
| Calendar connector | `POST /editorial-calendar/execute-flow-a-due` |

Import scripts: `deploy/server/import-flow-a-n8n-workflow.sh`. Readiness gate: `scripts/flow_a_readiness.py`.

## Workflows in repository

- `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` — Flow A (26 nodes, inactive in export)
- `n8n/workflows/silverman-blog-linkedin-draft-generation.json` — single-draft review path

## Development and Testing

Keep worker base URL configurable in n8n Set Configuration nodes. Server default: `http://192.168.0.194:8010` or `http://localhost:8010` from host.
