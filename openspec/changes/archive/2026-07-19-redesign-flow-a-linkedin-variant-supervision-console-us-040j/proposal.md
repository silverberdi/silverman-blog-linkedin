## Why

US-040G–I delivered calendar-first Week/Month, EventModal + toasts, and operator-local time on the deployed console (`192.168.0.194:8010`), but cancelled LinkedIn variants still appear as mute grey chips with no honest modal path — cancel remains irreversible through existing worker endpoints. US-040J (BL-015) makes cancelled events visually honest and actionable by shipping an approved reopen/reschedule-from-cancelled path over worker HTTP (ADR-0001), so operators understand what/why/what-next instead of “mystery cancelled” UX.

## Goals

- Keep cancelled events **visible** on Week/Month with distinct but calm styling (not alarming like failed/blocked).
- Make the cancelled EventModal answer in plain language: **What is this?** **Why is it cancelled?** **What can I do now?**
- Prefer shipping an approved **reopen/reschedule-from-cancelled** worker HTTP contract (new or extended under OpenSpec) as the business outcome, wired through the console with dry-run default, confirm for real, local-first schedule pick (US-040I), and success toast → editable pending/planned on the calendar.
- If reopen must be temporarily deferred inside the same change, ship an **explicit read-only** cancelled modal — never leave mystery cancelled UX or fake Edit controls.
- Keep cancel from an active event destructive, confirmed, and irreversible except through the new reopen path.
- Preserve Week default + Month secondary, EventModal + toasts, local-time (US-040I), session/`canMutate`, dry-run/confirm, worker HTTP-only, and `*_utc` wire fields unless this change explicitly extends them for reopen.
- Encode Shared UX DoD: Visual DoD (desktop + mobile) + operator walkthrough required before Story accepted; Vitest alone insufficient.
- Leave BL-015 open; do not close US-040G/H/I Story accepted as a side effect; document US-040K (max 2/local day) as follow-up — do not ship K product rules unless a hard dependency appears.

## Non-Goals

- **US-040K** max-2-publications-per-local-day density enforcement (note as follow-up constraint on reopen target days; do not ship K product rules here unless a hard dependency appears).
- Closing **US-040G / US-040H / US-040I** Visual DoD / Story accepted — separate operator gates.
- Public URL hosting / Google OIDC / BFF / user-management.
- LinkedIn API publish from the console; bypassing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; Flow B; n8n Execute Command; browser mount writes.
- Equating cancelled with LinkedIn API published/unpublished; bare “Flow A complete” language.
- Migrating LinkedIn variant schedules into Postgres; restoring wiped calendar/campaign rows beyond current live state.
- Push / deploy without explicit approval after apply/verify.
- Marking **US-040J Story accepted**, **Acceptance criteria validated**, or **BL-015 closed** from implementation, Vitest, or OpenSpec task checkboxes alone.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (US-040J only) | Remains open until operator-validated completion outcome |
| **US-040J** | Yes | Cancelled visibility + honest modal + preferred reopen/reschedule path |
| **US-040G / US-040H / US-040I** | Preserve | Week/Month, EventModal, toasts, local-time; do not regress; do not close their Story-accepted gates |
| **US-040K** | Out (follow-up) | Document density as future constraint on reopen target days; no K product enforcement unless hard dependency |
| **US-041 / BL-031** | Preserve separation | Postgres editorial calendar SoT ≠ LinkedIn variant campaign metadata schedules |

US-040J acceptance criteria addressed by this change (implementation + evidence gates; Story accepted only after walkthrough):

- Cancelled events visible on Week/Month with clear cancelled styling and label.
- Event modal for cancelled items explains cancellation (reason/source/timestamp when available) in operator language; raw codes only in diagnostics.
- Approved reopen/reschedule-from-cancelled via worker HTTP (preferred) OR explicit interim read-only cancelled modal if reopen deferred inside the same change — no mystery cancelled UX.
- Reopened items reappear as editable supervision targets (pending/planned as applicable) and respect dry-run/confirm, local time (US-040I); density limits (US-040K) noted as follow-up.
- Cancel from an active event remains destructive, confirmed, and irreversible except through the new reopen path.
- Visual DoD evidence (desktop + mobile) for required scenes; Vitest alone insufficient for Story accepted.
- Operator walkthrough on deployed or agreed preview before Story accepted.
- Failures / blocked states clearly communicated (failure toast).
- Existing completed work not duplicated or unintentionally changed (no silent bypass of publication guards; no n8n Execute Command).

Intentionally excluded: US-040K density product rules (unless hard dependency), G/H/I Story accepted closure, deploy/push, Story accepted from code alone, Google/OIDC, LinkedIn API publish from console.

## What Changes

- **BREAKING (worker contract):** Introduce an approved `cancelled → pending` reopen/reschedule path (new authenticated POST or explicitly extended existing supervision contract under OpenSpec). Cancel remains irreversible **except** through this path. Prior docs that said cancel is irreversible through existing endpoints are superseded for the reopen-eligible subset defined in design/specs.
- Add reopen service semantics: dry-run default; require future `new_scheduled_at_utc` (US-040I absolute future rules); restore editable `pending` supervision target; audit reopen on `operator_supervision`; no LinkedIn API call; fail closed for ineligible states (e.g. published; failed→cancelled recovery paths out of scope unless design proves otherwise).
- Console: calm cancelled chip treatment on Week/Month; cancelled EventModal answers what/why/what-next; reopen → local ScheduleEditor (or equivalent) → confirm → toast → calendar refresh showing editable pending.
- If reopen is deferred mid-change: ship explicit read-only cancelled modal copy (no fake Edit); still satisfy visibility + honesty ACs.
- Update `linkedin-publication-integration` and `linkedin-variant-supervision-console` requirements; Vitest + pytest for reopen + cancelled UX; rebuild static assets into worker static path.
- Honest CURRENT-STATE / US-040J product status (implemented ≠ Story accepted; Visual DoD + walkthrough gated; BL-015 open; G/H/I Story accepted still gated; K still not delivered).

## Capabilities

### New Capabilities

_(none — cancelled handling and reopen extend existing publication + console capabilities)_

### Modified Capabilities

- `linkedin-publication-integration`: Add approved reopen/reschedule-from-cancelled worker HTTP contract (`cancelled` → editable `pending` with new future schedule), dry-run/idempotency/auth/stable error codes, `operator_supervision` audit, auto-queue eligibility restoration rules, and qualified language (cancelled ≠ LinkedIn API published); supersede “cancel irreversible through existing endpoints” for the reopen-eligible subset.
- `linkedin-variant-supervision-console`: Add calm cancelled Week/Month visibility, cancelled EventModal what/why/what-next copy, reopen/reschedule UX (or explicit interim read-only modal), toast success/failure, US-040J Visual DoD / walkthrough gates; preserve Week/Month/EventModal/toasts/local-time, session/`canMutate`, dry-run/confirm, worker HTTP SoT, and qualified publication language.

## Impact

- **Product:** Advances BL-015 / US-040J toward honest cancelled-event supervision; BL-015 stays open; US-040J Story accepted only after Visual DoD + operator walkthrough; does not close US-040G/H/I Story accepted.
- **Worker:** New or extended authenticated mutation (preferred `POST` reopen/reschedule-from-cancelled) in LinkedIn supervision/publication services; campaign metadata `publish_state` + `operator_supervision` updates; schedule-visibility already surfaces cancelled — may need additive cancellation reason/timestamp fields if missing for modal honesty; pytest coverage; no LinkedIn API call on reopen.
- **Frontend:** `frontend/linkedin-variant-supervision-console/` — cancelled chip styles, EventModal cancelled branch, reopen/ScheduleEditor wiring, error maps, tests, static rebuild into `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`.
- **Ops docs:** Update [linkedin-variant-supervision-mechanics.md](../../../docs/operations/linkedin-variant-supervision-mechanics.md) (and related preview-fallback irreversibility notes where they conflict) to describe the approved reopen path.
- **Specs:** Deltas under this change; sync later updates main.
- **Lifecycle (approval-gated):** apply → verify → implementation commit → sync → archive → explicit push → explicit deploy → Visual DoD / operator walkthrough → only then Story accepted. No apply until explicit approval of this proposal.

## Lifecycle gates (normative for this change)

```text
explicit approval of this proposal
→ /opsx-apply
→ /opsx-verify
→ explicit implementation commit approval
→ /opsx-sync (separate commit)
→ /opsx-archive (separate commit)
→ explicit push approval
→ explicit deploy approval
→ Visual DoD capture + operator walkthrough
→ Story accepted only after walkthrough (BL-015 remains open)
```
