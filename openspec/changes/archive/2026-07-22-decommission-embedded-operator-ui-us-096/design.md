## Context

US-093 / US-094 / US-095 are implemented and LAN-deployed on `feat/us-095-regress-separated-operator-ui` (`BUILD_REVISION=a16fda8…`, 2026-07-22): separated Silverman Authority Manager on `:8011` with typed `SILVERMAN_OPERATOR_UI_API_BASE_URL`, CORS allowlist, and prod pairing against worker `:8010`. CURRENT-STATE still documents worker-embedded `GET /flow-a/console/linkedin-variant-supervision` as an optional compatibility path; US-096 is not started.

Today the worker still:

- Serves SPA HTML at `GET /flow-a/console/linkedin-variant-supervision` and mounts `/…/assets` via `StaticFiles`
- Ships committed Vite output under `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`
- Documents `npm run build:embedded` as a pre-step for the worker Dockerfile

The frontend still has `deliveryMode=embedded` / `build:embedded` for that path (pairing skipped in embedded mode).

Stakeholders: system owner (hard UI/API independence), content operator (bookmarks to `:8010/.../console/...` must fail closed with a clear path to `:8011`). Constraints: smallest coherent decommission; ADR-0001 unchanged; no BL-035; no publication-flag mutation; no Story accepted marking in this change.

## Goals / Non-Goals

**Goals:**

- Purge operator-console static assets from the worker image/process and stop serving former console routes; fail closed with operator-visible messaging (optionally naming LAN `:8011` as the supported console).
- Make worker build/deploy succeed without any frontend production build / embed step.
- Keep separated UI (`:8011`) as the only supported operator console; HTTP + pairing only; no API internals in the UI.
- Update CURRENT-STATE / ubuntu deploy (RUNTIME-STATE if live wording still claims compatibility) accordingly.
- Prove via tests: no console assets/routes on API; API build independent of frontend prod build; US-093/094/095 holds remain green where applicable.

**Non-Goals:**

- Google/OIDC/JWT (BL-035); redesign US-094 pairing or US-095 matrix; mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; n8n Execute Command; public exposure beyond BL-026; Story accepted for US-093–096; unrelated backlog reopen.

## Decisions

### D1 — Fail-closed decommission responses on former console URLs (not silent 404-only)

**Choice:** Keep explicit route handlers (or a narrow prefix handler) for:

- `GET /flow-a/console/linkedin-variant-supervision`
- `GET /flow-a/console/linkedin-variant-supervision/` (if currently accepted)
- `GET /flow-a/console/linkedin-variant-supervision/assets/{path:path}` (and equivalent)

Return a clear operator-visible outcome: prefer a small **HTML** page (and/or structured JSON for non-browser clients) stating the embedded console is decommissioned and that the supported console is the separated operator UI on LAN port **8011** (e.g. `http://192.168.0.194:8011`). Use a non-success status such as **410 Gone** (preferred) or **404** with the same clear body—never return partial SPA shells, empty mounts, or leftover hashed assets.

Do **not** invent public hosting, redirects to internet URLs, or auto-proxy to the UI container from the worker.

**Why:** US-096 requires fail closed with a clear operator-visible outcome, not a silent partial UI. Bookmarks to `:8010/.../console/...` are the migration risk.

**Alternatives considered:** Bare FastAPI 404 with no body (unclear); HTTP 302 to `:8011` (can surprise operators / break scripts; optional later if explicitly wanted—default is messaging without hard redirect); keep empty StaticFiles mount (violates “does not ship assets”).

### D2 — Delete embed pipeline from worker; do not leave orphan static trees in the image

**Choice:**

1. Remove `StaticFiles` mount and SPA-serving code paths (`load_console_html`, `console_assets_dir` serving, etc.) from worker startup.
2. Delete committed/generated assets under `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/` from the worker package (or ensure the directory is absent from the image COPY set).
3. Update `Dockerfile` / deploy scripts / README comments so API build **must not** require `npm run build:embedded` or copying SPA into `src/.../static/`.
4. Frontend: remove or retire `build:embedded` / `VITE_OPERATOR_UI_DELIVERY=embedded` as a supported production path; default Vitest/config to separated semantics where tests still need a delivery mode. Keep separated Dockerfile + compose `silverman-operator-ui` unchanged in role.

**Why:** Hard independence means the API artifact has no operator UI surface and no embed build coupling.

**Alternatives considered:** Leave assets on disk but unmounted (still “ships” UI surface; fails AC); keep `build:embedded` for local demos (reopens compatibility path; out of scope).

### D3 — Docs: exclusive separated topology; drop “optional compatibility”

**Choice:** Update CURRENT-STATE topology note, ubuntu deploy guide, and compose comments to state exclusively: operators use `:8011`; worker `:8010` is API-only; embedded console is decommissioned (not supported, not compatibility). Update RUNTIME-STATE only if live notes still imply the embedded path. Do not claim Story accepted.

**Why:** Matches US-096 AC on documentation and CURRENT-STATE honesty.

### D4 — Preserve pairing, CORS, n8n, and publication guards

**Choice:** No redesign of US-094 pairing agreement, US-093 CORS allowlist, or n8n workflow exports. Remove only embedded-mode exemptions (e.g. “embedded skips pairing”). Do not touch `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

**Why:** AC: preserve existing completed work except intentional removal of the embedded path.

### D5 — Test strategy (behavioral, no live publication)

**Choice:**

| Proof | Approach |
|-------|----------|
| API does not serve console SPA | pytest: former console GET returns decommission response; no Vite `index.html` / hashed JS from worker package paths; asset GET fail closed |
| API build independent of frontend | Documented/assertable: worker Dockerfile/scripts have no `build:embedded` requirement; optional CI-style check that package lacks console static tree |
| Separated UI unchanged in role | Existing US-093/094/095 Vitest holds stay green (update any tests that still expect embedded serving on the worker) |
| No publication mutation | Existing enablement tests untouched; no new code paths flip the flag |

Update or retire tests that currently skip/assert embedded assets (e.g. `tests/test_operator_ui_cors_us093.py`, `tests/test_linkedin_variant_pending_supervision.py` console asset sections).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operators bookmark `:8010/.../console/...` and think the console vanished | Clear 410/HTML messaging naming `:8011` |
| Historical specs/tests still require worker-served SPA | Delta specs supersede; update pytest/Vitest in the same change |
| Accidental leftover assets in Docker layer cache | Delete tree + assert absence; rebuild worker image on deploy |
| Over-deletion of non-console static helpers | Scope deletes to `linkedin-variant-supervision-console` embed path only |
| Marking Story accepted prematurely | Proposal/tasks forbid Story accepted; progress checklist only “work started / demonstrated” when evidenced |

## Migration Plan

1. Implement decommission on current BL-034 branch or `feat/us-096-…` from latest synced HEAD after US-095 archive.
2. Land code + tests + docs; `/opsx-verify` before commit.
3. On explicit approval: deploy worker (API-only) + confirm `:8011` still pairs to `:8010`; hit old console URL and confirm fail-closed message.
4. Rollback: re-enable previous image tag that still embeds the console (temporary); preferred forward fix is keep `:8011` healthy rather than restoring embed.

## Open Questions

- Prefer **410 Gone** vs **404** for decommissioned console URLs? Default in this design: **410** with HTML body (implementation may use 404 only if framework constraints force it—document the chosen status in CURRENT-STATE).
- Soft **redirect** (302) to `:8011` in addition to messaging? Default: **no** automatic redirect; messaging only unless operator asks during apply.
