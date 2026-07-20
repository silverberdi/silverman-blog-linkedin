## Context

BL-015 remains closed as pre-send supervision. US-083 (honest status + action matrix), US-084 (postpone/reschedule for `pending` + `queued`), and US-085 (cancel for not-Live pending + queued) are implemented, synced, archived, and deployed. Today:

- Worker `publish_linkedin_due_variants` / `POST /publish-linkedin-due-variants` already supports targeted `campaign_id` + `variant`, `dry_run` (default `true`), `publish_now` (bypasses `publish_after_utc` / schedule due gates only), `auto_queue_pending` (queue then publish), fail-closed when `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is off, sequence/cadence guards, and once-only / URN evidence preservation.
- Console EventModal action matrix marks **`publish_now` unavailable / “Not available yet (US-086)”** for all not-Live items.
- Console API client has correct / defer / cancel / reopen — **no** typed publish-due client yet.
- Routine “sí o sí” still depends on SSH / deploy-script publish-due, which fails the US-086 happy-path AC.

US-086 is the final BL-032 control-center mutation: deliberate **publish now** from the console.

Constraints: ADR-0001 (HTTP only), fail closed on LinkedIn enablement for real publish, no second publish pipeline, apply order US-083 → US-084 → US-085 → US-086, preserve cancel/postpone as distinct controls.

## Goals / Non-Goals

**Goals:**

- Deliberate **publish now** from the console for eligible not-Live LinkedIn variants so the LinkedIn API send happens on that action.
- Primary eligibility: **Waiting to send / `queued`**. Also **Scheduled / `pending`** via existing `auto_queue_pending: true` + `publish_now: true` when not excluded (deferred future time, cancelled eligibility, etc.).
- Real publish requires explicit confirmation; dry-run default; preview ≠ Live on LinkedIn (US-083 honesty).
- Success: **Live on LinkedIn** + traceable identity (URN from publish response; optional schedule-visibility URN for re-open verification).
- Block/failure: plain-language reason; never claim published.
- Prefer existing `POST /publish-linkedin-due-variants` + EventModal matrix; change worker only if a console-blocking gap appears.
- Preserve US-083/US-084/US-085; keep BL-015 closed.

**Non-Goals:**

- New parallel publish HTTP route or browser LinkedIn API client.
- Unpublish / edit of Live posts; Live remains non-target for publish-now.
- Changing cancel or postpone semantics beyond coexistence.
- Flow B; ADR-0001 / enablement bypass; Story accepted by code alone.
- Reopening BL-015; unattended cron/n8n production activation.

## Decisions

### D1 — Mutation SoT stays `POST /publish-linkedin-due-variants`

- Console publish-now **commits** only via existing authenticated publish-due endpoint (new typed client method, e.g. `publishDueVariant`).
- Request shape for targeted console action:
  - Always: `campaign_id`, `variant`, `dry_run`, `publish_now: true`
  - When operator state is **Waiting to send / `queued`**: `auto_queue_pending: false` (default)
  - When operator state is **Scheduled / `pending`**: `auto_queue_pending: true` so one deliberate action queues then publishes under existing worker semantics
- Dry-run default `true`; real requires explicit confirm (US-083 ConfirmationFlow / `confirmRealMutation("publish_now")` or equivalent).
- Do **not** invent `POST /publish-linkedin-now` or browser mount writes.
- Idempotency / already-published protection unchanged (repeat real publish_now on Live must not duplicate LinkedIn posts).

**Alternatives considered:** Separate console-only publish route — rejected (second pipeline). Queue via `POST /queue-linkedin-publication` then a second publish call from the UI — rejected (two-step UX, race-prone, duplicates worker auto_queue+publish path). Leave pending matrix-blocked forever — rejected (product asks honest eligibility for Scheduled when allowed).

### D2 — Eligibility matrix (honest, not “always available”)

| State | Operator label | Publish now |
|-------|----------------|-------------|
| `queued` | Waiting to send | **Available** when `campaignId` + `variantId` + `canMutate` (and not blocked by known client-side enablement-off banner when `linkedin_publication_enabled` is false — still call worker for authoritative fail-closed on real) |
| `pending` (not deferred-future-excluded) | Scheduled | **Available** when identity + `canMutate`; request uses `auto_queue_pending: true` + `publish_now: true` |
| `pending` deferred with future `scheduled_at_utc` | Scheduled (deferred) | **Unavailable** — plain “deferred time not due; publish now does not bypass a deferred schedule” (worker already skips) |
| `publishing` | Waiting to send / in-flight | **Unavailable** — “send already in progress” |
| `published` / API evidence | Live on LinkedIn | **Unavailable** — already live (non-target) |
| `cancelled` | Cancelled | **Unavailable** — use reopen (US-040J) first |
| `failed` / critical | Failed | **Unavailable** (or blocked with recovery path language) — not primary US-086 happy path; do not invent failed→publish-now recovery UX |

Identity for queued/pending: schedule-visibility `campaignId` / `variantId` (same pattern as US-084/US-085); pending-supervision join not required for publish-now.

### D3 — Enablement, safeguards, and failure honesty

- Real publish MUST fail closed when `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is off (`linkedin_publish_not_enabled` or equivalent). Console SHOULD surface enablement from schedule-visibility / pending-supervision `linkedin_publication_enabled` in the matrix/banner, but worker remains authoritative.
- `publish_now` bypasses **only** ordinary timing gates (`publish_after_utc`, schedule due at auto-queue). It MUST NOT bypass sequence, cadence, evidence fail-closed, supervision exclusions, or deferred time.
- Map worker codes to plain language + usable next step: not enabled, sequence, cadence, evidence invalid, config/credentials, content/platform failure, already published (idempotent), auth/session.
- Preview/dry-run success MUST NOT claim Live on LinkedIn or show a real URN as committed live evidence.

### D4 — Success outcome: Live + URN

- On **real** success for the targeted variant: refresh schedule-visibility (+ pending-supervision as applicable); primary status **Live on LinkedIn**.
- Show traceable publication identity from the publish-due response `results[].linkedin_post_urn` (and/or auto_queue path equivalent) in toast/modal suitable for operator verification.
- If re-opening a Live item later needs URN without the mutation response, apply MAY add optional `linkedin_post_urn` (secret-safe, non-credential) to LinkedIn schedule-visibility items when Live — narrow read-model only; do not invent a second evidence store.

### D5 — Deliberate publish-now UX + matrix

In EventModal for eligible LinkedIn items:

1. Primary **Publish now** affordance when D2 says available.
2. Publish panel: Preview vs real (dry-run default), mode banner, explicit confirmation before real submit; copy states this **sends to LinkedIn API now** (not a status re-label, not postpone, not cancel).
3. Action matrix:
   - `publish_now` **available** when D2 eligible + `canMutate` (supersede “not available yet / US-086”).
   - Cancel (US-085) and postpone (US-084) remain distinct and available under their own eligibility.
4. After real Live refresh: matrix does not offer publish-now as available for that Live item; postpone/cancel remain unavailable for Live per prior stories.

### D6 — Spec supersession

- Console: ADDED US-086 publish-now requirements; MODIFIED US-083 matrix / “unavailable until US-086” scenarios and any US-084/US-085 “MUST NOT implement publish-now” framing so publish-now is a working control when eligible; preserve postpone, cancel, and honesty.
- Publication-integration: ADDED affirmation that console control-center publish-now uses existing publish-due with `publish_now` (+ `auto_queue_pending` for pending); lightly MODIFIED safety boundaries to allow console publish path alongside cancel; do not redesign cadence/once-only.

### D7 — Testing and docs

- Vitest: publish Waiting to send; publish Scheduled (auto_queue+publish_now); preview ≠ Live; real success shows Live + URN; enablement-off / cadence / sequence plain failures; matrix; Live non-target; US-083/US-084/US-085 regressions (cancel + postpone still distinct).
- Pytest: confirm targeted publish_now + auto_queue_pending still pass; add only if new worker/read-model behavior appears (e.g. schedule-visibility URN).
- Rebuild static console assets; CURRENT-STATE after implementation; do not mark Story accepted by code alone.

## Risks / Trade-offs

- **[Risk] Operators confuse preview publish with Live on LinkedIn** → Mitigation: US-083 mode banner + confirmation; preview copy forbids Live claim and URN-as-live.
- **[Risk] Pending publish_now surprises operators by also queuing** → Mitigation: panel copy states Scheduled path authorizes/queues then sends in one deliberate action; still one confirmation.
- **[Risk] Cadence/sequence blocks look like “console broken”** → Mitigation: plain-language mapping + next step (wait / cancel earlier / fix evidence).
- **[Risk] Enablement off still shows Publish now available** → Mitigation: matrix/banner when `linkedin_publication_enabled` false; real always fail-closed at worker.
- **[Risk] Scope creep into failed-recovery publish or unpublish** → Mitigation: D2; tasks gates; Live/failed non-targets.
- **[Risk] Stale “not available yet US-086” tests left behind** → Mitigation: update matrix + Vitest in same change.
- **[Risk] Cross-campaign accidental publish** → Mitigation: always send targeted `campaign_id` + `variant`; never call bare scan from console publish-now.

## Migration Plan

1. Explicit approval of this OpenSpec change → `/opsx-apply`.
2. Confirm worker publish-due targeted paths; add typed console client; EventModal control + matrix; Vitest; optional schedule-visibility URN if needed; pytest if touched; static rebuild.
3. Deploy on explicit approval; controlled validation with enablement respected; operator walkthrough for Story accepted.
4. Rollback: revert deploy/assets; already-published LinkedIn posts remain (once-only); no automatic unpublish.

## Open Questions

- None blocking. Exact microcopy and whether schedule-visibility exposes URN for re-open verification may be refined at apply if AC intent holds (Live + URN on success path is mandatory).
