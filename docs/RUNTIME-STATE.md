# Runtime State

Volatile point-in-time operational snapshot. **Not** architectural authority — see [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Durable status: [CURRENT-STATE.md](CURRENT-STATE.md). Maintenance: [project-runtime-context-maintenance.md](operations/project-runtime-context-maintenance.md).

Update after deploys, activation changes, smoke tests, external-integration validation, or confirmed revision changes.

## Snapshot

**`verified_at_utc`:** `2026-07-22T02:40:32Z`
**Evidence source:** Post-deploy probe after `fix-operator-ui-env-label-narrowing` LAN redeploy (`deploy-worker.sh` OVERALL PASS; `BUILD_REVISION=a16fda86e4f7…`).

| Fact | Value | Evidence |
|------|-------|----------|
| Worker URL | `http://192.168.0.194:8010` | Live `/health` HTTP 200 |
| Operator UI URL | `http://192.168.0.194:8011` | Live UI HTTP 200; container `silverman-operator-ui` |
| Health | `status=healthy`, `folders_ready=true`, `deployment_environment=prod` | `/health` |
| Editorial mount (container) | `/data/silverman-blog-linkedin` | `/health` `base_path` (prior durable path) |
| Editorial mount (host) | `/home/silverman/silverman-blog-linkedin-worker/data/silverman-blog-linkedin` | Compose (durable path; **not** compartido) |
| Calendar SoT | `calendar_store=postgres:silverman_linkedin_db` (assumed unchanged; not re-probed this pass) | Prior RUNTIME-STATE |
| Public blog mount | `/public-blog` → `/home/silverman/silverberdi.github.io` | Deploy verify PASS |
| Container images | `silverman-blog-linkedin-worker:local`, `silverman-operator-ui:local` | `docker ps` after recreate |
| `BUILD_REVISION` | `a16fda86e4f798b7b09d4984b4120cea81d41483` | Worker container env |
| Separated UI runtime config | `deliveryMode=separated`, `apiBaseUrl=http://192.168.0.194:8010`, `envLabel=prod` | `GET :8011/config.js` |
| UI↔API pairing (live) | **Applied** — UI `prod` + API `deployment_environment=prod` | `/health` + `config.js` |
| CORS allowlist (deploy export) | `SILVERMAN_OPERATOR_UI_ORIGINS=http://192.168.0.194:8011` | Deploy command env (compose export; not necessarily persisted in host `.env`) |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | `true` | Server `.env` (boolean only; **not mutated** by this deploy) |
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
| Operator Story acceptance for US-093 / US-094 / US-095 | **Not Story accepted** — deploy/build unblock only |
| Host `.env` persistence of pairing keys | Pairing applied via deploy-time exports; keys may be `UNSET` in host `.env` while containers advertise prod |

## Operator notes

- Prefer CURRENT-STATE for Story accepted / BL closed narrative. This file is the **live** lean snapshot.
- Repo n8n exports stay `active: false`; server workflows may be active.
- Historical 2026-07-21 BL-030 snapshot superseded by this 2026-07-22 redeploy evidence.
- US-096 embedded-console decommission is implemented in repo but **not** reflected in this live snapshot until the next worker redeploy confirms former `:8010/.../console/...` URLs return 410 and the API image has no console SPA surface.
