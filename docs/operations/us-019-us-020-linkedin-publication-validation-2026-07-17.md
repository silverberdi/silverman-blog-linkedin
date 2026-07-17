# US-019 / US-020 — LinkedIn publication evidence + sequence/cadence validation

**Date (UTC):** 2026-07-17
**Host:** `192.168.0.194`
**Changes:**
- `store-linkedin-publication-evidence-us-019` (archived `2026-07-16`)
- `respect-linkedin-audience-cadence-us-020` (archived `2026-07-16`, HEAD `3c4d9f5`)
**Deployed revision:** `BUILD_REVISION=3c4d9f58c0e3a490e0f7b26ed97399aaf877eec6`
**Scope:** Close BL-007 stories US-019 and US-020 with controlled operational evidence. Does not activate n8n publish-pending; does not claim unattended LinkedIn publication.

## Overall status

**`PASS`** — BL-007 closed.

## 1. Deploy and revision confirmation

| Check | Result | Notes |
|-------|--------|-------|
| Sync repo → `/home/silverman/silverman-blog-linkedin-worker` | **PASS** | rsync of `Dockerfile`, `pyproject.toml`, `README.md`, `src/`, `prompts/`, `deploy/server/` |
| Image rebuild + `--force-recreate` | **PASS** | `deploy-worker.sh` + pin rebuild; `verify-worker-deploy.sh` OVERALL PASS (12 checks) |
| Container env `BUILD_REVISION` | **PASS** | `3c4d9f58c0e3a490e0f7b26ed97399aaf877eec6`; `.build_git_sha` matches |
| US-020 symbols in running image | **PASS** | `linkedin_publish_blocked_sequence` / `_cadence` / `_evidence_invalid` importable |
| `GET /health` | **PASS** | `healthy`, `folders_ready: true` |
| OpenAPI `/publish-linkedin-due-variants` | **PASS** | present |

Note: target-layout `deploy-worker.sh` without `.git` initially baked a timestamp `BUILD_REVISION`; a follow-up rebuild with `BUILD_REVISION=$(cat .build_git_sha)` pinned the git SHA (same pattern as US-018).

## 2. Dry-run smoke (zero mutation)

Command: `run-publish-pending-linkedin-variants.sh` (defaults → `dry_run=true`, `publish_now=true`, `auto_queue_pending=true`).

Eligible campaigns at scan time: only `state=distribution_scheduled`
(`flow-a-2026-07-06-why-i-did-not-start-with-the-database`,
`flow-a-2026-07-10-deferring-is-not-avoiding-it-can-be-architecture`).
Campaigns in `flow_a_complete` remain ineligible for publication (unchanged contract).

| Check | Result | Notes |
|-------|--------|-------|
| Plan completed | **PASS** | `status=completed`, `dry_run=true`; 8 auto-queue results, 2 publish-phase results |
| Cadence guard visible | **PASS** | `technical-architect` (2026-07-06) → `linkedin_publish_blocked_cadence` (sibling `engineering-leadership` published `2026-07-16T20:26:57Z`) |
| Sequence pre-filter visible | **PASS** | 8× `linkedin_publish_auto_queue_skipped_sequence` for later variants while earlier ones await publication |
| US-019 evidence on published skips | **PASS** | published skips carry `linkedin_post_urn` + `published_at` (e.g. `urn:li:share:7483618197204770818`) |
| Zero mutation | **PASS** | campaign aggregate SHA-256 identical before/after (`dbb07a527033e277…`) |
| No LinkedIn API calls | **PASS** | planned publish carries `linkedin_publish_dry_run`; blocked result has null URN |

## 3. Controlled real window

Baseline: `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` (unchanged throughout).

### 3.1 Cadence block without LinkedIn call

Target: `flow-a-2026-07-06-why-i-did-not-start-with-the-database` / `technical-architect`

Command: `run-publish-pending-linkedin-variants.sh --real --campaign-id … --variant technical-architect`

| Check | Result | Notes |
|-------|--------|-------|
| Auto-queue | **PASS** | `pending` → `queued`; `metadata_written: true` |
| Publish blocked | **PASS** | `skip_reason=linkedin_publish_blocked_cadence`; remains `queued` |
| No external post | **PASS** | `linkedin_post_urn=null`, `published_at=null`, `linkedin_publication=null` |
| Sibling campaigns untouched | **PASS** | deferring campaign hash unchanged during this step |

### 3.2 Sequence auto-queue skip (no mutation)

Target: `flow-a-2026-07-10-deferring-is-not-avoiding-it-can-be-architecture` / `engineering-leadership`
(while `executive-recruiter` still `pending`)

| Check | Result | Notes |
|-------|--------|-------|
| Auto-queue skipped | **PASS** | `linkedin_publish_auto_queue_skipped_sequence` |
| Metadata unchanged | **PASS** | campaign SHA identical; variant remains `pending` |
| No publish-phase entry | **PASS** | `results=[]` |

### 3.3 Allowed publish with complete US-019 evidence

Target: same deferring campaign / `executive-recruiter` (first in `AUDIENCE_SEQUENCE`, no prior `published` sibling)

| Check | Result | Notes |
|-------|--------|-------|
| Auto-queue + publish | **PASS** | `publish_state=published`, `published_at=2026-07-17T02:11:19Z` |
| URN | **PASS** | `urn:li:share:7483704861348519936` |
| Complete success evidence | **PASS** | top-level `linkedin_post_urn` + `published_at`; `linkedin_publication={provider:linkedin_rest_posts, post_urn, published_at, http_status:201}` |
| Response surfaces evidence | **PASS** | both `results[]` and `auto_queue_results[]` carry URN/`published_at` |

### 3.4 Idempotent replay

Second `--real` on the same variant:

| Check | Result | Notes |
|-------|--------|-------|
| Auto-queue skip | **PASS** | `linkedin_publish_auto_queue_skipped_state`; `metadata_written: false` |
| Publish replay | **PASS** | warning `linkedin_publish_already_published`; same URN and `published_at` |
| No second post | **PASS** | URN stable `urn:li:share:7483704861348519936` |

### 3.5 Post-publish cadence (sequence released, cadence holds)

After `executive-recruiter` published, re-run `--real` for `engineering-leadership` on the deferring campaign:

| Check | Result | Notes |
|-------|--------|-------|
| Sequence released | **PASS** | auto-queue succeeded (`pending` → `queued`) — earlier sibling no longer awaiting |
| Cadence blocked | **PASS** | publish `skip_reason=linkedin_publish_blocked_cadence`; remains `queued`; null URN |

## Acceptance criteria mapping

### US-019

| Criterion | Evidence |
|-----------|----------|
| Store external publication identifier | Real publish wrote non-empty `linkedin_post_urn` + nested `post_urn` |
| Record failures clearly | Failure-context shape covered by unit tests; this window exercised blocked (non-failed) paths with stable codes |
| Avoid retries that could create duplicates | Replay: `linkedin_publish_already_published`, identical URN/`published_at` |
| Outcome visible | Response + metadata carry URN/`published_at`/`http_status` |
| Blocked states communicated | Cadence/sequence codes distinct from failure; `publish_state` not falsely `published` |
| No unintended change | Dry-run zero mutation; targeted real runs only touched intended campaigns/variants |

### US-020

| Criterion | Evidence |
|-----------|----------|
| Respect audience cadence and sequence | Cadence block (3.1, 3.5); sequence auto-queue skip (3.2); sequence release after earlier publish (3.5) |
| Outcome visible | Stable reasons in dry-run and real responses |
| Blocked states communicated | Distinct `linkedin_publish_blocked_cadence` vs `linkedin_publish_auto_queue_skipped_sequence` |
| Existing work preserved | US-018 publish-once + safety-delay path still works; enablement baseline unchanged |

## Out of scope (not claimed)

- n8n publish-pending workflow activation (export remains `active: false`)
- Unattended scheduled LinkedIn publication (no cron/schedule wired)
- BL-008 retry/recovery policy
- Publishing remaining `pending` / cadence-blocked `queued` variants (left for later due windows)
- Evidence fail-closed path with missing `published_at` (covered by unit tests; not forced live)

## Residual campaign state after validation

| Campaign | Variant | `publish_state` | Notes |
|----------|---------|-----------------|-------|
| `…-2026-07-06-…` | `technical-architect` | `queued` | cadence-blocked; no URN |
| `…-deferring-…` | `executive-recruiter` | `published` | URN `urn:li:share:7483704861348519936` |
| `…-deferring-…` | `engineering-leadership` | `queued` | cadence-blocked after exec publish; no URN |
