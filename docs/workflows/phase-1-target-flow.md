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
      │  n8n trigger (manual or scheduled)
      ▼
  ┌─────────┐
  │   n8n   │
  └────┬────┘
       │  GET /health          (optional sanity check)
       │
       │  POST /process-ready  (or POST /process-file for single file)
       ▼
  ┌─────────────────┐
  │  HTTP Worker    │
  │  (Docker/local) │
  └────────┬────────┘
           │
           ├──► validate folder layout under data root
           │
           ├──► read Markdown from blog-posts/ready/
           │
           ├──► generate LinkedIn variants (LLM)
           │         ├── executive / recruiter
           │         ├── technical leadership
           │         └── short provocative
           │
           ├──► write drafts ──────────────────► linkedin-posts/review/
           │         ├── my-architecture-post-executive.md
           │         ├── my-architecture-post-technical.md
           │         └── my-architecture-post-short.md
           │
           ├──► write metadata ────────────────► metadata/runs/
           │                                    metadata/campaigns/
           │
           └──► move source file
                    │
                    ├── success ──────────────► blog-posts/processed/
                    │                              my-architecture-post.md
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
| 3 | Worker | Validate paths, read source, generate variants |
| 4 | `linkedin-posts/review/` | Worker writes LinkedIn draft files |
| 5 | `metadata/runs/`, `metadata/campaigns/` | Worker writes run and campaign metadata |
| 6 | `blog-posts/processed/` or `error/` | After successful Flow A through scheduling and source lifecycle, worker moves consumed sources from `ready/` to `processed/`; failures may mark `error/` per validation policy |
| 7 | Human | Review drafts; move to `approved/`; publish manually |

## Editorial source folders (Flow A)

- `blog-posts/ready/` — pending operator-approved input awaiting Flow A consumption.
- `blog-posts/processed/` — source Markdown and companion images successfully consumed by Flow A (publish → package → schedule → source lifecycle).
- Traceability lives in `metadata/campaigns/<campaign-id>.json` (`original_source_relative_path`, `processed_source_relative_path`, and optional image paths). After successful Flow A, operators should not manually relocate processed files; re-run services by `campaign_id` when idempotent recovery is needed.

## Out of Scope in This Flow (Phase 1)

- Dairector content paths
- GitHub blog publishing
- Automatic LinkedIn API publishing
- n8n Execute Command

## Related Documents

- `docs/context/project-overview.md`
- `docs/context/worker-architecture.md`
- `docs/context/backlog-and-phasing.md`
