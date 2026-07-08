## Why

LinkedIn publication integration (`linkedin-publication-integration`) is implemented with manually configured `SILVERMAN_LINKEDIN_ACCESS_TOKEN` and `SILVERMAN_LINKEDIN_MEMBER_URN`. Postman-based token generation validated scopes and identity but is not a sustainable production model for Silverio Bernal's personal profile. Tokens expire, refresh must be automated where LinkedIn allows, and reauthorization must be explicit and safe when refresh is unavailable.

## Goals

- Replace manual access-token handling with a production-oriented OAuth 2.0 authorization-code flow and token lifecycle.
- Silverio authorizes the LinkedIn Developer App once; the worker handles callback, exchange, secure storage, and refresh-before-publish.
- Preserve all existing publication safety gates (dry-run default, publication enabled flag, queue/due semantics).
- Provide safe diagnostics and operator documentation without exposing secrets.

## Non-Goals

- Publishing to LinkedIn as part of this change (no `--real-publish`, no live API publication validation).
- Activating n8n workflows, cron, or scheduled triggers.
- LinkedIn Page publishing, image upload, analytics, or comment automation.
- Modifying the public blog repository.
- Committing, pushing, or archiving this change as part of proposal creation.
- Broad infrastructure unrelated to OAuth lifecycle (beyond documented Cloudflare Tunnel prerequisite).

## What Changes

- Add OAuth authorization URL generation (HTTP endpoint and/or CLI-safe mechanism) with `response_type=code`, scopes `openid profile w_member_social`, secure random `state` stored server-side with expiration, and no `client_secret` exposure.
- Add public callback endpoint `GET /linkedin/oauth/callback` that validates state, exchanges authorization code with LinkedIn, persists token metadata, and returns human-readable success/failure without secrets in response or logs.
- Add file-based token store outside repo/workspace at configurable `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` with chmod `600` expectation; store access token, refresh token (if returned), scope, timestamps, and member URN.
- Add token provider that resolves a valid access token before real publication, refreshes when expired or near expiry, updates store on success, and returns action-required errors when refresh is impossible (without marking queued variants `failed`).
- Integrate token provider into existing publication flow, replacing direct environment-only access-token usage while preserving dry-run defaults and scheduling semantics.
- Add safe diagnostic endpoint or script showing token store status, expiry metadata, scopes, member URN, and publication enabled — never token values.
- Update deployment documentation for LinkedIn Developer App prerequisites, redirect URL, Cloudflare Tunnel, initial authorization, refresh behavior, reauthorization, and Postman as fallback only.
- Add/extend tests for authorization URL, state validation, callback handling, token exchange, store redaction, refresh logic, publication action-required behavior, and diagnostic redaction.

## Capabilities

### New Capabilities

- `linkedin-oauth-token-lifecycle`: OAuth authorization URL generation, callback handling, secure file-based token store, automatic refresh-before-publish token provider, safe diagnostics, and operator documentation for LinkedIn OAuth on a single-owner deployment.

### Modified Capabilities

- `linkedin-publication-integration`: Replace environment-only `SILVERMAN_LINKEDIN_ACCESS_TOKEN` as the primary credential source with token-provider resolution; add stable error codes for OAuth action-required states; preserve config-error semantics (action-required MUST NOT mark queued variants `failed`).

## Impact

- **Dependency**: Requires `linkedin-publication-integration` (active change) — queue/publish/cancel endpoints, `linkedin_client.py`, `linkedin_publication_flow.py`, and `linkedin_config.py` must exist before apply.
- **Worker API**: New routes `GET /linkedin/oauth/authorize` (or equivalent), `GET /linkedin/oauth/callback`, and safe diagnostic route; publication endpoints unchanged in scheduling semantics.
- **Configuration**: New env vars for OAuth (`SILVERMAN_LINKEDIN_CLIENT_ID`, `SILVERMAN_LINKEDIN_CLIENT_SECRET`, `SILVERMAN_LINKEDIN_REDIRECT_URI`, `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH`, optional refresh skew); `SILVERMAN_LINKEDIN_ACCESS_TOKEN` / `SILVERMAN_LINKEDIN_MEMBER_URN` remain as documented fallback only.
- **Security**: State store, token file permissions, log/response redaction; public callback route exposed via `https://api.silverman.pro/linkedin/oauth/callback` through Cloudflare Tunnel.
- **Tests**: New `tests/test_linkedin_oauth_token_lifecycle.py` (or extended modules); existing `tests/test_linkedin_publication.py` updated for token-provider integration.
- **Docs**: Update `docs/deployment/linkedin-publication-prerequisites.md` and `.env.example`; document tunnel and reauthorization.
- **Out of scope**: n8n JSON, cron, real LinkedIn publish execution, campaign state transitions.
