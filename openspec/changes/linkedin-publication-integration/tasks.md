## 1. Configuration and LinkedIn client foundation

- [ ] 1.1 Add env vars to `deploy/server/silverman-worker.env.example`: `SILVERMAN_LINKEDIN_ACCESS_TOKEN`, `SILVERMAN_LINKEDIN_MEMBER_URN` (required), `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES` (default 120), optional `SILVERMAN_LINKEDIN_API_VERSION`
- [ ] 1.2 Implement settings loader validating publication config without logging tokens; require member URN (no `/v2/userinfo` auto-resolve)
- [ ] 1.3 Implement `linkedin_client.py` with injectable HTTP client for member text post (commentary = variant text + blog URL); map 401/403 to stable error classes
- [ ] 1.4 **Apply-time:** Verify exact current LinkedIn Posts API payload schema and required headers against official LinkedIn documentation before coding client

## 2. Publication flow services

- [ ] 2.1 Implement `linkedin_publication_flow.py` with result dataclasses for queue, publish-due, and cancel
- [ ] 2.2 Implement `queue_linkedin_publication(...)`: eligibility, `pending` → `queued`, compute `publish_after_utc` from safety delay or request override; no LinkedIn API
- [ ] 2.3 Implement `publish_linkedin_due_variants(...)`: eligible `queued` variants where `publish_after_utc <= now` or `publish_now`; real API only when enabled
- [ ] 2.4 Implement `cancel_linkedin_publication(...)`: `queued` → `cancelled`; reject `published`
- [ ] 2.5 Implement dry-run paths for all three services (validate only, no state mutation)
- [ ] 2.6 Config errors (missing token, missing URN, not enabled) fail response but MUST NOT set variant `failed`
- [ ] 2.7 Real API failures mark variant `failed` with stable codes and retry metadata
- [ ] 2.8 Do NOT transition campaign state beyond `distribution_scheduled` in v1
- [ ] 2.9 Define stable error code constants matching spec

## 3. HTTP endpoints (all default dry_run: true)

- [ ] 3.1 Add Pydantic models and route `POST /queue-linkedin-publication` (`campaign_id`, `variant`, optional `dry_run`, `safety_delay_minutes`, `publish_after_utc`)
- [ ] 3.2 Add route `POST /publish-linkedin-due-variants` (optional `campaign_id`, `variant`, optional `dry_run`, `publish_now`)
- [ ] 3.3 Add route `POST /cancel-linkedin-publication` (`campaign_id`, `variant`, optional `dry_run`)
- [ ] 3.4 Wire all routes with `Depends(require_api_key)`; ensure responses exclude body text and tokens
- [ ] 3.5 Verify all three paths appear in OpenAPI

## 4. Unit and HTTP tests

- [ ] 4.1 Create `tests/test_linkedin_publication.py` with mocked LinkedIn client
- [ ] 4.2 Test queue: `pending` → `queued`, `publish_after_utc` set, default safety delay 120
- [ ] 4.3 Test publish-due: due variant → `published`; not-yet-due skipped unless `publish_now`
- [ ] 4.4 Test cancel: `queued` → `cancelled`; reject cancel on `published`
- [ ] 4.5 Test config errors do NOT mark variant `failed`
- [ ] 4.6 Test real API failure marks variant `failed`
- [ ] 4.7 Test dry-run defaults (omit `dry_run` → no mutation, no API)
- [ ] 4.8 Test idempotent `published` rerun
- [ ] 4.9 Test eligibility failures (wrong state, missing artifact, hash mismatch)
- [ ] 4.10 Test HTTP auth and 422 for all three endpoints
- [ ] 4.11 Verify no n8n workflow JSON modified; run full `pytest`

## 5. Deployment smoke and evidence

- [ ] 5.1 Add `deploy/server/run-linkedin-publication-smoke.sh` (dry-run default; real mode gated; queue + publish-due + optional cancel)
- [ ] 5.2 Extend `collect-flow-a-smoke-evidence.sh` to display `pending` / `queued` / `published` / `failed` / `cancelled` counts (informational only; Flow A Core PASS unchanged)

## 6. Documentation

- [ ] 6.1 Add `docs/deployment/linkedin-publication-prerequisites.md` (Developer App, token, `w_member_social`, required member URN, two-step queue/publish workflow, safety delay, cancel, personal text post only)
- [ ] 6.2 Document future immediate mode (`SAFETY_DELAY=0` or `publish_now`) and future operator UI (out of scope v1)
- [ ] 6.3 Update README with LinkedIn publication smoke usage and env vars

## 7. Validation

- [ ] 7.1 Run `openspec validate linkedin-publication-integration --strict`
- [ ] 7.2 Run `openspec validate --all`
- [ ] 7.3 Manual dry-run smoke: queue → verify planned `publish_after_utc` → publish-due dry-run (operator step)

## Out of scope (do not implement in apply)

- LinkedIn native scheduling; auto-publish on `scheduled_at_utc` or `publish_after_utc` without HTTP call
- OAuth UI, token refresh, `/v2/userinfo` member URN auto-resolve
- Image upload, company page publishing, rich link/article scheduling
- Campaign `distribution_complete` transition
- n8n workflow JSON changes, activation, cron/webhooks
- Operator review UI
- Commit, push, or archive unless explicitly requested
