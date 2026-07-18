## Context

US-040A–C delivered the Flow A LinkedIn variant supervision console as React + TypeScript + Vite under `frontend/linkedin-variant-supervision-console/`, served same-origin at `GET /flow-a/console/linkedin-variant-supervision`. Baseline includes:

- Dual first-class List + Month calendar views; shared `ScheduleEditor`; CSS-grid month + mobile agenda
- Typed `SupervisionApiClient` + injectable `AuthProvider` (`MemoryBearerAuthProvider`: in-memory API key via prompt; never `localStorage`/`sessionStorage`)
- Worker auth via existing `require_api_key` middleware on pending-supervision, schedule-visibility, US-017 POSTs, and `POST /editorial-calendar/update-item-schedule`
- Error mapping for 401/422 and known business codes; unsaved schedule-draft warning on view switch
- Qualified language: `pending` / `queued` / `cancelled` / `flow_a_complete` / blog handoff ≠ LinkedIn API published

US-040D (BL-015) must make this architecture **ready** for a future public URL protected by Google authentication—without activating public hosting or integrating a live IdP in this slice, and without rewriting calendar/list/schedule-editor components.

**Constraints:** ADR-0001 browser → worker HTTP only; no n8n Execute Command; no browser filesystem writes; no hardcoded secrets; preserve US-040A–C SoT; leave BL-015 open; do not claim US-040E done.

## Goals / Non-Goals

**Goals:**

- Explicit UI session states: anonymous, authenticated, expired-session, forbidden, service-unavailable.
- Keep authn/authz behind typed client + worker middleware; swappable provider for OIDC bearer / secure session cookie.
- Mutation gating: unauthenticated and read-only sessions cannot execute edit/defer/cancel/calendar schedule-update.
- Mobile expiry: preserve visible context + unsaved schedule drafts; guide re-auth; no silent draft loss.
- Same-origin default + documented restrictable CORS strategy for future public exposure.
- Document public deploy + Google activation as out of scope pending a separate security change.

**Non-Goals:**

- Live public URL / internet exposure; live Google OAuth/OIDC IdP.
- US-040E polish beyond auth-readiness UX.
- BFF/DB/user-management; LinkedIn API publish; enablement bypass; Flow B.
- Closing BL-015 / BL-021; Story accepted from apply alone.
- Rewriting US-040A–C visibility or mutation SoT.

## Decisions

### D1 — SessionState model at the auth/client boundary (not in calendar components)

**Choice:** Introduce a small frontend `SessionState` (or equivalent) derived by the auth provider + typed client from credential presence and HTTP outcomes:

| State | Trigger (local API-key era) | Operator meaning |
|-------|-----------------------------|------------------|
| `anonymous` | No in-memory credential | Not signed in; reads/mutations blocked until auth |
| `authenticated` | Credential held; last relevant call succeeded or not yet 401/403 | Signed in for this browser session |
| `expired` | 401 after a prior credential (client clears provider) | Session no longer valid; re-auth required |
| `forbidden` | HTTP 403 | Credential present but not authorized for the action |
| `service_unavailable` | Network failure or HTTP 5xx (especially 503) | Worker/API unavailable |

Surface these via AppShell banners / status summary. List, Month calendar, and `ScheduleEditor` consume **capabilities** (`canRead`, `canMutate`) and session banners from the store/client—not ad-hoc status parsing.

**Why:** AC requires representing all five states even while local ops still use API-key auth; keeps calendar components free of auth protocol details.

**Alternatives considered:** Only map 401 as today — rejected (missing anonymous/forbidden/unavailable UX). Per-component fetch status — rejected (divergent SoT; breaks OIDC swap goal).

### D2 — Capabilities: `canRead` / `canMutate` (read-only ready)

**Choice:** `AuthProvider` exposes (or the store derives):

- `canRead` — credential present and session not forbidden/expired for reads
- `canMutate` — credential present **and** provider reports mutation allowed

For `MemoryBearerAuthProvider` (local ops): credential held ⇒ `canRead` and `canMutate` both true. No credential ⇒ both false.

Future Google/OIDC provider MAY set `canMutate=false` for read-only roles without changing ScheduleEditor/List mutation **call sites**—those sites MUST check `canMutate` before enabling commit controls and before calling mutation client methods.

**Why:** AC: “Prevent unauthenticated or read-only sessions from executing schedule mutations.”

**Alternatives considered:** Server-only enforcement without UI gating — rejected (AC requires UI prevention; worker still remains authoritative reject). Hardcode API-key ⇒ always mutate — rejected (blocks future read-only roles).

### D3 — Keep worker `require_api_key`; no IdP in this change

**Choice:** Do **not** replace worker middleware with Google/OIDC in US-040D. Local/ops auth remains Bearer API key via injectable provider. Document the swap contract: a future provider returns either `Authorization: Bearer <oidc_access_token>` or relies on `credentials: 'include'` cookies with empty/minimal auth headers—client request construction MUST support both without calendar component edits.

Worker continues to reject unauthenticated mutation/read with existing 401 semantics. If/when 403 appears, client maps to `forbidden`. No new public-facing auth endpoints in this change.

**Why:** AC readiness only; activation requires separate security change before internet exposure.

**Alternatives considered:** Implement Google OAuth now — rejected (explicitly out of scope). Add BFF session service — rejected (AC / prior variants forbid BFF unless separate change).

### D4 — Same-origin default; CORS documented for future only

**Choice:** Production console remains **same-origin** (Vite assets served by worker; relative API paths). Do **not** open wildcard CORS in this change.

Document in frontend README + ops/CURRENT-STATE follow-up notes:

1. Preferred: continue same-origin after any future public URL (reverse proxy terminates TLS and serves console + API together).
2. If a future architecture serves the SPA from a distinct origin, CORS MUST be an explicit allowlist of console origins, restricted methods/headers, and MUST NOT use `*` with credentials; that policy lands only in the separate security/public-exposure change.

**Why:** AC requires same-origin **or** explicitly documented restrictable CORS; documenting without enabling keeps readiness without expanding attack surface.

**Alternatives considered:** Enable permissive CORS “for readiness” — rejected (unsafe; contradicts fail-closed security posture).

### D5 — Mobile session expiry preserves context and drafts

**Choice:** On 401 → transition to `expired`, clear credential, show re-auth guidance banner. MUST:

- Keep last-loaded list/calendar snapshot visible (stale-but-visible) unless operator explicitly clears
- Keep `ScheduleEditor` open with unsaved draft fields intact when expiry hits mid-edit
- Disable mutation commit controls until re-authenticated with `canMutate`
- After successful re-auth, allow resume of the same draft without forcing a blank editor
- MUST NOT silently discard `unsavedScheduleDraft` on auth clear alone

Re-auth UX for local ops: reuse provider prompt (or a dedicated non-secret “Sign in” control that calls `getRequestHeaders()`). Do not store credentials in browser storage.

**Why:** AC mobile expiry + unsaved schedule drafts.

**Alternatives considered:** Full page reset on 401 — rejected (loses drafts/context). Persist drafts in `sessionStorage` — rejected (AC forbids secrets in storage; drafts may be sensitive editorial text—prefer in-memory React state only for this slice).

### D6 — Secrets and local-only assumptions

**Choice:** Strengthen audits and UI copy:

- No hardcoded API keys, tokens, mount paths (`/data/...`), LAN IPs, or “only works on localhost” assumptions in frontend source, built HTML/JS, logs, or browser storage
- Relative same-origin paths only for API calls (already the pattern)
- Error messages name HTTP status / operator actions; never echo credentials
- Docs examples use non-secret wording (“your API key”) without fake credential-like strings

**Why:** Explicit US-040D AC.

### D7 — Scope documentation and status language

**Choice:** At apply time, update CURRENT-STATE to record US-040D **auth readiness implemented** while stating:

- Public URL hosting / internet exposure **not activated**
- Google/OIDC IdP **not integrated** (separate security change required before exposure)
- US-040A–C preserved; US-040E not done; Story not accepted; BL-015 open

Frontend README MUST include a short “Public URL & Google auth” section stating the same.

**Why:** AC documentation requirement + prevent over-claiming.

### D8 — Testing

**Choice:**

- Vitest: session-state mapping (anonymous/authenticated/expired/forbidden/unavailable); mutation controls disabled when `!canMutate`; expiry mid-edit preserves draft; secrets scan of source; client maps 403/5xx; provider swap smoke (mock OIDC-style headers without calendar edits)
- Pytest: existing console route + secrets audit remain green; no requirement for live Google
- No real LinkedIn/DeepSeek/ComfyUI/Google IdP calls

## Risks / Trade-offs

- [Risk] Operators confuse “auth readiness” with “safe to expose publicly” → Mitigation: CURRENT-STATE + README explicit deferral; no public deploy in this change.
- [Risk] Stale visible data after expiry misread as live authoritative → Mitigation: banner states session expired / data may be stale; refresh after re-auth.
- [Risk] Worker never returns 403 today → Mitigation: client still maps 403; tests simulate it; UI ready without inventing fake worker roles.
- [Risk] Scope creep into US-040E polish → Mitigation: only auth-state banners/gating/draft preservation; no at-a-glance count redesign.
- [Risk] Accidental CORS opening → Mitigation: D4 documents only; no middleware CORS widen in apply tasks unless already present and must be restricted—default unchanged same-origin.

## Migration Plan

1. Implement session/capability model + UI gating + client mappings behind existing Vite app.
2. Rebuild static assets into worker static path; verify same-origin console route.
3. Update docs (CURRENT-STATE, progress-checklist/user-stories checkboxes only when demonstrated).
4. Rollback: revert frontend build + source; worker mutation SoT unchanged so rollback is console-layer only.

## Open Questions

_None blocking propose._ If apply discovers worker already emits non-401 auth failures that need stable codes, map them under `forbidden` without inventing a parallel auth product.
