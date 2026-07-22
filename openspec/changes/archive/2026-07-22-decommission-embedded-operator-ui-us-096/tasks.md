## 1. Branch and baseline

- [x] 1.1 Create/switch to `feat/us-096-decommission-embedded-operator-ui` (or continue from latest synced BL-034 HEAD after US-095 / envLabel-narrowing archive); do not implement on `main`
- [x] 1.2 Confirm separated UI path is live-ready baseline: `:8011` ↔ `:8010`, pairing, CORS, typed client—verify hold only (no US-094/US-095 redesign)

## 2. Worker: decommission embedded console serving

- [x] 2.1 Replace `GET /flow-a/console/linkedin-variant-supervision` SPA serving with a fail-closed operator-visible decommission response (prefer 410 + clear HTML/body naming separated UI on LAN `:8011`; no secrets; no partial SPA)
- [x] 2.2 Remove `StaticFiles` mount (and equivalent) for `/flow-a/console/linkedin-variant-supervision/assets`; ensure asset GETs also fail closed with clear messaging (not silent empty mount)
- [x] 2.3 Remove or neutralize worker helpers that load/serve console HTML/assets (`load_console_html`, `console_build_dir`, etc.) so the API process has no operator UI surface
- [x] 2.4 Delete shipped console SPA tree under `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/` (or ensure it is absent from the worker package/image COPY set)

## 3. Worker build / deploy path: no frontend embed

- [x] 3.1 Update root `Dockerfile` (and any deploy scripts/comments) so worker API build does **not** require `npm run build:embedded` or copying SPA assets into `src/.../static/`
- [x] 3.2 Update `deploy/server/silverman-worker.compose.yaml` (and related env/README comments) so the worker is API-only and `silverman-operator-ui` is the exclusive supported console path

## 4. Frontend: retire embedded delivery mode

- [x] 4.1 Remove or retire supported `build:embedded` / `VITE_OPERATOR_UI_DELIVERY=embedded` production path; keep separated image (`frontend/.../Dockerfile`) as the only production delivery
- [x] 4.2 Update `operatorUiConfig` / client / Vitest defaults so tests do not require worker-embedded same-origin serving; preserve US-093 config fail-closed and US-094 pairing for separated mode
- [x] 4.3 Ensure UI still consumes worker only via `SILVERMAN_OPERATOR_UI_API_BASE_URL` + pairing; no worker Python, editorial mounts, API business logic, or API secrets in the UI

## 5. Tests

- [x] 5.1 Add/update pytest proving former console index and asset paths fail closed (no Vite SPA / hashed console assets returned)
- [x] 5.2 Add/update assertion that worker package/image does not ship operator-console static assets (or equivalent build-independence check)
- [x] 5.3 Update or remove tests that previously expected embedded console serving (e.g. pending-supervision console asset sections, CORS tests that hit embedded HTML)
- [x] 5.4 Re-run US-093 / US-094 / US-095 Vitest holds applicable to separated mode; keep green without restoring embed
- [x] 5.5 Confirm no mutation of `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; no n8n Execute Command; Flow A/B and LinkedIn HTTP contracts unchanged aside from intentional console decommission

## 6. Docs and product progress

- [x] 6.1 Update `docs/CURRENT-STATE.md` topology: exclusive separated UI → API; embedded console decommissioned (not supported/compatibility); do not claim Story accepted
- [x] 6.2 Update `docs/deployment/ubuntu-server-worker-deployment.md` (and related deploy notes) likewise; note bookmarks to `:8010/.../console/...` fail closed toward using `:8011`
- [x] 6.3 Update `docs/RUNTIME-STATE.md` only if live topology notes still present the embedded path after deploy evidence
- [x] 6.4 Update `docs/product/user-stories.md` / `docs/product/progress-checklist.md` / `docs/product/backlog.md` status lines only for US-096 ACs actually demonstrated; leave Story accepted unchecked; do not mark US-093–095 Story accepted solely due to this change

## 7. Verification and business validation

- [x] 7.1 Run targeted pytest + Vitest for touched modules; fix warnings attributable to this change; `git diff --check` clean; secrets audit on new/modified files
- [x] 7.2 Business validation checklist against US-096 ACs (worker has no UI surface; API build without frontend embed; UI HTTP-only; exclusive topology docs; clear fail-closed messaging; preserved contracts)—record demonstrated vs still-pending operator/LAN gates without Story accepted
