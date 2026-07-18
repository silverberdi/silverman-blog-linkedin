## Why

US-040A–C delivered a React console with injectable auth, dual list/calendar views, and schedule mutation over worker HTTP—but auth UX still centers on an in-memory API-key prompt without explicit session-state modeling for a future public URL. US-040D makes the console **ready** for later public exposure protected by Google/OIDC without rewriting calendar/list/schedule-editor components, and without activating public hosting or live IdP integration in this slice.

## Goals

- Keep authentication and authorization behind the existing typed frontend API client + worker middleware boundary (injectable `AuthProvider`).
- Represent **anonymous**, **authenticated**, **expired-session**, **forbidden**, and **service-unavailable** states in the UI (even while local ops still use worker API-key auth).
- Forbid hardcoded API keys, tokens, operational secrets, mount paths, or local-only assumptions in frontend source, rendered HTML, logs, or browser storage.
- Prefer same-origin calls; if any cross-origin path exists, document an explicitly restrictable CORS strategy for future public exposure.
- Design the request layer so a later Google/OIDC bearer token or secure session cookie can replace the current auth header without changing calendar/list/schedule-editor components.
- Prevent unauthenticated or read-only sessions from executing schedule mutations (edit/defer/cancel/calendar schedule-update).
- Handle mobile session expiry gracefully: preserve visible context, guide re-auth, do not silently lose unsaved schedule drafts.
- Document that public deployment and Google authentication **activation** are out of scope for this BL slice and require a separate security change before internet exposure.
- Surface failures/blocked auth states clearly; keep outcomes understandable; use qualified GLOSSARY language (`pending` / `queued` / `cancelled` / `flow_a_complete` / blog handoff ≠ LinkedIn API published).

## Non-Goals

- Actually activating public URL hosting / internet exposure.
- Actually integrating live Google OAuth / OIDC IdP (readiness only).
- US-040E polish beyond what auth-readiness UX requires.
- BFF, database, or user-management product.
- LinkedIn API publish; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` bypass; Flow B.
- Closing BL-015 or BL-021; marking Story accepted from proposal or apply alone.
- Rewriting US-040A–C visibility or schedule-mutation sources of truth.
- Replacing worker `require_api_key` with Google auth in production in this change.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (US-040D only) | Leave backlog open; A–C preserved; E remains |
| **US-040D** | Yes | All acceptance criteria in `docs/product/user-stories.md` |
| **US-040A / US-040B / US-040C / US-038–US-040** | Preserve | Stack, dual views, schedule visibility, list + calendar mutations |
| **US-040E** | Out | Polish beyond auth-readiness UX |
| **Flow B / BL-016+** | Out | Explicitly excluded |

**US-040D acceptance criteria addressed:** client + middleware auth boundary; anonymous / authenticated / expired / forbidden / service-unavailable UI states; no hardcoded secrets or local-only assumptions in source/HTML/logs/storage; same-origin or documented restrictable CORS; request layer swappable to OIDC bearer/session cookie without calendar component churn; unauthenticated/read-only cannot mutate schedules; mobile session-expiry preserves context and unsaved drafts; document public deploy + Google activation as out of scope pending separate security change; understandable outcomes and failures; no unintentional duplication of completed work.

**Intentionally excluded:** live public URL; live Google/OIDC IdP; US-040E; Story accepted / BL-015 closed checkboxes; BFF/DB/user-mgmt; LinkedIn API publish; Flow B; rewriting A–C SoT.

## Frontend stack decision (preserve)

**Keep React + TypeScript + Vite** under `frontend/linkedin-variant-supervision-console/`. Keep CSS-grid calendar and shared `ScheduleEditor`. No divergent auth SoT that bypasses worker HTTP (ADR-0001: browser → worker HTTP only; no n8n Execute Command; no browser filesystem writes).

## What Changes

- Extend the injectable `AuthProvider` / typed client contract to expose explicit session/capability state (anonymous, authenticated, expired, forbidden, service-unavailable) without embedding secrets.
- Map HTTP auth/availability outcomes (missing credential, 401, 403, 5xx/network) to operator-facing session banners and mutation gating.
- Gate edit/defer/cancel and calendar schedule-update UI so unauthenticated and read-only sessions cannot execute mutations; preserve visible list/calendar context and unsaved schedule drafts across expiry + re-auth guidance.
- Document same-origin default and (if applicable) a CORS allowlist strategy that can be restricted for future public exposure; document that public hosting + Google activation require a separate security OpenSpec change.
- Keep local ops on worker API-key auth via the same provider boundary; design replacement path for OIDC bearer or secure session cookie without touching calendar/list/schedule-editor business components.
- Rebuild static console assets into the existing worker-served path; update CURRENT-STATE / progress only when US-040D outcomes are demonstrated (preserve A–C; do not claim E done; do not close BL-015).

## Capabilities

### New Capabilities

_None — US-040D extends the existing supervision console auth-readiness contract rather than inventing a parallel auth product._

### Modified Capabilities

- `linkedin-variant-supervision-console`: Require explicit session-state UI, mutation gating for unauthenticated/read-only sessions, secrets-safe request layer ready for OIDC bearer/session cookie swap, same-origin or documented CORS, mobile expiry draft preservation, and explicit out-of-scope documentation for public URL + Google activation; preserve US-040A–C baselines; defer US-040E.

## Impact

- **Product:** Advances BL-015 / US-040D; BL-015 remains open; US-040E remains unimplemented; US-040A–C baseline preserved.
- **Frontend:** Auth session model + UI banners; mutation gating; draft preservation on expiry; typed client/error mapping extensions; docs in frontend README / ops notes as needed.
- **Worker:** Prefer no new mutation SoT; optional documentation-only or minimal CORS/header middleware clarification if required for readiness—MUST NOT activate public hosting or Google IdP. Existing `require_api_key` remains the local auth mechanism.
- **APIs:** Browser → worker HTTP only (ADR-0001); no n8n Execute Command; no browser filesystem writes; no LinkedIn publish.
- **Deploy:** Same Vite build → worker static assets; no separate frontend server; **no** internet exposure activation in this change.
- **Docs:** CURRENT-STATE / progress-checklist / user-stories only when demonstrated at apply time; do not mark Story accepted or BL-015 closed; explicitly record public URL + Google activation as deferred to a separate security change.
- **Tests:** Frontend Vitest for session states, mutation gating, expiry draft preservation, secrets audit; pytest secrets/console route as needed; no real LinkedIn/DeepSeek/ComfyUI/Google IdP.
