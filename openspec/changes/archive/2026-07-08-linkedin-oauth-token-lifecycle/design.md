## Context

Flow A Core is complete. `linkedin-publication-integration` (active change) implements queue-and-safety-delay LinkedIn publication with manually configured `SILVERMAN_LINKEDIN_ACCESS_TOKEN` and `SILVERMAN_LINKEDIN_MEMBER_URN`. Real publication is gated behind dry-run defaults, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, and per-variant queue/due semantics.

Production prerequisites are in place:

- LinkedIn Developer App with products **Share on LinkedIn** (`w_member_social`) and **Sign In with LinkedIn using OpenID Connect** (`openid`, `profile`).
- Public site: `https://silverman.pro/privacy-policy/`, `https://silverman.pro/terms/`.
- Public API base: `https://api.silverman.pro` via Cloudflare Tunnel → worker `localhost:8010`.
- Registered OAuth redirect: `https://api.silverman.pro/linkedin/oauth/callback`.
- Candidate member URN from OIDC userinfo: `urn:li:person:4AlAhKj7Uf`.

Postman manual token flow validated scopes and identity but is not the desired operating model. This change adds OAuth token lifecycle only — no real LinkedIn publish execution, no n8n activation, no cron.

**Dependency:** Requires `linkedin-publication-integration` modules (`linkedin_config.py`, `linkedin_client.py`, `linkedin_publication_flow.py`, publication HTTP endpoints).

## Goals / Non-Goals

**Goals:**

- One-time browser authorization by Silverio; worker handles callback, code exchange, secure persistence, and refresh-before-publish.
- File-based token store outside repo at `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` with restrictive permissions.
- Token provider abstraction used by publication flow instead of reading access token directly from environment.
- Safe diagnostics and operator docs; never log or return token values, `client_secret`, or full authorization codes.
- Config/action-required errors do not mark queued variants `failed`.

**Non-Goals:**

- Executing real LinkedIn publication (`--real-publish`) as part of this change.
- n8n workflow changes, cron, or scheduled triggers.
- LinkedIn Page publishing, image upload, analytics.
- Public blog repo changes.
- Commit, push, or archive during proposal/apply of this change.

## Decisions

### 1. OAuth flow: authorization code with server-side state

**Decision:** Implement standard OAuth 2.0 authorization code flow per LinkedIn docs.

- Authorization URL: `response_type=code`, `client_id`, `redirect_uri`, `scope=openid profile w_member_social`, cryptographically random `state`.
- Store `state` server-side with TTL (e.g. 10 minutes) in a small file or in-memory dict with file backing under token store parent directory.
- Callback `GET /linkedin/oauth/callback` validates `state`, exchanges `code` at `https://www.linkedin.com/oauth/v2/accessToken` with `client_secret` (server-side only).
- On success, fetch OIDC userinfo if needed to resolve `member_urn` (`sub` → `urn:li:person:{sub}`) and persist full token record.

**Alternatives considered:**

- *Implicit flow* — rejected (less secure, no refresh token).
- *Long-lived manual env token only* — current v1; rejected for production.

### 2. Authorization URL entry point

**Decision:** Expose `GET /linkedin/oauth/authorize` (API-key protected) returning JSON `{ "authorization_url": "..." }` and optionally redirect when `?redirect=true`. Also provide a small CLI script `scripts/linkedin_oauth_authorize_url.py` that prints the URL without starting the server — useful for local operator use.

**Rationale:** HTTP endpoint supports production tunnel setup; CLI supports local debugging without exposing authorize on public routes if tunneled selectively.

### 3. File-based token store (single-owner)

**Decision:** JSON file at `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` (default e.g. `/data/silverman-blog-linkedin/secrets/linkedin-oauth-tokens.json` on server, outside git workspace).

Stored fields:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "scope": "openid profile w_member_social",
  "token_type": "Bearer",
  "created_at": "2026-07-08T18:00:00Z",
  "expires_at": "2026-07-08T19:00:00Z",
  "refresh_expires_at": null,
  "member_urn": "urn:li:person:4AlAhKj7Uf"
}
```

- Write atomically (temp file + rename).
- On write, set file mode `0600` where OS supports it.
- `str()` / repr / diagnostic serializers MUST redact token fields.

**Alternatives considered:**

- *Database* — overkill for single-owner deployment.
- *Env var only* — current model; insufficient for refresh lifecycle.

### 4. OAuth state store

**Decision:** Separate small JSON file alongside token store (e.g. `linkedin-oauth-state.json`) mapping `state` → `{ created_at, expires_at }`. Prune expired entries on read/write. State single-use: delete on successful validation.

### 5. Token provider interface

**Decision:** New module `linkedin_token_provider.py` with:

```python
@dataclass
class TokenResolutionResult:
    status: Literal["ok", "action_required"]
    access_token: str | None
    member_urn: str | None
    error_code: str | None  # stable code when action_required

def resolve_linkedin_access_token(...) -> TokenResolutionResult
```

Resolution order:

1. Load token store; if missing/empty → `action_required` (`linkedin_oauth_token_missing`).
2. If access token valid with skew buffer (e.g. 5 minutes before `expires_at`) → return token + member URN.
3. If expired/near expiry and refresh token present → call LinkedIn refresh endpoint; on success update store; on failure → `action_required` (`linkedin_oauth_refresh_failed` or `linkedin_oauth_reauthorization_required`).
4. Fallback: if `SILVERMAN_LINKEDIN_ACCESS_TOKEN` and `SILVERMAN_LINKEDIN_MEMBER_URN` env vars set, use them (documented as manual fallback only).

Publication flow calls provider only when `dry_run` is false and publication enabled; dry-run never touches token store or LinkedIn OAuth endpoints.

### 6. Publication integration (minimal touch)

**Decision:** Modify `load_linkedin_publication_settings` / `linkedin_publication_flow.py` to accept resolved credentials from token provider instead of requiring env access token. `real_publish_ready` becomes: publication enabled + resolved access token + member URN.

Config/action-required from token provider MUST map to existing stable error semantics — variant stays `queued`, response includes `linkedin_oauth_reauthorization_required` or related codes.

No changes to queue/cancel scheduling, safety delay, or campaign state rules.

### 7. Public callback vs protected routes

**Decision:**

| Route | Auth | Public via tunnel |
|-------|------|-------------------|
| `GET /linkedin/oauth/callback` | None (LinkedIn redirect) | Yes |
| `GET /linkedin/oauth/authorize` | API key | Optional (prefer operator-local or key) |
| `GET /linkedin/oauth/status` | API key | Optional |

Callback returns simple HTML or plain text success/failure page — no JSON secrets. Errors from LinkedIn (`error`, `error_description`) shown generically without echoing codes in logs at info level.

**Risk mitigation:** Document minimizing public exposure; only callback must be public for OAuth. Rotate Cloudflare tunnel token if exposed.

### 8. Safe diagnostics

**Decision:** `GET /linkedin/oauth/status` (API-key protected) returns:

```json
{
  "token_store_configured": true,
  "token_present": true,
  "access_token_expires_at": "2026-07-08T19:00:00Z",
  "refresh_token_present": true,
  "refresh_expires_at": null,
  "scopes": "openid profile w_member_social",
  "member_urn": "urn:li:person:4AlAhKj7Uf",
  "publication_enabled": false
}
```

Never include `access_token`, `refresh_token`, or `client_secret`.

### 9. Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `SILVERMAN_LINKEDIN_CLIENT_ID` | OAuth | LinkedIn app client id |
| `SILVERMAN_LINKEDIN_CLIENT_SECRET` | OAuth | Server-side only; never in responses |
| `SILVERMAN_LINKEDIN_REDIRECT_URI` | OAuth | `https://api.silverman.pro/linkedin/oauth/callback` |
| `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` | OAuth | Absolute path outside repo |
| `SILVERMAN_LINKEDIN_OAUTH_STATE_TTL_SECONDS` | No | Default `600` |
| `SILVERMAN_LINKEDIN_TOKEN_REFRESH_SKEW_SECONDS` | No | Default `300` |
| `SILVERMAN_LINKEDIN_ACCESS_TOKEN` | Fallback | Manual Postman token only |
| `SILVERMAN_LINKEDIN_MEMBER_URN` | Fallback | Manual override if not in store |

Existing publication env vars unchanged in behavior.

### 10. Logging and redaction

**Decision:** Central redaction helper masks values matching token patterns in log messages. Never log authorization `code`, `access_token`, `refresh_token`, or `client_secret`. Callback success logs at info: "LinkedIn OAuth callback succeeded; member_urn=urn:li:person:…".

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Public callback endpoint abuse | State validation; short TTL; no sensitive data in response; rate-limit at Cloudflare if needed |
| Token file readable on shared host | chmod 600; path outside repo; document permission check in deploy docs |
| LinkedIn refresh token not issued or short-lived | Fail safe with reauthorization message; env fallback documented |
| Tunnel exposes entire worker API | Document exposing only required routes; API key on non-callback endpoints |
| Refresh fails mid-publish | action_required; variant not marked failed until real API attempt |

## Migration Plan

1. Deploy worker with new OAuth modules; keep publication disabled (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` unset/false).
2. Configure OAuth env vars and token store path on server with `chmod 600` directory under `/data/silverman-blog-linkedin/secrets/`.
3. Operator calls authorize URL, completes browser consent, verifies callback success page.
4. Call `GET /linkedin/oauth/status` to confirm token present and expiry metadata.
5. Remove reliance on manual env token when store is populated (env vars optional fallback).
6. Enable publication in a **separate** change/operator action after OAuth validation.

**Rollback:** Delete token store file; revert to env `SILVERMAN_LINKEDIN_ACCESS_TOKEN` fallback; disable publication flag.

## Open Questions

- Exact LinkedIn refresh token lifetime and whether `refresh_expires_at` is returned — handle gracefully when absent.
- Whether authorize endpoint should be tunnel-public or operator-SSH-only — default API-key + document both patterns.
