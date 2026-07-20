## Context

BL-015 remains closed as pre-send supervision. US-083 (honest status + action matrix) and US-084 (postpone/reschedule for `pending` + `queued`) are implemented and deployed. Today:

- Worker `cancel_linkedin_publication` / `POST /cancel-linkedin-publication` already transitions **`pending` → `cancelled`**, **`queued` → `cancelled`**, and failed recovery cancel, with dry-run default, no LinkedIn API call, and reject for `published`.
- Console EventModal cancel is wired mainly through **pending-supervision join** (`supervisionItem` + `actions.includes("cancel")`).
- Action matrix marks **`cancel_queued` unavailable / “Not available yet (US-085)”** even though Waiting to send is not Live on LinkedIn.
- Queued items typically lack pending-supervision join, so Cancel is not offered from schedule-visibility alone.

US-085 is the next BL-032 step: deliberate cancel for not-Live variants including **Scheduled** and **Waiting to send**.

Constraints: ADR-0001 (HTTP only), no LinkedIn enablement bypass for publication, no second cancel pipeline, apply order US-083 → US-084 → US-085 → US-086.

## Goals / Non-Goals

**Goals:**

- Deliberate cancel from the console for **not-Live** LinkedIn variants including **Scheduled (`pending`)** and **Waiting to send (`queued`)**.
- Real cancel requires explicit confirmation; preview/dry-run cannot be mistaken for completed cancel (reuse US-083 honesty).
- After real cancel: status **Cancelled**; publish actions no longer offered; **reopen** remains approved restore where already allowed (US-040J).
- Plain-language outcomes/failures with usable next steps.
- Prefer extending existing `POST /cancel-linkedin-publication` + EventModal matrix; confirm worker path; change worker only if a console-blocking gap appears.
- Preserve US-083/US-084; keep BL-015 closed.

**Non-Goals:**

- US-086 publish-now / LinkedIn API publish or unpublish of Live posts.
- New parallel cancel HTTP route.
- Flow B; ADR-0001 / enablement bypass; Story accepted by code alone.
- Reopening BL-015; changing reopen semantics beyond continuing to use US-040J.

## Decisions

### D1 — Mutation SoT stays `POST /cancel-linkedin-publication`

- Console cancel **commits** only via existing authenticated cancel endpoint (typed client `cancelVariant`).
- Dry-run default `true`; real requires explicit confirm (US-083 ConfirmationFlow / `confirmRealMutation("cancel")`).
- Idempotency semantics unchanged.
- Do **not** invent `POST /cancel-linkedin-queued` or browser mount writes.

**Alternatives considered:** New cancel-queued-only route — rejected (duplicate pipeline). Leave queued matrix-blocked — rejected (fails US-085 AC).

### D2 — Identity and eligibility (pending vs queued)

| State | Operator label | US-085 cancel |
|-------|----------------|---------------|
| `pending` (and pending-like deferred/blocked still in supervision window) | Scheduled | **Working** when identity resolvable + `canMutate` (existing supervision join / `actions` cancel when present) |
| `queued` | Waiting to send | **Working** when `campaignId` + `variantId` present on schedule item + `canMutate` (schedule-visibility identity; **no** pending-supervision join required) |
| `publishing` (in-flight) | Waiting to send / in-flight | **Unavailable** — plain “send already in progress”; do not cancel mid-flight from this story unless worker already safely allows and product copy is honest |
| `published` / API evidence | Live on LinkedIn | **Unavailable** — already live; worker `linkedin_publish_cancel_not_allowed` |
| `cancelled` | Cancelled | Not this control — reopen (US-040J) |
| `failed` | Failed | **Out of primary US-085 AC** (AC targets scheduled + waiting-to-send). Existing recovery cancel MAY remain reachable if already product-honest; do not invent a new failed-cancel UX as a US-085 goal |

**Queued cancel identity:** mirror US-084/reopen pattern — use schedule-visibility `campaignId` / `variantId` when pending-supervision join is absent.

**Pending cancel:** keep working path via supervision join; present as deliberate control (same cancel panel family as queued, phase-aware copy).

### D3 — Cancel semantics (worker — confirm, do not redesign)

Normative behavior already in `linkedin-publication-integration` (confirm at apply):

1. `pending` → `cancelled` with `operator_supervision.cancellation.phase` `pre_queue`.
2. `queued` → `cancelled` with phase `post_queue`.
3. Set `auto_queue_eligible` false; preserve evidence; **no LinkedIn API call**.
4. Irreversible except approved reopen for reopen-eligible cancellations.
5. Reject Live / ineligible states with stable codes.

Apply MUST run existing cancel tests and only patch worker if a gap blocks console ACs (for example unexpected auth/enablement coupling). Cancel MUST NOT require LinkedIn publication enablement to succeed (cancel is withdrawal, not publish).

### D4 — Deliberate cancel UX + matrix

In EventModal for eligible LinkedIn items:

1. Primary **Cancel** affordance for Scheduled and Waiting to send when eligible + `canMutate`.
2. Cancel panel: reason optional, Preview vs real (dry-run default), mode banner, explicit confirmation before real submit.
3. Copy must distinguish cancel (withdraw / will not send) from postpone (US-084 keeps Waiting to send / Scheduled with new time).
4. Phase-aware helper: scheduled cancel vs waiting-to-send cancel (never queued LinkedIn API; not unpublish).
5. Action matrix:
   - `cancel_pending` available when pending-like + eligible + `canMutate`.
   - `cancel_queued` **available** when queued + identity + `canMutate` (supersede “not available yet / US-085”).
   - `publish_now` remains unavailable (US-086).
6. After real cancel refresh: primary status **Cancelled**; matrix offers reopen when eligible, not publish-now as available, not cancel again as a pending/queued cancel.

### D5 — Outcomes, failures, next steps

- Reuse / extend `mutationOutcomeToast` and error mapping (`linkedin_publish_cancel_not_allowed`, action-not-allowed, idempotency, 401/422) with plain-language primary text + usable next step.
- Preview success MUST NOT claim Cancelled for real.
- Real success MUST state cancelled / will not send and MUST NOT claim LinkedIn API published or unpublish of a live post.

### D6 — Spec supersession

- Console: ADDED US-085 cancel requirements; MODIFIED US-083 matrix / carve-outs and US-084 “cancel remains not shipped” language so cancel-queued is a working control; preserve postpone and honesty.
- Publication-integration: ADDED (or lightly MODIFIED) affirmation that console control-center cancel for pending+queued uses the existing cancel endpoint; do not redesign cancel state machine. Update any stale “operator review UI out of scope” wording that contradicts the console.

### D7 — Testing and docs

- Vitest: cancel Scheduled; cancel Waiting to send; preview ≠ real; post-real Cancelled + no publish actions; matrix; blocked Live/session; US-083/US-084 regressions.
- Pytest: confirm pending + queued cancel still pass; add only if new worker behavior appears.
- Rebuild static console assets; CURRENT-STATE after implementation; do not mark Story accepted by code alone.

## Risks / Trade-offs

- **[Risk] Operators confuse cancel-queued with postpone-queued** → Mitigation: distinct controls and copy; cancel withdraws; postpone keeps Waiting to send.
- **[Risk] In-flight `publishing` race** → Mitigation: unavailable with plain “send already in progress”; worker reject if attempted.
- **[Risk] Cancel button missing for queued because supervision join required** → Mitigation: D2 schedule-visibility identity path.
- **[Risk] Scope creep into failed-recovery cancel redesign or publish-now** → Mitigation: tasks gates; primary ACs are pending + queued.
- **[Risk] Stale “not available yet US-085” tests/copy left behind** → Mitigation: update matrix + Vitest assertions in same change.

## Migration Plan

1. Explicit approval of this OpenSpec change → `/opsx-apply`.
2. Confirm worker cancel for pending/queued; narrow fixes only if needed; pytest.
3. Console cancel control + matrix + confirmation; Vitest; static rebuild.
4. Deploy on explicit approval; operator walkthrough for Story accepted.
5. Rollback: revert deploy/assets; real cancel writes remain (restore only via reopen where eligible).

## Open Questions

- None blocking. Exact microcopy may be refined at apply if AC intent holds. Failed-state cancel UX remains non-goal unless already reachable without new product inventiveness.
