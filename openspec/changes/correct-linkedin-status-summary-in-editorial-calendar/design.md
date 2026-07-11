## Context

Flow A calendar completion persists `flow_a_completion` summary evidence when a campaign reaches `flow_a_complete`. `_build_completion_facts_from_campaign` in `editorial_calendar_flow_a_execute.py` currently reads:

- `linkedin_package.get("status")`
- `linkedin_distribution.get("status")`

Campaign metadata uses different shapes per canonical specs:

- `linkedin_package.package_status` (for example `generated`) — see `linkedin-derivative-package-generation`
- `linkedin_distribution` — object with `distribution_id`, `strategy`, `anchor_utc`, `variant_ids`; no top-level `status` field — see `linkedin-distribution-scheduling-model`
- Per-variant schedule evidence lives in top-level `campaign["variants"][]` (`scheduled_at_utc`, `publish_state`) — not nested under `linkedin_distribution`

HTTP step results return `status: completed` for successful package and schedule operations, and tests/examples expect calendar summary values `linkedin_package_status: completed` and `linkedin_distribution_status: completed`. The field-name mismatch causes `null` summaries on otherwise completed calendar items.

Reconciliation and completion both call `_build_completion_facts_from_campaign`. Idempotency and conflict detection live in `editorial_calendar_plan.complete_flow_a_calendar_item` via `_flow_a_completion_equivalent`.

**Planner constraint (forward-only scope):** `find_due_items` returns only `scheduled` and `due` items. Calendar items already `status=completed` are excluded from `execute_due_editorial_calendar_flow_a`. Automatic HTTP repair therefore applies to reconcile-close paths, not to re-visiting closed rows.

## Goals / Non-Goals

**Goals:**

- Derive accurate LinkedIn summary statuses from authoritative campaign metadata when completing or reconciling calendar items.
- Persist non-null LinkedIn summaries on **post-execution completion** and on **reconcile-close** of `scheduled`/`due` items.
- Preserve idempotency when stored summaries already match derived values.
- Allow planner-level **repair** when an already-`completed` item has `null` or missing LinkedIn summary fields and derived facts supply non-null values while other fields match (used by reconcile helper and unit tests; not routed through HTTP for historical rows).
- Keep reconciliation side-effect free (no republish, repackage, reschedule, lifecycle moves).

**Non-Goals:**

- Changing campaign metadata schema or HTTP step response shapes.
- Surfacing LinkedIn API publication states in calendar summaries.
- New endpoints, n8n changes, or bulk migration scripts.
- Extending `find_due_items` to include `completed` items with incomplete LinkedIn summaries.

## Decisions

### 1. Centralize derivation in a shared helper

**Decision:** Add `derive_flow_a_linkedin_completion_statuses(campaign: dict) -> tuple[str | None, str | None]` in `editorial_calendar_plan.py` (alongside `FLOW_A_COMPLETION_SUMMARY_KEYS`). `_build_completion_facts_from_campaign` calls this helper.

**Rationale:** Single source of truth for calendar summary derivation; testable without full executor setup; keeps reconciliation and post-execution completion aligned.

**Alternative considered:** Derive inline in `editorial_calendar_flow_a_execute.py`. **Rejected** — duplicates logic if planner tests or future callers need the same mapping.

### 2. Package status mapping

**Decision:** Set `linkedin_package_status` using campaign evidence in priority order:

1. When `linkedin_package.package_status == "generated"` → `"completed"`.
2. When campaign `state` is `derivatives_generated`, `distribution_scheduled`, `distribution_complete`, or `flow_a_complete` and `linkedin_package` exists with `package_id` → `"completed"`.
3. When package metadata indicates failure (future-safe: explicit failure marker if present) → `"failed"`.
4. Otherwise → `null`.

**Rationale:** Calendar summary uses step-outcome vocabulary (`completed`) consistent with tests, examples, and HTTP results; maps from canonical metadata field `package_status`.

**Alternative considered:** Store raw `generated` in calendar. **Rejected** — breaks existing examples, tests, and operator expectation that completion summaries use operational outcome language.

### 3. Distribution status mapping

**Decision:** Set `linkedin_distribution_status` using campaign evidence in priority order:

1. When campaign `state` is `distribution_scheduled`, `distribution_complete`, or `flow_a_complete` and `linkedin_distribution` exists with `distribution_id` → `"completed"`.
2. When top-level `campaign["variants"][]` entries include `scheduled_at_utc` and `publish_state` `pending` for all scheduled variants → `"completed"`.
3. When scheduling evidence is absent or campaign state is before `distribution_scheduled` → `null`.

**Rationale:** No `linkedin_distribution.status` in metadata; lifecycle state plus distribution object and variant schedule rows are authoritative evidence that scheduling completed.

### 4. Repair semantics (planner-level, forward-only HTTP)

**Decision:** Extend completion equivalence in `editorial_calendar_plan.py`:

- When a completed item's stored `flow_a_completion` has `null` or missing `linkedin_package_status` and/or `linkedin_distribution_status`, and newly derived facts supply non-null values while all other summary keys and canonical parent fields match, treat as **repair** (persistable mutation, not conflict, not idempotent skip).
- When stored LinkedIn summary values are **non-null and differ** from newly derived values, retain existing `calendar_completion_facts_conflict` behavior.

**HTTP repair scope (forward-only):**

- **In scope:** `scheduled`/`due` item reconciles to `completed` via `execute-flow-a-due` → first persist uses corrected derivation (fixes the common “campaign done, calendar still open” case).
- **In scope:** Post-execution Flow A completion → first persist uses corrected derivation.
- **Out of scope for HTTP:** Item already `status=completed` with null summaries — excluded by `find_due_items`; operator may patch `calendar.json` manually for legacy rows.

**Rationale:** Smallest change that fixes the bug for all forward paths and open reconcile paths. Strict equivalence would block null→completed as conflict if a caller invokes `complete_flow_a_calendar_item` on an already-completed row.

**Alternatives considered:**

- Extend `find_due_items` for `completed` repair scan. **Rejected** — out of scope; unnecessary for construction phase with few legacy rows.
- One-off migration script. **Rejected** — violates scope guardrails.

### 5. No campaign metadata writes

**Decision:** Read-only derivation from campaign JSON. Do not add `status` fields to `linkedin_package` or `linkedin_distribution` objects.

**Rationale:** Smallest diff; campaign schema is stable and spec'd; calendar summary is a derived view.

### 6. Realistic test fixtures

**Decision:** Replace fictional campaign fixtures using `linkedin_package: {"status": "completed"}` with shapes matching production metadata (`package_status: "generated"`, `linkedin_distribution` with `distribution_id`, top-level `variants[]`).

**Rationale:** Existing executor tests pass today while masking the production bug.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Repair overwrites operator-customized summary values if someone manually set non-null incorrect values | Non-null stored values that differ from derived facts still fail closed with `calendar_completion_facts_conflict` |
| Derived `completed` could mask partial package/distribution failure on inconsistent campaign metadata | Derivation requires lifecycle state + object evidence; `flow_a_complete` reconciliation already gates on processed lifecycle |
| Legacy `completed` rows keep null summaries until manual edit | Documented in proposal non-goals and migration plan; acceptable for small historical set |
| Reconciliation repair triggers calendar write on every run until persisted | After first successful repair, equivalence matches and subsequent runs are idempotent no-op |

## Migration Plan

1. Deploy worker with derivation fix (Mac dev → Docker on `192.168.0.194` per project norms).
2. **Open calendar items:** Run `POST /editorial-calendar/execute-flow-a-due` with `dry_run=false` for any `scheduled`/`due` item whose campaign is already `flow_a_complete` — reconciliation closes with non-null LinkedIn summaries and no Flow A side effects.
3. **Legacy completed rows (optional):** If any item is already `status=completed` with null LinkedIn summaries, operator edits those two fields manually in `editorial-calendar/calendar.json` once (out of band; not automated in this change).
4. Verify `calendar.json` items show populated `flow_a_completion.linkedin_package_status` and `linkedin_distribution_status` for new completions and reconciled items.
5. Rollback: revert worker image; calendar writes are forward-only but original null state is low-risk.

## Open Questions

_(none — derivation rules are fully determined by existing campaign metadata specs; forward-only repair scope is decided)_

## Apply handoff (next context)

Run `/opsx-apply correct-linkedin-status-summary-in-editorial-calendar` and implement `tasks.md` in order:

1. Derivation helper in `editorial_calendar_plan.py`
2. Wire `_build_completion_facts_from_campaign`
3. Repair equivalence in `complete_flow_a_calendar_item`
4. Tests per tasks §4 (realistic fixtures; HTTP reconcile path + planner unit repair)
5. `/opsx-verify`, then update `CURRENT-STATE` and product checklist only with demonstrated evidence

Do **not** mix `auto_queue_pending` or other unrelated changes into the BL-003 implementation commit.
