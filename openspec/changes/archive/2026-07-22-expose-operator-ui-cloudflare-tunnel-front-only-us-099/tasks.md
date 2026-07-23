## 1. Baseline and scope guardrails

- [x] 1.1 Confirm US-099 ACs only (user-stories / backlog BL-035 Story 3 / progress-checklist); do not invent ACs; do not mark Story accepted
- [x] 1.2 Confirm US-097 Google OIDC + allowlist and US-098 operator JWT baselines remain intact (verify hold — no OIDC/JWT claim rework unless documented cookie topology tweak)
- [x] 1.3 Confirm non-goals: publishing worker API; BL-034 Story accepted; publication-flag mutation; n8n Execute Command; UI as n8n target; full BL-029; Story accepted marking

## 2. Front-only public topology and private hop

- [x] 2.1 Document/configure Cloudflare Tunnel (or equivalent) targeting separated operator UI only; worker API remains LAN/private (not internet-published)
- [x] 2.2 Implement private UI→API hop (prefer same-origin reverse proxy of typed-client + `/auth/*` routes to private worker) so browser needs no public API base URL
- [x] 2.3 Ensure public UI Google OAuth redirect/callback works via the private hop (public UI origin proxies `/auth/google/*` as needed)
- [x] 2.4 Set `SILVERMAN_OPERATOR_UI_ORIGINS` (or equivalent) to the exact public UI origin when any cross-origin remains; forbid `*` CORS
- [x] 2.5 Apply minimal cookie SameSite/Secure/Path adjustments only if required by topology; document; do not change JWT iss/aud/exp/allowlist rules
- [x] 2.6 Preserve n8n → worker Bearer API-key path on private API (ADR-0001); UI is not an n8n target

## 3. Fail-closed public access and visible outcomes

- [x] 3.1 Public UI URL anonymous session: non-mutating, clear unauthenticated messaging
- [x] 3.2 Non-allowlisted Google identity on public URL: clear forbidden; no mutable session
- [x] 3.3 Allowlisted Google sign-in on public URL: authenticated `canMutate` via operator JWT/session through private hop (no worker API key)
- [x] 3.4 Clear failure/blocked states (pairing, config, auth) remain understandable on public URL

## 4. Tests

- [x] 4.1 Pytest/Vitest: CORS allowlist accepts exact public UI origin; rejects wildcard / unlisted origins as applicable
- [x] 4.2 Vitest/config holds: separated client uses same-origin or private API base (no public worker hostname required)
- [x] 4.3 Re-run applicable US-093 / US-094 / US-095 / US-097 / US-098 holds; keep green without claiming Story accepted
- [x] 4.4 Secrets audit: no tunnel tokens, API keys, client secrets, or JWT signing secrets in frontend source/built assets/docs examples

## 5. Docs and product status (demonstrated only)

- [x] 5.1 Update `docs/CURRENT-STATE.md`: US-099 front-only public UI + private API + private hop; Google allowlist/JWT retained; not Story accepted
- [x] 5.2 Update ubuntu deploy docs (`docs/deployment/ubuntu-server-worker-deployment.md` and related deploy examples) for tunnel/front-only topology (placeholders only)
- [x] 5.3 Update `docs/operations/service-permissions-and-exposure.md` accepted exposure: front-only UI when US-099 active; worker API stays private
- [x] 5.4 Update `docs/RUNTIME-STATE.md` only when live tunnel topology is actually activated (non-secret flags only)
- [x] 5.5 Update `docs/product/user-stories.md` / `progress-checklist.md` / `backlog.md` status lines only for US-099 gates actually demonstrated; leave Story accepted and acceptance-criteria-validated unchecked
- [x] 5.6 `git diff --check` clean on touched paths; no secrets staged

## 6. Business validation

- [x] 6.1 Trace each US-099 AC to a test or documented evidence artifact; record any gap without inventing ACs
- [x] 6.2 Confirm worker API is not published; UI-only public ingress + private hop demonstrated; n8n private API path retained
- [x] 6.3 Confirm Story accepted remains unchecked for US-099 / BL-035

### AC → evidence (US-099)

| AC | Evidence |
|----|----------|
| UI-only public ingress; API private | `deploy/server/cloudflared.operator-ui.example.yml`; CURRENT-STATE; service-permissions inventory |
| Private hop; no public API base in browser | nginx template + `API_BASE_URL=/`; Vitest `us099.front-only-private-hop.test.tsx` |
| Exact public origin CORS; no `*` | pytest `test_cors_public_ui_origin_allowlisted_no_wildcard`; wildcard reject hold |
| Topology docs without secrets | CURRENT-STATE, ubuntu deploy, front-only overlay, RUNTIME-STATE **not live** |
| Fail-closed unauth / non-allowlisted | Vitest anonymous + forbidden holds (US-099 + US-097 vocabulary) |
| Visible Cloudflare UI + Google sign-in | Proxied `/auth/google/*`; front-only overlay redirect URI placeholders |
| Clear failures/blocked | Config + auth messaging retained; pairing/config holds green |
| Preserve ADR-0001 / no publication-flag / BL-026 / BL-034 | Compose n8n→`:8010`; no publication-flag mutation; exposure inventory; UI/API split |

**Gaps:** Live Cloudflare hostname activation and operator Story accepted remain operator-owned (intentionally unchecked).
