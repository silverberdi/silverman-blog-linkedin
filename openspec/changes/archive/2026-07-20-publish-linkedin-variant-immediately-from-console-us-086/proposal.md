## Why

US-083/US-084/US-085 delivered honest LinkedIn status, postpone/reschedule, and cancel for not-Live variants, but **publish now** from the Silverman Authority Manager console remains matrix-blocked as “not available yet (US-086).” Operators still need SSH or deploy-script publish-due for a deliberate “sí o sí” send. US-086 closes that gap so an eligible LinkedIn variant can be sent to the LinkedIn API from the console on that action — not a status re-label, not a hidden delay.

## What Changes

- Treat **publish now** as a **deliberate control-center action** in EventModal for eligible not-Live LinkedIn variants, covering at least:
  - **Waiting to send / `queued`** — primary happy path: targeted publish-due with `publish_now: true`.
  - **Scheduled / `pending`** — eligible via the same endpoint using existing `auto_queue_pending: true` + `publish_now: true` (queue then publish in one deliberate action), subject to existing supervision exclusions (including deferred time not bypassed).
- Wire the console through authenticated `POST /publish-linkedin-due-variants` (typed API client) — **no** second publish pipeline, **no** browser filesystem writes, **no** n8n Execute Command.
- Reuse US-083 honesty: dry-run default, mode banner, **explicit confirmation** for real publish; preview MUST NOT be mistaken for **Live on LinkedIn**.
- On **real success**: console shows **Live on LinkedIn** with traceable publication identity (e.g. `linkedin_post_urn`) suitable for operator verification.
- On **block or failure**: plain-language reason (not enabled, cadence, sequence, content/platform failure, etc.) and MUST NOT claim published.
- Supersede US-083/US-085 matrix carve-out “publish_now unavailable / not available yet (US-086)” when eligible + `canMutate`.
- Preserve US-083/US-084/US-085 behavior; keep **BL-015** closed; cancel and postpone remain distinct controls.

## Goals

- Satisfy **all** US-086 acceptance criteria in `docs/product/user-stories.md`.
- Prefer extending existing LinkedIn publication worker endpoints (`publish_now` / publish-due semantics) + EventModal action matrix over new routes.
- Fail closed when `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is off; respect duplicate-publication / once-only safeguards, sequence, and cadence (publish_now bypasses timing gates only).
- Preserve **US-083** honest labels and preview-vs-real; preserve **US-084** postpone and **US-085** cancel as distinct non-regressing controls.
- Keep **BL-015** closed; respect ADR-0001 and secret-safety.
- Update CURRENT-STATE if capability language changes; do **not** mark Story accepted by proposal or implementation alone.

## Non-goals

- Reopening **BL-015**.
- Flow B work.
- Changing cancel (US-085) or postpone (US-084) semantics beyond coexistence beside publish-now.
- Marking US-086 / BL-032 Story accepted by proposal or implementation alone.
- Bypassing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or ADR-0001.
- Inventing a second LinkedIn publish endpoint or browser-side LinkedIn API client.
- Unpublish / edit of already **Live on LinkedIn** posts (Live remains non-target for publish-now).
- Turning routine publish-now into unattended cron/n8n production automation.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `linkedin-variant-supervision-console`: BL-032 / US-086 deliberate **publish now** for eligible not-Live LinkedIn variants (**queued** primary; **pending** via auto-queue+publish_now when product-allowed); action matrix makes `publish_now` **available** when eligible; explicit confirmation + preview-vs-real honesty; post-real Live on LinkedIn + URN; plain-language blocks/failures; preserve US-083/US-084/US-085; BL-015 stays closed.
- `linkedin-publication-integration`: affirm / clarify console control-center use of existing `POST /publish-linkedin-due-variants` with targeted `campaign_id` + `variant`, `publish_now: true`, and `auto_queue_pending` when publishing from Scheduled; no second pipeline; only narrow worker gaps if apply discovers console-blocking defects — do not redesign publish-due state machine, cadence, or once-only safeguards.

## Impact

- Frontend: `frontend/linkedin-variant-supervision-console/` — EventModal publish-now control, action matrix, confirmation/dry-run copy, typed client for publish-due, Vitest, static rebuild into worker assets.
- Worker: prefer **confirm existing** `publish_linkedin_due_variants` / `POST /publish-linkedin-due-variants` for targeted publish_now (and auto_queue_pending for pending); pytest only if behavior/docs gaps; no new mutation route preferred.
- Specs: deltas under the two modified capabilities above.
- Docs after implementation (not this proposal commit): `docs/CURRENT-STATE.md` if capability language changes; product progress only when criteria are demonstrated.
- **No** n8n Execute Command; **no** SSH/deploy-script requirement for the routine happy path once console path ships.

## Related backlog / stories

- **BL-032** — Turn the LinkedIn Console Into an Operator Control Center
- **US-086** — Publish a LinkedIn Variant Immediately From the Console (this change only)
- Predecessors: **US-083**, **US-084**, and **US-085** implemented, synced, archived, and deployed; apply order US-083 → US-084 → US-085 → **US-086**
- Addresses all US-086 acceptance criteria listed in `docs/product/user-stories.md`
- Intentionally excluded: BL-015 reopen, Flow B, cancel/postpone redesign, Story accepted by code alone, enablement / ADR-0001 bypass
