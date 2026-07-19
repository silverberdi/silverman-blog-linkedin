## Context

US-040G–J are implemented and deployed on `192.168.0.194:8010` (console-layer): calendar-first Week/Month, EventModal + toasts, operator-local primary clock (`localDayKey`), cancelled honesty + `POST /reopen-linkedin-variant`. None are Story accepted; Visual DoD + walkthrough remain open. BL-015 stays open.

Today:

- Interim LinkedIn defer/reopen checks: **per-campaign** duplicate-slot + same-**UTC**-day within 72h (`linkedin_supervision_defer_duplicate_slot` / `linkedin_supervision_defer_saturation`).
- Interim blog calendar schedule-update: **max 1 blog item per UTC day** (`calendar_schedule_duplicate_slot` / `calendar_schedule_saturation`).
- US-040I local-day Week/Month bucketing is the operator clock for density UX; wire fields remain `*_utc`.
- Reopen MAY land on a local day that already has publications — K’s max-2/local-day was explicitly deferred from J.
- Schedule-visibility already aggregates LinkedIn campaign variants + editorial calendar blog items for the console plan.

**SoT separation (preserve):** Editorial calendar rows live in Postgres (`silverman_linkedin_db`). LinkedIn variant schedules live in campaign metadata. Console continues to read/mutate both through worker HTTP only (ADR-0001).

**Constraints:** Client + server fail-closed; plain-language density errors; no LinkedIn API publish for enforcement; no enablement bypass; no n8n Execute Command; no browser mount writes; qualified Flow A language; Story accepted gated by Visual DoD + walkthrough; BL-021 MAY later supersede this interim rule.

## Goals / Non-Goals

**Goals:**

- Max **2** density members per **operator-local** calendar day across the live supervision plan (inclusion set in D1).
- Week/Month density surfacing (full at 2; conflict understandable before commit).
- Validate on reschedule/defer/reopen (+ blog schedule-update when blog counts) client-side and server-side; fail closed with plain language.
- Grandfathered 3+ days remain visible with a clear move-to-fix path; no silent data loss.
- Preserve G–J baselines, session/`canMutate`, dry-run/confirm, ADR-0001, `*_utc` wire fields.
- Encode Visual DoD + walkthrough gates; honest CURRENT-STATE / product status; leave BL-015 and G–J Story accepted open.

**Non-Goals:**

- Closing G/H/I/J Story accepted or BL-015.
- Public URL / Google OIDC / BFF / user-management.
- LinkedIn API publish from console; enablement bypass; Flow B; n8n Execute Command.
- Full BL-021 cadence supersession (document K as interim that BL-021 MAY supersede).
- Replacing interim duplicate-slot / UTC-day+72h / blog-1/UTC-day checks — they remain additive.
- Story accepted / BL-015 closed from implementation alone.

## Decisions

### D1 — Density inclusion set (operator-obvious)

**Choice:** A **density member** for a local day is any schedule-visibility item whose `scheduled_at_utc` (or blog due time) falls on that operator-local day and that matches:

| Channel | Counts toward cap? | Notes |
|---------|-------------------|--------|
| LinkedIn `pending` / `queued` | **Yes** | Live planned / in-flight schedule |
| LinkedIn deferred display (still `pending` with schedule; `auto_queue_eligible` false) | **Yes** | Still on the plan |
| LinkedIn `published` (still shown on calendar for that day) | **Yes** | Occupies the day for anti-spam honesty (“this day already had publication(s)”) |
| LinkedIn `cancelled` | **No** | Slot freed until reopen restores `pending` |
| LinkedIn `failed` / blocked-without-schedule | **No** | Not live planned; remain visible; not density members |
| Blog calendar items shown on schedule-visibility | **Yes** | Shared plan density (blog + LinkedIn share the 2/day budget) |
| Blog items cancelled/removed / not returned by schedule-visibility | **No** | |

When evaluating a mutation that **moves** an item, **exclude that item’s current identity** from the target-day count (self-move same local day MUST be allowed when others_on_day ≤ 1 after exclusion).

**Rationale:** Matches US-040K default intent (live planned LinkedIn + blog if shown); cancelled exclusion avoids surprise after cancel; published-on-calendar counts so operators cannot stack two new pendings onto a day that already shows two publishes; failed excluded from cap but not hidden.

**Not chosen:** Per-campaign-only counting (allows cross-campaign spam). Counting cancelled. Ignoring blog. Ignoring published historical occupancy.

### D2 — Operator timezone for server-side local-day keys

**Choice:**

1. Console sends an IANA timezone string on density-gated mutations (e.g. `operator_timezone` from `Intl.DateTimeFormat().resolvedOptions().timeZone`).
2. Worker validates the zone (zoneinfo / equivalent); computes local day keys for the proposed UTC instant and for density members’ UTC schedules in that zone.
3. Optional env fallback `SILVERMAN_OPERATOR_TIMEZONE` for non-console callers; if neither request TZ nor valid env TZ is available, **fail closed** with a stable timezone-required/invalid code (do not silently fall back to UTC day for K’s product rule).
4. Wire schedule fields remain `*_utc` — do not replace them with local datetime API fields.

**Rationale:** US-040I established local day as the product clock; server must agree with Week/Month or operators get false accept/reject. Client-only enforcement fails the AC. Env-only TZ can disagree with the browser the operator is using.

**Not chosen:** UTC-day as K’s clock (contradicts US-040I). Client-only cap. Silent UTC fallback when TZ missing.

### D3 — Cross-plan counting via shared evaluator

**Choice:** Implement a shared worker helper (e.g. `evaluate_local_day_density(...)`) that:

1. Accepts `base_path`, target UTC instant, `operator_timezone`, optional `exclude_item_id` / campaign+variant / calendar `item_id`.
2. Loads the same sources schedule-visibility uses (campaign metadata LinkedIn variants + editorial calendar blog items in a sufficient window around the target local day — expand UTC window to cover TZ edges).
3. Counts density members (D1) on the target local day excluding the moving item.
4. Returns `ok` when `count < 2` after placing would yield ≤ 2; returns density failure when placing would yield **> 2** (i.e. when `others_on_day >= 2`).

Wire into:

- `POST /defer-linkedin-variant`
- `POST /reopen-linkedin-variant`
- Editorial calendar schedule-update (blog) when blog items are density members

Prefer reusing schedule-visibility loading primitives over a divergent scan. Do **not** require a new public GET for MVP if mutations can evaluate internally; console client-side uses already-loaded schedule-visibility snapshot + `localDayKey`.

**Rationale:** Cap is plan-wide anti-spam, not per-campaign. Single evaluator keeps defer/reopen/blog consistent.

**Not chosen:** Only checking LinkedIn siblings in one campaign. Separate incompatible counters per channel without a shared day budget.

### D4 — Additive to interim saturation / duplicate-slot (not a replacement)

**Choice:** Keep existing interim checks:

- LinkedIn: duplicate-slot + same-UTC-day within 72h (per campaign)
- Blog: interim max-1 per UTC day

Run **both** families. K’s max-2/local-day is an **additional** product rule. Document in specs/CURRENT-STATE that **BL-021 MAY later supersede** K’s interim 2/local-day (and possibly the older interim checks).

Error precedence (recommended): validate time/eligibility → duplicate-slot → interim saturation → **local-day density** (or density before interim saturation — either is fine if documented; prefer density after structural slot checks). Console maps each code to distinct plain language.

**Rationale:** User explicitly asked for additive policy, not BL-021 supersession.

**Not chosen:** Removing UTC-day+72h checks in this change. Claiming K completes BL-021.

### D5 — Stable density error codes + plain-language UX

**Choice:** Introduce stable machine codes, fixed at apply, e.g.:

- `linkedin_supervision_local_day_density` (defer/reopen LinkedIn path)
- `calendar_schedule_local_day_density` (blog schedule-update path)
- `operator_timezone_invalid` / `operator_timezone_required` (TZ gate)

Console `explainErrorCodes` (and toast/modal) MUST map density codes to human copy such as: **“This day already has 2 publications.”** Prefer prevention in ScheduleEditor / reopen pick (disable or warn saturated local days) over cryptic post-submit codes alone. Still fail closed server-side if the client is bypassed.

**Rationale:** AC requires plain language, not only `*_saturation` codes.

**Not chosen:** Reusing `*_saturation` for the 2/local-day rule (overloads meaning; interim saturation is different).

### D6 — Week/Month density surfacing + grandfathered 3+

**Choice:**

1. **Full (2):** Subtle “full” treatment on the local day (Week column header and/or Month cell) — calm, not alarm-red.
2. **Over-full (3+):** Distinct but still calm “over capacity” cue; **do not hide** chips; EventModal remains the fix path (reschedule/move).
3. **Empty / 1:** No density alarm.
4. Mutations that would create a 3rd (or add to an already 3+ day) fail closed; mutations that **reduce** density (move one event off an over-full day to an under-full day) succeed when otherwise valid.
5. No automatic redistribution or silent deletes.

**Rationale:** Matches Visual DoD scenes and “no silent data loss.”

**Not chosen:** Hiding overflow history. Auto-spreading events. Alarm fatigue (failed/blocked styling for density).

### D7 — Client-side prevention aligned with server

**Choice:** Console computes day occupancy from the current schedule-visibility snapshot using the same inclusion rules (D1) and `localDayKey` (US-040I). ScheduleEditor / reopen datetime flows:

- Warn or block selecting a local day where `others_on_day >= 2` (excluding the item being edited).
- On submit, still rely on worker enforcement.
- Dry-run default + confirm for real unchanged.

**Rationale:** Prefer prevention before commit; server remains authoritative.

### D8 — Honest status and acceptance gates

**Choice:** After apply: CURRENT-STATE / user-stories / progress-checklist reflect console+worker implementation evidence only; leave Acceptance criteria validated and Story accepted open until Visual DoD + walkthrough. Do not mark BL-015 closed. Do not mark US-040G/H/I/J Story accepted as a side effect.

### D9 — No LinkedIn API / no ADR-0001 breach

**Choice:** Density evaluation and refusals MUST NOT call LinkedIn, DeepSeek, ComfyUI, or Git. Console MUST NOT write mounts. All mutations remain authenticated worker HTTP.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Browser TZ ≠ env TZ → server/client disagree | Prefer request `operator_timezone`; fail closed if missing/invalid; Vitest + pytest with fixed TZ fixtures |
| Window scan misses items near month edges | Expand UTC load window around target local day for TZ offsets (±1 day minimum) |
| Published counting surprises operators who thought “only pending” | Modal/help copy: “Published items on this day count toward the 2/day limit”; Visual DoD includes this |
| Interim saturation + density both fire | Distinct codes + distinct plain language; document additive relationship |
| Performance scanning all campaigns on every defer | Reuse schedule-visibility primitives; bound window; acceptable for operator console scale |
| Over-claiming Story accepted | Tasks gate Visual DoD + walkthrough; Vitest insufficient |
| Accidental G–J Story accepted / BL-015 closed | Explicit non-goals + doc task language |
| Blog max-1 UTC vs shared max-2 local | Keep both; blog can still fail interim 1/UTC-day independently of K |

## Migration Plan

1. Implement shared density evaluator + wire defer/reopen/blog schedule-update; pytest with America/Chicago (or fixed TZ) fixtures including local-midnight boundary.
2. Console density cues + ScheduleEditor/reopen prevention + error maps; Vitest ~1280/~375; production `npm run build` into worker static path.
3. Honest CURRENT-STATE / product status; note interim vs BL-021.
4. Deploy only after explicit approval; then Visual DoD + operator walkthrough before Story accepted.

**Rollback:** Feature is additive validation — revert worker density checks + console cues; existing schedules unchanged (grandfathered 3+ remain).

## Open Questions

_(None blocking propose — resolve at apply only if implementation discovers a hard conflict.)_

- Exact OpenAPI field name for timezone (`operator_timezone` vs `timezone`) — fix at apply; prefer `operator_timezone`.
- Whether schedule-visibility GET should optionally echo per-day density counts for UX — optional optimization; client can compute from items for MVP.
