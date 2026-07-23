## Why

US-097 and US-098 delivered Google OIDC allowlist identity and operator JWT console→API auth on the separated LAN Authority Manager (`:8011` → `:8010`). Public internet use still requires a **front-only** topology so attackers cannot reach the worker API hostname even if they obtain a browser session cookie/JWT scoped to the UI. **BL-035 / US-099** activates Cloudflare Tunnel (or equivalent) for the operator UI only, with a private UI→API hop—without publishing the API, rewriting auth, or breaking ADR-0001.

## What Changes

- Supported public topology publishes **only** the operator UI via Cloudflare Tunnel (or equivalent); the worker API remains LAN / private-network only (not internet-published).
- Internet-facing console does **not** require a publicly routable worker API base URL in the browser; UI→API uses a private hop (same-origin reverse proxy, internal Docker DNS, or equivalent).
- CORS / origin allowlisting and tunnel hostname configuration match the public UI origin; permissive `*` CORS is forbidden for this exposure.
- Docs (CURRENT-STATE, ubuntu deploy, RUNTIME-STATE when live) describe front-only public exposure + private API + Google allowlist at topology level without embedding secrets.
- Unauthenticated or non-allowlisted access via the public UI URL fails closed with clear messaging; probing the private API from the public internet is out of supported exposure (API not published).
- Operators use the Cloudflare UI URL + Google sign-in; failures/blocked states remain clear.
- Preserve US-097/US-098 auth, BL-034 UI/API split, ADR-0001 n8n→worker on private API, BL-026 least-privilege intent; no LinkedIn publication-flag mutation.
- Docs/tests cover demonstrated US-099 outcomes only; **Story accepted remains unchecked**.

### Goals

- Satisfy **US-099** acceptance criteria in `docs/product/user-stories.md` (BL-035 Story 3 only).
- Activate front-only public UI exposure with private API and private UI→API hop.
- Fail closed; no secrets in artifacts, docs, logs, or responses.

### Non-goals (intentionally excluded)

| Item | Reason |
|------|--------|
| **US-097** Google OIDC identity/allowlist rework | Already implemented; preserve |
| **US-098** JWT mint/validate rework | Already implemented; only minimal topology-driven CORS/cookie/SameSite if required and documented |
| Publishing the worker API on the public internet | Contradicts US-099 |
| BL-034 Story accepted for US-093/US-094/US-095 | Separate operator gate |
| Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | Out of scope |
| n8n Execute Command; making UI an n8n target | ADR-0001 |
| Full BL-029 CI/UAT stand-up | Unrelated |
| Marking US-099 / BL-035 Story accepted | Operator gate after demonstrated ACs |
| Unrelated backlog | Scope discipline |

### Acceptance criteria addressed (US-099)

All US-099 ACs in `docs/product/user-stories.md` are in scope for this change’s demonstrated outcomes (UI-only tunnel; private API; private hop; CORS/origin match; topology docs; fail-closed public access; visible outcomes; preserve completed work).

### Acceptance criteria intentionally excluded

- US-097 / US-098 ACs (already demonstrated; not reworked here except topology-required CORS/cookie adjustments).
- Product “Story accepted” / checklist acceptance-validated gates (remain operator-owned).

## Capabilities

### New Capabilities

- None. US-099 advances operator UI deployment / exposure topology rather than introducing a separate capability name.

### Modified Capabilities

- `operator-ui-deployment`: Define Cloudflare Tunnel (or equivalent) front-only public UI topology; private worker API; private UI→API hop (no public API base URL in browser); public-origin CORS allowlist (no `*`); topology docs pointers including RUNTIME-STATE when live.
- `operator-console-google-auth`: Update deferred-public-topology language; require public UI origin + Google/JWT fail-closed behavior remain intact on the public URL; document any required CORS/cookie/SameSite adjustment for cross-site tunnel→API private hop.
- `linkedin-variant-supervision-console`: Update “public URL activation deferred” wording; separated UI must work with private-hop API base (relative/same-origin) without pasting public API hostname; preserve AuthProvider/session vocabulary.
- `separated-operator-ui-capability-regression`: Extend regression holds for front-only public path without claiming Story accepted or publishing the API.
- `service-permissions-and-exposure`: Accept front-only public Authority Manager UI under US-099 while keeping worker API / n8n LAN-private; retain LinkedIn OAuth callback exception vocabulary.
- `ubuntu-server-worker-deployment`: Document tunnel/front-only + private API topology on ubuntu deploy path without secrets.

## Impact

- **Deploy / topology:** Cloudflare Tunnel (or equivalent) config for UI only; reverse-proxy or compose-internal private hop from UI container to worker; env examples for public UI origin and CORS allowlist (placeholders only).
- **Worker:** CORS allowlist includes public UI origin; optional SameSite/Secure cookie adjustments for Google/JWT cookies if private hop is same-site via proxy — minimal, documented; API bind remains private.
- **Separated UI:** Runtime config uses private/same-origin API base when front-only; Google sign-in redirect URIs include public callback paths as required; no worker API key in browser.
- **Tests:** Topology/config/CORS holds + Vitest/pytest for public-origin allowlist and fail-closed anonymous/forbidden; keep US-093/094/095/097/098 holds green.
- **Docs:** CURRENT-STATE, ubuntu deploy, RUNTIME-STATE (when live), service-permissions exposure inventory.
- **Product pointers:** Status lines for US-099 work-started / outcome-demonstrated only when shown; Story accepted unchecked.
- **Systems unchanged:** LinkedIn publication enablement; n8n→worker HTTP on private API; Google allowlist set; operator JWT claim rules (unless documented cookie topology tweak).
