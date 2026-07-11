# Flow A Target Flow

Flow A automation pipeline: calendar connector through source lifecycle completion. Terminology: [GLOSSARY.md](../GLOSSARY.md). Status: [CURRENT-STATE.md](../CURRENT-STATE.md).

Human LinkedIn draft review is a separate path: [linkedin-draft-review-flow.md](linkedin-draft-review-flow.md).

## Actors

- **Operator** — places approved Markdown in `blog-posts/ready/`; manual Git commit/push after handoff
- **n8n** — orchestrates HTTP calls (workflow imported; activation optional — see [RUNTIME-STATE.md](../RUNTIME-STATE.md))
- **Worker** — queue acceptance, publish, package, schedule, lifecycle, reconciliation
- **ComfyUI** — optional blog hero image generation before publish validation

## Flow diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLOW A AUTOMATION                                    │
└─────────────────────────────────────────────────────────────────────────────┘

  [Operator]
      │
      │  approved Markdown (+ optional PNG) in ready/
      ▼
  blog-posts/ready/
      │
      │  n8n calendar connector OR manual worker smoke
      ▼
  blog-posts/queued/          ← queue acceptance (ready → queued)
      │
      │  publish → package → schedule → lifecycle completion
      ▼
  blog-posts/processed/       ← campaign flow_a_complete
      │
      └── failure ──────────► blog-posts/error/
                                 (requeue via worker recovery)

  Side effects (worker):
  - Public checkout handoff (_posts/, assets/images/)  ← NOT site published/live
  - linkedin-posts/generated/ package artifacts
  - metadata/campaigns/<id>.json lifecycle
```

## Step summary

| Step | Location | Action |
|------|----------|--------|
| 1 | `blog-posts/ready/` | Operator places approved source |
| 2 | Calendar / n8n | Due item triggers worker over HTTP |
| 3 | `blog-posts/queued/` | Worker queue-accepts (`POST /editorial-calendar/execute-flow-a-due` or publish path) |
| 4 | Worker | `POST /publish-blog-post` — handoff to public checkout |
| 5 | Worker | `POST /generate-linkedin-package` — multi-variant package |
| 6 | Worker | `POST /schedule-linkedin-distribution` — stagger metadata |
| 7 | `metadata/campaigns/` | Campaign state → `distribution_scheduled` / `flow_a_complete` |
| 8 | `blog-posts/processed/` | Source lifecycle completion |
| 9 | Operator | Manual Git commit/push for site published/live |

## Editorial source folders

| Folder | Meaning |
|--------|---------|
| `blog-posts/ready/` | Operator-approved inbox not yet worker-accepted |
| `blog-posts/queued/` | Worker-accepted Flow A execution |
| `blog-posts/processed/` | Consumed through scheduling and lifecycle completion |
| `blog-posts/error/` | Terminal failures; requeue via `requeue_flow_a_source_from_error` |

Traceability: `metadata/campaigns/<campaign-id>.json` (`original_source_relative_path`, `queued_source_relative_path`, `processed_source_relative_path`).

## Recovery classifications

| Symptom | Layer |
|---------|-------|
| `blog_publish_public_repo_not_configured` | Worker deployment (public mount) |
| `blog_publish_target_exists` + reconciliation skip | Worker idempotency / reconciliation |
| `deepseek_config_invalid` | Provider config |
| Worker smoke PASS, n8n fails same step | n8n payload / branch mapping |

See [editorial-calendar-flow-a-execution-connector.md](editorial-calendar-flow-a-execution-connector.md) for queue semantics.

## Out of scope in Flow A automation

- Dairector content paths
- Automatic Git commit/push (handoff only)
- Real LinkedIn API publication (separate guarded endpoints)
- n8n Execute Command
- Flow B human draft review path

## Related documents

- [editorial-calendar-orchestration.md](editorial-calendar-orchestration.md)
- [editorial-calendar-flow-a-execution-connector.md](editorial-calendar-flow-a-execution-connector.md)
- [blog-publishing-bridge.md](blog-publishing-bridge.md) — operator CLI alternative to worker publish
- n8n workflow: `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json`
- Deploy smoke: `deploy/server/run-flow-a-worker-smoke.sh`
