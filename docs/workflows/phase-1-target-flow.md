# Phase 1 Target Flow

End-to-end flow for the first operational capability: manual blog placement through worker processing to LinkedIn review drafts and metadata.

## Actors

- **Author** — places Markdown blog posts manually
- **n8n** — orchestrates HTTP calls to the worker
- **Worker** — validates paths, generates LinkedIn variants, moves files, writes metadata
- **Reviewer** — reads drafts in `linkedin-posts/review/` (human, outside worker)

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 1 TARGET FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

  [Author]
      │
      │  manually writes / copies Markdown blog post
      ▼
  blog-posts/ready/
  └── my-architecture-post.md
      │
      │  n8n trigger (manual or scheduled) — Flow A calendar connector
      ▼
  blog-posts/queued/          ← worker accepts due calendar item (queue acceptance)
  └── my-architecture-post.md
      │
      │  publish → package → schedule → lifecycle completion
      ▼
  blog-posts/processed/
  └── my-architecture-post.md
                    │
                    └── failure ──────────────► blog-posts/error/
                                                   my-architecture-post.md

  [Reviewer]
      │
      │  human review (phase 1: manual LinkedIn publish later)
      ▼
  linkedin-posts/review/
      │
      │  approve acceptable drafts
      ▼
  linkedin-posts/approved/
      │
      │  manual publish (phase 1)
      ▼
  linkedin-posts/published/     ◄── automated publish = Phase 6 (future)
```

## Step Summary

| Step | Location | Action |
|------|----------|--------|
| 1 | `blog-posts/ready/` | Author places Markdown blog post |
| 2 | n8n | Trigger workflow; call worker over HTTP |
| 3 | `blog-posts/queued/` | Worker queue-accepts due calendar item (ready → queued) |
| 4 | Worker | Validate queued source, publish blog, generate package, schedule distribution |
| 5 | `linkedin-posts/review/` | Worker writes LinkedIn draft files |
| 6 | `metadata/runs/`, `metadata/campaigns/` | Worker writes run and campaign metadata |
| 7 | `blog-posts/processed/` or `error/` | After scheduling, worker moves consumed sources from `queued/` to `processed/`; deterministic failures may use `error/` |
| 8 | Human | Review drafts; move to `approved/`; publish manually |

## Editorial source folders (Flow A)

- `blog-posts/ready/` — operator-approved inbox not yet worker-accepted.
- `blog-posts/queued/` — worker-accepted work for Flow A execution (`processing` is logical metadata only).
- `blog-posts/processed/` — sources successfully consumed through scheduling and source lifecycle completion.
- `blog-posts/error/` — terminal failures; requeue via internal `requeue_flow_a_source_from_error`.
- Traceability lives in `metadata/campaigns/<campaign-id>.json` (`original_source_relative_path`, `queued_source_relative_path`, `processed_source_relative_path`, and optional image paths).

## Out of Scope in This Flow (Phase 1)

- Dairector content paths
- GitHub blog publishing
- Automatic LinkedIn API publishing
- n8n Execute Command

## Related Documents

- `docs/context/project-overview.md`
- `docs/context/worker-architecture.md`
- `docs/context/backlog-and-phasing.md`
