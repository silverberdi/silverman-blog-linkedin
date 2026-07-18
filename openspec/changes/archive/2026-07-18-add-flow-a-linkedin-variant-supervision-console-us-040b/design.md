## Context

US-040A delivered the Flow A LinkedIn variant supervision console as React + TypeScript + Vite under `frontend/linkedin-variant-supervision-console/`, served by the worker at `GET /flow-a/console/linkedin-variant-supervision`. Baseline includes:

- First-class `ListView` with Stories 1–3 edit/defer/cancel via US-017
- Typed injectable-auth API client + shared `SupervisionItem` / store
- Scaffolds only for `MonthCalendarView`, `Filters`, `ItemDetail`, `ScheduleEditor`, `StatusSummary`
- Dry-run default, real-mutation confirmation, enablement display-only, qualified language
- Read SoT for list: `GET /flow-a/linkedin-variants/pending-supervision` (pending LinkedIn variants only)

US-040B (BL-015) must make **List** and **Month calendar** dual first-class visibility surfaces so operators can see scheduled Flow A **blog** posts and **LinkedIn** variants by day from laptop or phone—without raw mount inspection, without calendar mutations (US-040C), and without public Google auth (US-040D).

**Constraints:** ADR-0001 (browser → worker HTTP only); no BFF/DB/user-management; no separate frontend server; secrets never in source, built assets, logs, or browser storage; `pending` / `queued` / `cancelled` / `flow_a_complete` ≠ LinkedIn API published; blog calendar `completed` ≠ site live unless separately evidenced.

## Goals / Non-Goals

**Goals:**

- Dual first-class List + Month calendar with persistent switcher that preserves filters, selected campaign context, dry-run, and unsaved schedule-edit drafts (or warns).
- Full month UX (nav, today, selected day, empty days) + dark theme + mobile agenda expansion.
- Place blog + LinkedIn schedule items on correct days with required identity/state/time fields.
- One shared normalized model (extend worker reads as needed); consistent filters; explicit UTC + operator-local times.
- Preserve list mutation parity and US-040A stack/serving.

**Non-Goals:**

- Calendar or editorial-calendar write-back; new mutation SoT (US-040C).
- Public URL / Google auth activation (US-040D).
- Full US-040E polish beyond visibility needs.
- LinkedIn API publish, enablement bypass, n8n Execute Command, Flow B, second frontend app.

## Decisions

### D1 — Keep React + TypeScript + Vite; extend scaffolds in place

**Choice:** Implement US-040B inside `frontend/linkedin-variant-supervision-console/` by promoting existing scaffolds. Do not create a second app or rewrite the list/mutation path.

**Why:** US-040A already established stack, route, static serving, typed client, and shared store. Smallest coherent diff.

**Alternatives considered:** New calendar-only microfrontend — rejected (divergent caches, dual deploy). Rewrite list into calendar-primary — rejected (AC requires list preserved as first-class).

### D2 — Calendar rendering: CSS grid first; library only if justified

**Choice:** Default to a **pure CSS grid** month layout plus small local date helpers (UTC day-key bucketing, month navigation). Add a production calendar library **only** if apply proves date-grid edge cases (DST, locale week-start) cannot be handled safely with a tiny helper; if added, document justification in the frontend README and keep the dependency small.

**Why:** Matches US-040A “keep deps small” and the user’s stack decision. Month visibility does not need drag-resize or event mutation widgets (those are US-040C).

**Alternatives considered:** FullCalendar / React Big Calendar — useful for complex interactions but overweight for read-only month visibility and risk of implying mutation UX.

### D3 — Schedule-visibility read aggregation (worker HTTP)

**Choice:** Add a thin authenticated **read-only** aggregation endpoint dedicated to console schedule visibility, e.g.:

`GET /flow-a/schedule-visibility`

(Exact path may be `GET /flow-a/linkedin-variants/schedule-visibility` if naming consistency is preferred at apply time; one stable path MUST be documented in the delta spec and client.)

**Response intent (normative shape refined in specs):**

- `status` / `observed_at_utc` / `read_only: true`
- `issues[]` (partial calendar/campaign/draft reads; secret-safe)
- `items[]` where each item includes at least:
  - stable `item_id` (or composable key)
  - `channel` (`blog` | `linkedin`)
  - `campaign_id` (nullable when unknown)
  - `variant_id` (nullable for blog)
  - title or campaign label
  - `audience` (nullable)
  - `scheduled_at_utc` (ISO-8601 UTC; blog uses calendar `due_at_utc`; LinkedIn uses variant `scheduled_at_utc`)
  - `publication_state` (operator-facing display enum — see D4)
  - `source_state` (raw calendar status or LinkedIn `publish_state` / supervision flags for diagnostics)
  - `blocked` / critical-failure indicators when applicable
  - `linkedin_api_published` boolean **false** unless true LinkedIn API published evidence exists (never infer from `pending`/`queued`/`flow_a_complete`)

**Sources (server-side only):**

| Channel | Primary source | Notes |
|---------|----------------|-------|
| Blog | `editorial-calendar/calendar.json` items | Map calendar statuses into display states; do not claim site live from `completed` alone |
| LinkedIn | Campaign `variants[]` (+ calendar join when available) | Include pending, queued, published, cancelled, failed, and deferred-context pending rows; reuse secret-safe integration-failure patterns from pending-supervision |

**List path unchanged:** `GET /flow-a/linkedin-variants/pending-supervision` remains the SoT for pending rows and list mutations. Schedule-visibility MAY overlap pending LinkedIn rows; the frontend MUST normalize both into one shared model store so identity/state/schedule cannot diverge.

**Why not only pending-supervision?** It intentionally returns only `publish_state=pending` LinkedIn variants and cannot satisfy “blog posts + planned/queued/published/…” month visibility.

**Why not browser-compose `GET /editorial-calendar/status`?** Status returns counts only, not per-item schedule rows. `plan-due` is planner-oriented and mutates nothing but is the wrong semantic for “show the month.” A dedicated read aggregation keeps ADR-0001 and avoids filesystem access from the browser.

**Alternatives considered:**

| Alternative | Why not |
|-------------|---------|
| Expand pending-supervision to all states/channels | Breaks Story 1–3 “pending window” semantics and confuses mutation eligibility |
| Client reads raw calendar via static file route | Violates ADR-0001 / AC (no browser mount reads) |
| Reuse only plan-due | Due-only subset; wrong operator month view |

### D4 — Operator-facing publication states (display mapping)

**Choice:** Define a **display** vocabulary used by both views (colors/labels), mapped from existing sources **without inventing new worker `publish_state` values**:

| Display state | Typical sources (examples) | Must NOT imply |
|---------------|----------------------------|----------------|
| `planned` | Calendar `planned` / future `scheduled` blog items | LinkedIn API published |
| `pending` | LinkedIn `publish_state=pending` | LinkedIn API published |
| `queued` | LinkedIn `publish_state=queued` | LinkedIn API published |
| `published` | LinkedIn `publish_state=published` (API evidence) | Blog handoff/`flow_a_complete` alone |
| `deferred` | Pending + operator defer / `auto_queue_eligible=false` | Cancelled or API published |
| `cancelled` | LinkedIn `publish_state=cancelled` | API published |
| `blocked` | Enablement-off context on actionable items, or explicit block flags surfaced by aggregation | Silent hide of the item |
| `failed` | LinkedIn `failed`, calendar `failed`, integration-failure siblings | Success |

Blog calendar `completed` MUST map to a non-misleading label (e.g. display as planned/completed-handoff context distinct from LinkedIn `published`) and MUST NOT be labeled LinkedIn API published. Exact blog completed label copy is an apply detail; qualified language is mandatory.

### D5 — Shared normalized frontend model

**Choice:** Extend the shared model (evolve `SupervisionItem` → or introduce `ScheduleItem` that SupervisionItem embeds/aliases) so every visible row/chip shares:

- Stable identity: LinkedIn = `campaign_id` + `variant_id`; Blog = `calendar_item_id` (and `campaign_id` when present)
- `channel`, display `publication_state`, `scheduled_at_utc`, title/label, audience
- Status color token keyed by display state
- `actions` only for pending LinkedIn (edit/defer/cancel); empty/read-only for blog and non-pending LinkedIn in US-040B

**Store:** One React store/context (extend `SupervisionStoreProvider`) holding:

1. Pending snapshot (list + mutations) from pending-supervision
2. Schedule-visibility items from the new GET
3. UI state: `activeView`, filters, selected campaign/item, dry-run, month cursor, selected day, unsaved schedule-edit draft flag

Calendar and list selectors MUST derive from this store—**no divergent per-view caches**. After successful real list mutations, refresh **both** pending and schedule-visibility reads (or a coordinated refresh helper).

### D6 — View switcher persistence

**Choice:** Persistent control in `AppShell` / `ViewSwitcher` for desktop and mobile. Switching List ↔ Calendar MUST keep filters, selected campaign context, dry-run mode, and month cursor. If an unsaved schedule-edit draft exists (list defer form / schedule editor scaffold draft), switching MUST warn and require confirm before discard (US-040B visibility; full schedule editor commit remains US-040C).

### D7 — Filters apply to both views

**Choice:** Implement `Filters` for:

- Channel (`blog` / `linkedin` / all)
- Campaign (id or label match)
- Publication state (display enum multi-select)
- Blocked only
- Due soon (configurable window, e.g. next 48h from `observed_at_utc` / client now — document constant)

Filtered-out **critical** failures (failed/blocked/integration issues) MUST remain discoverable via count, warning banner, or “show hidden critical” / reset affordance—never silently disappear without signal.

### D8 — Timezone presentation

**Choice:** Store and transmit schedules as UTC. UI MUST show:

- Primary: stored UTC (`scheduled_at_utc`)
- Secondary: operator-local interpretation via `Intl` / `timeZone` from the browser environment

Do not persist a new timezone preference server-side in US-040B. Calendar day bucketing MUST use a documented rule (prefer **UTC calendar date** of `scheduled_at_utc` for placement consistency across operators; show local time as secondary text). Document the bucketing rule in UI helper text to avoid “wrong day” confusion.

### D9 — Mobile UX

**Choice:**

- List: stacked rows/cards (CSS already leaning operational; ensure touch targets ≥ ~44px for primary actions).
- Calendar: month grid remains; selected day opens **agenda-style expansion** (list of that day’s items) instead of requiring horizontal scroll of a dense table.

### D10 — Mutations and out-of-scope boundaries

**Choice:** US-040B is **read/visibility** for calendar. List retains US-017 POSTs only. Calendar chips MUST NOT offer reschedule/write in this change (selection for detail may be allowed; schedule commit is US-040C). No enablement bypass; no LinkedIn API calls from console reads.

### D11 — Worker / deploy surface

**Choice:** Implement aggregation in a dedicated Python module (or extend an existing supervision module carefully) + route in `main.py`. Frontend build still emits into `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/`. Dockerfile remains Python-slim with build-before-deploy. Secrets audit continues over source + built assets.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Schedule-visibility payload large with many campaigns | Cap/window by month query params (`from_utc`/`to_utc` or `year`/`month`) on the GET; document defaults to visible month ± padding |
| UTC day-bucket vs local midnight surprises | Document UTC bucketing; show both UTC and local on chips/detail |
| Dual fetches briefly inconsistent | Single refresh helper; shared store; show observed_at timestamps |
| Filter hides failed items unnoticed | Critical-failure counter + reset / “show critical” affordance |
| Accidental calendar mutation UX | No write controls on calendar in US-040B; copy states visibility-only |
| Mapping blog `completed` to “published” | Forbidden for LinkedIn API meaning; use qualified handoff/completed language |
| Calendar library creep | Default CSS grid; README justification gate for any new prod dep |

## Migration Plan

1. Implement worker schedule-visibility GET + tests (read-only, auth, partial issues, no mutations).
2. Extend frontend model/client/store; implement Filters + MonthCalendarView + ViewSwitcher persistence.
3. Rebuild static assets; confirm console route still serves SPA.
4. Run frontend + pytest; secrets audit; `git diff --check`.
5. Update CURRENT-STATE / progress-checklist / user-stories only for demonstrated US-040B criteria—not Story accepted / BL-015 closed.
6. Rollback: revert frontend build + route/module if needed; list-only console remains usable if calendar fails closed with error banner (prefer soft-degrade: list works if schedule GET fails).

## Open Questions

- Exact GET path naming (`/flow-a/schedule-visibility` vs nested under linkedin-variants) — prefer the shorter Flow A path unless apply finds routing consistency reasons otherwise.
- Whether month query uses `year`+`month` or ISO range — prefer `year`/`month` for simple month nav.
- Blog `completed` display label wording — resolve at apply with GLOSSARY-qualified copy (not LinkedIn “published”).
