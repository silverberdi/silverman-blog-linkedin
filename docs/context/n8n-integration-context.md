# n8n Integration Context

## Why Execute Command Is Not Used

n8n Execute Command runs arbitrary shell commands on the host where n8n executes. That capability:

- Expands the attack surface if workflows are compromised or misconfigured
- Blurs accountability between orchestration and implementation
- Makes behavior harder to test, version, and review in isolation
- Increases operational risk on a shared Linux server

**Decision:** Do not enable n8n Execute Command for this system. Use a dedicated HTTP worker instead. See ADR-0001.

## n8n as Orchestrator

n8n responsibilities:

- Detect or schedule when processing should run
- Call worker HTTP endpoints
- Branch on worker JSON responses (success, partial failure, errors)
- Future: notify on completion, trigger review reminders, coordinate publish workflows

n8n does **not**:

- Read/write editorial Markdown directly for generation logic
- Invoke shell scripts for core processing
- Hold business logic for LinkedIn variant generation

## Worker Integration: HTTP Request Nodes Only

All worker integration must use n8n **HTTP Request** nodes:

| Workflow action | HTTP call |
|-----------------|-----------|
| Health check | `GET /health` |
| Process all ready posts | `POST /process-ready` |
| Process one file | `POST /process-file` |

Request bodies, headers, and authentication (if added later) must be configured explicitly in the workflow. Do not use Execute Command, SSH nodes, or custom command runners as substitutes for worker endpoints.

## Future Workflows

### Manual workflow (Phase 4 target)

1. Manual trigger (or webhook) in n8n
2. Optional: verify worker health (`GET /health`)
3. `POST /process-ready`
4. Parse response; notify or log counts
5. Human reviews output in `linkedin-posts/review/`

### Scheduled workflow (Phase 4 target)

1. Cron trigger (e.g., daily or on interval)
2. `GET /health` — skip or alert if unhealthy
3. `POST /process-ready`
4. Record summary (future: write to n8n data store or external log)

Importable n8n workflow JSON will be delivered in the **n8n integration** OpenSpec change, not during bootstrap.

## Development and Testing

During local development, n8n on the server may call:

- A worker running locally (if network allows), or
- A worker running in a dev container on the server

Workflow design should keep the worker base URL configurable (environment variable or n8n credential) so the same workflow exports work across dev and production.
