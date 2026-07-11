# Phase 3 Report: US-002 live-site confirmation validation

**Date:** 2026-07-11  
**Server:** silverman@192.168.0.194  
**Change:** confirm-live-blog-site-publication  
**Script:** `deploy/server/run-us002-live-site-confirmation-smoke.sh`

## Preconditions applied

- Worker image rebuilt with US-002 modules (`blog_live_site_confirmation.py`, Git fetch/ff-only reconciliation)
- `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true` (from US-001 window)
- `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED=true` during validation window
- `GIT_SSH_COMMAND` and deploy key mounts unchanged from US-001

## Container egress precheck

| Check | Result |
|-------|--------|
| `GET https://silverman.pro` from worker container | **PASS** — HTTP `403` (reachable; root may block bare clients) |

## Smoke outcome

| Check | Result |
|-------|--------|
| First publish (`git_publication: true`, `live_site_confirmation: true`) | **Partial** — push succeeded; probe failed (`blog_live_site_confirmation_unreachable`, HTTP `404`, 5 attempts) — GitHub Pages propagation lag |
| Remote `origin/main` advanced | **PASS** — commit `5908147893fca76a6af798b36d84440ee2edab98` |
| Second publish after propagation | **PASS** — `status: completed`, `blog_live_site_publication.status: confirmed`, HTTP `200`, `attempts: 1` |
| Idempotent rerun | **PASS** — `blog_git_publication.status: already_published`, `blog_live_site_publication.status: already_confirmed` |
| `public_slug` in probed page body | **PASS** — slug marker present at probed canonical URL during validation window |
| Campaign metadata evidence | **PASS** — `blog_git_publication` + `blog_live_site_publication` recorded during smoke |

## Probe evidence (confirmed run)

| Field | Value |
|-------|--------|
| `http_status` | `200` |
| `attempts` | `1` |
| `commit_sha` | `5908147893fca76a6af798b36d84440ee2edab98` |
| `confirmed_at` | `2026-07-11T06:56:35Z` |

## Operational notes

1. **Propagation delay:** First probe immediately after push may return `partial` while GitHub Pages builds; retry with `live_site_confirmation: true` is safe (idempotent).
2. **URL shape:** Canonical public URL uses Jekyll permalink `/{yyyy}/{mm}/{dd}/{slug}/`, not `/{yyyy-mm-dd}/{slug}/`.
3. **User-Agent:** Live probe uses `User-Agent: silverman-blog-linkedin-live-site-probe/1.0`; some CDN paths return `403` without it.
4. **Remote reconciliation / duplicate-artifact guards:** Implemented and covered by unit tests; not exercised in this smoke (no divergent remote or cross-campaign collision scenario).

## Post-validation cleanup (completed)

Validation used an isolated smoke post (not editorial content). After evidence was recorded:

- Public site: removal commit `558c1c3` on `silverberdi.github.io` (2026-07-11); US-001 smoke removed in `b128c57` the same day
- Editorial mount: smoke ready sources removed
- Campaign metadata: `flow-a-2026-07-11-us002-live-site-smoke-validation` removed

Smoke validation posts MUST NOT remain on `silverman.pro`.

## BL-001 / US-002

US-002 acceptance criteria demonstrated with real HTTP evidence on `silverman.pro` during the validation window. BL-001 business outcome (automated path from checkout to confirmed live site) is satisfied when combined with US-001.
