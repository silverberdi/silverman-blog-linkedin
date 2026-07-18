## Why

US-040B delivered dual first-class List + Month calendar **visibility** for Flow A blog and LinkedIn schedules, but operators still cannot adjust future unpublished timing from the calendar when they notice conflicts or better windows. US-040C adds **schedule modification** through one shared schedule editor (list, month, and mobile agenda entry points) that reuses LinkedIn US-017 defer/reschedule semantics and adds an explicit authenticated worker API for editorial-calendar updates—without a second mutation SoT, LinkedIn API publish, or public Google auth.

## Goals

- Allow selecting a future unpublished item from Month calendar, mobile agenda, or List and open the **same** schedule editor.
- Preserve existing list edit/defer/reschedule/cancel; calendar schedule actions MUST reuse the same worker semantics (no divergent LinkedIn or calendar mutation SoT).
- Support changing scheduled date/time for **future unpublished** blog and LinkedIn items only; published/historical items remain read-only.
- LinkedIn: reuse/extend existing US-017 `POST /defer-linkedin-variant` pending-variant semantics (not a parallel LinkedIn schedule writer).
- Editorial calendar: explicit authenticated worker API to update canonical `calendar.json` with validation, idempotency, and conflict protection; browser MUST NOT write calendar files.
- Validate against cadence/rescheduling rules (past dates, invalid formats, saturation, duplicate slots, unsupported states)—using approved BL-021 rules when present, otherwise interim rules fixed in this change’s design/spec until BL-021 closes.
- Dry-run visible before real mutation; explicit confirmation for committed schedule changes.
- After success: refresh calendar + list consistently; show previous/new schedule, affected item, and whether related LinkedIn variants changed or remained separate overrides.
- Persist traceable audit (actor/source, timestamp, previous/new value, reason, idempotency key, worker result).
- Do not call LinkedIn publication API or publish blog content as part of schedule edit.
- Keep React + TypeScript + Vite under `frontend/linkedin-variant-supervision-console/`; promote `ScheduleEditor` scaffold; keep CSS-grid calendar; no divergent calendar-mutation UX.
- Preserve US-040A + US-040B; leave BL-015 open; do not mark Story accepted or claim US-040D–E done.

## Non-Goals

- US-040D public URL + Google auth activation.
- US-040E polish beyond what schedule-mutation UX requires.
- BFF, database, user-management, or public hosting.
- LinkedIn API publish; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` bypass; Flow B.
- Rewriting US-040B list + month visibility baseline or inventing a second calendar mutation SoT.
- Closing BL-015 or marking US-040C Story accepted from proposal or apply alone.
- Completing BL-021 as a full product definition (consume / interim cadence-reschedule rules only).

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (US-040C only) | Leave backlog open; A–B preserved; D–E remain |
| **US-040C** | Yes | All acceptance criteria in `docs/product/user-stories.md` |
| **US-040A / US-040B / US-038–US-040** | Preserve | Stack, dual views, schedule-visibility read, list US-017 mutations |
| **US-017** | Consume / additive extend only | Defer/reschedule remains the LinkedIn mutation SoT |
| **BL-021** | Consume / interim | Cadence-reschedule validation; do not close BL-021 |
| **US-040D–US-040E** | Out | Public auth / polish beyond mutation UX |
| **Flow B / BL-016+** | Out | Explicitly excluded |

**US-040C acceptance criteria addressed:** shared schedule editor from month/agenda/list; preserve list actions; future unpublished only / published read-only; LinkedIn reuses US-017; calendar via authenticated worker API (no browser file writes); cadence/reschedule validation; dry-run + confirmation; post-success dual-view refresh + previous/new + related-variant outcome; audit trail; no LinkedIn API / blog publish; understandable outcomes and failures; no unintentional duplication of completed work.

**Intentionally excluded:** US-040D–E; Story accepted / BL-015 closed checkboxes; BFF/DB/public hosting; LinkedIn API publish; Flow B.

## Frontend stack decision (preserve)

**Keep React + TypeScript + Vite** under `frontend/linkedin-variant-supervision-console/`. Promote the existing `ScheduleEditor` scaffold into the shared mutation surface used by List, Month calendar, and mobile agenda. Keep the **CSS-grid** month calendar; do not introduce a second calendar-mutation library or divergent SoT.

## What Changes

- Promote `ScheduleEditor` to a shared editor opened from Month, mobile agenda, and List for eligible future unpublished items.
- Wire calendar/agenda schedule actions to the same mutation path as list defer/reschedule for LinkedIn (`POST /defer-linkedin-variant`), with dry-run default and explicit confirm for real commits.
- Add authenticated worker API for editorial-calendar schedule updates of future unpublished blog items (canonical `calendar.json` via existing atomic save + conflict fingerprint patterns); browser never writes mounts.
- Surface validation failures (past dates, invalid formats, saturation, duplicate slots, unsupported states) with stable codes.
- After real success: coordinated refresh of schedule-visibility + pending-supervision; success banner with previous/new schedule, affected item, and related LinkedIn override outcome (changed vs separate).
- Persist audit fields for both channels; rebuild static console assets into the existing worker-served path.
- Docs progress updates only when US-040C outcomes are demonstrated (not from propose).

## Capabilities

### New Capabilities

_None — US-040C extends the existing supervision console and editorial-calendar contracts rather than inventing a parallel console or calendar product name._

### Modified Capabilities

- `linkedin-variant-supervision-console`: Require shared schedule editor from List / Month / mobile agenda; dry-run + confirmation; dual-view refresh and outcome messaging; preserve US-040B visibility and Stories 1–3 list mutations; defer US-040D–E.
- `editorial-calendar-orchestration`: Add authenticated schedule-update API for future unpublished calendar items with validation, idempotency, conflict protection, dry-run, and audit; reuse atomic calendar persistence; no browser filesystem writes.
- `linkedin-publication-integration`: Additive-only audit/source fields for console-driven defer/reschedule when needed to satisfy US-040C traceability; MUST NOT introduce a second LinkedIn schedule mutation SoT or change pending-only defer eligibility.

## Impact

- **Product:** Advances BL-015 / US-040C; BL-015 remains open; US-040D–E remain unimplemented; US-040A/B baseline preserved.
- **Frontend:** Promote `ScheduleEditor`; open from month/agenda/list; confirmation + dry-run UX; outcome banners; typed client methods for calendar schedule update + existing defer.
- **Worker:** New authenticated calendar schedule-update endpoint (path fixed in design/spec); LinkedIn continues to use US-017 defer (optional additive audit fields); reuse `save_calendar_atomic` / fingerprint conflict protection.
- **APIs:** Browser → worker HTTP only (ADR-0001); no n8n Execute Command; no LinkedIn publish; no blog publish/git as part of schedule edit.
- **Deploy:** Same Vite build → worker static assets; no separate frontend server.
- **Docs:** CURRENT-STATE / progress-checklist / user-stories only when demonstrated at apply time; do not mark Story accepted or BL-015 closed.
- **Tests:** Frontend schedule-editor + dual-view refresh; pytest for calendar schedule update + LinkedIn defer reuse/extensions; secrets audit; no real LinkedIn/DeepSeek/ComfyUI.
- **Preserved:** ADR-0001; dry-run default; enablement display-only; `pending` / `queued` / `cancelled` / `flow_a_complete` ≠ LinkedIn API published; blog handoff ≠ LinkedIn API published; secrets not in source, built assets, logs, or browser storage.
