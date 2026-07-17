# Current State

Canonical project status for `silverman-blog-linkedin`. Authority rules: [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Terminology: [GLOSSARY.md](GLOSSARY.md). Live flags: [RUNTIME-STATE.md](RUNTIME-STATE.md).

**`last_verified_at_utc`:** `2026-07-16T14:26:47Z`
**Last verified baseline revision:** `da21e99` (worker content serving BL-005 window — **not** a permanent runtime requirement)

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

- **31** canonical OpenSpec specs (strict validation passing at last baseline)
- **882** automated tests at last baseline
- Worker deployed at `http://192.168.0.194:8010` (see [RUNTIME-STATE.md](RUNTIME-STATE.md))
- Editorial base: `/data/silverman-blog-linkedin` (container); public GitHub Pages checkout: `/public-blog`

Key endpoints include `GET /health`, Flow A (`POST /publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution`, `/complete-flow-a-ready-path`, calendar connector), LinkedIn publication (`/queue-linkedin-publication`, `/publish-linkedin-due-variants`, `/cancel-linkedin-publication`), and Flow B-adjacent draft endpoints (`/process-ready`, `/process-file`, `/generate-linkedin-draft`).

## Ownership matrix

| Concern | Owner |
|---------|-------|
| Editorial source approval | Human operator |
| Flow A validation and lifecycle | Worker |
| Image generation | Worker → ComfyUI |
| Public checkout file writes | Worker (handoff only) |
| Git commit / push (guarded) | Worker when enabled **and** request opts in (`git_publication: true`); manual fallback documented |
| Live-site HTTP confirmation (guarded) | Worker when enabled **and** request opts in (`live_site_confirmation: true`) after Git push evidence |
| LinkedIn package generation | Worker |
| LinkedIn schedule metadata | Worker |
| LinkedIn real API publish | Worker when explicitly enabled — **operationally validated** (US-003; guard `false` by default) |
| Workflow timing / orchestration | n8n Schedule Trigger daily 09:00 UTC (server active; repo export inactive) |
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

- Guarded Git commit/push after blog handoff with per-request `git_publication: true` (US-001) — operationally validated on `192.168.0.194` with real remote push to `origin/main`; smoke artifacts removed from public site and editorial mount; see [phase3-us001-git-publication-validation-2026-07-11.md](operations/phase3-us001-git-publication-validation-2026-07-11.md)
- Live-site HTTP confirmation after Git push with per-request `live_site_confirmation: true` (US-002) — operationally validated on `192.168.0.194` (`blog_live_site_publication.status: confirmed`, HTTP 200 + slug marker during validation window); smoke artifacts removed; see [phase3-us002-live-site-confirmation-validation-2026-07-11.md](operations/phase3-us002-live-site-confirmation-validation-2026-07-11.md)
- LinkedIn API real publish (US-003/US-004/US-005, BL-002) — operationally validated on `192.168.0.194`: OAuth + queue + publish-due with `publish_now`, `linkedin_post_urn` stored, operator-confirmed visibility, idempotent rerun, safeguards restored; see [phase3-us003-linkedin-publication-validation-2026-07-11.md](operations/phase3-us003-linkedin-publication-validation-2026-07-11.md). v1 text-only API (no LinkedIn image upload); article link preview image deferred to BL-009.
- Calendar reconciliation: stale item `scheduled` → `completed` via authoritative `campaign_id` without repeating pipeline
- Calendar `flow_a_completion` LinkedIn summaries (BL-003 / US-006–US-008) — **operationally validated** on `192.168.0.194` after deploy (`BUILD_REVISION=1784088086`): reopen of `2026-07-10-a-bounded-context-is-not-a-folder` to `scheduled` + `POST /editorial-calendar/execute-flow-a-due` (`dry_run=false`) reconciled with `linkedin_package_status=completed` and `linkedin_distribution_status=completed` from canonical campaign metadata; two remaining legacy completed rows with null summaries operator-patched once; all three calendar items now show non-null LinkedIn summaries
- Worker smoke and n8n import confirmed; n8n Flow A workflow is **activated on the Ubuntu server** under US-010 (repo export remains `active: false`; activation ≠ BL-005 unattended)
- Canonical Flow A n8n identity (**US-009** / BL-004 identification slice): **validated 2026-07-15** — export `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json`, stable id `silvermanFlowAPublish01`, name **Silverman Blog LinkedIn Flow A Publish**. Evidence: [us-009 validation](operations/us-009-canonical-flow-a-n8n-identity-validation-2026-07-15.md).
- Flow A n8n activation (**US-010** / BL-004 activation slice): **validated 2026-07-15** — server `active: true`, Schedule Trigger `0 9 * * *` UTC, single-flight (static-data + shared-mount lockfile TTL 2h), idle restart + skip + TTL recovery with empty ready. Repo export `active: false`. Ready-folder HTTP path retained. Evidence: [us-010 validation](operations/us-010-flow-a-n8n-activation-validation-2026-07-15.md). *(Node count at US-010 was 31; later ready-path completion export is 35 — see implemented section.)*
- Ready-path completion HTTP + n8n wiring (`flow-a-ready-path-completion-http`): **deployed and re-imported** on `192.168.0.194` — `POST /complete-flow-a-ready-path` after schedule; server Set Configuration `git_publication` / `live_site_confirmation` / `update_calendar` true (repo export defaults remain `false`); n8n **35** nodes active. Operationally validated under BL-005 — see [bl-005-unattended-flow-a-validation-2026-07-15.md](operations/bl-005-unattended-flow-a-validation-2026-07-15.md).
- LinkedIn publication guard (**US-011** / BL-004 story 3): **validated 2026-07-15** — Flow A schedule ≠ LinkedIn enablement; `distribution_scheduled` ≠ LinkedIn API published; fail-closed `linkedin_publish_not_enabled` with temporary flag `false` then restore of recorded baseline `true`. US-011 is not permanent LinkedIn-off. Evidence: [us-011 validation](operations/us-011-linkedin-publication-guard-validation-2026-07-15.md).
- Fully unattended Flow A (**BL-005** / US-012–US-014): **validated 2026-07-16** — Manual Post A + Schedule Post B on remediated 35-node ready-path; both campaigns `flow_a_complete` with git+live, package, schedule, lifecycle, calendar; no LinkedIn API publish (variants `pending`). Schedule fire hit Pages-lag 404 then post-lag resume (US-002 pattern). Evidence: [bl-005-unattended-flow-a-validation-2026-07-15.md](operations/bl-005-unattended-flow-a-validation-2026-07-15.md).
- LinkedIn variant review policy (**US-015** / BL-006 story 1): **policy defined** — operator-facing Flow A strategy-driven publication default, optional `pending` supervision window, Flow A vs Flow B mandatory review distinction, blocked/deferred states. Evidence: [linkedin-variant-review-policy.md](operations/linkedin-variant-review-policy.md).
- LinkedIn variant quality criteria (**US-016** / BL-006 story 2): **criteria defined** — operator-facing quality and differentiation criteria, normative default variant audience/objective mapping, supervision-window checklist, criteria-failure vs technical-block communication; campaign `variants[]` includes `objective` and `audience_lens` at package generation. Evidence: [linkedin-variant-quality-criteria.md](operations/linkedin-variant-quality-criteria.md).
- LinkedIn variant supervision mechanics (**US-017** / BL-006 story 3): **implemented** (worker routes + docs + tests) — `POST /correct-linkedin-variant`, `POST /defer-linkedin-variant`, extended `POST /cancel-linkedin-publication` for `pending` pre-queue cancel; `operator_supervision` metadata on `variants[]`. Not operationally validated in production smoke. Evidence: [linkedin-variant-supervision-mechanics.md](operations/linkedin-variant-supervision-mechanics.md). **BL-006 closed** when US-015, US-016, and US-017 acceptance criteria demonstrated (2026-07-16).
- **BL-007 / US-018 scheduled LinkedIn publication execution:** opt-in `auto_queue_pending` on publish-due identifies due `pending` variants, applies US-017 supervision exclusions, queues through the existing safety-delay service, and preserves once-only publish behavior. Operator script and manual inactive HTTP-only n8n export are included. **Operationally validated 2026-07-16** on `192.168.0.194` (`BUILD_REVISION=c7bce02`): dry-run smoke with zero campaign mutation, then controlled real window — one due variant queued+published once with URN evidence and idempotent repeat run. Evidence: [us-018 validation](operations/us-018-scheduled-linkedin-publication-validation-2026-07-16.md). Not unattended: no cron/schedule wired; n8n publish-pending export stays `active: false`.
- **BL-007 / US-019 publication evidence formalization:** complete success evidence (`linkedin_post_urn`, `published_at`, `linkedin_publication` with `provider`/`post_urn`/`published_at`/`http_status`) and failure-context taxonomy; additive URN/`published_at` on `auto_queue_results`. **Operationally validated 2026-07-17** on `192.168.0.194` (`BUILD_REVISION=3c4d9f5`): real publish of `executive-recruiter` on `flow-a-2026-07-10-deferring-is-not-avoiding-it-can-be-architecture` wrote URN `urn:li:share:7483704861348519936` with `http_status=201`; replay idempotent. Evidence: [us-019/us-020 validation](operations/us-019-us-020-linkedin-publication-validation-2026-07-17.md).
- **BL-007 / US-020 publish-time sequence and cadence guard:** per-campaign guard at publish time (plain / combined / targeted / scan) plus auto-queue sequence pre-filter; 72h cadence anchored to stored `published_at`; evidence fail-closed; stable block reasons. **Operationally validated 2026-07-17** on `192.168.0.194` (`BUILD_REVISION=3c4d9f5`): dry-run zero mutation with cadence + sequence reasons; real cadence block without LinkedIn call; real sequence auto-queue skip; post-publish cadence after allowed publish. Evidence: [us-019/us-020 validation](operations/us-019-us-020-linkedin-publication-validation-2026-07-17.md). **BL-007 closed.**

## Implemented but not operationally validated

- OAuth LinkedIn token refresh in production (refresh token not present in current token store)

## Manual steps (by design)

- Git commit and push to GitHub Pages when automatic Git publication is disabled, not opted in (`git_publication: false`), or validation window is closed — manual fallback after worker handoff
- LinkedIn draft review and manual publish (Flow B path) or guarded API publish when enabled
- n8n workflow activation when operator chooses unattended orchestration
- Editorial source placement in `blog-posts/ready/`

## Incomplete / deferred

- Flow B automation beyond draft generation orchestration
- Dairector content paths
- **BL-015** Flow A LinkedIn variant supervision console (US-038–US-040) — backlog defined; not implemented. US-017 worker mechanics implemented. See [backlog.md](product/backlog.md). Mechanics: [linkedin-variant-supervision-mechanics.md](operations/linkedin-variant-supervision-mechanics.md)
- Former BL-007 construction WIP absorbed under US-018; record: [bl-007-auto-queue-pending-handoff.md](product/bl-007-auto-queue-pending-handoff.md). **BL-007 closed 2026-07-17** after US-018/US-019/US-020 operational validation.

## Completion layers (qualified)

| Layer | Status at last baseline |
|-------|-------------------------|
| Flow A core worker pipeline | Operationally validated |
| Campaign `flow_a_complete` | Validated for test post |
| Blog handoff to public checkout | Validated |
| Git commit/push to remote (US-001) | Operationally validated (controlled smoke) |
| Live-site confirmation (US-002) | Operationally validated (controlled smoke; HTTP 200 + slug marker) |
| Site published/live | Operationally validated via US-002 probe when `live_site_confirmation` opted in; manual Git still valid when automation disabled |
| LinkedIn package/scheduling | Validated |
| LinkedIn API publication | Operationally validated (US-003 controlled smoke; `executive-recruiter` on bounded-context campaign) |
| Fully unattended Flow A | Operationally validated (BL-005 Manual + Schedule; not LinkedIn API publish) |

Do not describe any single layer as "Flow A complete" without qualification. See [GLOSSARY.md](GLOSSARY.md).

## Flow A readiness defaults

`scripts/flow_a_readiness.py` `DEFAULT_EXPECTED_COMMITS` (`88cd5bc`, `96519c3`, `9dba064`) gates validated operational capabilities via ancestry checks — not the same as **`last_verified_baseline`** (`615091c` @ `2026-07-11T07:45:00Z` above), which is a point-in-time verification snapshot. Neither is a permanent runtime requirement; use `--expected-commit` to override defaults for forks or bisect.

## Related documents

- Workflows: [flow-a-target-flow.md](workflows/flow-a-target-flow.md), [linkedin-draft-review-flow.md](workflows/linkedin-draft-review-flow.md)
- Product: [backlog.md](product/backlog.md), [bl-007-auto-queue-pending-handoff.md](product/bl-007-auto-queue-pending-handoff.md)
- ADRs: [docs/decisions/](decisions/)
- Specs: `openspec/specs/`
