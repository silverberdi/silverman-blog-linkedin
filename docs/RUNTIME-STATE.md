# Runtime State

Volatile point-in-time operational snapshot. **Not** architectural authority — see [CONTEXT-AUTHORITY.md](CONTEXT-AUTHORITY.md). Durable status: [CURRENT-STATE.md](CURRENT-STATE.md). Maintenance: [project-runtime-context-maintenance.md](operations/project-runtime-context-maintenance.md).

Update after deploys, activation changes, smoke tests, external-integration validation, or confirmed revision changes.

## Snapshot

**`verified_at_utc`:** `2026-07-23T16:27:00Z`
**Evidence source:** Operator Story accepted for US-097/US-098/US-099 (BL-035 closed). Last deploy on branch `feat/us-099-expose-operator-ui-cloudflare-tunnel` included Google userinfo `/v1` fix (`BUILD_REVISION=09547be…`). Live public UI + Google path validated by operator 2026-07-22/23 (SSH re-probe not available at this write).

| Fact | Value | Evidence |
|------|-------|----------|
| Worker URL | `http://192.168.0.194:8010` | Prior live `/health`; LAN private API |
| Operator UI URL (LAN) | `http://192.168.0.194:8011` | Separated UI container |
| Operator UI URL (public) | `https://authority.silverman.pro` | Cloudflare Tunnel front-only (US-099); operator-validated Google sign-in |
| Health / pairing | `deployment_environment=prod`; UI `envLabel=prod` | Prior probes |
| Private UI→API hop | **Live** — `apiBaseUrl=/`; nginx → `silverman-blog-linkedin-worker:8000` | Prior curl via UI origin + public hop |
| `BUILD_REVISION` (last known) | `09547bee4a36073eba18c7aa60442177b0ed4519` | Post userinfo-fix deploy |
| Google operator auth | **Enabled / configured** on live stack | Prior `config.js` + `/auth/google/status`; operator login |
| US-099 Cloudflare UI tunnel | **Live** — hostname `authority.silverman.pro` → UI only; worker API not published | Operator use + prior public probes |
| BL-035 / US-097–US-099 | **Story accepted** 2026-07-23; **BL-035 closed** | Product backlog / checklist / user-stories |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | `true` (assumed unchanged; **not mutated** by BL-035) | Prior RUNTIME-STATE |

## Unverified / unknown

| Fact | Status |
|------|--------|
| DeepSeek API quota | `unknown` |
| ComfyUI / Comfy Cloud availability right now | `unknown` |
| n8n workflow `active` flags right now | `unknown` |
| Operator Story acceptance for US-093 / US-094 / US-095 | **Not Story accepted** (BL-034 remains open for those gates) |
| Fresh SSH health probe at this write | **Not re-run** (host unreachable from this session) |

## Operator notes

- Prefer CURRENT-STATE for Story accepted / BL closed narrative.
- Follow-up after BL-035: operator console **UI polish** (especially mobile) — not claimed complete.
- Repo n8n exports stay `active: false`; server workflows may be active.
