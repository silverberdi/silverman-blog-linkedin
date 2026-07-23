# Runtime State

Volatile point-in-time operational snapshot. **Not** architectural authority — see [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Durable status: [CURRENT-STATE.md](CURRENT-STATE.md). Maintenance: [project-runtime-context-maintenance.md](operations/project-runtime-context-maintenance.md).

Update after deploys, activation changes, smoke tests, external-integration validation, or confirmed revision changes.

## Snapshot

**`verified_at_utc`:** `2026-07-22T17:17:20Z`
**Evidence source:** Post-deploy probe after US-096 decommission LAN deploy (`deploy-worker.sh` OVERALL PASS; `BUILD_REVISION=c34cb9f93a08…`).

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
| `BUILD_REVISION` | `c34cb9f93a08a0dfddd258bc60d48393d771f1ec` | Worker container env |
| Separated UI runtime config | `deliveryMode=separated`, `apiBaseUrl=http://192.168.0.194:8010`, `envLabel=prod` | `GET :8011/config.js` |
| UI↔API pairing (live) | **Applied** — UI `prod` + API `deployment_environment=prod` | `/health` + `config.js` |
| Former embedded console | **Decommissioned** — `GET /flow-a/console/linkedin-variant-supervision` (+ `/assets/…`) → **HTTP 410** HTML naming `:8011`; no SPA; static tree absent in worker image | Live curl + `docker exec` probe |
| CORS allowlist (deploy export) | `SILVERMAN_OPERATOR_UI_ORIGINS=http://192.168.0.194:8011` | Deploy command env (compose export; not necessarily persisted in host `.env`) |
| US-099 front-only Cloudflare UI tunnel | **Not live** — implemented in repo (private hop + UI-only tunnel examples); public UI hostname not activated on this stack | Repo docs/examples; no live public UI probe |
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
| Operator Story acceptance for US-093 / US-094 / US-095 / US-096 | **Not Story accepted** — deploy/build evidence only |
| Host `.env` persistence of pairing keys | Pairing applied via deploy-time exports; keys may be `UNSET` in host `.env` while containers advertise prod |

## Operator notes

- Prefer CURRENT-STATE for Story accepted / BL closed narrative. This file is the **live** lean snapshot.
- Repo n8n exports stay `active: false`; server workflows may be active.
- Historical 2026-07-22 envLabel-narrowing snapshot superseded by this US-096 decommission redeploy evidence.
