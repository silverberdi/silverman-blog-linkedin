## Why

US-038–US-040 delivered a working same-origin Flow A LinkedIn variant supervision console as a single static HTML/JS asset. That surface is hard to extend safely for month calendar UX, shared list/calendar models, and future Google/OIDC auth (US-040B–US-040D) without a maintainable componentized frontend. US-040A modernizes the **console layer only**—same worker APIs, same mutation SoT, no Flow B—so later variants can land on a typed, buildable stack without rewriting publication or n8n.

## Goals

- Decide the frontend stack in this proposal before `/opsx-apply`: **React + TypeScript + Vite** (default; justified below).
- Migrate the existing list-oriented pending-variant supervision experience into that stack as a first-class view, preserving operator-understandable access at (or compatibly replacing) `GET /flow-a/console/linkedin-variant-supervision`.
- Scaffold componentized operational screens and a typed API client boundary so US-040B–US-040D can extend without rewriting list/business components or inventing a second mutation SoT.
- Serve static Vite build artifacts from the existing worker/deployment path (no separate frontend server in production).
- Keep list and calendar views on one shared normalized frontend model (calendar UX itself remains US-040B/US-040C).
- Keep dependency additions small and justified; validate build, key components, API error mapping, and desktop/mobile viewports.

## Non-Goals

- US-040B full month calendar visibility / dark responsive calendar UX (beyond scaffolding and shared-model boundaries).
- US-040C schedule mutation from calendar / new calendar mutation SoT.
- US-040D public URL exposure and Google auth activation (readiness boundaries only).
- US-040E operational polish beyond what stack migration requires.
- Backend-for-frontend, database, user-management system, or public hosting changes.
- New mutation endpoints or parallel persistence; reuse existing US-017 `POST /correct-linkedin-variant`, `POST /defer-linkedin-variant`, `POST /cancel-linkedin-publication`.
- Rewriting worker business logic, n8n workflows, Python utilities (beyond serving static build output), file contracts, publication guards, or HTTP mutation semantics.
- LinkedIn API publication, enablement-flag bypass, n8n Execute Command, or browser filesystem/path reads.
- Flow B.
- Claiming **US-040A Story accepted** or **BL-015 closed** from proposal or apply alone.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (US-040A only) | Leave backlog open; Stories 1–3 already demonstrated; variants A–E remain |
| **US-040A** | Yes | All acceptance criteria in `docs/product/user-stories.md` |
| **US-038 / US-039 / US-040** | Consume / preserve | Same route semantics, list UX, edit/defer/cancel via US-017 |
| **US-017** | Consume only | No contract rewrite |
| **US-040B–US-040E** | Boundaries only | Scaffold / API-client readiness; do not implement those stories |
| **Flow B / BL-016+** | Out | Explicitly excluded |

**US-040A acceptance criteria addressed:**

1. Frontend stack decision documented here before implementation (React + TypeScript + Vite).
2. Console-layer modernization only; no worker/n8n/publication-pipeline rewrite.
3. Preserve same-origin console route or compatible replacement during migration.
4. Preserve list-oriented pending-variant supervision as a first-class view.
5. Componentized screens including scaffolding for list, month calendar, item detail, schedule editor, status summary, filters, confirmation flows, and shared API/error handling (full calendar/schedule behavior deferred).
6. Centralized typed browser API client so future Google/OIDC (US-040D) can inject auth without changing business components.
7. Static build artifacts serveable by existing worker/deployment path; no separate production frontend server.
8. No BFF, database, user-management, or public hosting change.
9. List and calendar backed by the same worker read models or one shared normalized frontend model.
10. Small, documented, justified dependency additions.
11. Frontend validation: build success, key component behavior, API error mapping, desktop and mobile viewports.
12. Outcome visible/understandable; failures/blocked states clearly communicated; existing work not duplicated or unintentionally changed.

**Intentionally excluded:** US-040B–US-040E full delivery; Story accepted / BL-015 closed checkboxes; new mutation SoT; LinkedIn API publish; Flow B.

## Frontend stack decision (required before apply)

**Decision: React + TypeScript + Vite.**

| Option | Verdict |
|--------|---------|
| **React + TypeScript + Vite** (chosen) | Strong component model for operational screens; Vite produces static assets the worker can serve; TypeScript enables a typed API client for later OIDC; ecosystem fits calendar libs in US-040B without forcing them now. |
| Vue + TypeScript + Vite | Equivalent modern SPA stack; rejected to avoid introducing a second UI paradigm in a repo with no existing frontend preference and where React is the documented default recommendation. |
| SvelteKit / Next.js | Overweight for a same-origin static console; risks a separate Node server or SSR topology out of scope. |
| Stay on single-file HTML/JS | Insufficient for componentized list+calendar scaffolding and typed auth-injectable client without an ad-hoc framework. |

Dependencies MUST stay small: React, React DOM, TypeScript, Vite, and minimal test tooling (e.g. Vitest + Testing Library and/or Playwright viewport checks). Calendar UI libraries are deferred to US-040B unless a zero-cost scaffold stub needs none.

## What Changes

- Add a Vite + React + TypeScript frontend package (or `frontend/` app) whose production build emits static assets consumed by the worker.
- Replace (or atomically coexist-then-replace) the monolithic `linkedin_variant_supervision_console.html` with built artifacts served at the existing console route (or a documented compatible replacement that keeps operator access understandable).
- Port the list-oriented pending-supervision UX (load pending rows, enablement display-only, dry-run default, edit/defer/cancel with confirm for real cancel, qualified language) into React components.
- Scaffold component/API boundaries for month calendar view, item detail, schedule editor, status summary, filters, and confirmation flows—wired enough that US-040B/US-040C can fill behavior without reshaping the tree.
- Introduce a typed API client wrapping `GET /flow-a/linkedin-variants/pending-supervision` and US-017 POSTs; auth header injection lives only at that boundary.
- Normalize pending-supervision (and any future calendar read) into one shared frontend model used by list and calendar scaffolds.
- Extend worker static serving only as needed to deliver `index.html` + hashed assets (no new business routes, no BFF).
- Add frontend build/test scripts and validation covering build, components, error mapping, desktop/mobile viewports.
- Update CURRENT-STATE / progress-checklist for US-040A **in progress / demonstrated** only when acceptance is shown—not Story accepted / BL-015 closed from apply alone.

## Capabilities

### New Capabilities

_None — US-040A extends the existing supervision console capability rather than inventing a parallel console name._

### Modified Capabilities

- `linkedin-variant-supervision-console`: Require modern React+TS+Vite console delivery as static build artifacts; preserve list-first supervision and US-017 mutation wiring; require typed API-client boundary (auth-injectable); require shared normalized model for list/calendar; require component scaffolding for calendar/detail/schedule/filters/status/confirmations without implementing US-040B–US-040C behavior; supersede “single committed static HTML file” as the sole delivery form while preserving route and operator semantics.

## Impact

- **Product:** Advances BL-015 / US-040A; BL-015 remains open; US-040B–US-040E remain unimplemented.
- **Frontend:** New Vite app + build pipeline; replaces monolithic static HTML as the served console.
- **Worker:** Thin serving change for built static assets at the console route; **no** mutation SoT, pending-supervision contract, or publication-guard changes required for US-040A.
- **APIs:** Consume existing GET pending-supervision + US-017 POSTs unchanged.
- **Deploy:** Dockerfile / packaging MUST include prebuilt frontend assets (or a documented build step) so production still runs one worker process—no separate frontend server.
- **Docs:** CURRENT-STATE console delivery note; progress-checklist US-040A marks only when demonstrated.
- **Tests:** Frontend unit/component + viewport checks; existing Python console/secrets tests updated for new asset layout; no real LinkedIn/DeepSeek/ComfyUI.
- **Preserved:** ADR-0001 (browser → worker HTTP only); dry-run default; real-cancel confirmation; enablement display-only; `pending` / `cancelled` / `flow_a_complete` ≠ LinkedIn API published; secrets not in source, HTML, logs, or browser storage; Flow B deferred.
