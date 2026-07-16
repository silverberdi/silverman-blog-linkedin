# Glossary

Precise terminology for `silverman-blog-linkedin`. Authority rules: [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Current status: [CURRENT-STATE.md](CURRENT-STATE.md).

## Flow A and completion layers

| Term | Definition | MUST NOT mean |
|------|------------|---------------|
| **Flow A** | End-to-end automation from calendar/queue acceptance through blog publish, LinkedIn package, distribution scheduling, and source lifecycle completion | Flow B human draft review path |
| **Flow A core** | Worker pipeline: queue acceptance → publish → package → schedule → lifecycle → campaign `distribution_scheduled` or `flow_a_complete` | Fully unattended n8n production |
| **`distribution_scheduled`** | Campaign metadata state after LinkedIn distribution timing is recorded | LinkedIn API publication completed |
| **Flow A n8n active / scheduled** | Canonical Flow A workflow enabled with Schedule Trigger (US-010) | `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` or LinkedIn API posts |
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
| **Blog Git publication** | Worker `git commit` / `git push` when enabled and opted in (`git_publication: true`); evidence in campaign `blog_git_publication` |
| **Live-site confirmation** | Worker HTTP probe of `source_public_url` after successful Git push when enabled and opted in (`live_site_confirmation: true`); evidence in campaign `blog_live_site_publication` |
| **Site published/live** | Public HTTP reachability — recorded by `blog_live_site_publication.status` `confirmed` (or operator manual verification); Git push alone is not sufficient |

Worker handoff ≠ blog Git publication ≠ live-site confirmation. Git push alone ≠ site published/live.

## LinkedIn publication states

| Term | Definition |
|------|------------|
| **LinkedIn package/scheduling implemented** | Worker generates packages and schedule metadata (`linkedin-posts/generated/`, campaign `linkedin_distribution`) |
| **LinkedIn API publication (implemented)** | Worker exposes queue/publish/cancel endpoints; guarded by `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` (fail-closed when not `true`) |
| **LinkedIn API publication (operationally validated)** | Real posts published via LinkedIn API under a controlled smoke (BL-002); live flag is independent of Flow A schedule — see [RUNTIME-STATE.md](RUNTIME-STATE.md) |
| **US-011 publication guard** | Acceptance that Flow A schedule cannot silently publish to LinkedIn; evidence may temporarily disable then restore prior enablement — MUST NOT mean LinkedIn must stay `false` forever |
| **LinkedIn variant supervision window** | Flow A phase while `publish_state` is `pending` and before LinkedIn API queue/send: variant is scheduled (`scheduled_at_utc`) and the operator MAY optionally edit, delay, or cancel. Not mandatory human review; non-intervention allows publication per distribution strategy. Policy: [linkedin-variant-review-policy.md](operations/linkedin-variant-review-policy.md); quality criteria: [linkedin-variant-quality-criteria.md](operations/linkedin-variant-quality-criteria.md) |
| **Variant publication objective** | Publication purpose for a LinkedIn variant — what the variant optimizes for (e.g. signal hireable judgment, teach a design move). Distinct from voice `tone` in campaign `variants[]` metadata. Canon: `#linkedin-derivative-package`; criteria: [linkedin-variant-quality-criteria.md](operations/linkedin-variant-quality-criteria.md) |
| **Criteria failure** | Editorial judgment that a variant does not meet US-016 quality or differentiation criteria during optional supervision. Guides operator action (edit, defer, cancel) — **not** a new `publish_state` value and **not** mandatory approval. Persistence deferred to US-017. Does not contradict optional supervision: absence of recorded criteria pass does not block strategy-driven publication |
| **Mandatory review (Flow B)** | Human approval required before any publish for system-generated Flow B content. Distinct from Flow A optional supervision and from technical `publish_state`. Flow B implementation deferred; policy encoded in editorial canon and US-015 |
| **`pending`** | Variant authorized for future publish window; after Flow A schedule, also the optional supervision window (not API-queued, not LinkedIn API published) |
| **`queued`** | Variant queued with `publish_after_utc` |
| **`publishing`** | In-flight API publish |
| **`published`** | Confirmed API publication (or manual move to `linkedin-posts/published/`) |

`distribution_scheduled` and `flow_a_complete` record campaign lifecycle after package/schedule — they MUST NOT be read as LinkedIn API published.

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
