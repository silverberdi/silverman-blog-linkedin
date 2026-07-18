## Why

US-040A delivered a maintainable React + TypeScript + Vite Flow A supervision console with a first-class list and only scaffolds for month calendar, filters, and shared-model wiring. Operators still cannot inspect **what publishes each day** across blog and LinkedIn from laptop or phone without raw files. US-040B adds **list + month schedule visibility** on that same console—additive, dual first-class views—without schedule mutations (US-040C), public Google auth (US-040D), or polish beyond visibility (US-040E).

## Goals

- Provide two first-class views (`List` and `Month calendar`); neither replaces, hides permanently, or weakens the other.
- Preserve list as the detail-heavy operational surface for pending LinkedIn variants (Stories 1–3 fields and US-017 edit/defer/cancel).
- Ship a persistent desktop/mobile view switcher that MUST NOT clear filters, selected campaign context, dry-run mode, or unsaved schedule edits without warning.
- Deliver full month calendar UX: current month, prev/next, today marker, selected-day, empty-day states; dark theme; readable contrast; mobile touch targets.
- Place scheduled Flow A blog posts and LinkedIn variants on the correct calendar day with title/campaign label, campaign id, variant id (when applicable), audience, channel, publication state, and scheduled time.
- Distinguish planned, pending, queued, published, deferred, cancelled, blocked, and failed without implying `pending`/`queued` are LinkedIn API published.
- Keep the same item recognizable across list + calendar via stable ids/labels/status colors/fields from one shared normalized model (extend worker reads if needed; no divergent caches).
- Apply channel, campaign, publication-state, blocked, and due-soon filters consistently to both views; keep hidden critical failures discoverable.
- Handle timezones explicitly (stored UTC + useful operator-local interpretation).
- Mobile: stacked list rows/cards; calendar agenda-style day expansion (or equivalent) instead of forced horizontal table scrolling.
- Read data via worker HTTP only (ADR-0001); no browser filesystem/path reads.
- Frontend validation for calendar UX, filters, dual-view consistency, and desktop + mobile viewports.
- Update CURRENT-STATE / progress-checklist / user-stories only for demonstrated US-040B progress when later applied—do not mark Story accepted or BL-015 closed from propose or apply alone.

## Non-Goals

- US-040C schedule mutations from calendar / new calendar mutation SoT / editorial calendar write-back.
- US-040D public URL + Google auth activation (keep injectable-auth boundary; do not activate).
- US-040E polish beyond what visibility UX requires (at-a-glance counts may be thin if needed for filters/discoverability only).
- BFF, database, user-management, public hosting, or a second frontend app/server.
- New mutation endpoints that duplicate US-017; LinkedIn API publish; enablement bypass; n8n Execute Command; Flow B.
- Rewriting the worker publication pipeline or claiming US-040A incomplete.
- Claiming **US-040B Story accepted** or **BL-015 closed** from proposal or apply alone.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-015** | Partial (US-040B only) | Leave backlog open; A demonstrated; C–E remain |
| **US-040B** | Yes | All acceptance criteria in `docs/product/user-stories.md` |
| **US-040A / US-038–US-040** | Preserve | React/Vite console, list + US-017 mutations, route, dry-run, qualified language |
| **US-017** | Consume only | No contract rewrite; list mutations unchanged |
| **US-040C–US-040E** | Out | Visibility only; no calendar mutation / public auth / polish beyond visibility |
| **Flow B / BL-016+** | Out | Explicitly excluded |

**US-040B acceptance criteria addressed:** dual first-class List + Month views; persistent switcher without silent context loss; full month UX; blog + LinkedIn items on correct days with required fields; state distinction without false “published”; cross-view recognizability; blocking/partial warnings; consistent filters with discoverable hidden failures; explicit timezone handling; mobile list + agenda patterns; dark theme; worker HTTP only; understandable outcomes and failures; no unintentional duplication of completed work.

**Intentionally excluded:** calendar schedule writes (US-040C); Google/public auth (US-040D); full US-040E polish; Story accepted / BL-015 closed checkboxes.

## Frontend stack decision (preserve)

**Keep React + TypeScript + Vite** under `frontend/linkedin-variant-supervision-console/`. Prefer extending existing scaffolds (`MonthCalendarView`, `Filters`, `ViewSwitcher`, shared `SupervisionItem` / store) rather than a second app.

**Calendar UI library:** Allowed only if small and justified in proposal/README during apply. Default preference: **pure CSS grid month layout** (no new production dependency) unless a minimal date-math helper is required for correctness; document any production dependency addition in the frontend README.

## What Changes

- Promote month calendar from scaffold to a first-class dark, responsive month view with navigation, today/selected/empty states, and day placement of schedule items.
- Extend the shared normalized frontend model (and worker read path as needed) so calendar can show **blog** editorial-calendar items and **LinkedIn** variants across operator-facing publication states—not only `pending` LinkedIn rows—while list remains the detail-heavy pending-supervision surface.
- Implement real `Filters` (channel, campaign, publication state, blocked, due-soon) applied to both views with a discoverability affordance for filtered-out critical failures.
- Harden view switching so filters, selected campaign context, dry-run, and unsaved schedule-edit drafts survive switches (or warn before discard).
- Display schedules as stored UTC plus operator-local interpretation where useful.
- Mobile layouts: stacked list; agenda-style day expansion for calendar.
- Frontend tests covering calendar UX, filter consistency, dual-view identity, desktop + mobile viewports; rebuild static assets into the existing worker-served path.
- Docs progress updates only when US-040B outcomes are demonstrated (not from propose).

## Capabilities

### New Capabilities

_None — US-040B extends the existing supervision console capability rather than inventing a parallel console name._

### Modified Capabilities

- `linkedin-variant-supervision-console`: Require dual first-class List + Month calendar visibility; full month UX; shared-model schedule items for blog + LinkedIn with qualified publication-state display; consistent filters; explicit timezone presentation; mobile agenda/list patterns; worker HTTP reads only (extend aggregation reads if needed); preserve US-040A stack delivery and Stories 1–3 list mutations; defer US-040C–US-040E.

## Impact

- **Product:** Advances BL-015 / US-040B; BL-015 remains open; US-040C–US-040E remain unimplemented; US-040A baseline preserved.
- **Frontend:** Fill calendar/filters/view-switcher scaffolds; extend shared model/store; optional small date helper only if justified; dark theme CSS for month + mobile agenda.
- **Worker:** Likely a **thin read-only aggregation extension** (new GET or expanded existing read) so month view can include editorial calendar blog items and non-pending LinkedIn variant states without browser filesystem access. **No** US-017 mutation changes; **no** calendar write-back; **no** publication-guard changes.
- **APIs:** Consume existing pending-supervision + US-017 POSTs for list; add/extend authenticated read-only schedule-visibility data for calendar (design decides exact shape).
- **Deploy:** Same Vite build → worker static assets; build-before-deploy unchanged; no separate frontend server.
- **Docs:** CURRENT-STATE / progress-checklist / user-stories only when demonstrated at apply time.
- **Tests:** Frontend calendar/filters/dual-view/viewport; Python tests for any new/extended read aggregation + secrets audit; no real LinkedIn/DeepSeek/ComfyUI.
- **Preserved:** ADR-0001; dry-run default; real-mutation confirmation; enablement display-only; `pending` / `queued` / `cancelled` / `flow_a_complete` ≠ LinkedIn API published; secrets not in source, built assets, logs, or browser storage; Flow B deferred.
