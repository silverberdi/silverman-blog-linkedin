# US-018 — Scheduled LinkedIn publication execution validation

**Date (UTC):** 2026-07-16
**Host:** `192.168.0.194`
**Change:** `implement-scheduled-linkedin-publication-execution-us-018` (archived `2026-07-16`)
**Deployed revision:** `BUILD_REVISION=c7bce027cc7dc2f9a685b117ecf90b31ad3db074` (HEAD after impl `1b4a8fb` + sync `c86b33d` + archive `c7bce02`)
**Scope:** BL-007 story 1 only. US-019 (publication-evidence polish) and US-020 (cadence/sequence) remain deferred. BL-007 stays open.

## Overall status

**`PASS`**

## 8.1 Deploy and revision confirmation

| Check | Result | Notes |
|-------|--------|-------|
| Sync repo → `/home/silverman/silverman-blog-linkedin-worker` | **PASS** | rsync of `Dockerfile`, `pyproject.toml`, `src/`, `prompts/`, deploy scripts incl. `run-publish-pending-linkedin-variants.sh` and `finish-pending-linkedin-publication.sh` |
| Image rebuild + `--force-recreate` | **PASS** | `verify-worker-deploy.sh` OVERALL PASS (12 checks) |
| Container env `BUILD_REVISION` | **PASS** | `c7bce027cc7dc2f9a685b117ecf90b31ad3db074`; `.build_git_sha` matches |
| `GET /health` | **PASS** | `healthy`, `folders_ready: true` |
| OpenAPI `/publish-linkedin-due-variants` | **PASS** | present (20 paths) |

Note: `/health` does not expose `BUILD_REVISION`; confirmation is via container env and deploy metadata (allowed per engineering rule). Target-layout `deploy-worker.sh` falls back to a timestamp `BUILD_REVISION` (no `.git` in target); a follow-up rebuild pinned the env to the git SHA.

## 8.2 Dry-run smoke (zero mutation)

Command: `run-publish-pending-linkedin-variants.sh` (no flags → `dry_run=true`, `publish_now=true`, `auto_queue_pending=true`).

| Check | Result | Notes |
|-------|--------|-------|
| Identify/queue/publish plan | **PASS** | 7 `pending` variants across 2 `distribution_scheduled` campaigns planned for queue+publish |
| Skip reasons surfaced | **PASS** | `executive-recruiter` (2026-07-06 campaign, already `published`) → `linkedin_publish_auto_queue_skipped_state` |
| `metadata_written: false` on all auto-queue results | **PASS** | |
| Zero mutation | **PASS** | SHA-256 of all `metadata/campaigns/*.json` identical before/after (`7ef124a0…`) |
| No LinkedIn API calls / URNs | **PASS** | all `linkedin_post_urn: null`; warnings `linkedin_publish_dry_run` |

## 8.3 Controlled real window (single variant)

Target: campaign `flow-a-2026-07-06-why-i-did-not-start-with-the-database`, variant `engineering-leadership` (`pending`, `scheduled_at_utc=2026-07-11T14:00:00Z` — due).

Command: `run-publish-pending-linkedin-variants.sh --real --campaign-id … --variant engineering-leadership` (script preflight confirmed `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` baseline).

| Check | Result | Notes |
|-------|--------|-------|
| Auto-queue phase | **PASS** | `pending` → `queued` (`publish_after_utc=2026-07-16T22:26:56Z`, safety delay applied); `metadata_written: true` |
| Publish phase (once) | **PASS** | `publish_state=published`, `published_at=2026-07-16T20:26:57Z` |
| URN evidence | **PASS** | `urn:li:share:7483618197204770818` |
| Repeat-run idempotency | **PASS** | second `--real` run: auto-queue skipped (`linkedin_publish_auto_queue_skipped_state`, `metadata_written: false`); publish replay warned `linkedin_publish_already_published`; same URN, same `published_at`, no second post |
| Supervision/state exclusions respected | **PASS** | previously `published` variant excluded by D3 state rule in both dry-run and real windows |
| Other campaigns untouched | **PASS** | SHA-256 of all other campaign files identical before/after (`35d23c0e…`) |
| Enablement flag policy | **PASS** | baseline `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` unchanged (no temporary flip needed; restore-per-policy = keep recorded baseline) |

`publish_now=true` (script default) bypassed only the strategy schedule gate; supervision and state exclusions still applied. The `queued` safety delay (`publish_after_utc`) is bypassed by `publish_now` per the approved contract's operator-override semantics; `--respect-schedule` retains both gates.

## US-018 acceptance criteria mapping

| Criterion | Evidence |
|-----------|----------|
| Identify due variants | Dry-run plan (7 due/planned) + real-window identification of due `pending` variant |
| Move only eligible variants to queued state | Only `pending` moved; `published` variant skipped with stable code |
| Publish each variant once | Single URN; repeat run produced no new post (`linkedin_publish_already_published`) |
| Outcome visible and understandable | Script per-variant `auto-queue:` / `publish:` outcome lines + JSON skip codes |
| Failures/blocked states clearly communicated | Stable skip codes (`linkedin_publish_auto_queue_skipped_state` observed; `_not_due` / `_supervision` covered by unit tests) |
| Existing completed work not duplicated or changed | Zero-mutation dry run; other-campaign hash equality; published variant unchanged on repeat |

## Out of scope (not claimed)

- US-019 external-identifier/failure evidence polish; US-020 cadence/sequence (deferred; BL-007 open)
- n8n publish-pending workflow activation (export remains `active: false`; manual trigger only)
- Unattended scheduled LinkedIn publication (no cron/schedule wired to this endpoint)
- Remaining `pending` variants — not published in this window
