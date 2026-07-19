## Context

US-074/US-075 locked next-week LinkedIn gap policy (gap = 0 posts in `pending`/`queued`/`published`; `min_lead_days` default 5; empty coverage = proxy for needing upstream content). US-076 shipped `load_gap_operator_settings()` + Postgres/UI SoT and is deployed on `192.168.0.194:8010`. There is still no runtime sensor that returns `gaps[]` for the next operator-local week.

Existing building blocks: campaign LinkedIn variants + schedule-visibility loaders (`_load_linkedin_items`), local-day bucketing (`local_day_key_for_utc`), and density membership states `{pending, queued, published}` in `local_day_density` (US-040K). Calendar SoT remains US-041 / `editorial_calendar_store` for schedule identity; gap coverage counts LinkedIn publications by local day, not blog calendar rows alone.

Constraints: ADR-0001 (n8n → HTTP only); detect-only non-mutation; do not redefine gap as density; do not implement US-078–US-082; `gap_trigger_enabled` fail-closed for later trigger but detect MAY run for inspection when disabled.

Stakeholders: content operator (inspect next-week gaps); system operator (authenticated HTTP); future US-082 implementer (stable result shape).

## Goals / Non-Goals

**Goals:**

- Detect-only next-week (Mon–Sun) gap scan using operator timezone from settings.
- Gap day = LinkedIn coverage count ≤ `gap_posts_threshold` (default 0 ⇒ exactly 0 posts).
- Apply `min_lead_days` so days without enough lead from “now” are not returned as actionable gaps.
- Authenticated HTTP result: `gaps[]` (or empty / no-gap status), target ISO week, operator timezone, settings source metadata.
- Reuse settings loader and LinkedIn coverage enumeration; never mutate campaigns/calendar/drafts.
- Document detect-vs-trigger clearly in ops/CURRENT-STATE.

**Non-Goals:**

- Trigger, discovery, draft, approve, promote, spill, LinkedIn API publish.
- Filesystem inventory of `ready/` or `pending-approval/` as gap input.
- Changing US-040K density max-2 semantics or US-041 calendar mutation contracts.
- Requiring `gap_trigger_enabled=true` to run detect.
- Closing BL-019 / Story accepted without operator walkthrough.

## Decisions

### D1 — Coverage source: LinkedIn schedule items with density membership states

**Choice:** Count LinkedIn items whose `publish_state` / source state is in `{pending, queued, published}` (same membership set as US-040K density for LinkedIn), bucketed by operator-local day of `scheduled_at_utc` (or equivalent scheduled timestamp already used by schedule-visibility). Do **not** invent coverage from blog `ready/` / `pending-approval/` folder listings.

**Why:** Matches locked policy wording (“0 LinkedIn posts pending/queued/published”) and reuses proven loaders (`_load_linkedin_items` / shared helpers) so console Week view and sensor cannot disagree on what occupies a day.

**Alternatives:**

| Option | Rejected because |
|--------|------------------|
| Blog calendar rows only | Policy is LinkedIn coverage, not blog due dates |
| Filesystem `ready/` count | Explicitly forbidden by US-077 AC / policy proxy rule |
| Count only `published` | Would treat pending/queued as empty and false-trigger drafts |

### D2 — Next operator-local week window

**Choice:** Given `now_utc` and `operator_timezone`, compute the **next** Mon–Sun week in that timezone: the Monday after the Monday of the current local week (i.e. always look ahead one full week, not “rest of this week”). Emit ISO week id for that target week (`YYYY-Www` in the operator timezone’s ISO calendar).

**Why:** Matches planning notes (“Friday afternoon → following week”) and US-077 “next operator-local week”.

**Note:** `gap_scan_mode` remains `next_week` only in v1 (already locked in settings); reject or ignore other modes if ever present until a later change.

### D3 — Gap definition vs density ceiling

**Choice:** A day is a **gap** iff LinkedIn coverage count for that local day is ≤ `gap_posts_threshold` (default 0). Days with ≥1 covering posts are **not** gaps even when count is 1 (under max-2). Do **not** treat “room under density max-2” as a gap.

**Why:** US-077 + US-040K separation: gap = empty; density = capacity elsewhere.

### D4 — `min_lead_days` filters actionable gaps

**Choice:** After identifying zero-coverage days in the target week, include a day in `gaps[]` only when the local calendar distance from “today” (operator-local date of `now`) to that gap day is ≥ `min_lead_days` (default 5). Days that are empty but too soon are omitted from actionable `gaps[]` (MAY optionally appear in a diagnostic `non_actionable_empty_days[]` field for operators — nice-to-have; not required if response stays minimal).

**Why:** Planning notes: lead before a gap day is actionable; Friday→next-week Monday typically satisfies lead ≈ 3–10 depending on clock — sensor must still honor the knob.

**Clarification:** Lead is measured in whole local calendar days between operator-local “today” and the gap local date (inclusive/exclusive rule MUST be documented in code comments and tests; prefer: `gap_date - today_date` in days ≥ `min_lead_days`).

### D5 — HTTP surface (detect-only)

**Choice:**

- Authenticated `GET /flow-b/calendar-gaps` (preferred) — inspection/diagnostic; query may accept optional `now_utc` override for tests only when explicitly allowed in dry diagnostic mode, otherwise server clock.
- Alternatively `POST /flow-b/calendar-gaps/detect` with empty body / `{ "dry_run": true }` — if GET + query is awkward for auth clients, POST is acceptable; MUST remain non-mutating either way.

Response shape (normative fields):

| Field | Meaning |
|-------|---------|
| `status` | e.g. `gaps_found` \| `no_gap` \| error statuses |
| `operator_timezone` | Effective IANA zone used |
| `settings_source` | `defaults` \| `database` |
| `gap_trigger_enabled` | Echo effective flag (informational; does not gate detect) |
| `target_week` | ISO week string + optional Mon/Sun local dates |
| `gaps` | List of actionable gap local dates (`YYYY-MM-DD`) and/or weekday labels |
| `min_lead_days` | Effective knob applied |
| `gap_posts_threshold` | Effective threshold applied |
| `read_only` | Always `true` for this capability |
| `observed_at_utc` | Observation timestamp |

MUST NOT: write campaign metadata, move files, create drafts, call LinkedIn/DeepSeek/ComfyUI/Git.

**Why:** US-077 requires orchestration-suitable clear result + authenticated inspect path; ADR-0001 HTTP boundary.

### D6 — `gap_trigger_enabled` does not block detect

**Choice:** Detect runs regardless of `gap_trigger_enabled`. Response echoes the flag. Docs state: inspection allowed when false; auto-trigger (US-082) remains fail-closed when false.

**Why:** Explicit user/AC requirement; avoids blocking operator diagnostics before trigger exists.

### D7 — Module layout

**Choice:** New module e.g. `flow_b_calendar_gap_detect.py` with pure `detect_next_week_calendar_gaps(base_path, *, now_utc=..., store=..., environ=...)` plus thin FastAPI route in `main.py`. Reuse `_load_linkedin_items` (or extract a tiny shared coverage helper if import cycles require it — prefer lazy import pattern already used by density).

**Why:** Smallest coherent diff; mirrors settings + density patterns.

### D8 — Auth, errors, secrets

**Choice:** Same worker API-key auth as other Flow B / Flow A routes. Structured JSON errors (auth 401/403; validation 422; unexpected 5xx). Never return secrets. Calendar/settings store unavailability → clear blocked status, no invented coverage.

### D9 — Tests

**Choice:** Unit tests with temp editorial base + fixture campaigns: empty week → all days gaps (subject to lead); one pending on Wednesday → that day not a gap; `min_lead_days` filters near days; defaults when settings row missing; auth required; repeated calls non-mutating; `gap_trigger_enabled=false` still returns detect result. No real external APIs.

### D10 — Docs / product status

**Choice:** Update `docs/CURRENT-STATE.md` and Flow B policy cross-links to **implemented** for detect. Update user-stories/progress only for demonstrated automated AC; leave Story accepted unchecked; do not close BL-019.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Schedule-visibility month window vs week spanning two months | Load LinkedIn items across a UTC window covering full target week ±1 day (same DST safety as density) |
| Disagreement with console Week view | Same membership states + local-day key helper |
| Operators confuse detect with trigger | Echo `gap_trigger_enabled`; docs + CURRENT-STATE; no draft side effects |
| `min_lead_days` edge (inclusive count) | Lock rule in D4 + explicit tests |
| Scope creep into US-082 | Specs/tasks forbid trigger routes and draft creation |

## Migration Plan

1. Implement detect module + HTTP + tests locally after explicit approval (`/opsx-apply`).
2. `/opsx-verify` → implementation commit → sync → archive (separate commits).
3. Deploy only with explicit approval (out of propose scope).
4. Rollback: revert worker build; no schema migration required for detect-only.

## Open Questions

None blocking. Resolved by AC/proposal:

- Coverage states: pending/queued/published (D1).
- Detect when trigger disabled: allowed (D6).
- UI chrome for gaps in Authority Manager: **not required** for US-077 (HTTP inspect sufficient); optional later.
