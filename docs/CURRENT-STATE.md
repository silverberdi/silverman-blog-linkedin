# Current State

Canonical project status for `silverman-blog-linkedin`. Authority rules: [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Terminology: [GLOSSARY.md](GLOSSARY.md). Live flags: [RUNTIME-STATE.md](RUNTIME-STATE.md).

**`last_verified_at_utc`:** `2026-07-17T20:46:19Z`
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

- **45** canonical OpenSpec specs (includes `flow-a-concurrency-duplicate-execution-protection` after US-033 sync) (strict validation passing)
- **1,147** automated tests collected after US-034 concurrency protection (10 focused US-034 tests + prior suite; full run 1145 passed excluding two pre-existing unrelated failures: compose `local-ai-stack` assertion and sandbox `git init` readiness)
- Worker deployed at `http://192.168.0.194:8010` (see [RUNTIME-STATE.md](RUNTIME-STATE.md))
- Editorial base: `/data/silverman-blog-linkedin` (container); public GitHub Pages checkout: `/public-blog`

Key endpoints include `GET /health`, read-only `GET /flow-a/operational-status`, authenticated Flow A incomplete-campaign recovery (`GET /flow-a/incomplete-campaign-recovery/{campaign_id}`, `POST .../resume`, `POST .../repair`, `POST .../cancel` — US-031 + US-032, implemented/tested, not deployed), authenticated `POST /flow-a/operational-alerts/evaluate` (US-028 + US-029 + US-030) and `POST /flow-a/operational-alerts/report-orchestration-failure` (US-030), Flow A (`POST /publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution`, `/complete-flow-a-ready-path`, calendar connector), LinkedIn publication (`/queue-linkedin-publication`, `/publish-linkedin-due-variants`, `/cancel-linkedin-publication`), and Flow B-adjacent draft endpoints (`/process-ready`, `/process-file`, `/generate-linkedin-draft`).

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
- LinkedIn retry and recovery classification (**US-021** / BL-008 story 1): **policy defined 2026-07-16, operationally exercised 2026-07-17, operator-accepted** — normative classification of publication outcomes (recoverable transient / recoverable after remediation / non-recoverable as-is / uncertain, keyed on `last_error_code` + `http_status`; unlisted combinations fail safe to uncertain), blocked as a separate non-failure class, token-renewal-precedes-re-queue rule, and mandatory operator verification on LinkedIn before re-queueing uncertain outcomes. Uncertain class and the operator-verification procedure exercised live during the US-022 validation. Evidence: [linkedin-retry-recovery-classification.md](operations/linkedin-retry-recovery-classification.md), [us-021/us-022 validation](operations/us-021-us-022-linkedin-retry-recovery-validation-2026-07-17.md).
- LinkedIn article preview input verification (**US-023** / BL-009 story 1): **operationally validated 2026-07-17, operator-accepted** on `192.168.0.194` (`BUILD_REVISION=d15d85b`): initial dry-run detected a real live-site failure (`linkedin_preview_validation_og_tags_missing` — no `og:image`; `linkedin_preview_validation_og_description_mismatch` — excerpt-based description) on both 2026-07-15 campaigns; remediation on the public blog repo (`silverberdi.github.io` commit `e4d10de`: `og:image`/`twitter:image` from `page.image`, description tags prefer `page.description`, `_config.yml` url set to `https://silverman.pro`) with approved commit/push; passing dry-run + real runs persisted `linkedin_article_preview_validation` evidence with no other field changes. Zero LinkedIn API involvement (US-024 boundary). Evidence: [us-023 validation](operations/us-023-linkedin-preview-input-validation-2026-07-17.md).
- Flow A operational alerts (**US-028 + US-029 + US-030 / BL-011**): **deployed and operator-accepted 2026-07-17** on `192.168.0.194` (`BUILD_REVISION=b67c538`). **BL-011 closed 2026-07-17.** Controlled live smoke: evaluate returned live US-028 candidates (`item_moved_to_error`, `blog_publication_failure`); report ingest produced `failed_n8n_workflow`; eight-type `summary.counts`; evaluate-only zero lifecycle mutation; emit with flags unset → `emission.status=disabled`; auth 401; smoke entry cleaned up. `unhealthy_worker` covered by local degraded fixtures (healthy live folders correctly yield count 0). US-029 types covered by fixtures + live eight-type contract. **Follow-up enabled 2026-07-17:** emit flags on; n8n webhook + Error Trigger + evaluate/emit schedule active; live emit smoke `emission.status=emitted` (2 fingerprints). Evidence: [flow-a-operational-alerts.md](operations/flow-a-operational-alerts.md).

## Implemented but not operationally validated

- Flow A concurrency and duplicate-execution protection (**US-034 / BL-013 story 2**): **implemented, automated-tested, and acceptance criteria validated** (2026-07-18 fixture review) — first-time distribution schedule apply (`derivatives_generated` → `distribution_scheduled`) uses campaign-metadata fingerprint CAS with exclusive flock so overlapping schedule calls yield one durable schedule write and an idempotent completed loser (or `linkedin_schedule_metadata_mismatch` on identity conflict); LinkedIn publish-due re-checks durable URN evidence immediately before the API call and persists successful publish evidence via CAS so concurrent first-publish races retain a single URN; already-published / `publish_now` short-circuits with `linkedin_publish_already_published` and zero API calls; abandoned-claim stale detect + reclaim remain operator-visible (`stale`/`retryable`, `reclaimed_from_stale`, non-stale `flow_a_execution_already_claimed`). US-033 claim/image/blog protections left intact. Not deployed; not operationally validated on the live worker; US-035 and BL-013 remain open. Evidence: [flow-a-concurrency-duplicate-execution-protection-us-034.md](operations/flow-a-concurrency-duplicate-execution-protection-us-034.md), `tests/test_flow_a_concurrency_us034.py`.
- Flow A concurrency and duplicate-execution protection (**US-033 / BL-013 story 1**): **implemented, automated-tested, and acceptance criteria validated** (2026-07-18 fixture review) — claim transitions to `execution_state=processing` use campaign-metadata fingerprint CAS with exclusive flock so overlapping claims yield one winner and one `flow_a_execution_already_claimed` / `manual_intervention_required` loser; same-identity queue acceptance remains `skipped_already_queued`; pre-ComfyUI reusable-asset re-check skips generation without overwriting readable public assets; blog publish preserves `already_published` short-circuit and fail-closed `blog_publish_target_exists`; concurrent first-publish fixtures leave a single public artifact set. Calendar connector surfaces already-claimed in item `errors` without publish/ComfyUI for losers. **Out of scope for US-033:** US-034 (delivered separately above), US-035 (restart validation), Git push, live-site mutation, LinkedIn API publish, deploy. Not deployed; not operationally validated on the live worker; US-035 and BL-013 remain open. Evidence: [flow-a-concurrency-duplicate-execution-protection-us-033.md](operations/flow-a-concurrency-duplicate-execution-protection-us-033.md), `tests/test_flow_a_concurrency_us033.py`.
- Flow A incomplete-campaign recovery (**US-031 + US-032 / BL-012**): **implemented and automated-tested** — authenticated inspect/resume/repair under `/flow-a/incomplete-campaign-recovery` (US-031); additive US-032 recovery-action taxonomy (`recommended_recovery_action`), durable `flow_a_recovery.attempts` ledger (max 50, inspect ≤20), and authenticated `POST .../cancel` with post-cancel resume/repair gating (`flow_a_recovery_cancelled`). Inspect remains read-only; dry-run does not persist cancel state or attempts; ledger over-cap trims oldest. Derives `last_valid_stage` from durable milestones through `distribution_scheduled` then `flow_a_complete`; resume multi-stage catch-up with `dry_run` / `stop_after_stage`; error-folder campaigns require explicit requeue (`requeue_required`); allowlisted repairs only. Does not invent durable stage success or rewrite confirmed evidence on cancel/history writes. Not deployed; not operationally validated; US-031 and US-032 not operator-accepted; BL-012 remains open. Evidence: [flow-a-incomplete-campaign-recovery.md](operations/flow-a-incomplete-campaign-recovery.md), `tests/test_flow_a_incomplete_campaign_recovery.py`.
- Flow A operational status (**US-026 + US-027 / BL-010**): **deployed and operator-accepted 2026-07-17** on `192.168.0.194` (`BUILD_REVISION=b67c538`). **BL-010 closed 2026-07-17.** Controlled live smoke of authenticated `GET /flow-a/operational-status`: `status=partial` with 46 successful runs, 6 campaigns (4 successful / 1 failed / 1 blocked / 1 in progress), LinkedIn publish_state counts, stage-duration aggregates (`campaigns_with_stage_durations=6`, `executions_with_duration=46`), `github_pages_checkout` dependency failure, auth 401, invalid `now_utc` 422, deterministic repeat GET, byte-for-byte zero mutation (128 files). Evidence: [flow-a-operational-status.md](operations/flow-a-operational-status.md).
- LinkedIn retry limits and recovery evidence (**US-022** / BL-008 story 2): **operationally validated 2026-07-17 (`BUILD_REVISION=d15d85b`) on the primary recovery chain, operator-accepted. BL-008 closed 2026-07-17.** Demonstrated on real variant `a-bounded-context :: engineering-leadership`: controlled transport failure (container-scoped hosts injection, reverted) → `failed` with `linkedin_publish_api_error`/`http_status null` → classified `uncertain` → blind and wrong-class re-queues rejected with stable codes and zero mutation → operator-attested `linkedin_post_absence_verified` re-queue (recovery event appended) → successful retry (`urn:li:share:7483974070842241024`, attempt #2, 1 retry consumed) → failed attempt retained in append-only history → replay idempotent. Correction (`/correct-linkedin-variant`), failed-cancellation, exhaustion, and legacy normalization remain at unit-test scope. Evidence: [us-021/us-022 validation](operations/us-021-us-022-linkedin-retry-recovery-validation-2026-07-17.md). Per-variant retry budget (initial + 2 manual retries; only real LinkedIn API calls count), append-only `linkedin_publication_attempts` and `linkedin_recovery_history` evidence, class-aware re-queue with `recovery_confirmation` enum on `POST /queue-linkedin-publication`, failed-content correction via `POST /correct-linkedin-variant` (content-invalid class only), and `failed → cancelled` via `POST /cancel-linkedin-publication` with full evidence preservation. The previously recorded US-021 divergence is resolved in code: manual re-queue of a `failed` variant no longer clears stored `linkedin_publication` evidence. No new endpoints, env vars, or `publish_state` values; enablement guard unchanged. Evidence: [linkedin-retry-recovery-classification.md](operations/linkedin-retry-recovery-classification.md), unit suites `tests/test_linkedin_publication.py` / `tests/test_linkedin_supervision_flow.py`.
- LinkedIn article preview rendering confirmation (**US-024** / BL-009 story 2): **operationally demonstrated 2026-07-17, operator-accepted.** Procedure executed end-to-end on a real campaign: pre-publish Post Inspector attempt recorded as `confirmation_blocked` (LinkedIn-side app crash across browsers; site-side crawler accessibility verified); post-publish observation of real post `urn:li:share:7483953784612786177` (`keep-contracts-boring :: executive-recruiter`, published 2026-07-17T18:40:27Z via the guarded path) with passing US-023 inputs showed no article card → decision-matrix outcome `preview_not_rendered_post_format` (v1 text-post format observation, not an input or procedure failure). Completed evidence records: [blocked attempt](operations/us-024-preview-confirmation-blocked-2026-07-17.md), [post-publish confirmation](operations/us-024-preview-confirmation-keep-contracts-boring-2026-07-17.md). Procedure doc: [linkedin-preview-rendering-confirmation.md](operations/linkedin-preview-rendering-confirmation.md).
- LinkedIn article preview fallback policy (**US-025** / BL-009 story 3): **operationally demonstrated 2026-07-17, operator-accepted. BL-009 closed 2026-07-17** — inputs verified, rendering observed (`preview_not_rendered_post_format`: v1 text post renders no article card), reaction executed per policy; `content.article` remains a named deferred future-change candidate. Fallback decision executed end-to-end on the recorded `preview_not_rendered_post_format` trigger (`keep-contracts-boring`): post-publish default **accept and record** (`fallback_accept_rendering`) with zero endpoint calls, campaign document sha256 unchanged, zero retry-budget consumption, no `recovery_confirmation` use; escalation recorded as `fallback_format_change_deferred` naming the `content.article` future-change preconditions (now backed by one operationally recorded triggering outcome). Canonical spec `linkedin-article-preview-fallback` synced 2026-07-17. Evidence: [us-025 fallback decision](operations/us-025-preview-fallback-decision-keep-contracts-boring-2026-07-17.md). Policy doc: [linkedin-preview-fallback-policy.md](operations/linkedin-preview-fallback-policy.md).
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
