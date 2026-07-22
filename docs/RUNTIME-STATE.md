# Runtime State

Volatile point-in-time operational snapshot. **Not** architectural authority — see [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Durable status: [CURRENT-STATE.md](CURRENT-STATE.md). Maintenance: [project-runtime-context-maintenance.md](operations/project-runtime-context-maintenance.md).

Update after deploys, activation changes, smoke tests, external-integration validation, or confirmed revision changes.

## Snapshot

**`verified_at_utc`:** `2026-07-21T19:32:13Z`
**Evidence source:** BL-030 / US-071 live LAN probe (`GET /health` + container inspect + boolean `.env` names only). Mac repo HEAD at probe time may be ahead of the running image.

| Fact | Value | Evidence |
|------|-------|----------|
| Worker URL | `http://192.168.0.194:8010` | Live `/health` HTTP 200 |
| Health | `status=healthy`, `folders_ready=true` | `/health` |
| Editorial mount (container) | `/data/silverman-blog-linkedin` | `/health` `base_path` |
| Editorial mount (host) | `/home/silverman/silverman-blog-linkedin-worker/data/silverman-blog-linkedin` | Compose (durable path; **not** compartido) |
| Calendar SoT | `calendar_store=postgres:silverman_linkedin_db`, `calendar_store_ready=true` | `/health` |
| Public blog mount | `/public-blog` → `/home/silverman/silverberdi.github.io` | Compose |
| Container image | `silverman-blog-linkedin-worker:local` (created `2026-07-21T17:59:41Z`) | `docker inspect` |
| `BUILD_REVISION` / `.build_git_sha` | **Not exposed** on `/health`; host `.build_git_sha` **missing** | Live probe 2026-07-21 — treat as unknown until next deploy stamps SHA |
| Supervision console assets (in image) | `index-Dd92hzfG.js` / `index-BRVrIP7S.css` | Files inside running container static tree |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | `true` | Server `.env` (boolean only) |
| `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED` | `true` | Server `.env` |
| `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED` | `true` | Server `.env` |
| `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED` | `true` | Server `.env` |
| `SILVERMAN_COMFYUI_ENABLED` | `UNSET` in `.env` (Comfy may still be used via other config) | Server `.env` name check |

## Unverified / unknown

| Fact | Status |
|------|--------|
| Exact git SHA of running worker image | `unknown` (no `/health` build field; `.build_git_sha` missing) |
| DeepSeek API quota | `unknown` |
| ComfyUI / Comfy Cloud availability right now | `unknown` |
| n8n workflow `active` flags right now | `unknown` this probe (not re-exported) — see last known notes in CURRENT-STATE |
| US-094 UI↔API environment pairing on live LAN | `not applied` — repo implements pairing; live `.env` / `/health.deployment_environment` not re-probed for this change |

## Operator notes

- Prefer CURRENT-STATE for Story accepted / BL closed narrative. This file is the **live** lean snapshot.
- Repo n8n exports stay `active: false`; server workflows may be active.
- Historical 2026-07-19 US-040L-centric snapshot superseded by this 2026-07-21 refresh (BL-030).
