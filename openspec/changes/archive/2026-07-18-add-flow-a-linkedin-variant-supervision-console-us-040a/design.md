## Context

US-038–US-040 implemented Flow A LinkedIn variant supervision as:

- Authenticated read: `GET /flow-a/linkedin-variants/pending-supervision`
- Same-origin operator UI: `GET /flow-a/console/linkedin-variant-supervision` serving a single committed HTML/JS file (`src/silverman_blog_linkedin/static/linkedin_variant_supervision_console.html`)
- Mutations: browser → existing US-017 POSTs only (`correct` / `defer` / `cancel`); dry-run default; confirm for real cancel; enablement display-only

US-040A (BL-015 variant) modernizes that **console layer** to React + TypeScript + Vite so US-040B–US-040D can add calendar UX and auth readiness without rewriting worker business logic, n8n, or publication guards. This is not Flow B.

**Constraints:** ADR-0001 (browser → worker HTTP only); no BFF/DB/user-management; no separate production frontend server; secrets never in source, rendered HTML, logs, or browser storage; qualified language (`pending` / `cancelled` / `flow_a_complete` ≠ LinkedIn API published).

## Goals / Non-Goals

**Goals:**

- Ship a React + TypeScript + Vite app whose production build is served by the existing worker at the preserved (or compatible) console route.
- Preserve list-oriented pending-variant supervision as a first-class, fully working view (edit/defer/cancel parity with US-039/US-040).
- Scaffold component and API boundaries for calendar, detail, schedule editor, status summary, filters, and confirmations.
- Centralize HTTP behind a typed client with injectable auth headers for later OIDC (US-040D).
- Keep one shared normalized frontend model so list and calendar cannot disagree on identity/state/schedule/actions.
- Validate build, key components, API error mapping, desktop and mobile viewports.

**Non-Goals:**

- Full month calendar UX (US-040B) or schedule mutations from calendar / new calendar SoT (US-040C).
- Public URL + Google auth activation (US-040D); polish beyond migration (US-040E).
- Changing pending-supervision GET contract or US-017 POST semantics unless a defect blocks the port (prefer no backend change).
- Node process in production; CDN/public hosting; Flow B.

## Decisions

### D1 — Stack: React + TypeScript + Vite

**Choice:** React 18+ with TypeScript and Vite for build/dev.

**Why:** Matches the US-040A default recommendation; component model fits operational screens; Vite emits static assets the Python worker can serve; TypeScript enables a typed API client for future OIDC without changing business components.

**Alternatives considered:**

| Alternative | Why not |
|-------------|---------|
| Vue + Vite | Equivalent; avoided dual paradigm vs documented React default |
| SvelteKit / Next.js | SSR or separate Node server conflicts with “worker serves static only” |
| Keep monolithic HTML | Cannot sustainably scaffold list+calendar+auth boundaries |

### D2 — Repo layout and build output

**Choice:** Place the app under `frontend/linkedin-variant-supervision-console/` (or equivalent single `frontend/` root dedicated to this console). Production `vite build` writes into a package-served directory, e.g.:

`src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`

containing `index.html` + hashed `assets/*`.

**Why:** Keeps frontend source out of Python module noise; build artifacts remain importable/copyable into the Docker image via existing `COPY src ./src` once built into `src/.../static/...`.

**Alternatives considered:**

| Alternative | Why not (for US-040A) |
|-------------|------------------------|
| Commit only source; build inside Docker with Node | Heavier Dockerfile; longer CI; acceptable later if operator prefers, but default is **prebuild on Mac/CI and copy artifacts** so the runtime image stays Python-slim |
| Serve from a second container | Explicitly out of scope |

**Deploy implication:** Document a required `npm ci && npm run build` (or makefile target) before `docker build` / deploy so the image contains current assets. Optionally add a CI check that `static/.../index.html` exists and is not stale relative to `frontend/` (lightweight; not a Node runtime in prod).

### D3 — Route and serving strategy

**Choice:** Preserve **`GET /flow-a/console/linkedin-variant-supervision`** as the operator entry URL. The handler serves the Vite `index.html` (SPA shell). Same-origin relative asset URLs under a fixed prefix, e.g. `/flow-a/console/linkedin-variant-supervision/assets/*`, served as static files from the build directory.

**Why:** Operators already bookmark/document the Stories 1–3 path; no compatible-replacement confusion if the URL stays identical.

**Implementation notes:**

- Console HTML GET remains **unauthenticated** (same as today); API calls remain authenticated.
- Configure Vite `base` to the asset prefix so hashed chunks resolve under the worker path (not `/assets` at site root).
- Prefer `StaticFiles` mount for `/assets` (or full console prefix) plus `HTMLResponse` for the index route; avoid path traversal outside the build dir.
- **Remove** (or stop loading) the legacy monolithic `linkedin_variant_supervision_console.html` after cutover so there is one SoT for the UI. Short coexistence (legacy file unused) is allowed only during apply if tests are migrated in the same change.

**Compatible replacement (fallback only):** If Vite `base`/`StaticFiles` proves awkward for a subdirectory route, a documented redirect from the old path to a new path (e.g. `/flow-a/console/linkedin-variant-supervision/`) is acceptable **only** if operator docs and CURRENT-STATE name both and the list UX remains first-class. Prefer preserving the exact path.

### D4 — Typed API client and auth injection

**Choice:** All browser HTTP goes through `api/client` (typed TypeScript module):

- `getPendingSupervision()`
- `correctVariant(...)`, `deferVariant(...)`, `cancelVariant(...)`

Auth is supplied via an injectable `AuthProvider` / `getRequestHeaders()` used only inside the client:

| Phase | Mechanism |
|-------|-----------|
| US-040A (now) | Session/runtime API key → `X-API-Key` (prompt or local-only in-memory; **not** committed, **not** `localStorage` for secrets) |
| US-040D (later) | OIDC bearer or secure session cookie — swap provider implementation; **list/calendar components unchanged** |

**Error mapping:** Client normalizes HTTP 401/422 and known US-017 stable codes into a shared `ApiError` shape consumed by banners/confirmations.

**ADR-0001:** Browser talks only to worker HTTP endpoints; no Execute Command; no raw mount reads.

### D5 — Shared normalized frontend model

**Choice:** Map `GET /flow-a/linkedin-variants/pending-supervision` (and later calendar reads in US-040B) into one `SupervisionItem` (or equivalent) model with stable identity (`campaign_id` + `variant_id`), schedule, publish/eligibility state, available actions, and issues.

**Why:** List and calendar scaffolds MUST render from the same store/selectors so they cannot disagree. US-040A implements the normalizer + list consumption; calendar scaffold may show empty/placeholder month chrome wired to the same store without full US-040B behavior.

### D6 — Component inventory (US-040A depth)

| Component / area | US-040A depth |
|------------------|---------------|
| `AppShell` | Implemented (title, dry-run banner, enablement display-only, view switcher stub) |
| `ListView` | **Implemented** — parity with Stories 1–3 list UX |
| `MonthCalendarView` | **Scaffold** — mounts, uses shared model, stub empty/placeholder; no full dark month UX |
| `ItemDetail` | **Scaffold** — can host draft preview used by list edit |
| `ScheduleEditor` | **Scaffold** — list defer may use a thin form that will converge here in US-040C |
| `StatusSummary` | **Scaffold or thin** — counts/issues from shared model |
| `Filters` | **Scaffold** — props/state shape ready; optional no-op until US-040B |
| `ConfirmationFlow` | **Implemented** for real cancel (and real mutations) |
| `api/*`, `models/*`, `errors/*` | **Implemented** |

### D7 — Dependencies (keep small)

**Allowed for US-040A:** `react`, `react-dom`, `typescript`, `vite`, `@types/react` / `@types/react-dom`, Vitest + Testing Library (and optionally Playwright or Vite preview + viewport CSS checks for mobile/desktop).

**Deferred:** Full calendar libraries (FullCalendar, etc.) → US-040B unless a zero-dep CSS grid stub suffices for scaffolding.

**Justification gate:** Each added production dependency MUST be documented in the frontend README (or design follow-up note in CURRENT-STATE) for usability, maintainability, accessibility, or calendar interaction needs.

### D8 — Behavioral parity preserved from Stories 1–3

The modernized list MUST retain:

- Pending rows: campaign id, variant id, audience, `scheduled_at_utc`, `publish_state`, draft visibility, issues, integration failures, deferred/`auto_queue_eligible` context
- Dry-run default on; explicit real write; confirmation for real cancel
- Enablement off = display-only (does not hide rows; does not bypass guards)
- Qualified copy: `pending` / `cancelled` / `flow_a_complete` ≠ LinkedIn API published
- Mutations only via existing US-017 POSTs

### D9 — Worker / Python surface

**Preferred:** Minimal change — `load_console_html()` (or successor) reads Vite `index.html` from the new static dir; mount static assets. **No** changes to pending-supervision aggregation or US-017 handlers for US-040A success path.

Update secrets-audit tests to scan built `index.html` + JS assets (or source + build output policy documented in tasks).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Docker image ships without rebuilt frontend | Document mandatory build-before-deploy; fail tests if `index.html` missing; optional CI check |
| Vite `base` misconfigured → blank console | Integration test that console route returns HTML referencing assets under the chosen prefix; smoke fetch assets 200 |
| Dual UI during migration confuses operators | Single cutover in one change; delete or stop serving legacy HTML |
| Auth key accidentally stored in `localStorage` | Spec + review: in-memory / session only; secrets audit includes storage API misuse in source |
| Scaffold calendar looks “done” but is US-040B | Label scaffold; CURRENT-STATE states US-040B not implemented |
| Scope creep into BFF or new mutation routes | Explicit non-goals; reuse US-017 only |
| Frontend test toolchain slows Python CI | Keep frontend tests invocable via npm script; wire into CI only as needed without requiring Node in the worker image |

## Migration Plan

1. **Scaffold** Vite+React+TS app; typed client; shared model; AppShell + ListView port from existing HTML behavior.
2. **Add** calendar/detail/schedule/filters/status scaffolds (non-functional or placeholder).
3. **Configure** Vite `base` + worker static serving for index + assets at the preserved console route.
4. **Cut over** console handler to Vite `index.html`; migrate Python secrets/console tests to new assets.
5. **Remove** legacy monolithic HTML from the serve path (delete file in same change once parity verified).
6. **Document** `npm run build` before deploy; update CURRENT-STATE console delivery note.
7. **Rollback:** Redeploy previous worker image / restore prior static HTML path if cutover fails (git revert of change). No data migration—console is presentational.

**Coexistence:** Optional brief dual-file existence during apply is OK; production MUST serve only the Vite build at the operator URL when the change completes.

## Open Questions

1. Exact Vite `base` string vs trailing-slash route (`.../linkedin-variant-supervision` vs `.../linkedin-variant-supervision/`) — resolve during apply with one working StaticFiles layout; prefer no URL change for operators.
2. Whether to commit built assets to git or generate only in CI/deploy — **default: commit built assets into `src/.../static/...`** so current Dockerfile (`COPY src`) needs no Node; revisit if asset churn is painful.
3. Playwright vs CSS/@media component tests for mobile viewport — prefer Vitest + Testing Library + explicit viewport width tests first; add Playwright only if needed for AC evidence.

None of these block proposal approval; resolve during `/opsx-apply` within the constraints above.
