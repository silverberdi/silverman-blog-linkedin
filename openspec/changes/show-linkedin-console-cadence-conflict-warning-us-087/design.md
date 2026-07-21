## Context

BL-021 apply order is US-051 → **US-087** → US-088 → US-089. US-051 (and US-052 residual warning text) already define **cadence conflict** as the same gate as live `linkedin_publish_blocked_cadence` / related cadence skip at `scheduled_at_utc` — not density-full, OAuth, enablement-off, or sequence-alone.

Today Silverman Authority Manager Week/Month + EventModal show BL-032 operator labels (Scheduled / Waiting to send / Live / Failed / Cancelled) via schedule-visibility, but there is **no** cadence-conflict projection on calendar chips. Operators can believe a Scheduled slot will send when publish-due would refuse for cadence. Interim defer saturation (`_defer_cadence_errors`) and US-040K density are **not** the US-051 cadence-conflict meaning and MUST NOT drive this warning.

Constraints: ADR-0001 (authenticated worker HTTP only; no browser filesystem SoT), no second publish pipeline, no enablement bypass, US-020 publish-time guard remains authoritative at send and MUST NOT be reimplemented as a disagreeing constant.

## Goals / Non-Goals

**Goals:**

- Red (or equivalent) Week/Month warning on not-yet-Live LinkedIn items whose current slot is cadence-infeasible under US-051/US-020.
- EventModal plain-language conflict + usable next step (earliest feasible time and/or postpone / wait for replan).
- Additive schedule-visibility fields (if needed) from authenticated worker HTTP; console consumes them via typed client / shared model.
- Distinct from Failed / Cancelled / Waiting to send / Live / density-full; feasible items show no cadence warning.
- Visual DoD: desktop + mobile evidence for conflict chips and EventModal explanation.

**Non-Goals:**

- US-088 shift-forward placement; US-089 replan endpoint/ops path.
- Changing US-020 72h math, cron, n8n, OAuth, or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Marking US-052 / US-087 / BL-021 Story accepted by code alone.
- Expanding conflict UX to sequence (unless a later story does).

## Decisions

### D1 — Worker projects cadence conflict on schedule-visibility (SoT)

Console MUST NOT invent cadence math in the browser from raw campaign files. Authenticated `GET /flow-a/schedule-visibility` remains the calendar read SoT and MUST expose additive fields on LinkedIn items when a slot is cadence-infeasible.

**Additive fields (minimal):**

| Field | Type | Meaning |
|-------|------|---------|
| `cadence_conflict` | `bool` | `true` only when evaluating at this item’s `scheduled_at_utc` would hit the US-020 **cadence** refuse/skip gate (same meaning as `linkedin_publish_blocked_cadence`) |
| `cadence_conflict_code` | `string \| null` | Stable code when conflicted: `linkedin_publish_blocked_cadence`; otherwise `null` |
| `cadence_earliest_feasible_at_utc` | `string \| null` | Earliest UTC instant at which same-campaign cadence would clear (`max(published_at) + 72h` among same-campaign successful `published` evidence), when computable; else `null` |

Optional future fields (not required for US-087 AC): plain-language server summary strings. Prefer frontend copy keyed off `cadence_conflict` + earliest-feasible for operator-local display.

**Alternatives considered:** Browser-only heuristic — rejected (ADR-0001 / false truth). New dedicated HTTP route — rejected (schedule-visibility already aggregates calendar items). Pending-supervision-only — rejected (Week/Month placement is schedule-visibility-driven).

### D2 — Evaluation semantics: cadence-only at `scheduled_at_utc`

Reuse the **same** US-020 cadence interval rule (`CADENCE_MINIMUM_INTERVAL` = 72h; anchored to stored same-campaign `published_at` evidence). For projection:

1. Evaluation instant = item’s `scheduled_at_utc` (parsed UTC). If missing/unparsable → `cadence_conflict=false` (no false warning; optional issue already covered by schedule-visibility issues).
2. Consider only same-campaign siblings with `publish_state=published` and valid `published_at`.
3. Conflict when any such `published_at + 72h > scheduled_at_utc`.
4. **Do not** set `cadence_conflict=true` for sequence-alone, density-full, enablement-off, OAuth, or `linkedin_publish_blocked_evidence_invalid` alone. Evidence-invalid remains a distinct publish-time class; if evidence is missing/unparsable for a published sibling, fail closed for **publish** elsewhere, but for US-087 do **not** paint the cadence-conflict warning as if it were a normal 72h conflict (MAY leave conflict false and rely on existing issues / diagnostics).
5. Cross-campaign independence unchanged.
6. Extract or share a read-only helper with the publication guard (prefer calling shared cadence-interval logic; MUST NOT duplicate a second disagreeing constant). Do **not** change publish-due behavior.

**Alternatives considered:** Evaluate at wall-clock `now` — rejected (AC requires conflict at current slot). Call full `_publish_guard_block_reason` and treat any non-null as conflict — rejected (would fold sequence/evidence into cadence UX).

### D3 — Which items get the warning

Apply projection and UI warning to LinkedIn-channel items that are **not Live on LinkedIn** and still schedule-tied, primarily:

| Operator status | `publish_state` | Cadence warning eligible? |
|-----------------|-----------------|---------------------------|
| Scheduled | `pending` | Yes, when `scheduled_at_utc` present and cadence-infeasible |
| Waiting to send | `queued` (and in-flight `publishing` if shown) | Yes, same rule |
| Live on LinkedIn | `published` / API evidence | **No** |
| Cancelled | `cancelled` | **No** |
| Failed | `failed` | **No** (Failed presentation stays primary; do not overlay cadence-conflict as the status story) |
| Blog channel | n/a | **No** |

Feasible slots → `cadence_conflict=false` → no warning affordance.

### D4 — Visual affordance (Week / Month) — distinct from status

- Keep US-083 primary status labels unchanged.
- Add a **cadence-conflict indicator** on conflicted chips (red accent / warning icon / `data-testid` such as `cadence-conflict-indicator`) that does **not** replace Scheduled / Waiting to send.
- MUST NOT reuse Failed chip styling as the sole signal (Failed remains failed).
- MUST NOT look like density-full day cue (US-040K day-level full/over cues stay separate).
- MUST NOT imply Live on LinkedIn.
- Month dense cells: indicator still readable (icon/badge on chip or overflow affordance that survives density).

### D5 — EventModal explanation + next step

When `cadence_conflict` is true for the opened LinkedIn item:

1. Plain-language statement that this slot would be **blocked for campaign cadence** (72h since last successful same-campaign LinkedIn publication) — not density, not OAuth, not enablement.
2. Usable next step, at least one of:
   - Show **earliest feasible** local time from `cadence_earliest_feasible_at_utc` (with timezone cue), and point to existing **Postpone / reschedule** (US-084) as the immediate operator action; and/or
   - “Postpone to a later time” / “wait for replan” (US-089 not implemented — copy MUST NOT claim replan exists as a working control yet).
3. Do not claim the item is Live; do not claim automatic shift-forward already ran (US-088 out of scope).

### D6 — Residual US-052 obligation (document only in scope)

US-052 already states residual conflicts after placement still require US-087 warning. This change **implements the warning**; it does **not** implement shift-forward. No delta to `linkedin-publishing-windows-and-shift-forward-policy` required unless apply discovers a contradiction (none expected).

### D7 — Testing, Visual DoD, docs

**Pytest:** schedule-visibility sets `cadence_conflict` true/false correctly for fixtures with published sibling inside/outside 72h of `scheduled_at_utc`; Live/cancelled/failed/blog do not get true; read remains non-mutating; earliest-feasible populated when computable; enablement flag unchanged.

**Vitest:** Week + Month show indicator only when conflict true; EventModal copy + next step; feasible item has no indicator; distinct from Failed/Cancelled/Waiting-to-send/density cues; mobile viewport readability where existing console tests already use viewport helpers.

**Visual DoD scenes (desktop + mobile)** — required for Story accepted (Vitest alone insufficient unless operator waives as with prior console stories):

1. Week: conflicted Scheduled chip with red/warning indicator + primary Scheduled label still visible.
2. Month: same for a conflicted item (dense month if practical).
3. EventModal: open conflicted item — plain conflict explanation + earliest feasible / postpone next step.
4. Negative: cadence-feasible Scheduled item — **no** cadence-conflict indicator.
5. Distinctness: Failed chip and density-full day cue remain visually/verbally different from cadence-conflict warning.
6. Mobile: EventModal sheet readable for conflict explanation.

**Docs after apply:** update CURRENT-STATE that US-087 is implemented (not Story accepted); do not close BL-021.

## Risks / Trade-offs

- **[Risk] Operators confuse cadence warning with Failed or density-full** → Mitigation: keep primary status label; separate indicator + EventModal vocabulary per US-051 blocked-state table.
- **[Risk] Duplicate 72h constant drifts from US-020** → Mitigation: share `CADENCE_MINIMUM_INTERVAL` / shared helper; pytest anchors to same interval.
- **[Risk] Sequence-blocked items look “fine” while cadence-clear** → Mitigation: accepted non-goal; sequence remains distinct; do not fold into this warning.
- **[Risk] Race: sibling publishes after schedule-visibility read** → Mitigation: warning is projection at read time; publish-time guard remains authoritative; refresh after mutations.
- **[Risk] Scope creep into US-088/US-089** → Mitigation: tasks explicitly exclude shift-forward/replan; next-step copy points to postpone + future replan without claiming them done.
- **[Trade-off] Earliest feasible ≠ full preferred-window shift-forward** → Acceptable for US-087; US-088 owns window-aware placement.

## Migration Plan

1. Approve this OpenSpec change → `/opsx-apply`.
2. Worker schedule-visibility projection + pytest.
3. Console Week/Month/EventModal + Vitest; rebuild static assets.
4. Deploy only with explicit approval; operator walkthrough + Visual DoD for Story accepted.
5. Rollback: revert deploy/assets; no campaign metadata mutation from this read-only projection.

## Open Questions

- None blocking. Exact microcopy and iconography may be refined at apply if AC intent holds. If apply discovers pending-supervision rows also need the same fields for EventModal join, mirror the additive fields there without inventing a second cadence engine.
