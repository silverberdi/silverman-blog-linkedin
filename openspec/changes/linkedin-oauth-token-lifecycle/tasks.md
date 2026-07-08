## 1. Configuration and foundations

- [x] 1.1 Add OAuth environment variable constants and loaders (`CLIENT_ID`, `CLIENT_SECRET`, `REDIRECT_URI`, `TOKEN_STORE_PATH`, state TTL, refresh skew) in new `linkedin_oauth_config.py`
- [x] 1.2 Extend `deploy/server/silverman-worker.env.example` with OAuth variables and token store path at `/secrets/linkedin-oauth-tokens.json` (outside editorial workspace mount)
- [x] 1.3 Document chmod `600` on token file and chmod `700` host secrets directory layout in deployment docs; add dedicated `/secrets` volume in `silverman-worker.compose.yaml` and host dir creation in `deploy-worker.sh`

## 2. Token store and state store

- [x] 2.1 Implement `linkedin_token_store.py` with atomic JSON read/write, `0600` permissions, and redacted `__repr__`/serialization
- [x] 2.2 Define token record schema (access_token, refresh_token, scope, created_at, expires_at, refresh_expires_at, member_urn)
- [x] 2.3 Implement `linkedin_oauth_state_store.py` with secure random state generation, TTL, single-use deletion, expired entry pruning, and fail-safe rejection when state removal cannot be persisted

## 3. OAuth client and token provider

- [x] 3.1 Implement `linkedin_oauth_client.py` for authorization URL building, authorization-code exchange, and refresh-token grant (httpx, mockable)
- [x] 3.2 Resolve member URN from OIDC userinfo or token response (`sub` → `urn:li:person:{sub}`) on successful exchange
- [x] 3.3 Implement `linkedin_token_provider.py` with `resolve_linkedin_access_token()` returning `ok` or `action_required` and stable error codes
- [x] 3.4 Implement refresh-before-expiry logic using `SILVERMAN_LINKEDIN_TOKEN_REFRESH_SKEW_SECONDS`; short-circuit `linkedin_oauth_reauthorization_required` when `refresh_expires_at` is past without calling LinkedIn; preserve existing `refresh_expires_at` when refresh response omits `refresh_token_expires_in`
- [x] 3.5 Support env fallback (`SILVERMAN_LINKEDIN_ACCESS_TOKEN`, `SILVERMAN_LINKEDIN_MEMBER_URN`) only when token store is empty or unconfigured — not after refresh failure, expired refresh token, or reauthorization-required states

## 4. HTTP endpoints

- [x] 4.1 Add API-key-protected `GET /linkedin/oauth/authorize` returning `{ "authorization_url": "..." }` (optional `redirect=true`)
- [x] 4.2 Add public `GET /linkedin/oauth/callback` with state validation, code exchange, human-readable HTML success/failure with escaped messages (no secrets, no raw provider-controlled HTML)
- [x] 4.3 Add API-key-protected `GET /linkedin/oauth/status` safe diagnostics (metadata only, no token values)
- [x] 4.4 Ensure callback and OAuth paths never log `access_token`, `refresh_token`, `client_secret`, or full authorization `code`
- [x] 4.5 Add `scripts/linkedin_oauth_authorize_url.py` CLI-safe URL printer for local operator use

## 5. Publication integration

- [x] 5.1 Update `linkedin_publication_flow.py` publish-due path to resolve credentials via token provider before real API calls
- [x] 5.2 Map token provider `action_required` to stable codes (`linkedin_oauth_token_missing`, `linkedin_oauth_refresh_failed`, `linkedin_oauth_reauthorization_required`) without marking variants `failed`
- [x] 5.3 Ensure dry-run publish-due does not call token refresh or LinkedIn OAuth endpoints
- [x] 5.4 Preserve existing safety gates: dry_run default true, publication enabled flag, queue/due/publish_now semantics unchanged

## 6. Tests

- [x] 6.1 Add `tests/test_linkedin_oauth_token_lifecycle.py` covering authorization URL parameters, state TTL/single-use, callback error paths, callback HTML escaping, mocked exchange success/failure, and state consume persist failure
- [x] 6.2 Add tests for token store redaction and diagnostic endpoint (no cleartext tokens)
- [x] 6.3 Add tests for refresh decision logic (valid, near expiry, expired with/without refresh token, expired `refresh_expires_at` without LinkedIn call, refresh preserves `refresh_expires_at`)
- [x] 6.4 Extend `tests/test_linkedin_publication.py` for publish-due `action_required` — no LinkedIn API call, variant stays `queued`
- [x] 6.5 Add tests proving env fallback works when store empty and does not apply after refresh failure or missing refresh token
- [x] 6.6 Run full `pytest` suite and confirm all existing tests pass (`593 passed`)

## 7. Documentation

- [x] 7.1 Update `docs/deployment/linkedin-publication-prerequisites.md` with OAuth flow, scopes, redirect URL, tunnel prerequisite, refresh/reauthorization, Postman as fallback only
- [x] 7.2 Document Cloudflare Tunnel mapping `api.silverman.pro` → `localhost:8010` and tunnel token rotation if exposed
- [x] 7.3 Document initial authorization steps (authorize URL → browser consent → callback success → status check)
- [x] 7.4 Document minimizing public exposure of non-callback worker routes

## 8. Validation (no real publish)

- [x] 8.1 Run `openspec validate linkedin-oauth-token-lifecycle --strict`
- [x] 8.2 Run `openspec validate --all`
- [x] 8.3 Manually verify authorize URL generation and callback handling in dry/local mode with mocked LinkedIn responses (no `--real-publish`)
