## 1. Worker schedule-visibility read

- [x] 1.1 Add authenticated read-only `GET /flow-a/schedule-visibility` (or design-equivalent fixed path) aggregating Flow A blog calendar items + LinkedIn variant schedules for a requested month/range without mutating files or calling LinkedIn/DeepSeek/ComfyUI/Git (AC: worker HTTP SoT; ADR-0001)
- [x] 1.2 Return secret-safe `items[]` with channel, campaign/variant ids where available, title/label, audience, `scheduled_at_utc`, operator-facing publication display state, source/raw state, blocked/critical indicators, and `issues[]` for partial reads (AC: correct day fields; state distinction; partial warnings)
- [x] 1.3 Map display states (planned/pending/queued/published/deferred/cancelled/blocked/failed) without inventing new LinkedIn `publish_state` values and without equating `pending`/`queued`/`flow_a_complete`/blog handoff/`completed` with LinkedIn API published (AC: qualified language)
- [x] 1.4 Keep `GET /flow-a/linkedin-variants/pending-supervision` and US-017 POSTs unchanged for list mutations (AC: preserve Stories 1–3; no new mutation SoT)
- [x] 1.5 Add pytest coverage for auth rejection, happy path blog+LinkedIn items, calendar missing/partial issues, month windowing, and non-mutation idempotency of reads (AC: failures communicated; existing work not broken)

## 2. Shared model, API client, and store

- [x] 2.1 Extend typed API client with schedule-visibility GET + types/error mapping; keep injectable auth; no secrets in source/storage (AC: typed client; worker HTTP only)
- [x] 2.2 Extend shared normalized model so List and Month calendar share stable ids, labels, status colors, schedule, channel, and actions (pending LinkedIn only) with no divergent caches (AC: cross-view recognizability)
- [x] 2.3 Extend store with filters, selected campaign/item, month cursor, selected day, dry-run, unsaved schedule-draft flag, and coordinated refresh of pending + schedule-visibility after real list mutations (AC: dual-view consistency; switcher context)

## 3. Filters and view switcher

- [x] 3.1 Implement `Filters` for channel, campaign, publication state, blocked, and due-soon; apply the same filter selection to both List and Month calendar (AC: consistent filters)
- [x] 3.2 Add discoverability for filtered-out critical failures (count, warning, and/or show-critical/reset affordance) so failures are never hidden silently (AC: discoverable critical failures)
- [x] 3.3 Harden persistent desktop/mobile view switcher so switching does not clear filters, selected campaign context, dry-run, or unsaved schedule drafts without warning/confirm (AC: switcher persistence)

## 4. Month calendar and mobile visibility UX

- [x] 4.1 Implement full `MonthCalendarView`: current month, prev/next, today marker, selected-day, empty-day states, dark theme, readable contrast, mobile touch targets (AC: month UX; dark theme)
- [x] 4.2 Place blog and LinkedIn schedule items on the correct UTC-bucketed day with title/label, campaign id, variant id, audience, channel, publication state, and scheduled time (AC: day placement fields)
- [x] 4.3 Show stored UTC plus operator-local interpretation; document UTC day-bucketing in UI/helper copy (AC: timezone handling)
- [x] 4.4 Mobile: stacked list rows/cards; calendar agenda-style day expansion (or equivalent) instead of forced horizontal table scrolling (AC: mobile layouts)
- [x] 4.5 Prefer CSS grid month layout; if any production calendar dependency is added, justify it in the frontend README (AC: small deps; stack preserved)
- [x] 4.6 Ensure List remains first-class with Stories 1–3 detail/actions; calendar remains visibility-only (no US-040C schedule writes) (AC: dual first-class; no calendar mutation SoT)

## 5. Frontend and worker verification

- [x] 5.1 Add Vitest coverage for calendar navigation/day placement/empty states, filter consistency across views, and shared-model identity across List + calendar (AC: frontend validation calendar/filters/dual-view)
- [x] 5.2 Add desktop and mobile viewport validation evidence for List + Month calendar (including agenda expansion) (AC: desktop + mobile viewports)
- [x] 5.3 Rebuild static assets into worker static path; confirm console route still serves SPA; secrets audit on source + built assets passes (AC: static serving; secrets)
- [x] 5.4 Run targeted pytest for schedule-visibility + existing pending-supervision/console tests; run frontend test/build; fix warnings attributable to this change; run `git diff --check`
- [x] 5.5 Verify no BFF/DB/user-mgmt/public hosting, no LinkedIn API publish calls, no enablement bypass, no n8n Execute Command, no browser mount-path reads, and US-040C–US-040E not implemented (AC: non-goals)

## 6. Docs and business progress (demonstrated only)

- [x] 6.1 Update `docs/CURRENT-STATE.md` for US-040B list+month visibility (schedule-visibility read; dual first-class views; filters; US-040C–US-040E still not implemented; not Story accepted / not BL-015 closed)
- [x] 6.2 Update `docs/product/progress-checklist.md` US-040B marks only for criteria actually demonstrated (do not mark Story accepted or BL-015 closed from apply alone)
- [x] 6.3 Update `docs/product/user-stories.md` US-040B acceptance checkboxes only when each criterion is demonstrated with evidence
- [x] 6.4 Final business-validation pass against US-040B acceptance criteria in `docs/product/user-stories.md`: confirm dual views, switcher persistence, month UX, day placement, state distinction, shared-model recognizability, filters + discoverability, timezones, mobile patterns, dark theme, worker HTTP only, understandable outcomes/failures, and no unintentional duplication of US-040A / US-040C–E / Flow B
