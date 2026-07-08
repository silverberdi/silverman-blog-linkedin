## Context

Flow A Core is complete and server-validated. A campaign in state `distribution_scheduled` has:

- `source_public_url`, `linkedin_package`, `linkedin_distribution`
- per-variant `scheduled_at_utc` (internal distribution schedule), `publish_state: pending`, artifacts at `linkedin-posts/generated/<campaign_id>/<variant_id>.md`

This child change (umbrella slice 8) adds deferred LinkedIn API integration with a **queue-and-safety-delay** product decision: real publication must not post immediately by default. The operator queues a variant, gets a review window, then explicitly publishes due variants (or cancels).

**Scheduling ownership:** All scheduling is worker-side. `scheduled_at_utc` is our internal distribution calendar. `publish_after_utc` is the safety-delay gate before LinkedIn API call. LinkedIn receives the post only when our worker calls the API — we do not assume LinkedIn native personal-profile scheduling.

**Constraints (unchanged):** HTTP-only n8n boundary; worker owns API calls and metadata; secrets never in responses; no n8n/cron/auto-triggers in this slice.

## Goals / Non-Goals

**Goals:**

- Two-phase publication: queue/authorize, then publish due variants.
- Safety delay default 120 minutes; future immediate mode via config `0` or `publish_now: true`.
- Personal-profile text post: commentary = variant text + blog URL (no image, no company page, no rich link/article scheduling).
- Required `SILVERMAN_LINKEDIN_MEMBER_URN` (no `/v2/userinfo` auto-resolve).
- Config errors do not mark variants `failed`; only real API/content failures do.
- Campaign stays `distribution_scheduled` in v1.
- Cancellation `queued` → `cancelled`.

**Non-Goals:**

- LinkedIn-side scheduling, OAuth UI, token refresh, image upload, company pages.
- n8n changes, cron, auto-publish on `scheduled_at_utc`.
- Campaign `distribution_complete` transition.
- Operator review UI (future; cancel endpoint is v1 escape hatch).

## Decisions

### 1. Two-endpoint model (preferred over single publish)

**Decision:** Three HTTP endpoints:

| Endpoint | Purpose | LinkedIn API |
|----------|---------|--------------|
| `POST /queue-linkedin-publication` | Authorize variant; `pending` → `queued`; set `publish_after_utc` | Never |
| `POST /publish-linkedin-due-variants` | Publish `queued` variants where due (or `publish_now`) | When real-enabled |
| `POST /cancel-linkedin-publication` | `queued` → `cancelled` | Never |

**Rationale:** Clear separation between authorization and execution; safer than a single endpoint that might call LinkedIn immediately.

### 2. Per-variant publish states

**Decision:**

| State | Meaning |
|-------|---------|
| `pending` | Scheduled (Flow A Core); not authorized for LinkedIn API |
| `queued` | Authorized; waiting for `publish_after_utc` |
| `published` | Successfully sent to LinkedIn |
| `failed` | Real LinkedIn API attempt failed (or content rejected) |
| `cancelled` | Operator cancelled before publish |

Transitions: `pending` → `queued` (queue); `queued` → `published` | `failed` (publish-due); `queued` → `cancelled` (cancel); `failed` → `queued` (re-queue retry, optional v1 path via queue from failed).

### 3. Safety delay configuration

**Decision:**

- `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES` — default `120` for this phase.
- Queue endpoint computes `publish_after_utc = max(now + safety_delay, optional publish_after_utc request)` unless request supplies explicit `publish_after_utc`.
- Immediate publish requires **either** safety delay config `0` **or** `publish_now: true` on publish-due endpoint (bypasses `publish_after_utc` check for specified variant(s)).

**Future:** Set env to `0` for immediate mode without redesigning flow.

### 4. Configuration and credentials

**Decision:**

| Variable | Required | Purpose |
|----------|----------|---------|
| `SILVERMAN_LINKEDIN_ACCESS_TOKEN` | Real publish | OAuth token (external) |
| `SILVERMAN_LINKEDIN_MEMBER_URN` | **Yes v1** | Author URN `urn:li:person:{id}` — no auto-resolve |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | Real publish | Must be `true` |
| `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES` | No | Default `120` |
| `SILVERMAN_LINKEDIN_API_VERSION` | No | API version header |

**Config error handling:** Missing token, missing member URN, or publication not enabled → HTTP response fails with stable code; variant `publish_state` MUST NOT change to `failed`.

### 5. LinkedIn post format (v1)

**Decision:** Personal-profile **text post** via LinkedIn REST Posts API. Commentary includes generated variant text and `source_public_url` inline. No image upload, no company page, no rich link/article scheduling payload.

**Apply-time task:** Verify exact current Posts API payload schema and required headers against official LinkedIn docs before implementation.

### 6. Endpoint contracts (all default `dry_run: true`)

**`POST /queue-linkedin-publication`**

```json
{
  "campaign_id": "...",
  "variant": "executive-recruiter",
  "dry_run": true,
  "safety_delay_minutes": 120,
  "publish_after_utc": "2026-07-08T18:00:00Z"
}
```

- Real queue (`dry_run: false`): `pending` → `queued`, set metadata, no LinkedIn API.
- Dry-run: validate eligibility, return planned `publish_after_utc`, no mutation.

**`POST /publish-linkedin-due-variants`**

```json
{
  "campaign_id": "...",
  "variant": "executive-recruiter",
  "dry_run": true,
  "publish_now": false
}
```

- Publishes variants with `publish_state: queued` and `publish_after_utc <= now` (or `publish_now: true`).
- Real publish requires: `dry_run: false`, `PUBLICATION_ENABLED=true`, token, member URN, due variant (unless `publish_now`).

**`POST /cancel-linkedin-publication`**

```json
{
  "campaign_id": "...",
  "variant": "executive-recruiter",
  "dry_run": true
}
```

- Real cancel: `queued` → `cancelled`. Does not affect `published`.

### 7. Per-variant metadata fields

On queue (real): `publish_state: queued`, `publish_after_utc`, `publication_queued_at`, `publication_mode` (e.g. `safety_delay`), `publication_safety_delay_minutes`.

On publish (real success): `publish_state: published`, `published_at`, `linkedin_post_urn`, `linkedin_publication` (safe provider subset).

On publish (real API failure): `publish_state: failed`, `linkedin_publication.last_error_code`, `last_failed_at`, `retryable`.

On cancel: `publish_state: cancelled`, `linkedin_publication.cancelled_at`.

### 8. Campaign state

**Decision:** v1 MUST NOT transition campaign state to `distribution_complete`. Campaign remains `distribution_scheduled`. Only per-variant `publish_state` and publication metadata mutate.

### 9. Module layout

- `linkedin_client.py` — member text post creation; injectable for tests.
- `linkedin_publication_flow.py` — `queue_linkedin_publication`, `publish_linkedin_due_variants`, `cancel_linkedin_publication`; result dataclasses.
- `main.py` — three routes, Pydantic models, API key auth.

### 10. Smoke and evidence (this capability only)

- `deploy/server/run-linkedin-publication-smoke.sh` — dry-run default; exercises queue + publish-due dry-run paths.
- Evidence collector MAY display variant state counts (`pending`, `queued`, `published`, `failed`, `cancelled`) informationally.
- Flow A Core PASS semantics unchanged (`distribution_scheduled` + `linkedin_distribution`).

### 11. Operator escape hatch without UI

Cancel endpoint allows `queued` → `cancelled` before `publish_after_utc`. Operator workflow: queue → review artifact → cancel if needed, or wait and call publish-due when due.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operator forgets to call publish-due | Document manual two-step workflow; future n8n slice |
| Safety delay too short/long | Configurable env + per-request override |
| Accidental immediate publish | Default safety delay 120; `publish_now` explicit |
| Config error marks variant failed | Spec: config errors never set `failed` |
| LinkedIn API drift | Apply-time payload verification task |

## Migration Plan

1. Deploy worker with new endpoints (dry-run only without tokens).
2. Operator sets env vars on server.
3. Dry-run smoke: queue → verify `publish_after_utc` → publish-due dry-run.
4. Real workflow: queue variant → wait safety delay (or cancel) → publish-due with `--real`.
5. Future: n8n orchestration, UI, immediate mode via config.

## Open Questions

- Re-queue from `failed` in v1 (recommend: allow queue from `failed` treating as retry authorization).
- Exact LinkedIn Posts API commentary format — resolved at apply time.
