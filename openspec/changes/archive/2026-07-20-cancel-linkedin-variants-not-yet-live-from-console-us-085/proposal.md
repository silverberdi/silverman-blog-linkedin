## Why

US-083/US-084 delivered honest LinkedIn status, action-availability, and postpone/reschedule for not-Live variants, but cancel from the Silverman Authority Manager console is still incomplete as a control-center command: Scheduled (`pending`) cancel exists mainly as a pending-supervision path, while Waiting to send (`queued`) remains matrix-blocked as “not available yet (US-085)” even though the worker already supports `POST /cancel-linkedin-publication` for queued. US-085 closes that gap so operators can stop a post that is not yet Live on LinkedIn without leaving the console.

## What Changes

- Treat cancel as a **deliberate control-center action** in EventModal for LinkedIn variants that are **not yet Live on LinkedIn**, covering at least:
  - **Scheduled / `pending`** — confirm and wire the existing cancel-pending path as an intentional control (not spectator leftover).
  - **Waiting to send / `queued`** — ship a **working** cancel-queued mutation (supersede US-083/US-084 “not available yet / US-085” matrix carve-out).
- Reuse authenticated `POST /cancel-linkedin-publication` (and existing client `cancelVariant`) — **no** second cancel pipeline, **no** browser filesystem writes.
- Reuse US-083 honesty: real cancel requires explicit confirmation; preview/dry-run cannot be mistaken for a completed cancel.
- After **real** cancel: operator status shows **Cancelled**; publish actions for that variant are no longer offered; **reopen** remains the approved restore path where product already allows it (US-040J).
- Plain-language outcomes and failures/blocked states with a usable next step.
- Preserve US-083/US-084 behavior; keep **BL-015** closed; do **not** implement US-086 publish-now.

## Goals

- Satisfy **all** US-085 acceptance criteria in `docs/product/user-stories.md`.
- Preserve **US-083** honest labels, action matrix honesty (except correctly making cancel-queued available), and preview-vs-real semantics.
- Preserve **US-084** postpone/reschedule for pending + queued; cancel must not be confused with postpone.
- Keep **BL-015** closed; do not reopen supervision-only product scope.
- Prefer extending existing cancel endpoint + EventModal matrix over new routes or pipelines.
- Respect ADR-0001 (n8n → worker HTTP only), `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` fail-closed for publication paths, and secret-safety.
- Confirm worker cancel already accepts `pending` / `queued` (and existing failed recovery cancel where already allowed); change worker only if a gap blocks console AC.

## Non-goals

- **US-086** — Publish now / LinkedIn API publish from the console.
- ADR-0001 bypass; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` bypass for publication.
- Flow B work.
- Reopening **BL-015**.
- Marking US-085 / BL-032 Story accepted by proposal or implementation alone.
- Inventing a second cancel endpoint or unpublish-from-LinkedIn for already Live posts (Live remains non-cancellable via this control; worker already rejects `published`).
- Changing US-040J reopen semantics beyond continuing to use it as the approved restore path after cancel.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `linkedin-variant-supervision-console`: BL-032 / US-085 deliberate cancel for not-Live LinkedIn variants (**pending and queued**); action matrix makes cancel-queued **available** when eligible; explicit confirmation + preview-vs-real honesty; post-real Cancelled status and no publish actions offered; reopen remains restore path; preserve US-083/US-084; BL-015 stays closed; US-086 remains unavailable.
- `linkedin-publication-integration`: affirm / clarify console control-center use of existing `POST /cancel-linkedin-publication` for `pending` and `queued` (no second pipeline); only narrow worker gaps if apply discovers console-blocking defects — do not redesign cancel state machine.

## Impact

- Frontend: `frontend/linkedin-variant-supervision-console/` — EventModal cancel control (pending + queued identity, not pending-supervision-only for queued), action matrix, confirmation/dry-run copy, Vitest, static rebuild into worker assets.
- Worker: prefer **confirm existing** `cancel_linkedin_publication` for pending/queued; pytest only if behavior/docs gaps; no new mutation route preferred.
- Specs: deltas under the two modified capabilities above.
- Docs after implementation (not this proposal commit): `docs/CURRENT-STATE.md` if capability language changes; product progress only when criteria are demonstrated.
- **No** n8n Execute Command; **no** LinkedIn API publish / unpublish from this change.

## Related backlog / stories

- **BL-032** — Turn the LinkedIn Console Into an Operator Control Center
- **US-085** — Cancel LinkedIn Variants That Are Not Yet Live (this change only)
- Predecessors: **US-083** and **US-084** implemented and deployed; apply order US-083 → US-084 → **US-085** → US-086
- Addresses all US-085 acceptance criteria listed in `docs/product/user-stories.md`
- Intentionally excluded: US-086 publish-now, BL-015 reopen, Flow B, Story accepted by code alone
