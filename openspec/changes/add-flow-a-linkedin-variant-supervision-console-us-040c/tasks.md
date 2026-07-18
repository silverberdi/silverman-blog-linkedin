## 1. Worker LinkedIn defer extensions (US-017 reuse)

- [x] 1.1 Accept optional `actor` / `source` on `POST /defer-linkedin-variant` and persist them on the operator_supervision audit surface / deferral_history without changing pending-only defer eligibility (AC: LinkedIn reuse/extend; audit actor/source)
- [x] 1.2 Add interim LinkedIn defer duplicate-slot and same-day/72h saturation validation with stable error codes; dry-run validates without mutation; no LinkedIn API calls (AC: cadence/reschedule validation; no LinkedIn publish)
- [x] 1.3 Pytest: auth, dry-run default, actor/source audit, duplicate/saturation rejects, existing defer happy path unchanged, no calendar.json write on defer (AC: failures communicated; no second LinkedIn SoT)

## 2. Worker editorial calendar schedule-update API

- [x] 2.1 Implement authenticated `POST /editorial-calendar/update-item-schedule` with `item_id`, `new_due_at_utc`, `dry_run` default true, optional reason/idempotency_key/actor/source/expected_calendar_fingerprint (AC: explicit worker calendar API; browser MUST NOT write calendar files)
- [x] 2.2 Enforce eligibility: future unpublished only; reject completed/skipped/failed and past/invalid times with stable codes (AC: future unpublished only; published historical read-only)
- [x] 2.3 Enforce interim blog duplicate-slot / saturation rules; persist via `save_calendar_atomic` with fingerprint conflict → `calendar_completion_concurrent_update` (AC: validation; conflict protection)
- [x] 2.4 Persist schedule-change audit (actor/source, timestamp, previous/new due, reason, idempotency key, worker result) with idempotent replay (AC: traceable audit; idempotency)
- [x] 2.5 Guarantee schedule-update path does not call LinkedIn publish, DeepSeek, ComfyUI, Git, or blog publish/handoff (AC: no LinkedIn API / blog publish on schedule edit)
- [x] 2.6 Pytest: auth rejection, dry-run non-mutation, real atomic update, concurrent fingerprint conflict, unsupported state, past time, duplicate/saturation, idempotent replay, secrets-safe errors (AC: validation + audit + failures)

## 3. Schedule-visibility editability hints (additive)

- [x] 3.1 Extend schedule-visibility (and/or shared mapping) with `schedule_editable` / block reason and optional `calendar_fingerprint` when calendar is readable—without rewriting US-040B visibility baseline fields (AC: preserve US-040B; enable editor gating)
- [x] 3.2 Pytest: editable vs read-only items; fingerprint present when calendar loads; read remains non-mutating (AC: published read-only; visibility preserved)

## 4. Frontend shared ScheduleEditor and client

- [x] 4.1 Promote `ScheduleEditor` into shared mutation UI used by List, Month calendar, and mobile agenda; keep CSS-grid calendar; no divergent mutation SoT UX (AC: same editor from three surfaces; stack preserved)
- [x] 4.2 Extend typed API client for calendar schedule-update + optional actor/source on defer; keep injectable auth; no secrets in source/storage (AC: worker HTTP only; ADR-0001)
- [x] 4.3 Wire eligibility: only future unpublished editable items open commit path; published/historical read-only (AC: future unpublished only)
- [x] 4.4 Preserve list edit/defer/reschedule/cancel; calendar/agenda LinkedIn schedule commits call `POST /defer-linkedin-variant` only (AC: preserve list actions; reuse worker semantics)
- [x] 4.5 Dry-run visible by default; explicit confirmation for real schedule commits via existing confirmation flow (AC: dry-run + confirmation)
- [x] 4.6 After real success: refresh schedule-visibility + pending-supervision; show previous/new schedule, affected item, and related LinkedIn variants changed vs separate overrides (AC: dual-view refresh + outcome messaging)
- [x] 4.7 Map calendar and LinkedIn schedule failure codes to operator-visible errors without silent success (AC: failures clearly communicated)

## 5. Frontend and worker verification

- [x] 5.1 Vitest: ScheduleEditor entry from list/month/agenda, dry-run vs confirm, read-only published items, dual-view refresh messaging, error mapping (AC: frontend validation for mutation UX)
- [x] 5.2 Desktop + mobile viewport checks covering schedule editor opened from month and agenda (AC: usable on phone/laptop for mutation path; US-040E polish beyond this not required)
- [x] 5.3 Rebuild static assets into worker static path; console route still serves SPA; secrets audit on source + built assets passes (AC: static serving; secrets)
- [x] 5.4 Run targeted pytest for calendar schedule-update, defer extensions, schedule-visibility hints, and existing pending-supervision/console tests; run frontend test/build; fix warnings attributable to this change; run `git diff --check`
- [x] 5.5 Verify no BFF/DB/user-mgmt/public hosting, no LinkedIn API publish on schedule edit, no enablement bypass, no n8n Execute Command, no browser mount writes, and US-040D–US-040E not implemented (AC: non-goals)

## 6. Docs and business progress (demonstrated only)

- [x] 6.1 Update `docs/CURRENT-STATE.md` for US-040C schedule mutation (calendar API + shared editor; US-040A/B preserved; US-040D–E not done; not Story accepted; not BL-015 closed; BL-021 interim rules noted)
- [x] 6.2 Update `docs/product/progress-checklist.md` US-040C marks only for criteria actually demonstrated (do not mark Story accepted or BL-015 closed from apply alone)
- [x] 6.3 Update `docs/product/user-stories.md` US-040C acceptance checkboxes only when each criterion is demonstrated with evidence
- [x] 6.4 Final business-validation pass against US-040C acceptance criteria in `docs/product/user-stories.md`: shared editor from month/agenda/list; list actions preserved; future unpublished only; LinkedIn US-017 reuse; calendar worker API with validation/idempotency/conflict; cadence rules; dry-run + confirm; dual-view refresh + previous/new + related-variant outcome; audit; no LinkedIn/blog publish; understandable outcomes/failures; no unintentional duplication of US-040A/B / US-040D–E / Flow B
