## Why

Flow A Core is complete through distribution scheduling: blog posts publish to GitHub Pages, LinkedIn derivative variants are generated, and per-variant schedule metadata is persisted with `publish_state: pending`. Operators still manually publish each variant to LinkedIn. This child change implements the minimum safe LinkedIn API publication slice with a **queue-and-safety-delay** model so real publication is never immediate by default — the operator can review or cancel before a post becomes visible on LinkedIn.

## Goals

- Split LinkedIn publication into **queue/authorize** and **publish due variants** as separate worker actions.
- Introduce per-variant states: `pending` → `queued` → `published` | `failed` | `cancelled`.
- Apply a configurable safety delay (default 120 minutes) before a queued variant may be sent to LinkedIn.
- Publish personal-profile text posts whose commentary includes generated variant text and the blog URL.
- Persist publication metadata (`publish_after_utc`, `publication_queued_at`, URN, etc.) with idempotent, retry-safe semantics.
- Gate real LinkedIn API calls behind explicit request flags and environment configuration; all endpoints default to `dry_run: true`.
- Provide cancellation of queued variants before real publish.
- Ship unit tests, LinkedIn publication smoke script, optional evidence display, and operator documentation.

## Non-Goals

- LinkedIn-native scheduled posting (scheduling remains on our side via `scheduled_at_utc` and `publish_after_utc`).
- Immediate publication by default (future: set safety delay to `0` or pass `publish_now: true`).
- Full OAuth browser callback flow, token refresh automation, or `/v2/userinfo` auto-resolve for member URN.
- LinkedIn image upload, company page publishing, analytics, or comment automation.
- n8n workflow changes, activation, cron, webhook, or automatic publication when `scheduled_at_utc` elapses.
- Campaign-level transition to `distribution_complete` in v1.
- Operator UI for queue review (documented as future need; out of scope).
- Archiving the umbrella or committing/pushing as part of this proposal.

## What Changes

- Refine child OpenSpec change `linkedin-publication-integration` (umbrella slice 8) as a **follow-up to Flow A Core**.
- Add three worker HTTP endpoints (all default `dry_run: true`):
  - `POST /queue-linkedin-publication` — authorize variant; move `pending` → `queued`; set `publish_after_utc`; no LinkedIn API call.
  - `POST /publish-linkedin-due-variants` — publish `queued` variants where `publish_after_utc <= now` (or `publish_now: true`); calls LinkedIn API only when real-enabled.
  - `POST /cancel-linkedin-publication` — move `queued` → `cancelled` before real publish.
- Add environment variables: `SILVERMAN_LINKEDIN_ACCESS_TOKEN`, `SILVERMAN_LINKEDIN_MEMBER_URN` (required v1), `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES` (default `120`), optional `SILVERMAN_LINKEDIN_API_VERSION`.
- Define per-variant metadata: `publish_after_utc`, `publication_queued_at`, `publication_mode`, `publication_safety_delay_minutes`, `linkedin_post_urn`, `published_at`, `linkedin_publication`.
- Configuration errors (missing token, missing URN, publication not enabled) fail the HTTP response but MUST NOT set variant `publish_state: failed`.
- Only real LinkedIn API failures (or content/platform rejection) mark variant `failed`.
- Campaign state remains `distribution_scheduled` throughout v1; only per-variant `publish_state` and publication metadata change.
- Add LinkedIn publication smoke script and optional evidence collector display of variant states (`pending`, `queued`, `published`, `failed`, `cancelled`) without changing Flow A Core PASS semantics.
- Document LinkedIn prerequisites (`w_member_social`, manual OAuth token, personal profile only).

No n8n workflow JSON changes. No automatic triggers. No LinkedIn API calls unless explicitly real-enabled and variant is due (or `publish_now: true`).

## Capabilities

### New Capabilities

- `linkedin-publication-integration`: Queue-and-delay LinkedIn API publication for Flow A — configuration, queue/publish/cancel services, three HTTP endpoints, per-variant state model, safety delay, dry-run defaults, tests, smoke script, evidence display, and operator documentation.

### Modified Capabilities

<!-- Flow A Core smoke capability (flow-a-deployment-readiness-and-smoke-test) is NOT modified. LinkedIn publication smoke and evidence display belong to this change only. -->

## Impact

- **Umbrella reference**: Child slice 8 under `flow-a-automatic-blog-linkedin-publishing-roadmap`. Flow A Core remains complete at `distribution_scheduled`.
- **Worker API**: New endpoints `/queue-linkedin-publication`, `/publish-linkedin-due-variants`, `/cancel-linkedin-publication`; new `linkedin_client.py` and `linkedin_publication_flow.py`.
- **Campaign metadata**: Per-variant state transitions (`pending` → `queued` → `published` | `failed` | `cancelled`); no campaign state beyond `distribution_scheduled` in v1.
- **Scheduling model**: Existing `scheduled_at_utc` remains internal distribution schedule; `publish_after_utc` is the safety-delay gate before LinkedIn API call. Worker decides when LinkedIn receives the post.
- **Dependencies**: Requires `linkedin-distribution-scheduling-model` (`distribution_scheduled`, artifacts, `source_public_url`).
- **Deployment**: Smoke script, `.env.example` additions; evidence collector may display LinkedIn states informationally.
- **Tests**: `tests/test_linkedin_publication.py` covering queue, publish-due, cancel, dry-run, config errors, and API failures.
- **Future**: Immediate mode via `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES=0` or `publish_now: true`; operator UI for queue review; n8n orchestration (separate change).
