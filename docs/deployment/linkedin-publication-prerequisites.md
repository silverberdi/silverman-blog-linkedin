# LinkedIn publication prerequisites

Flow A Core stops at `distribution_scheduled` with per-variant `publish_state: pending`. This document covers the **follow-up** LinkedIn publication slice: queue → safety delay → publish-due. Flow A n8n activation/schedule does **not** enable LinkedIn API publication; `distribution_scheduled` is not LinkedIn API published. US-011 publication-guard acceptance (see [us-011 validation template](../operations/us-011-linkedin-publication-guard-validation-TEMPLATE.md)) may temporarily disable then restore the prior operator-approved flag — it is not a permanent leave-false policy.

**Implementation vs validation:** Worker endpoints (`/queue-linkedin-publication`, `/publish-linkedin-due-variants`, `/cancel-linkedin-publication`) are **implemented** and guarded by `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` (default `false`). First real API publication was **operationally validated** under BL-002 (controlled smoke); see [CURRENT-STATE.md](../CURRENT-STATE.md). US-018 combined due identification and auto-queue is **operationally validated**. US-019 publication-evidence formalization (spec + tests + additive `auto_queue_results` evidence fields) is **implemented, not deployed**. US-020 publish-time sequence and cadence guard is **implemented, not deployed**. BL-007 remains open; US-019/US-020 closure is a separate authorized validation step.

**BL-007 handoff:** The former local `auto_queue_pending` construction WIP was absorbed and rewritten under the approved US-018 OpenSpec change; see [bl-007-auto-queue-pending-handoff.md](../product/bl-007-auto-queue-pending-handoff.md). The canonical two-step path remains available.

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
3. **Cancel (optional)** — `POST /cancel-linkedin-publication` with `dry_run: false` moves `queued` → `cancelled` before publish, or `failed` → `cancelled` during recovery (US-022, evidence preserved). Cannot cancel `published` variants.
4. **Publish due** — `POST /publish-linkedin-due-variants` with `dry_run: false` publishes `queued` variants where `publish_after_utc <= now`, or use `publish_now: true` to bypass the delay.

All three endpoints default to `dry_run: true`. Dry-run publish-due does **not** refresh tokens or call LinkedIn OAuth endpoints.

## Combined due identification and auto-queue (US-018)

`POST /publish-linkedin-due-variants` accepts opt-in `auto_queue_pending: true`. The default remains `false`, so existing callers retain the two-step behavior above.

The combined request scans only `metadata/campaigns/*.json` and only Flow A campaigns in `distribution_scheduled`. It considers `pending` variants due when `scheduled_at_utc <= now_utc`, queues eligible variants through the same queue service, then evaluates queued variants through publish-due.

Two independent time gates apply:

1. `scheduled_at_utc` controls when a `pending` variant may be auto-queued.
2. Queueing computes `publish_after_utc` using `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES`; publish-due respects that second gate.

`publish_now: true` is an explicit operator override for the normal schedule and safety-delay gates. It does not override supervision: cancelled variants, variants blocked by `operator_supervision.auto_queue_eligible: false`, and deferred variants whose new schedule is still in the future remain excluded. A deferred `pending` variant becomes eligible at runtime when its new schedule is due; the worker does not persist a flip of `auto_queue_eligible` back to `true`. `failed` variants are never auto-requeued.

Safe preview:

```bash
./deploy/server/run-publish-pending-linkedin-variants.sh
```

The script defaults to `dry_run: true`. Use `--respect-schedule` to set `publish_now: false`; optional `--campaign-id` and `--variant` filters narrow the run (`--variant` requires `--campaign-id`). `--real` requires `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` and a separately approved real publication window.

The manual n8n export `n8n/workflows/silverman-blog-linkedin-publish-pending.json` performs health and publish-due calls over HTTP only. Its repository default is `dry_run: true` and `"active": false`. Importing it does not enable unattended automation; activation or scheduling requires separate approval.

## Publication evidence and failure taxonomy (US-019)

After a **real successful** LinkedIn publish, campaign variant metadata MUST contain complete evidence:

| Field | Status | Notes |
|-------|--------|-------|
| `linkedin_post_urn` | **Mandatory** | Non-empty URN from LinkedIn `x-restli-id` |
| `published_at` | **Mandatory** | UTC ISO8601 `Z` |
| `linkedin_publication.provider` | **Mandatory** | e.g. `linkedin_rest_posts` |
| `linkedin_publication.post_urn` | **Mandatory** | Equal to `linkedin_post_urn` |
| `linkedin_publication.published_at` | **Mandatory** | Equal to top-level `published_at` |
| `linkedin_publication.http_status` | **Mandatory** | Numeric on HTTP response (success is `201`); `null` only on transport failure |
| `linkedin_post_id` | **Optional** | Never a substitute for the URN |

After a **real failed** API attempt, `publish_state` becomes `failed` and `linkedin_publication` records at minimum: `last_error_code`, `last_failed_at`, `retryable` (descriptive evidence only — retry policy is BL-008), and `http_status` (nullable only when no HTTP response was received). Content rejection uses dedicated code `linkedin_publish_content_invalid` (distinct from generic `linkedin_publish_api_error`). A 201 without a usable post URN is treated as `linkedin_publish_api_error`, never as `published` with missing evidence.

**Blocked conditions** fail the HTTP response with a stable code but **never** mark the variant `failed`: enablement off (`linkedin_publish_not_enabled`), OAuth reauthorization / token provider `action_required`, missing member URN, missing token, and dry-run. There is no automatic retry of a failed real attempt within the same request or via auto-queue; manual re-queue via `POST /queue-linkedin-publication` is the only retry path. Under US-022, manual re-queue of a `failed` variant preserves the stored `linkedin_publication` evidence and records append-only attempt/recovery history (see the US-021/US-022 section below).

**Where operators see preserved URN evidence on re-runs:**

- Publish-phase `results[]` entries carry `linkedin_post_urn` and `published_at` for first publish and for already-published replay (`linkedin_publish_already_published`, zero LinkedIn API calls).
- Under `auto_queue_pending: true`, matching `auto_queue_results[]` entries also carry those fields for published and already-published outcomes (including cross-campaign scan skips with `linkedin_publish_auto_queue_skipped_state`). Entries without publication evidence serialize both fields as `null`.

Metadata and HTTP responses never include tokens, variant body text, or raw API response bodies.

## Publish-time sequence and cadence guard (US-020)

Every publish-due evaluation of a `queued` variant — plain publish-due, the combined `auto_queue_pending` flow, targeted requests, and the cross-campaign scan — enforces a per-campaign guard with two rules:

1. **Sequence rule.** A variant is never published while an earlier variant in the canonical audience sequence (`executive-recruiter` → `engineering-leadership` → `technical-architect` → `short-provocative`) is still awaiting publication (`pending` — including operator-deferred — or `queued` and unpublished).
2. **Cadence rule.** Successful publications within one campaign are separated by a real minimum of 3 days (72 hours), measured against stored `published_at` evidence — not schedule intent. A publish completed earlier in the same request counts, so at most one variant per campaign publishes per run. A campaign with no `published` variants has no cadence constraint.

**Blocking vs releasing states** for an earlier-sequence variant E relative to a later candidate V:

| E's condition | Effect on V |
|---|---|
| `pending` (including operator-deferred) | **Blocks** — defer means "this audience goes later, order preserved" |
| `queued` unpublished (auto- or manually queued) | **Blocks** |
| `published` with valid `published_at` | **Releases** the sequence; `published_at` feeds the cadence rule |
| `published` with missing/invalid `published_at` | **Blocks** the whole campaign with `linkedin_publish_blocked_evidence_invalid` (fail closed) |
| `failed` | **Releases** — never retried automatically; stored failure evidence untouched |
| `cancelled` | **Releases** — operator removed it from the plan |

**Stable reasons** reported per variant, without failing the overall operation and without any `publish_state` change, LinkedIn call, or OAuth call for the blocked variant:

- `linkedin_publish_blocked_sequence` — blocked by the sequence rule at publish time
- `linkedin_publish_blocked_cadence` — blocked by the 72-hour cadence rule
- `linkedin_publish_blocked_evidence_invalid` — a `published` sibling lacks a parsable `published_at`
- `linkedin_publish_auto_queue_skipped_sequence` — auto-queue pre-filter: a due `pending` variant is not queued while an earlier variant awaits publication (visibility only; the publish-time guard is the normative enforcement point)

**`publish_now` scope:** `publish_now: true` bypasses only the ordinary timing gates (`scheduled_at_utc` at auto-queue, `publish_after_utc` at publish). It never bypasses the sequence rule, the cadence rule, the evidence fail-closed rule, supervision exclusions, or a deferred time. Campaign-wide `publish_now` catch-up therefore proceeds at most one variant per campaign per run, 72 hours apart.

**No out-of-order escape hatch:** manually queueing a later-sequence variant via `POST /queue-linkedin-publication` does not bypass the guard — the queue remains an authorization, and the guard blocks the manually queued variant at publish time while an earlier variant is awaiting publication.

**Invalid `published_at` repair:** a `published` variant with missing, empty, or unparsable `published_at` blocks its whole campaign (other campaigns in the scan are unaffected). Repair is a deliberate manual metadata fix in `metadata/campaigns/<campaign-id>.json` — restore the correct UTC ISO8601 `Z` timestamp of the real publication (cross-check the LinkedIn post) and re-run publish-due. The worker never guesses or auto-repairs evidence.

The guard is evaluated per campaign document; campaigns never gate each other in the cross-campaign scan. Dry-run reports planned blocks with the same stable reasons, with zero metadata writes and zero LinkedIn/OAuth calls.

## Retry, recovery classification, and bounded manual retry (US-021 / US-022)

Full normative policy: [linkedin-retry-recovery-classification.md](../operations/linkedin-retry-recovery-classification.md) (US-021 policy defined; US-022 mechanics implemented and unit-tested — not deployed, not operationally validated). Classification is a deterministic function of the stored US-019 evidence (`last_error_code` + `http_status`); `retryable` is descriptive only. Summary:

| Class | Evidence | Recovery |
|---|---|---|
| Recoverable (transient) | `linkedin_publish_api_error` with `http_status` `429` or `>= 500` | Wait, then manual re-queue (no `recovery_confirmation`) |
| Recoverable after remediation | `linkedin_publish_token_invalid`, `linkedin_publish_token_expired` (token renewal first) or `linkedin_publish_insufficient_permission` (scope/product fix + reauthorization first) | Complete the named remediation, then re-queue with `recovery_confirmation: "remediation_completed"` |
| Non-recoverable as-is | `linkedin_publish_content_invalid` (`400`/`422`) | Correct content via `POST /correct-linkedin-variant` (supported for this failed class), then re-queue — never re-queue unchanged content |
| Uncertain (duplicate risk) | `linkedin_publish_api_error` with `http_status` `null` (transport failure) or `201` (success without usable URN); **any unlisted code/status combination fails safe here** | Mandatory LinkedIn verification (below), then re-queue with `recovery_confirmation: "linkedin_post_absence_verified"` |

Blocked outcomes (enablement off, OAuth `action_required`, missing token/URN, US-020 guard blocks, dry-run) are a separate non-failure class: `publish_state` unchanged, no re-queue involved, **no retry attempt consumed** — resolve the named condition and re-run publish-due.

### Retry budget (US-022)

Each variant allows **max 3 real LinkedIn API attempts** (initial + 2 manual retries). Only real API calls count — dry-runs, queue operations, blocked outcomes, corrections, cancellations, and manual evidence repair never consume the budget. The budget is per variant; variants never share a campaign pool. Queue and per-variant publish responses expose `publication_attempt_count`, `manual_retries_used`, and `manual_retries_remaining`; failed-state queue/correction/cancel responses also expose `recovery_classification`. When the budget is exhausted, re-queue fails with `linkedin_publish_retry_limit_exhausted` — cancel the variant or repair evidence manually.

Every real API attempt appends one immutable entry to `linkedin_publication_attempts`; every successful failed-state recovery action (`manual_requeue`, `content_corrected`, `recovery_cancelled`) appends one event to `linkedin_recovery_history`. Re-queue no longer clears `linkedin_publication`. Legacy `failed` variants without attempt history are normalized from their US-019 evidence on the first recovery action; invalid/missing evidence fails closed with `linkedin_publish_recovery_evidence_invalid` (manual metadata repair required).

### Operator steps and HTTP examples per class

All examples default-safe: run first with `"dry_run": true` to preview counters and planned actions with zero mutation; all endpoints require the API key header. `recovery_confirmation` accepts only the two enum values shown (anything else → HTTP 422) and is rejected on pending (non-failed) queue requests.

**Transient (429/5xx)** — wait, then re-queue directly:

```bash
curl -s -X POST http://localhost:8010/queue-linkedin-publication \
  -H "Authorization: Bearer $SILVERMAN_BLOG_LINKEDIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"campaign_id": "<campaign-id>", "variant": "<variant>", "dry_run": false}'
```

**Recoverable after remediation (token/permission)** — first confirm remediation via `GET /linkedin/oauth/status` (renew/reauthorize per the sections above), then:

```bash
curl -s -X POST http://localhost:8010/queue-linkedin-publication \
  -H "Authorization: Bearer $SILVERMAN_BLOG_LINKEDIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"campaign_id": "<campaign-id>", "variant": "<variant>", "dry_run": false,
       "recovery_confirmation": "remediation_completed"}'
```

Omitting the confirmation returns `linkedin_publish_recovery_confirmation_required`; sending it for the wrong class (or on a pending queue) returns `linkedin_publish_recovery_confirmation_invalid`.

**Uncertain (duplicate risk)** — perform the mandatory manual verification first: check the operator LinkedIn profile feed/activity for a matching post within the `last_failed_at` window.

- Post **exists** → re-queue is forbidden (it would create a duplicate that no existing safeguard catches, since no `published_at`/URN evidence was stored). Recovery is deliberate manual evidence repair in `metadata/campaigns/<campaign-id>.json` to `published` with the real URN and UTC `published_at` (same manual-repair pattern as invalid `published_at` under US-020).
- Post **absent** → re-queue with the attestation:

```bash
curl -s -X POST http://localhost:8010/queue-linkedin-publication \
  -H "Authorization: Bearer $SILVERMAN_BLOG_LINKEDIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"campaign_id": "<campaign-id>", "variant": "<variant>", "dry_run": false,
       "recovery_confirmation": "linkedin_post_absence_verified"}'
```

**Content-invalid (400/422)** — correct the content first (allowed on `failed` only for this class; variant stays `failed` and is never auto-queued), then re-queue explicitly without a confirmation:

```bash
curl -s -X POST http://localhost:8010/correct-linkedin-variant \
  -H "Authorization: Bearer $SILVERMAN_BLOG_LINKEDIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"campaign_id": "<campaign-id>", "variant": "<variant>", "dry_run": false,
       "draft_content": "<corrected variant text>"}'

curl -s -X POST http://localhost:8010/queue-linkedin-publication \
  -H "Authorization: Bearer $SILVERMAN_BLOG_LINKEDIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"campaign_id": "<campaign-id>", "variant": "<variant>", "dry_run": false}'
```

Re-queueing without a recorded correction matching the current artifact hash returns `linkedin_publish_content_correction_required`. Correction of a failed variant in any other class is rejected with `linkedin_supervision_action_not_allowed`.

**Cancel a failed variant (any class, including exhausted)** — no LinkedIn call, all evidence preserved:

```bash
curl -s -X POST http://localhost:8010/cancel-linkedin-publication \
  -H "Authorization: Bearer $SILVERMAN_BLOG_LINKEDIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"campaign_id": "<campaign-id>", "variant": "<variant>", "dry_run": false,
       "reason": "retry budget exhausted"}'
```

There is no automatic retry of any kind; manual re-queue remains the only retry path, over existing endpoints only (ADR-0001 HTTP-only boundary). Real publication still requires `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` — the fail-closed guard is unchanged by US-022.

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
