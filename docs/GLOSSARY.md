# Glossary

Precise terminology for `silverman-blog-linkedin`. Authority rules: [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Current status: [CURRENT-STATE.md](CURRENT-STATE.md).

## Flow A and completion layers

| Term | Definition | MUST NOT mean |
|------|------------|---------------|
| **Flow A** | End-to-end automation from calendar/queue acceptance through blog publish, LinkedIn package, distribution scheduling, and source lifecycle completion | Flow B human draft review path |
| **Flow A core** | Worker pipeline: queue acceptance → publish → package → schedule → lifecycle → campaign `distribution_scheduled` or `flow_a_complete` | Fully unattended n8n production |
| **`distribution_scheduled`** | Campaign metadata state after LinkedIn distribution timing is recorded | LinkedIn API publication completed |
| **`flow_a_complete`** | Campaign lifecycle metadata state after source moved to `blog-posts/processed/` | Entire product or feature complete |
| **Operational smoke pass** | Deterministic worker diagnostic (e.g. `run-flow-a-worker-smoke.sh`) confirming publish → package → schedule with expected campaign state | Unattended n8n scheduling |
| **Fully unattended Flow A** | n8n scheduled trigger + worker + elimination of manual Git and review steps | Same as `flow_a_complete` |
| **Flow B** | Human LinkedIn draft review path: variants in `linkedin-posts/review/` → `approved/` → `published/` | Flow A automatic distribution |

Documents MUST NOT use bare "Flow A is complete" or "Flow A complete" without naming the completion layer (campaign lifecycle, core validation, unattended operation, blog handoff, site publication).

## Editorial folder states

| State / folder | Meaning |
|----------------|---------|
| **`ready`** | Operator-approved inbox; not yet worker-accepted for Flow A |
| **`queued`** | Worker-accepted Flow A work (`blog-posts/queued/`) |
| **`processed`** | Source successfully consumed through scheduling and lifecycle completion |
| **`error`** | Terminal failure; requeue via worker recovery endpoints |

Traceability authority: `metadata/campaigns/<campaign-id>.json`.

## Blog handoff vs site publication

| Term | Definition |
|------|------------|
| **Blog handoff** / **blog files written** | Worker wrote Jekyll files to the public checkout mount (`/public-blog`) |
| **Site published/live** | Human Git commit and push; GitHub Pages deployed (e.g. `https://silverman.pro/...`) |

Worker handoff ≠ site published/live.

## LinkedIn publication states

| Term | Definition |
|------|------------|
| **LinkedIn package/scheduling implemented** | Worker generates packages and schedule metadata (`linkedin-posts/generated/`, campaign `linkedin_distribution`) |
| **LinkedIn API publication (implemented)** | Worker exposes queue/publish/cancel endpoints; guarded by `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` |
| **LinkedIn API publication (operationally validated)** | Real posts published via LinkedIn API in production — **not** validated as of last baseline |
| **`pending`** | Variant authorized for future publish window |
| **`queued`** | Variant queued with `publish_after_utc` |
| **`publishing`** | In-flight API publish |
| **`published`** | Confirmed API publication (or manual move to `linkedin-posts/published/`) |

## n8n and orchestration

| Term | Definition | MUST NOT mean |
|------|------------|---------------|
| **n8n workflow imported** | Workflow JSON exists in n8n instance | Unattended production automation |
| **n8n workflow active** | Workflow enabled for scheduled/webhook triggers | Same as Flow A core validated |

## OpenSpec terms

| Term | Definition |
|------|------------|
| **Active OpenSpec change** | Directory under `openspec/changes/<name>/` (not archived) governing approved work |
| **Canonical spec** | Requirement under `openspec/specs/` after sync from a completed change |
| **Archived change** | Directory under `openspec/changes/archive/` — historical evidence only |

## Operations

| Term | Definition |
|------|------------|
| **Reconciliation** | Worker aligns campaign/calendar state with filesystem or public-repo evidence without repeating pipeline side effects |
| **Idempotency** | Repeat calls return `completed` / `already_published` without duplicate artifacts or metadata corruption |

## Environment

| Term | Definition |
|------|------------|
| **`BUILD_REVISION`** | Git SHA baked into deployed worker image at build time (exposed via `/health` or deploy metadata) — not `SILVERMAN_BUILD_REVISION` |
