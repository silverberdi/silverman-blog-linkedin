## Why

US-083 delivered honest LinkedIn status and an action-availability matrix, but postpone/reschedule is still a spectator-adjacent ScheduleEditor path: operators can misuse a single lever without a deliberate control-center action, density/cadence refusals are not always actionable in plain language, and after a real change the Week/Month calendar can leave the old slot feeling like operator truth. US-084 is the next BL-032 step so the console commands **when** a LinkedIn variant that is **not yet Live on LinkedIn** — including Scheduled (`pending`) **and** Waiting to send (`queued`) — is eligible to go out.

## What Changes

- Redesign postpone/reschedule as a **deliberate control action** in EventModal / ScheduleEditor (clear intent, preview vs real, not accidental single-lever misuse) while reusing US-083 honesty patterns.
- Extend existing authenticated `POST /defer-linkedin-variant` (+ shared ScheduleEditor) so working postpone/reschedule covers **not-Live** LinkedIn variants including at least:
  - **Scheduled / `pending`** (existing path)
  - **Waiting to send / `queued`** (new working control — not “unavailable / not available yet”)
- After a **real** reschedule, ensure Week/Month calendar placement and the variant’s authoritative `scheduled_at_utc` **agree on the new local time** (no stale old slot as operator truth); refresh from worker reads after commit.
- Preserve US-040K max-2/local-day (and existing cadence/defer validations): refusals MUST be plain language with a usable next step.
- **Live on LinkedIn** remains non-reschedulable. **Cancelled** continues via reopen (US-040J), not this postpone control. **Failed** / in-flight publishing: only if product-honest and schedule-mutable; otherwise plain blocked reason + next step.
- Update console + worker-related specs (defer eligibility, schedule-visibility editability, article-preview delay policy if it still forbids queued defer). BL-015 stays closed. **No** second publication pipeline; **no** LinkedIn API publish from this change.

## Goals

- Satisfy **all** US-084 acceptance criteria in `docs/product/user-stories.md`, including AC1 for not-yet-live variants (**pending and queued**).
- Preserve **US-083** honest labels, action matrix, and preview-vs-real semantics; do not regress them.
- Keep **BL-015** closed; do not reopen supervision-only product scope.
- Prefer extending existing defer + ScheduleEditor / EventModal over new endpoints or pipelines.
- Respect ADR-0001 (n8n → worker HTTP only), `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` fail-closed, and secret-safety.

## Non-goals

- **US-085** — Cancel for waiting-to-send / queued (MAY keep matrix “not available yet” for cancel-queued).
- **US-086** — Publish now / LinkedIn API publish from the console.
- Editorial-calendar write-back as a new SoT for LinkedIn placement (LinkedIn authoritative schedule remains campaign metadata / schedule-visibility).
- Reopening **BL-015**; Flow B work; ADR-0001 or LinkedIn enablement bypass.
- Marking US-084 or BL-032 Story accepted / closed by implementation alone.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `linkedin-variant-supervision-console`: BL-032 / US-084 deliberate postpone/reschedule UX for not-Live LinkedIn variants (**pending and queued**), preview vs real, post-real calendar ↔ authoritative schedule agreement, plain-language density/cadence refusal with next step; supersede US-083 “no postpone redesign” carve-out; preserve US-083 honesty; BL-015 stays closed.
- `linkedin-publication-integration`: extend `POST /defer-linkedin-variant` / defer service to accept `queued` (not only `pending`) with defined queued-reschedule semantics; schedule-visibility `schedule_editable` for queued; dry-run default and idempotency preserved; no LinkedIn API publish.
- `linkedin-distribution-scheduling-model`: update supervised reschedule validation so defer is no longer pending-only (accept `pending` and `queued`; still reject Live / invalid times).
- `linkedin-article-preview-fallback`: update delay-policy language that currently forbids deferring `queued` variants so it aligns with US-084 (defer via existing endpoint is allowed; still not LinkedIn API publish).

## Impact

- Frontend: `frontend/linkedin-variant-supervision-console/` — EventModal postpone/reschedule control, ScheduleEditor, action matrix for queued reschedule available, post-mutation calendar refresh, density/cadence copy, Vitest, static rebuild.
- Worker: extend defer eligibility + schedule-visibility editability for queued; pytest for pending + queued paths; no new mutation route preferred.
- Specs: deltas under the four modified capabilities above.
- Docs after implementation (not this proposal commit): `docs/CURRENT-STATE.md` if capability language changes; product progress only when criteria are demonstrated.
- **No** n8n Execute Command; **no** LinkedIn API publish from console in this change.

## Related backlog / stories

- **BL-032** — Turn the LinkedIn Console Into an Operator Control Center
- **US-084** — Postpone and Reschedule LinkedIn Variants From the Console (this change only)
- Predecessor: **US-083** implemented and deployed; apply order US-083 → **US-084** → US-085 → US-086
- Addresses all US-084 acceptance criteria listed in `docs/product/user-stories.md` (AC1 includes queued)
- Intentionally excluded: US-085 cancel-queued mutation, US-086 publish-now, BL-015 reopen, Flow B
