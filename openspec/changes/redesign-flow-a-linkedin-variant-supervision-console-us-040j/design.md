## Context

US-040G–I are implemented and deployed on `192.168.0.194:8010` (console-layer): calendar-first Week/Month, EventModal + toasts, operator-local primary clock. None are Story accepted; Visual DoD + walkthrough remain open. BL-015 stays open.

Today:

- Cancel via `POST /cancel-linkedin-publication` moves `pending`/`queued`/`failed` → `cancelled`, sets `auto_queue_eligible` false, and is documented as irreversible through existing endpoints.
- Schedule-visibility already includes cancelled LinkedIn variants (calm grey chip styling exists in the model), but EventModal has no cancelled honesty path (what/why/what-next) and no reopen action.
- Schedule-visibility items do **not** currently expose cancellation reason / timestamp / phase for operator copy.
- US-040I local-first ScheduleEditor + future rules are the clock for any new schedule pick.
- US-040K (max 2 publications per local day) is the next product rule after J — not shipped here unless a hard dependency appears.

**SoT separation (preserve):** Editorial calendar rows live in Postgres (`silverman_linkedin_db`). LinkedIn variant schedules live in campaign metadata. Console continues to read both through worker HTTP only (ADR-0001).

**Constraints:** Prefer shipping reopen/reschedule as the business outcome; dry-run default + confirm for real; session/`canMutate`; no LinkedIn API publish from console; no enablement bypass; no n8n Execute Command; no browser mount writes; qualified Flow A language; Story accepted gated by Visual DoD + walkthrough.

## Goals / Non-Goals

**Goals:**

- Calm, honest cancelled visibility on Week/Month.
- Cancelled EventModal answers what / why / what-next in plain language.
- Approved worker HTTP reopen/reschedule-from-cancelled (`cancelled` → editable `pending` with new future `scheduled_at_utc`).
- Console happy path: confirm → local time pick (US-040I) → toast → calendar shows editable pending.
- Cancel remains destructive/confirmed; irreversible except via the new reopen path.
- Vitest + pytest + static rebuild; honest docs; Visual DoD / walkthrough gates encoded in tasks.

**Non-Goals:**

- US-040K density product enforcement (document as follow-up constraint).
- Closing US-040G/H/I Story accepted.
- Public URL / Google OIDC / BFF / user-management.
- LinkedIn API publish; enablement bypass; Flow B; n8n Execute Command.
- Reopen of `published` variants, or reopen of `failed→cancelled` recovery-terminal cancels (those stay on US-022 recovery vocabulary).
- Story accepted / BL-015 closed from implementation alone.

## Decisions

### D1 — Ship reopen/reschedule as the primary outcome (read-only only as escape hatch)

**Choice:** Implement the worker reopen contract and console wiring in this change as the preferred business outcome. The interim **explicit read-only cancelled modal** is allowed only if a hard implementation blocker appears mid-change; if used, copy MUST state reopen is not yet available and MUST NOT show fake Edit controls. Tasks MUST prefer the reopen path and treat read-only as a documented fallback, not the default plan.

**Rationale:** US-040J AC prefers reopen as the business outcome; mystery cancelled UX is forbidden either way.

**Not chosen:** Ship read-only-only and defer reopen to a later story (fails preferred AC). Fake Edit that no-ops.

### D2 — New authenticated `POST /reopen-linkedin-variant` (atomic reopen + reschedule)

**Choice:** Add a dedicated worker endpoint (name MAY be `POST /reopen-linkedin-variant` or equivalent kebab-case) that, in one real mutation:

1. Accepts `campaign_id`, `variant`, `new_scheduled_at_utc` (required, strictly after now), optional `reason` / `idempotency_key` / `actor` / `source`, `dry_run` default `true`.
2. Requires variant `publish_state` `cancelled` and reopen-eligible cancellation provenance (D3).
3. Sets `publish_state` → `pending`, updates `scheduled_at_utc`, restores strategy-driven eligibility (`auto_queue_eligible` `true`), audits reopen on `operator_supervision` (including archive of prior cancellation into history).
4. Makes **no** LinkedIn API call; does **not** auto-queue; does **not** bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` (enablement remains irrelevant to this pre-queue mutation, same as cancel/defer).
5. Returns structured JSON with `publish_state`, new schedule, dry-run flag, and stable error codes.

**Rationale:** Extending cancel to “un-cancel” is confusing. Extending defer alone cannot accept `cancelled`. Atomic reopen+new time matches the product happy path (confirm → choose new local time → toast → pending).

**Not chosen:** Two-step reopen-then-defer (extra round-trip; risk of pending-without-schedule). Reuse `POST /defer-linkedin-variant` by silently accepting cancelled (hides a new capability inside an old contract).

**Wire fields:** Keep `new_scheduled_at_utc` (and any existing `*_utc` patterns). Do not add local-timezone API fields in this change; console converts local → UTC at the typed client boundary (US-040I).

### D3 — Reopen eligibility (fail closed)

**Choice:** Allow reopen only when:

| Condition | Allowed? |
|-----------|----------|
| `publish_state` is `cancelled` | Required |
| Cancellation phase `pre_queue` (never queued) | Yes |
| Cancellation phase `post_queue` (was queued, never published; LinkedIn not called) | Yes — returns to `pending`, not `queued` |
| Cancelled from `failed` (`recovery_cancelled` / failed-cancellation path) | **No** — fail with stable `linkedin_reopen_not_allowed` (or equivalent); operator uses US-022 recovery vocabulary |
| `publish_state` is `published` / `pending` / `queued` / `failed` | **No** |
| Campaign not Flow A `distribution_scheduled` (same gate family as cancel/defer) | **No** — fail closed with existing campaign/state codes where reusable |

**Rationale:** Console cancelled chips are primarily supervision-window / pre-publish withdrawals. Failed→cancelled is a recovery terminal action with evidence; reopening it as a fresh pending would blur US-022 semantics. Post-queue cancel never called LinkedIn, so restoring `pending` (not re-queueing) is safe and honest.

**Not chosen:** Reopen everything that is grey on the calendar. Auto-requeue on reopen.

### D4 — Operator_supervision audit model

**Choice:** On successful real reopen:

- Append prior `operator_supervision.cancellation` (if present) into `cancellation_history[]` (or equivalent append-only list) with reopen metadata.
- Set `last_action` to `reopen` (or `reschedule_from_cancelled`), `last_action_at_utc`, `phase` `pre_queue`.
- Set `auto_queue_eligible` `true` (strategy-driven again once due).
- Record `reopen_history[]` entry with previous cancelled state summary, previous `scheduled_at_utc`, new `scheduled_at_utc`, reason, actor/source when supplied.
- Preserve draft content / content hashes unchanged.
- Idempotency: same key + same payload → replay success without double-append (mirror defer/cancel patterns).

Dry-run validates eligibility and schedule future-ness without metadata writes.

**Rationale:** Matches existing supervision audit patterns; keeps cancel history for “why was this cancelled?” even after reopen (modal MAY show last cancellation from history when currently pending again after refresh — post-reopen the chip is pending, so cancelled-modal copy is for still-cancelled items).

### D5 — Additive schedule-visibility cancellation fields

**Choice:** Extend schedule-visibility LinkedIn items (additive, nullable) so the cancelled modal can answer why without inventing browser-side campaign file reads:

- `cancellation_phase` (e.g. `pre_queue` / `post_queue`)
- `cancelled_at_utc`
- `cancellation_reason` (operator reason string when present; never secrets)
- Optional `reopen_eligible` boolean (server-computed from D3) so the UI does not guess

Do **not** require a second campaign-detail GET for the modal MVP if these fields cover what/why/what-next. Raw machine codes stay in expandable diagnostics.

**Rationale:** Current `ScheduleVisibilityItem` lacks cancellation context; pending-supervision intentionally omits cancelled variants. Calendar is the cancelled surface.

**Not chosen:** Browser reading campaign JSON from mounts. Forcing operators to open pending-supervision (cancelled items are not there).

### D6 — Console UX: calm chip + cancelled EventModal + reopen flow

**Choice:**

1. **Chip:** Keep cancelled visible on Week/Month; strengthen calm distinct styling/label (muted, not failed/blocked alarm). Do **not** require a new Cancelled metric chip in this change (optional later; empty-grid notes already deferred it).
2. **Modal (cancelled):** Three plain-language blocks — What (identity + LinkedIn variant / not API published), Why (reason/source/time when available; “Cancelled by operator” fallback), What next (Reopen & reschedule when `reopen_eligible` + `canMutate`; else explicit non-actionable copy).
3. **Reopen path:** Confirm (destructive-ish restore) → ScheduleEditor-style local datetime (reuse US-040I helpers) → dry-run default → real confirm → call reopen POST → success toast → refresh schedule-visibility (+ pending-supervision) → event appears as editable pending on its new local day.
4. **Cancel from active pending:** Unchanged — confirmed, destructive; copy MAY note restoration requires reopen (when shipped).
5. **Failures:** Map reopen error codes to plain language + failure toast; no silent success.

**Rationale:** Matches normative UX intent and shared DoD scenes.

**Not chosen:** Hide cancelled chips. Alarm-red cancelled styling. Opening cancelled items into the pending edit panel without explanation.

### D7 — US-040K density is follow-up only

**Choice:** Do not implement max-2-per-local-day product rules in this change. Reopen MAY reuse existing interim duplicate-slot / 72h saturation worker checks already applied to defer if those naturally apply to the new schedule; do **not** invent K’s 2/day cap. Document K as a follow-up constraint on reopen target days.

**Hard dependency check:** None — reopen does not require K to be honest/actionable.

### D8 — Honest status and acceptance gates

**Choice:** After apply: CURRENT-STATE / user-stories / progress-checklist reflect console+worker implementation evidence only; leave Acceptance criteria validated and Story accepted open until Visual DoD + walkthrough. Do not mark BL-015 closed. Do not mark US-040G/H/I Story accepted as a side effect.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operators reopen post-queue cancels expecting immediate re-queue | Spec + modal copy: returns to **pending**, not queued; strategy-driven when due |
| Failed→cancelled reopen confusion | Fail closed with clear code + modal “not reopenable; use recovery path” when such chips appear |
| Irreversibility docs (preview fallback) drift | Update supervision mechanics + note preview-fallback “irreversible through existing endpoints” is superseded for reopen-eligible cancels |
| Missing cancellation fields → weak why-copy | D5 additive schedule-visibility fields; fallback operator language when reason absent |
| Accidental US-040K scope creep | Explicit non-goal; tasks forbid 2/day product enforcement |
| Over-claiming Story accepted | Tasks gate Visual DoD + walkthrough; Vitest insufficient |
| Interim saturation codes surprise on reopen | Map existing defer-like saturation codes to plain language; density product remains K |

## Migration Plan

1. Implement worker reopen service + route + pytest; additive schedule-visibility fields.
2. Implement console cancelled modal + reopen UI; Vitest (~1280/~375); production `npm run build` into worker static path.
3. Update ops mechanics docs for reopen; honest CURRENT-STATE / product status language.
4. `/opsx-verify` → implementation commit (approval-gated) → sync → archive (separate commits).
5. Explicit push → explicit deploy to `192.168.0.194:8010`.
6. Capture Visual DoD (desktop + mobile) for US-040J scenes; operator walkthrough.
7. Only then mark Story accepted / Acceptance criteria validated; BL-015 remains open.

**Rollback:** Redeploy prior worker image + static assets. Reopen is additive; cancelled variants without reopen remain cancelled. No LinkedIn API side effects to unwind.

## Open Questions

1. Exact endpoint path string (`/reopen-linkedin-variant` vs `/reschedule-cancelled-linkedin-variant`) — prefer shorter `reopen-linkedin-variant` with required `new_scheduled_at_utc`; finalize at apply if naming bikeshed arises (contract semantics fixed here).
2. Whether schedule-visibility should expose a short `cancellation_source` (`operator` / `recovery`) for why-copy — default to derive from phase + last recovery event if cheap; otherwise omit and use phase+reason.
3. Optional Cancelled metric chip — **out of scope** unless apply discovers filters cannot surface cancelled items; filters already include publication state `cancelled`.
