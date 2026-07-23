## Context

US-097 and US-098 are implemented on the separated LAN Authority Manager (`:8011` → worker `:8010`): Google OIDC + allowlist, operator JWT in HttpOnly cookie, n8n API-key path retained. CURRENT-STATE and specs explicitly defer **US-099**: Cloudflare Tunnel (or equivalent) front-only public UI with private worker API and a private UI→API hop so browsers never need a publicly routable API base URL.

Authority: US-099 ACs only (`docs/product/user-stories.md`); BL-035 Story 3 (`docs/product/backlog.md`); progress gates (`docs/product/progress-checklist.md`). Preserve US-097/US-098 and BL-034 contracts. Do not invent ACs; do not mark Story accepted in propose/apply docs.

## Goals / Non-Goals

**Goals:**

- Publish **only** the operator UI via Cloudflare Tunnel (or equivalent); keep worker API LAN/private (not internet-published).
- Public console MUST NOT require a public worker API hostname in the browser; UI→API via private hop (same-origin reverse proxy preferred).
- CORS / origin allowlisting match the public UI origin; no `*` CORS.
- Docs: CURRENT-STATE, ubuntu deploy, RUNTIME-STATE (when live) describe front-only + private API + Google allowlist without secrets.
- Unauth / non-allowlisted public access fails closed with clear messaging; probing private API from internet is unsupported (API not published).
- Visible Cloudflare UI URL + Google sign-in; clear failure/blocked states.
- Preserve ADR-0001, BL-026 intent, BL-034 split, US-097/US-098 auth; no publication-flag mutation.
- Demonstrated-only product status; Story accepted unchecked.

**Non-Goals:**

- US-097 OIDC/allowlist rework; US-098 JWT claim rework (except minimal documented cookie/CORS for public topology).
- Publishing worker API (or general API routes) on the public internet.
- BL-034 Story accepted; BL-029 full stand-up; n8n Execute Command; Story accepted marking.

## Decisions

### D1 — Front-only public ingress: Cloudflare Tunnel → operator UI only

**Choice:** Cloudflare Tunnel (or equivalent) hostname targets the separated operator UI service only. Worker `:8010` remains bound to LAN / Docker private network and is **not** published as a Cloudflare public hostname.

**Why:** Direct match to US-099 AC1 and BL-026 least-privilege.

**Alternatives considered:** Tunnel both UI and API (rejected — publishes API); publish API with IP allowlist (rejected — still public API surface).

### D2 — Private UI→API hop via same-origin reverse proxy (preferred)

**Choice:** On the public UI origin, nginx in the UI container serves static UI and proxies worker paths needed by the console (typed-client API routes and `/auth/*`) to the private worker over Docker DNS (`SILVERMAN_OPERATOR_UI_WORKER_UPSTREAM`). Browser `SILVERMAN_OPERATOR_UI_API_BASE_URL=/` (normalized to empty same-origin base) so operators never configure a public API hostname.

**Why:** Satisfies US-099 AC2; keeps cookies and CORS simpler (same-site); Google OAuth `redirect_uri` can be `https://<public-ui>/auth/google/callback` proxied to the worker without publishing the API hostname.

**Alternatives considered:** Browser calls `https://api.…` public API (rejected — AC forbids); browser calls LAN IP from internet (rejected — unreachable / exposes topology); compose sidecar (deferred — UI-container nginx is smallest diff).

### D3 — CORS / origins: public UI origin explicitly allowlisted; never `*`

**Choice:** When any browser→worker call remains cross-origin (e.g. interim absolute LAN dual path), `SILVERMAN_OPERATOR_UI_ORIGINS` MUST include the exact public UI origin (`https://…`). Prefer same-origin proxy so console API calls need no CORS; still document allowlist for any residual cross-origin and for clarity. Wildcard `*` MUST NOT be used.

**Why:** US-099 AC3.

### D4 — Preserve Google + operator JWT; no cookie flag rework for preferred hop

**Choice:** Keep US-097 allowlist and US-098 JWT mint/validate. Same-origin proxy keeps `SameSite=Lax` + `Secure` on HTTPS — **no** SameSite/Path/Secure change and **no** JWT claim/allowlist changes.

**Why:** Non-goal to rework US-098; AC8 preserve completed work.

### D5 — Fail-closed public access messaging

**Choice:** Reuse existing anonymous / forbidden / expired-session vocabulary on the public UI URL. Non-allowlisted Google still `?auth=forbidden`. Docs state that bookmarking/probing the private API from the public internet is unsupported because the API is not published.

**Why:** US-099 AC5–AC7.

### D6 — Documentation honesty; RUNTIME-STATE when live

**Choice:** CURRENT-STATE + ubuntu deploy describe front-only topology; RUNTIME-STATE notes tunnel **not live** until operator activates. No secrets; Story accepted unchecked.

**Why:** US-099 AC4; precise status language.

### D7 — n8n and LinkedIn publication unchanged

**Choice:** n8n continues HTTP to private worker API (ADR-0001). No `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` mutation. LinkedIn OAuth public Cloudflare callback remains the existing BL-026 exception (distinct from Authority Manager UI tunnel).

**Why:** US-099 AC8; BL-026 inventory clarity.

## Open Questions

None — apply chose UI-container nginx private hop (D2).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Misconfigured tunnel publishes worker | Explicit “UI only” deploy checklist; CURRENT-STATE / exposure inventory forbid API public hostname |
| Proxy misses `/auth/*` → Google callback breaks | Tasks require proxy of Google start/callback + typed-client paths; smoke Google status/me |
| Cookie not sent after public cutover | Prefer same-origin proxy; document Secure/SameSite; re-auth after cutover |
| Accidental `*` CORS | Spec + tests forbid wildcard; env examples show exact origin |
| Story accepted marked early | Propose/tasks forbid; checklist gates remain unchecked |

## Migration Plan

1. Approve propose → `/opsx-apply` on feature branch (not `main`).
2. Implement proxy + tunnel docs/config + CORS origin + tests/docs.
3. Controlled live enablement updates RUNTIME-STATE (operator-owned).
4. `/opsx-verify` → implementation commit → sync → archive (separate approvals).

Rollback: disable tunnel / revert public hostname; LAN `:8011` path remains. No editorial data migration.
