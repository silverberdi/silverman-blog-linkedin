# Runtime State

Volatile point-in-time operational snapshot. **Not** architectural authority — see [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Durable status: [CURRENT-STATE.md](CURRENT-STATE.md). Maintenance: [project-runtime-context-maintenance.md](operations/project-runtime-context-maintenance.md).

Update after deploys, activation changes, smoke tests, external-integration validation, or confirmed revision changes.

## Snapshot

**`verified_at_utc`:** `2026-07-23T00:14:00Z`
**Evidence source:** Post-deploy probe after US-099 LAN deploy (`deploy-worker.sh` OVERALL PASS; `BUILD_REVISION=266607c…` on `feat/us-099-expose-operator-ui-cloudflare-tunnel`).

| Fact | Value | Evidence |
|------|-------|----------|
| Worker URL | `http://192.168.0.194:8010` | Live `/health` HTTP 200 |
| Operator UI URL | `http://192.168.0.194:8011` | Live UI HTTP 200; container `silverman-operator-ui` |
| Health | `status=healthy`, `folders_ready=true`, `deployment_environment=prod` | `/health` (worker + UI private hop) |
| Editorial mount (container) | `/data/silverman-blog-linkedin` | `/health` `base_path` (prior durable path) |
| Editorial mount (host) | `/home/silverman/silverman-blog-linkedin-worker/data/silverman-blog-linkedin` | Compose (durable path; **not** compartido) |
| Calendar SoT | `calendar_store=postgres:silverman_linkedin_db` (assumed unchanged; not re-probed this pass) | Prior RUNTIME-STATE |
| Public blog mount | `/public-blog` → `/home/silverman/silverberdi.github.io` | Deploy verify PASS |
| Container images | `silverman-blog-linkedin-worker:local`, `silverman-operator-ui:local` | `docker ps` after recreate |
| `BUILD_REVISION` | `266607c231e2cb71ebe5f07085a52f64d62efe94` | Worker container env |
| Separated UI runtime config | `deliveryMode=separated`, `apiBaseUrl=/`, `envLabel=prod`, `googleAuthEnabled=false` | `GET :8011/config.js` |
| UI↔API pairing (live) | **Applied** — UI `prod` + API `deployment_environment=prod` | `/health` via UI hop + `config.js` |
| Private UI→API hop (US-099) | **Live on LAN** — same-origin `/` + nginx proxy to `silverman-blog-linkedin-worker:8000`; `GET :8011/health` → worker healthy | curl via UI origin |
| Former embedded console | **Decommissioned** — `GET /flow-a/console/linkedin-variant-supervision` (+ `/assets/…`) → **HTTP 410** (assumed retained; not re-probed this pass) | Prior US-096 evidence |
| CORS allowlist (deploy export) | `SILVERMAN_OPERATOR_UI_ORIGINS=http://192.168.0.194:8011` | Deploy command env |
| US-099 Cloudflare UI tunnel | **Not live** — public UI hostname / cloudflared not activated; LAN private hop only | No public hostname probe |
| Google operator auth (US-097/098) | **Disabled on live stack** (`googleAuthEnabled=false`); secrets/redirect cutover still operator-owned | `config.js` |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | `true` (assumed unchanged; **not mutated** by this deploy) | Prior RUNTIME-STATE / deploy non-goal |
| `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED` | `true` (assumed unchanged) | Prior RUNTIME-STATE |
| `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED` | `true` (assumed unchanged) | Prior RUNTIME-STATE |
| `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED` | `true` (assumed unchanged) | Prior RUNTIME-STATE |
| `SILVERMAN_COMFYUI_ENABLED` | Prior: `UNSET` in `.env` (not re-checked this pass) | Prior RUNTIME-STATE |

## Unverified / unknown

| Fact | Status |
|------|--------|
| DeepSeek API quota | `unknown` |
| ComfyUI / Comfy Cloud availability right now | `unknown` |
| n8n workflow `active` flags right now | `unknown` this probe |
| Operator Story acceptance for US-093 / US-094 / US-095 / US-097 / US-098 / US-099 | **Not Story accepted** — deploy/build evidence only |
| Host `.env` persistence of pairing / private-hop keys | Pairing + hop applied via deploy-time exports; keys may be `UNSET` in host `.env` while containers advertise prod + `/` |

## Operator notes

- Prefer CURRENT-STATE for Story accepted / BL closed narrative. This file is the **live** lean snapshot.
- Repo n8n exports stay `active: false`; server workflows may be active.
- Historical 2026-07-22 US-096 decommission snapshot superseded by this US-099 private-hop LAN redeploy evidence.
- Public Cloudflare Tunnel front-only hostname remains an operator activation step (Google redirect URI + cloudflared).
