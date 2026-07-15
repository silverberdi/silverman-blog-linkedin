# LinkedIn publication prerequisites

Flow A Core stops at `distribution_scheduled` with per-variant `publish_state: pending`. This document covers the **follow-up** LinkedIn publication slice: queue → safety delay → publish-due. Flow A n8n activation/schedule does **not** enable LinkedIn API publication; `distribution_scheduled` is not LinkedIn API published. US-011 publication-guard acceptance (see [us-011 validation template](../operations/us-011-linkedin-publication-guard-validation-TEMPLATE.md)) may temporarily disable then restore the prior operator-approved flag — it is not a permanent leave-false policy.

**Implementation vs validation:** Worker endpoints (`/queue-linkedin-publication`, `/publish-linkedin-due-variants`, `/cancel-linkedin-publication`) are **implemented** and guarded by `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` (default `false`). First real API publication was **operationally validated** under BL-002 (controlled smoke); see [CURRENT-STATE.md](../CURRENT-STATE.md). Scheduled multi-variant execution remains **BL-007**.

**BL-007 handoff:** A local uncommitted opt-in `auto_queue_pending` path exists for construction convenience (queue+publish in one call). It is **deferred** — see [bl-007-auto-queue-pending-handoff.md](../product/bl-007-auto-queue-pending-handoff.md). Canonical contract on `main` remains separate queue then publish-due until BL-007 OpenSpec lands.

Public site prerequisites for LinkedIn app configuration:

- [Privacy policy](https://silverman.pro/privacy-policy/)
- [Terms of use](https://silverman.pro/terms/)

## LinkedIn Developer App and OAuth

1. Create a LinkedIn Developer App at [LinkedIn Developer Portal](https://www.linkedin.com/developers/).
2. Add products:
   - **Share on LinkedIn** — scope `w_member_social`
   - **Sign In with LinkedIn using OpenID Connect** — scopes `openid`, `profile`
3. Register redirect URL: `https://api.silverman.pro/linkedin/oauth/callback`
4. Configure worker OAuth environment variables (see below).

Required scopes (space-delimited): **`openid profile w_member_social`**

Member URN is resolved from OIDC (`sub` → `urn:li:person:{sub}`) during OAuth callback and stored in the token file.

### Cloudflare Tunnel prerequisite

Expose the worker API at `https://api.silverman.pro` via Cloudflare Tunnel mapping to `localhost:8010` on the Ubuntu server.

- Only the OAuth callback route must be publicly reachable for LinkedIn redirects.
- Prefer API-key protection for non-callback routes (`/linkedin/oauth/authorize`, `/linkedin/oauth/status`, publication endpoints).
- **If a Cloudflare tunnel connector token is exposed** (logs, chat, commit), rotate it immediately in the Cloudflare Zero Trust dashboard.

### Token store and permissions

- Path: `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` (production default `/secrets/linkedin-oauth-tokens.json` in container)
- Store **outside** the editorial workspace mount (`/data/silverman-blog-linkedin`) and **outside** the git workspace
- Worker writes atomically and sets file mode **`chmod 600`** where supported
- OAuth state file: `linkedin-oauth-state.json` alongside the token store parent directory (`/secrets/`)

Create the secrets directory on the Ubuntu server host (mounted into the container at `/secrets`):

```bash
mkdir -p /home/silverman/silverman-blog-linkedin-worker/secrets
chmod 700 /home/silverman/silverman-blog-linkedin-worker/secrets
```

`deploy/server/deploy-worker.sh` creates this directory automatically on deploy. Set in `.env`:

```
SILVERMAN_LINKEDIN_TOKEN_STORE_PATH=/secrets/linkedin-oauth-tokens.json
```

## Initial authorization flow

1. Ensure OAuth env vars and token store path are configured; keep `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` until verified.
2. Start the worker and confirm Cloudflare Tunnel routes `api.silverman.pro` → `localhost:8010`.
3. Request authorization URL (API key required):
   - `GET /linkedin/oauth/authorize` → `{ "authorization_url": "..." }`
   - Or locally: `python scripts/linkedin_oauth_authorize_url.py`
   - Optional redirect: `GET /linkedin/oauth/authorize?redirect=true`
4. Open the URL in a browser; sign in as Silverio and consent.
5. LinkedIn redirects to `GET /linkedin/oauth/callback` — success page shows member URN (no token values).
6. Verify status (API key required): `GET /linkedin/oauth/status` — confirms token present, expiry metadata, scopes, member URN.

## Automatic refresh before publication

When `POST /publish-linkedin-due-variants` runs with `dry_run: false`, the worker resolves credentials through the token provider:

- Valid access token (outside refresh skew) → used directly
- Near expiry or expired with refresh token → refresh grant, store updated
- Missing store / expired without refresh → `action_required` (variant stays `queued`, no LinkedIn API call)

Refresh skew default: `SILVERMAN_LINKEDIN_TOKEN_REFRESH_SKEW_SECONDS=300` (5 minutes before expiry).

## Reauthorization

When refresh fails or no refresh token exists, publish-due returns stable codes such as `linkedin_oauth_reauthorization_required`. Repeat the initial authorization flow. Queued variants are **not** marked `failed` for OAuth action-required states.

## Manual Postman / env token (fallback only)

`SILVERMAN_LINKEDIN_ACCESS_TOKEN` and `SILVERMAN_LINKEDIN_MEMBER_URN` remain as **manual fallback** only when the token store is empty or unconfigured. They are **not** used after refresh failure, expired refresh token, or reauthorization-required states. Use OAuth authorization above for production.

## Required environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `SILVERMAN_LINKEDIN_CLIENT_ID` | OAuth | LinkedIn app client id |
| `SILVERMAN_LINKEDIN_CLIENT_SECRET` | OAuth | Server-side only; never in HTTP responses or logs |
| `SILVERMAN_LINKEDIN_REDIRECT_URI` | OAuth | `https://api.silverman.pro/linkedin/oauth/callback` |
| `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` | OAuth | Container path `/secrets/linkedin-oauth-tokens.json` (host: `.../secrets/`, chmod 700 dir, 600 file) |
| `SILVERMAN_LINKEDIN_OAUTH_STATE_TTL_SECONDS` | No | OAuth state TTL; default `600` |
| `SILVERMAN_LINKEDIN_TOKEN_REFRESH_SKEW_SECONDS` | No | Refresh before expiry; default `300` |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | Real publish | Must be `true` for real LinkedIn API calls |
| `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES` | No | Default `120` — minutes after queue before variant is due |
| `SILVERMAN_LINKEDIN_API_VERSION` | No | LinkedIn REST API version header (YYYYMM), default `202606` |
| `SILVERMAN_LINKEDIN_ACCESS_TOKEN` | Fallback only | Manual Postman token when store empty |
| `SILVERMAN_LINKEDIN_MEMBER_URN` | Fallback only | Manual override when store empty |

Copy values into the server `.env` from `deploy/server/silverman-worker.env.example`. Never commit real tokens or client secrets.

## Two-step operator workflow

Scheduling is **worker-side only**. LinkedIn receives a post only when the worker calls the LinkedIn REST Posts API.

1. **Queue** — `POST /queue-linkedin-publication` with `dry_run: false` moves `pending` → `queued`, sets `publish_after_utc`, does **not** call LinkedIn.
2. **Review window** — default safety delay is 120 minutes (`SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES`). Inspect generated artifacts under `linkedin-posts/generated/`.
3. **Cancel (optional)** — `POST /cancel-linkedin-publication` with `dry_run: false` moves `queued` → `cancelled` before publish. Cannot cancel `published` variants.
4. **Publish due** — `POST /publish-linkedin-due-variants` with `dry_run: false` publishes `queued` variants where `publish_after_utc <= now`, or use `publish_now: true` to bypass the delay.

All three endpoints default to `dry_run: true`. Dry-run publish-due does **not** refresh tokens or call LinkedIn OAuth endpoints.

## Safety delay and immediate mode

- Default safety delay: **120 minutes** after queue before a variant is eligible for real publish.
- Future immediate mode without redesign:
  - Set `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES=0` at queue time, or
  - Pass `publish_now: true` on publish-due.

## Post format (v1)

- Personal-profile **text post** only via `POST https://api.linkedin.com/rest/posts`.
- Commentary includes generated variant text and `source_public_url` (blog URL).
- No image upload, no company page publishing, no analytics, no comments automation.

Required headers (verified against LinkedIn Posts API documentation):

- `Authorization: Bearer {token}`
- `Content-Type: application/json`
- `X-Restli-Protocol-Version: 2.0.0`
- `Linkedin-Version: {YYYYMM}`

### API version header (HTTP 426)

The worker sends `Linkedin-Version` from `SILVERMAN_LINKEDIN_API_VERSION` (default **`202606`**).

If LinkedIn returns **HTTP 426**, the configured version is no longer supported. Set `SILVERMAN_LINKEDIN_API_VERSION` to a current supported **YYYYMM** value per [LinkedIn API versioning](https://learn.microsoft.com/en-us/linkedin/marketing/versioning), redeploy, and retry publish-due.

## Minimizing public exposure

- Expose `https://api.silverman.pro/linkedin/oauth/callback` publicly for LinkedIn redirects.
- Keep `/linkedin/oauth/authorize` and `/linkedin/oauth/status` behind API key or operator-local access where possible.
- Do not expose unnecessary worker routes through the tunnel.

## Campaign state

v1 does **not** transition campaign state to `distribution_complete`. Campaign remains `distribution_scheduled`; only per-variant `publish_state` and publication metadata change.

## Smoke scripts

### Generic dry-run smoke

On the Ubuntu server:

```bash
./deploy/server/run-linkedin-publication-smoke.sh
```

Defaults to dry-run for queue and publish-due (safe without LinkedIn credentials). Real queue: `--real`. Real publish: `--real-publish` with publication enabled and credentials in `.env`. The script never prints secrets.

### US-003 controlled first-real-publish validation (BL-002)

**Warning:** `run-us003-linkedin-publication-validation-smoke.sh` publishes one **real** LinkedIn post when publication is enabled. The post remains on the operator profile until manually removed in LinkedIn. Unlike US-001/US-002 smoke validation, there is no automatic cleanup of the external artifact.

**Blocking prerequisites (tasks §0 — complete before validation window):**

1. Host token store files exist with `chmod 600` (`deploy/server/deploy-worker.sh` creates placeholders on deploy):
   - `/home/silverman/silverman-blog-linkedin-worker/secrets/linkedin-oauth-tokens.json`
   - `/home/silverman/silverman-blog-linkedin-worker/secrets/linkedin-oauth-state.json`
2. Cloudflare Tunnel routes `https://api.silverman.pro` → worker `localhost:8010` for OAuth callback.
3. OAuth env vars in server `.env` (`SILVERMAN_LINKEDIN_CLIENT_ID`, `SILVERMAN_LINKEDIN_CLIENT_SECRET`, `SILVERMAN_LINKEDIN_REDIRECT_URI`, `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH`) — no secrets in versioned files.
4. Browser authorization: `GET /linkedin/oauth/authorize` → consent → successful callback.
5. `GET /linkedin/oauth/status` reports `token_present`, `member_urn`, and expiry metadata (no token cleartext).

**Validation window procedure:**

1. Reconfirm OAuth status immediately before the run (token may expire between bootstrap and validation).
2. Operator approves exactly one variant on a Flow A `distribution_scheduled` campaign with `publish_state` `pending`.
3. Run on the Ubuntu server (example campaign from operational validation):

```bash
/home/silverman/silverman-blog-linkedin-worker/run-us003-linkedin-publication-validation-smoke.sh \
  --campaign-id flow-a-2026-07-10-a-bounded-context-is-not-a-folder \
  --variant executive-recruiter
```

The script:

- enables `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` and recreates the container (US-001 pattern);
- runs OAuth preflight via `GET /linkedin/oauth/status` (fail-closed);
- performs real queue → real publish-due with `publish_now: true`;
- asserts `linkedin_post_urn` and idempotent repeat publish-due (`linkedin_publish_already_published`);
- restores `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` in a trap/finally block.

**LinkedIn visibility checklist (US-004 — manual, after successful publish):**

- Record `linkedin_post_urn` and `published_at` from script output / campaign metadata.
- Confirm the post appears on the operator LinkedIn profile feed or activity.
- Optional: note public post URL if obtainable from the URN.
- Do not store LinkedIn session cookies or credentials in the repository.

**Safeguard restoration (US-005):**

- Script attempts automatic restoration to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false`.
- Operator confirms disabled state in Phase 3 report (`publication_enabled: false` on `/linkedin/oauth/status`).

**HTTP 426 remediation:**

If publish-due fails with LinkedIn HTTP 426 (unsupported API version), update `SILVERMAN_LINKEDIN_API_VERSION` to a current supported YYYYMM value per [LinkedIn API versioning](https://learn.microsoft.com/en-us/linkedin/marketing/versioning), redeploy, and retry publish-due only (do not re-queue if variant is already `queued` or `published` without operator review).

## Future operator UI (out of scope v1)

A review UI for queued variants is planned separately. v1 escape hatch: cancel endpoint before `publish_after_utc`.

## Separation from Flow A Core

Flow A Core success (`distribution_scheduled` + `linkedin_distribution`) does not require LinkedIn API publication. Evidence collector may display publication state counts informationally without changing Flow A Core PASS semantics.

## Article preview image metadata (package generation)

Flow A `POST /generate-linkedin-package` records **article preview metadata** derived from the canonical public blog hero image. This is **not** LinkedIn media upload and does not call LinkedIn APIs.

- **Source:** front matter `image` (for example `/assets/images/<public_slug>.png`) and the matching file under the public blog repo checkout (`assets/images/<public_slug>.png`).
- **Output:** `linkedin_package.article_preview` and per-variant fields including `public_image_url` (absolute HTTPS URL on `silverman.pro`), `article_title`, `article_description`, and `public_url`.
- **Validation:** when `SILVERMAN_GITHUB_PAGES_REPO_PATH` is configured, the worker checks that the public image file exists before marking preview status `available`. Missing assets yield status `missing` with stable code `linkedin_article_preview_public_image_missing` in `warnings[]` — package generation still completes.
- **Link preview semantics:** `public_image_url` is metadata for LinkedIn link/card preview behavior when publication is enabled later. The worker does not upload image bytes to LinkedIn during package generation.
- **Publication remains disabled:** `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` by default. Preview metadata does not publish posts or require a LinkedIn token.
