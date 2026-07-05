# Backlog and Phasing

OpenSpec changes must represent **coherent capabilities**, not one change per tiny file. Implementation starts only after a change is proposed, reviewed, validated, and approved.

## Phase 0: Context Bootstrap (current)

**Status:** In progress / complete when context docs and ADRs exist.

Deliverables:

- Project context documents (`docs/context/`)
- Architecture decision records (`docs/decisions/`)
- Workflow diagrams (`docs/workflows/`)
- Cursor project rule (`.cursor/rules/`)

No application code, Dockerfile, or OpenSpec change artifacts yet.

## Phase 1: Worker Foundation

**OpenSpec change:** `worker-foundation` (name TBD at proposal time)

Scope:

- Service skeleton (e.g., FastAPI application structure)
- Configuration via environment variables
- Folder path validation
- `GET /health` only

Explicitly not in this change: processing endpoints, OpenAI integration, n8n workflows.

## Phase 2: Process Ready Blog Posts

**OpenSpec change:** `process-ready`

Scope:

- `POST /process-ready`
- Read all Markdown files in `blog-posts/ready/`
- Generate LinkedIn variants (OpenAI integration)
- Write outputs to `linkedin-posts/review/`
- Write run/campaign metadata
- Move sources to `processed/` or `error/`

## Phase 3: Process Single Blog Post

**OpenSpec change:** `process-file`

Scope:

- `POST /process-file`
- Process one named file in `blog-posts/ready/`
- Same generation and metadata behavior as batch, scoped to one file

Useful for retries, manual triggers, and n8n workflows that target a specific post.

## Phase 4: n8n Integration Workflows

**OpenSpec change:** `n8n-integration`

Scope:

- Importable n8n workflow JSON
- HTTP Request nodes calling worker endpoints
- Manual trigger workflow
- Scheduled (cron) workflow
- Configurable worker base URL
- No Execute Command

## Phase 5: GitHub Blog Publishing

**OpenSpec change:** TBD at proposal time

Scope (future):

- Publish or sync blog posts to GitHub (pages or repo structure)
- Out of phase 1; depends on stable editorial pipeline

## Phase 6: LinkedIn Publishing Automation

**OpenSpec change:** TBD at proposal time

Scope (future):

- Move from manual publish to automated or semi-automated LinkedIn posting
- Requires approved drafts in `linkedin-posts/approved/`
- API credentials, rate limits, and human override policies to be defined in proposal

## Dependency Order

```
Phase 0 (context)
    └── Phase 1 (foundation + /health)
            └── Phase 2 (/process-ready)
                    ├── Phase 3 (/process-file)
                    └── Phase 4 (n8n workflows)
                            ├── Phase 5 (GitHub)
                            └── Phase 6 (LinkedIn publish)
```

Phases 5 and 6 may be proposed independently after phase 2+ stability; they are not blocked on each other.

## OpenSpec Discipline Reminder

- Do not implement before an approved change.
- Do not split foundation into dozens of micro-changes.
- Proposal, design, tasks, and specs are created through the OpenSpec workflow (`/opsx:propose`, `/opsx:apply`) when each phase starts.
