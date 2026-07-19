## Why

US-040G–J delivered calendar-first Week/Month, EventModal + toasts, operator-local time, and cancelled reopen on the deployed console (`192.168.0.194:8010`), but operators can still stack three or more live publications onto the same local day — including via reopen onto an already-busy day. US-040K (BL-015) adds an interim **max 2 publications per operator-local calendar day** density rule (client + server, fail closed) so the plan cannot look spammy, while leaving full cadence policy to BL-021.

## Goals

- Enforce a **maximum of 2 publications per operator-local calendar day** for items in the live supervision plan (exact inclusion set in design: default intent live planned LinkedIn — and blog if shown; cancelled/published-historical handling specified so counts do not surprise operators).
- Week/Month MUST surface day density (day with 2 looks “full”; conflict attempt understandable before commit).
- Reschedule/defer/reopen (and blog schedule-update when in scope) MUST validate the cap **client-side and server-side**; exceeding 2 fails closed with plain-language messaging (not only `*_saturation` codes).
- Existing days with 3+ items remain visible with a clear fix path (move events), no silent data loss.
- Preserve Week default + Month secondary, EventModal + toasts, local-time (US-040I), cancelled reopen (US-040J), session/`canMutate`, dry-run/confirm, worker HTTP-only (ADR-0001), `*_utc` wire fields.
- Encode Shared UX DoD: Visual DoD (desktop + mobile) + operator walkthrough before Story accepted; Vitest alone insufficient.
- Leave BL-015 open; do not close US-040G/H/I/J Story accepted as a side effect.
- Document K as **interim product policy** that BL-021 MAY later supersede; keep existing interim duplicate-slot + same-UTC-day/72h saturation as additive (not replaced).

## Non-Goals

- Closing **US-040G / US-040H / US-040I / US-040J** Visual DoD / Story accepted — separate operator gates remain open.
- Public URL hosting / Google OIDC / BFF / user-management.
- LinkedIn API publish from the console; bypassing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; Flow B; n8n Execute Command; browser mount writes.
- Full **BL-021** editorial cadence supersession (richer windows, global policy redesign) — K is interim and MAY be superseded later.
- Equating density enforcement with LinkedIn API publish; bare “Flow A complete” language.
- Migrating LinkedIn variant schedules into Postgres; restoring wiped calendar/campaign rows beyond current live state.
- Push / deploy without explicit approval after apply/verify.
- Marking **US-040K Story accepted**, **Acceptance criteria validated**, or **BL-015 closed** from implementation, Vitest, or OpenSpec task checkboxes alone.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (US-040K only) | Remains open until operator-validated completion outcome |
| **US-040K** | Yes | Max 2 publications per operator-local day + density UX |
| **US-040G / H / I / J** | Preserve | Do not regress; do not close their Story-accepted gates |
| **BL-021** | Out (document relationship) | Full cadence home; MAY later supersede K’s interim 2/local-day rule |
| **US-041 / BL-031** | Preserve separation | Postgres editorial calendar SoT ≠ LinkedIn variant campaign metadata schedules |

US-040K acceptance criteria addressed by this change (implementation + evidence gates; Story accepted only after walkthrough):

- Enforce max **2** publications per **operator-local** calendar day for the supervision-plan inclusion set defined in design (default: live planned LinkedIn + blog if shown; cancelled/published-historical rules explicit).
- Week/Month surface day density so a day with 2 looks “full” and a conflict attempt is understandable before commit.
- Reschedule/defer/reopen flows validate client-side and server-side; exceeding 2 fails closed with actionable plain-language messaging.
- Existing days with 3+ items remain visible with a clear path to fix density by moving events (no silent data loss).
- Interim duplicate-slot / 72h sibling rules MAY remain; 2/local-day is additive interim product policy.
- Do not call LinkedIn API publish as part of density enforcement.
- Visual DoD evidence (desktop + mobile) for required scenes; Vitest alone insufficient for Story accepted.
- Operator walkthrough on deployed or agreed preview before Story accepted.
- Failures / blocked states clearly communicated.
- Existing completed work not duplicated or unintentionally changed.

Intentionally excluded: G/H/I/J Story accepted closure, BL-015 closed, BL-021 full cadence, deploy/push, Story accepted from code alone, Google/OIDC, LinkedIn API publish from console.

## What Changes

- Add **cross-plan max-2-per-operator-local-day** density enforcement on worker mutation paths that place or move LinkedIn (and in-scope blog) schedule items: at least `POST /defer-linkedin-variant`, `POST /reopen-linkedin-variant`, and editorial-calendar schedule-update when blog items count toward the shared day.
- Define a stable density error code family (e.g. `*_local_day_density` / equivalent) distinct from interim `*_saturation` / duplicate-slot codes; map to plain language in console toasts/modal (“This day already has 2 publications”).
- Console: Week/Month density cues (full at 2; over-full at 3+ still visible); ScheduleEditor / reopen schedule pick prefers prevention (disable or warn saturated local days) before submit; client-side pre-check aligned with server.
- Specify inclusion/exclusion for density counting (cancelled out; published-historical and blog rules per design) so operators are not surprised.
- Preserve additive interim per-campaign duplicate-slot + same-UTC-day/72h saturation checks; document BL-021 MAY supersede K.
- Update `linkedin-publication-integration` and `linkedin-variant-supervision-console` requirements; Vitest + pytest; rebuild static assets into worker static path.
- Honest CURRENT-STATE / US-040K product status (implemented ≠ Story accepted; Visual DoD + walkthrough gated; BL-015 open; G–J Story accepted still gated).

## Capabilities

### New Capabilities

_(none — density is product policy on existing publication + console capabilities)_

### Modified Capabilities

- `linkedin-publication-integration`: Add max-2-per-operator-local-day density checks (additive to interim duplicate-slot / UTC-day+72h saturation) on defer, reopen, and any other in-scope LinkedIn schedule placement mutations; stable error codes; dry-run validates without mutation; no LinkedIn API call; document interim vs BL-021 relationship.
- `linkedin-variant-supervision-console`: Add Week/Month density surfacing, client-side cap validation on reschedule/defer/reopen (and blog schedule edit when counted), plain-language density errors, grandfathered 3+ day visibility + fix path; US-040K Visual DoD / walkthrough gates; preserve G–J baselines, session/`canMutate`, dry-run/confirm, worker HTTP SoT, local-time, `*_utc` wire fields.

## Impact

- **Product:** Advances BL-015 / US-040K toward anti-spam density supervision; BL-015 stays open; US-040K Story accepted only after Visual DoD + operator walkthrough; does not close US-040G/H/I/J Story accepted.
- **Worker:** Shared local-day density evaluation (operator timezone + UTC schedules); wired into defer/reopen (+ blog schedule-update if in inclusion set); pytest; OpenAPI/error codes; no LinkedIn API call for enforcement.
- **Frontend:** `frontend/linkedin-variant-supervision-console/` — density cues on Week/Month, ScheduleEditor/EventModal/reopen prevention + messaging, error maps, Vitest (~1280/~375), static rebuild into `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`.
- **Ops/docs:** CURRENT-STATE + product status honesty; note interim policy vs BL-021; update supervision mechanics if operator-facing density codes are documented there.
- **Specs:** Deltas under this change; sync later updates main.
- **Lifecycle (approval-gated):** apply → verify → implementation commit → sync → archive → explicit push → explicit deploy → Visual DoD / operator walkthrough → only then Story accepted. No apply until explicit approval of this proposal.

## Lifecycle gates (normative for this change)

1. Explicit user approval of this proposal (and design/specs/tasks) before `/opsx-apply`.
2. `/opsx-verify` after implementation; re-run if post-verify edits.
3. Explicit approval before implementation commit; separate sync and archive commits.
4. Explicit approval before push and before deploy to `192.168.0.194`.
5. Visual DoD (desktop + mobile) + operator walkthrough required before marking US-040K Acceptance criteria validated / Story accepted.
6. Do not mark BL-015 closed or US-040G/H/I/J Story accepted from this change alone.
