# LinkedIn publication prerequisites

Flow A Core stops at `distribution_scheduled` with per-variant `publish_state: pending`. This document covers the **follow-up** LinkedIn publication slice: queue → safety delay → publish-due. It is separate from Flow A Core PASS semantics.

## Developer App and OAuth token

1. Create a LinkedIn Developer App at [LinkedIn Developer Portal](https://www.linkedin.com/developers/).
2. Add the **Share on LinkedIn** product to obtain the `w_member_social` scope.
3. Obtain an OAuth 2.0 access token externally (manual token flow in v1 — no OAuth UI in the worker).
4. Required scope for personal-profile text posts: **`w_member_social`**.

The worker does **not** refresh tokens or run OAuth callbacks in v1.

## Required environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `SILVERMAN_LINKEDIN_ACCESS_TOKEN` | Real publish | OAuth access token (never logged or returned in HTTP responses) |
| `SILVERMAN_LINKEDIN_MEMBER_URN` | **Yes v1** | Author URN, e.g. `urn:li:person:{id}` — no `/v2/userinfo` auto-resolve |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | Real publish | Must be `true` for real LinkedIn API calls |
| `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES` | No | Default `120` — minutes after queue before variant is due |
| `SILVERMAN_LINKEDIN_API_VERSION` | No | LinkedIn REST API version header (YYYYMM), default `202504` |

Copy values into the server `.env` from `deploy/server/silverman-worker.env.example`. Never commit real tokens.

## Member URN

v1 requires an explicit `SILVERMAN_LINKEDIN_MEMBER_URN`. The worker does not call `/v2/userinfo` to resolve it. Obtain the person id from your OAuth/userinfo flow outside the worker and format as `urn:li:person:{id}`.

## Two-step operator workflow

Scheduling is **worker-side only**. LinkedIn receives a post only when the worker calls the LinkedIn REST Posts API.

1. **Queue** — `POST /queue-linkedin-publication` with `dry_run: false` moves `pending` → `queued`, sets `publish_after_utc`, does **not** call LinkedIn.
2. **Review window** — default safety delay is 120 minutes (`SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES`). Inspect generated artifacts under `linkedin-posts/generated/`.
3. **Cancel (optional)** — `POST /cancel-linkedin-publication` with `dry_run: false` moves `queued` → `cancelled` before publish. Cannot cancel `published` variants.
4. **Publish due** — `POST /publish-linkedin-due-variants` with `dry_run: false` publishes `queued` variants where `publish_after_utc <= now`, or use `publish_now: true` to bypass the delay.

All three endpoints default to `dry_run: true`.

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

## Campaign state

v1 does **not** transition campaign state to `distribution_complete`. Campaign remains `distribution_scheduled`; only per-variant `publish_state` and publication metadata change.

## Smoke script

On the Ubuntu server:

```bash
./deploy/server/run-linkedin-publication-smoke.sh
```

Defaults to dry-run for queue and publish-due (safe without LinkedIn credentials). Real queue: `--real`. Real publish: `--real-publish` with publication enabled and credentials in `.env`. The script never prints secrets.

## Future operator UI (out of scope v1)

A review UI for queued variants is planned separately. v1 escape hatch: cancel endpoint before `publish_after_utc`.

## Separation from Flow A Core

Flow A Core success (`distribution_scheduled` + `linkedin_distribution`) does not require LinkedIn API publication. Evidence collector may display publication state counts informationally without changing Flow A Core PASS semantics.
