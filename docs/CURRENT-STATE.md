# Current State

Canonical project status for `silverman-blog-linkedin`. Authority rules: [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Terminology: [GLOSSARY.md](GLOSSARY.md). Live flags: [RUNTIME-STATE.md](RUNTIME-STATE.md).

**`last_verified_at_utc`:** `2026-07-10T00:00:00Z`
**Last verified baseline revision:** `88cd5bc` (verification timestamp above — **not** a permanent runtime requirement)

## Purpose

Local HTTP worker for blog-to-LinkedIn content automation. n8n orchestrates over HTTP only (ADR-0001). The worker owns filesystem boundaries, validation, generation, metadata, and editorial lifecycle moves.

## Business goals

- **Short-term:** Attract recruiters and C-level executives for remote senior roles (~USD 7k/month).
- **Long-term:** Recognition in AI, architecture, digital transformation, agility, governance, and technology efficiency.

## Architecture summary

```
n8n (orchestrator, HTTP only) → Worker (FastAPI) → Editorial dirs + public blog checkout
                                      ↓
                              ComfyUI (optional images), DeepSeek (LLM)
```

- **27** canonical OpenSpec specs (strict validation passing at last baseline)
- **850** automated tests at last baseline
- Worker deployed at `http://192.168.0.194:8010` (see [RUNTIME-STATE.md](RUNTIME-STATE.md))
- Editorial base: `/data/silverman-blog-linkedin` (container); public GitHub Pages checkout: `/public-blog`

Key endpoints include `GET /health`, Flow A (`POST /publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution`, calendar connector), LinkedIn publication (`/queue-linkedin-publication`, `/publish-linkedin-due-variants`, `/cancel-linkedin-publication`), and Flow B-adjacent draft endpoints (`/process-ready`, `/process-file`, `/generate-linkedin-draft`).

## Ownership matrix

| Concern | Owner |
|---------|-------|
| Editorial source approval | Human operator |
| Flow A validation and lifecycle | Worker |
| Image generation | Worker → ComfyUI |
| Public checkout file writes | Worker (handoff only) |
| Git commit / push (guarded) | Worker when enabled **and** request opts in (`git_publication: true`); manual fallback documented |
| LinkedIn package generation | Worker |
| LinkedIn schedule metadata | Worker |
| LinkedIn real API publish | Worker when explicitly enabled (not operationally validated) |
| Workflow timing / orchestration | n8n when activated (currently inactive) |
| Secrets and environment flags | Operator |
| Deployment | Operator (`deploy/server/deploy-worker.sh`) |
| Behavioral requirements | Canonical OpenSpec specs |
| Real behavior evidence | Implementation and tests |
| Current status and known divergences | This document |
| Volatile live flags | [RUNTIME-STATE.md](RUNTIME-STATE.md) |
| Editorial policy | `content-strategy/silverman-editorial-system.md` |

## Runtime topology

| Item | Value |
|------|-------|
| Server | `192.168.0.194` |
| Worker port | `8010` |
| Editorial host path | `/home/silverman/compartido_mac/silverman-blog-linkedin` |
| Public blog host path | `/home/silverman/silverberdi.github.io` |
| Deploy guide | [ubuntu-server-worker-deployment.md](deployment/ubuntu-server-worker-deployment.md) |

## Operationally validated

Evidence from real post `04-a-bounded-context-is-not-a-folder.md` (2026-07-10):

- Flow A core end-to-end: ComfyUI image, validation, blog handoff, package, schedule, lifecycle, campaign **`flow_a_complete`**
- Blog live at `https://silverman.pro/2026/07/10/a-bounded-context-is-not-a-folder/` after **manual** Git commit/push
- `POST /publish-blog-post` idempotency: `already_published` with no metadata side effects
## Operationally validated (recent)

- Guarded Git commit/push after blog handoff with per-request `git_publication: true` (US-001) — controlled smoke on `192.168.0.194` with real remote push to `origin/main` (`commit_sha` `53d0a26…`); see [phase3-us001-git-publication-validation-2026-07-11.md](operations/phase3-us001-git-publication-validation-2026-07-11.md)
- Calendar reconciliation: stale item `scheduled` → `completed` via authoritative `campaign_id` without repeating pipeline
- Worker smoke and n8n import confirmed; n8n workflow remains **inactive** (import ≠ unattended automation)

## Implemented but not operationally validated

- LinkedIn real API publication (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` at last baseline)
- Fully unattended Flow A (n8n scheduling inactive)
- OAuth LinkedIn token refresh in production

## Manual steps (by design)

- Git commit and push to GitHub Pages when automatic Git publication is disabled, not opted in (`git_publication: false`), or validation window is closed — manual fallback after worker handoff
- LinkedIn draft review and manual publish (Flow B path) or guarded API publish when enabled
- n8n workflow activation when operator chooses unattended orchestration
- Editorial source placement in `blog-posts/ready/`

## Incomplete / deferred

- Flow B automation beyond draft generation orchestration
- Dairector content paths
- Operator review UI for LinkedIn publication
- US-002 remote Git reconciliation and live-site confirmation

## Completion layers (qualified)

| Layer | Status at last baseline |
|-------|-------------------------|
| Flow A core worker pipeline | Operationally validated |
| Campaign `flow_a_complete` | Validated for test post |
| Blog handoff to public checkout | Validated |
| Git commit/push to remote (US-001) | Operationally validated (controlled smoke; US-002 deferred) |
| Site published/live | US-002 deferred; Git push validated without live URL probe |
| LinkedIn package/scheduling | Validated |
| LinkedIn API publication | Implemented; not operationally validated |
| Fully unattended Flow A | Not achieved (n8n inactive) |

Do not describe any single layer as "Flow A complete" without qualification. See [GLOSSARY.md](GLOSSARY.md).

## Known spec↔implementation / tooling divergences

| Item | Notes | Resolution |
|------|-------|------------|
| `scripts/flow_a_readiness.py` `DEFAULT_EXPECTED_COMMITS` | Hardcoded `79f5345`, `962ba2f`, `53708eb` — stale vs current baseline `88cd5bc` | Separate OpenSpec change to update executable defaults (out of scope for context alignment) |

## Related documents

- Workflows: [flow-a-target-flow.md](workflows/flow-a-target-flow.md), [linkedin-draft-review-flow.md](workflows/linkedin-draft-review-flow.md)
- ADRs: [docs/decisions/](decisions/)
- Specs: `openspec/specs/`
