## Context

BL-015 remains closed as pre-send supervision. US-083 is implemented and deployed (honest operator-language status + EventModal action matrix + preview-vs-real framing). Today LinkedIn schedule mutation goes through shared `ScheduleEditor` → authenticated `POST /defer-linkedin-variant`, which **rejects `queued`** (`linkedin_supervision_variant_not_pending`). Schedule-visibility marks LinkedIn `schedule_editable` only for `pending`. US-084 AC1 requires postpone/reschedule for variants that are **not yet Live on LinkedIn**, which includes Waiting to send (`queued`) — pending-only under-delivers.

Constraints: ADR-0001 (HTTP only), no LinkedIn enablement bypass, no second publication pipeline, apply order US-083 → US-084 → US-085 → US-086.

## Goals / Non-Goals

**Goals:**

- Deliberate postpone/reschedule for **not-Live** LinkedIn items including **Scheduled (`pending`) and Waiting to send (`queued`)**, with unmistakable preview vs real.
- After real commit, Week/Month and authoritative `scheduled_at_utc` agree on the new local time (no stale old slot as operator truth).
- Plain-language density/cadence (and related) refusals with a usable next step (preserve US-040K max-2/local-day).
- Extend existing `POST /defer-linkedin-variant` (+ ScheduleEditor / EventModal); define clear queued-reschedule semantics; preserve US-083; keep BL-015 closed.

**Non-Goals:**

- US-085 cancel-queued mutation; US-086 publish-now / LinkedIn API publish.
- New parallel reschedule HTTP route (prefer extending defer).
- Returning cancelled via postpone (reopen remains US-040J).
- Flow B; ADR-0001 / enablement bypass; Story accepted by code alone.

## Decisions

### D1 — Mutation SoT stays `POST /defer-linkedin-variant` (extended eligibility)

- Console postpone/reschedule **commits** only via existing defer (campaign metadata + deferral history). Browser never writes mounts.
- Wire fields remain `new_scheduled_at_utc` (operator-local picker → UTC at typed client boundary).
- Dry-run default `true`; real requires explicit confirm (US-083 / ConfirmationFlow).
- Idempotency semantics unchanged (same key + identical payload → completed without duplicate history).
- Do **not** invent a parallel “reschedule” HTTP route.

**Alternatives considered:** New `POST /reschedule-linkedin-variant` — rejected (duplicate pipeline). Leave queued blocked — rejected (fails US-084 AC1).

### D2 — Eligibility and queued-reschedule semantics

| State | Operator label (US-083) | US-084 postpone/reschedule |
|-------|-------------------------|----------------------------|
| `pending` | Scheduled | **Working** when `canMutate` (+ schedule-editable) |
| `queued` | Waiting to send | **Working** when `canMutate` (+ schedule-editable) |
| `publishing` (in-flight) | Waiting to send / in-flight | **Unavailable** — plain reason (send already in progress); no defer |
| `published` / API evidence | Live on LinkedIn | **Unavailable** — already live |
| `cancelled` | Cancelled | Not this control — reopen (US-040J) |
| `failed` | Failed | **Unavailable** with plain reason + next step (not schedule-mutable in this story) |

**Queued-reschedule semantics (normative for apply):**

1. **Keep `publish_state` as `queued`** — do **not** return the variant to `pending`. Operator is changing *when* an already-authorized send may run, not withdrawing authorization (cancel remains US-085).
2. Update `scheduled_at_utc` to the new future UTC instant; append `operator_supervision.deferral_history` (previous + new); set `last_action` to `defer` with audit fields (`actor` / `source` as today).
3. **Do not call LinkedIn API.** Publish-due / due evaluation MUST treat the new future `scheduled_at_utc` as **not due** until that time (same “not yet due” gate as today for queued). `publish_now` on publish-due is out of scope for this console story (US-086).
4. **Pending path unchanged in spirit:** still stays `pending`; still sets `auto_queue_eligible` false / pre-queue supervision fields as today; runtime re-evaluation rules for deferred pending remain.
5. **Queued path:** do not force `phase` back to a pending-only pre-queue meaning that implies “not authorized”; keep authorized/`queued` truth while recording defer history. `auto_queue_eligible` may remain false or unchanged for already-queued variants (auto-queue already occurred); must not flip `queued` → `pending`.
6. **Sequence / cadence:** existing US-020 publish-time sequence/cadence guards remain; deferring an earlier-sequence variant to a future time continues to block followers until that earlier variant publishes, fails, or is cancelled. Interim defer cadence/saturation + US-040K density continue to apply to the **new** local day/time for both pending and queued.
7. **Errors:** reject Live / cancelled / failed / in-flight publishing with stable codes + plain console mapping. Prefer keeping `linkedin_supervision_variant_not_pending` for states that remain ineligible (or document additive clarity); queued MUST succeed when otherwise valid (no longer fail solely for being queued).
8. **schedule-visibility:** `schedule_editable` true for LinkedIn `pending` **and** `queued` (not live); block reason for live/cancelled/failed/publishing as applicable.

**Alternatives considered:** Queued defer returns to `pending` — rejected (conflates with withdraw/re-authorize; cancel/reopen territory). Queued-only UI lie without worker change — rejected (false capability).

### D3 — Deliberate control UX (beyond spectator single-lever)

In EventModal for eligible LinkedIn items (`pending` or `queued`):

1. Primary action labeled for intent (e.g. **Postpone / reschedule**).
2. Control shows: current local schedule, new local datetime picker, density cue for target local day, **Preview (no change)** vs **Make real change**.
3. Action matrix: postpone/reschedule **available** for Scheduled and Waiting to send when editable + `canMutate`; cancel-queued and publish-now remain unavailable until US-085/US-086.
4. Blog ScheduleEditor path unchanged except shared preview honesty.

### D4 — Calendar ↔ authoritative schedule agreement after real reschedule

- Authoritative LinkedIn schedule = campaign variant `scheduled_at_utc` via schedule-visibility (and pending-supervision when joined).
- On **successful real** defer (pending or queued): refresh reads into shared model; Week/Month place the chip on the **new** local day/time; previous slot is not operator truth for that identity.
- Preview/dry-run MUST NOT move calendar placement.
- No editorial-calendar write-back as LinkedIn SoT; demote/hide stale secondary join context.

### D5 — Density / cadence refusal: plain language + next step

- Keep client-side US-040K pre-check and worker enforcement for pending **and** queued defer.
- Map density, defer-time-invalid, cadence/saturation, ineligible state, auth to operator sentences + usable next step.
- Never claim LinkedIn API published on defer success or refusal.

### D6 — Spec supersession

- Console: ADDED US-084 requirements; MODIFIED US-083 carve-out and matrix so queued postpone is a working control.
- Worker: MODIFIED defer + supervised reschedule validation + schedule-visibility editability; MODIFIED article-preview fallback delay policy that forbade queued defer.
- Purpose framing: control-center postpone for not-Live (pending+queued); cancel-queued and publish-now still out of scope.

### D7 — Testing and docs

- Vitest: deliberate control; pending + queued real reschedule calendar agreement; preview does not move; density/cadence next step; live/failed/cancelled unavailable; US-083 regressions.
- Pytest: defer accepts queued (keeps queued, updates schedule, dry-run/idempotency); rejects live; schedule-visibility editable for queued; density/cadence still enforced.
- After implementation: CURRENT-STATE if needed; do not mark Story accepted by code alone.

## Risks / Trade-offs

- **[Risk] Queued defer vs article-preview “cannot defer queued” policy** → Mitigation: update `linkedin-article-preview-fallback` in this change; delay = defer endpoint for pending **and** queued.
- **[Risk] Operators confuse postpone-queued with cancel-queued** → Mitigation: copy states postpone changes time only; cancel remains US-085; status stays Waiting to send.
- **[Risk] In-flight `publishing` race** → Mitigation: reject publishing with plain “send already in progress”.
- **[Risk] Sequence blocking surprises after postponing earlier variant** → Mitigation: plain outcome/next-step copy; existing US-020 guards unchanged.
- **[Risk] Scope creep into publish-now / cancel-queued** → Mitigation: tasks gates; no new publish/cancel-queued routes.

## Migration Plan

1. Re-approve corrected OpenSpec change → `/opsx-apply`.
2. Worker defer + schedule-visibility eligibility; pytest.
3. Console deliberate control + matrix + refresh agreement; Vitest; static rebuild.
4. Deploy on explicit approval; operator walkthrough for Story accepted.
5. Rollback: revert deploy/assets; real defer writes remain (no automatic undo).

## Open Questions

- None blocking. Exact microcopy may be refined at apply if AC intent holds. If apply discovers `publish_after_utc` (or equivalent) must move with `scheduled_at_utc` for due gates, update both consistently in the same change without expanding to US-086.
