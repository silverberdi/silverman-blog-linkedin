## Context

US-049 (BL-020 Story 1) is implemented locally: Postgres table `editorial_content_backlog_items` in `silverman_linkedin_db`, authenticated CRUD-lite at `/editorial/content-backlog`, and an Authority Manager Content backlog modal. Canonical capability: `openspec/specs/editorial-content-backlog/spec.md`. Flow B discovery / draft / gap-trigger remain independent of the backlog. US-050 Story 2 asks operators to identify topic dependencies and prioritize / reprioritize that optional queue — without gating Flow B and without claiming Story accepted or BL-020 closed.

Constraints: ADR-0001 (HTTP only); ADR-0002 (blog canonical); reuse US-049 store/API patterns; no new UI kit; no discovery seed as required wiring; no deploy in this change.

Stakeholders: editorial manager (dependencies + priority queue); system operator (same Postgres DB); Flow B maintainers (independence).

## Goals / Non-Goals

**Goals:**

- Persist dependency edges between backlog items via stable `item_id` references; reject cycles, self-edges, and dangling refs with structured 4xx.
- Support prioritization and reprioritization (coarse `priority` enum + explicit queue ordering) over authenticated worker HTTP.
- Thin Authority Manager extension of the existing Content backlog surface: show deps; change priority / queue order; clear failure messaging.
- Keep empty/unused backlog and unused dependency fields non-blocking for Flow B.
- Pytest (+ Vitest for UI); docs/progress only for demonstrated criteria.

**Non-Goals:**

- Discovery seed/override from backlog as required input (MAY note as future optional).
- Auto-publish, packaging pipeline, LinkedIn enablement changes.
- New app / PrimeReact / chrome redesign.
- Flow A or gap-trigger enablement default changes.
- Story accepted / BL-020 closed / deploy / push.

## Decisions

### D1 — Dependency model: outbound `depends_on_item_ids` on the item

**Choice:** Each backlog item gains an optional list field `depends_on_item_ids: string[]` (default `[]`) meaning “this item depends on these other backlog items.” Persist as JSONB on `editorial_content_backlog_items` (same pattern as `linkedin_derivatives`). Memory store mirrors the field.

**Semantics:** Dependency is planning metadata only — it does not schedule Flow B, block discovery, or enforce publish order outside the backlog UI/API.

**Validation (fail closed, structured 4xx):**

- Every referenced id MUST exist in the backlog store at write time.
- Self-reference forbidden.
- Duplicate ids in the list collapsed or rejected (prefer reject with clear message).
- Bounded list length (e.g. ≤ 20, match derivative note bound class).
- **Cycle rejection:** after applying the proposed edge set for the item, the directed graph of all items MUST be acyclic (DFS / Kahn). Reject with a stable error code (e.g. `dependency_cycle`) and actionable message.
- Dangling / unknown id → `dependency_not_found` (or equivalent) 4xx; no partial persist.

**Why:** Smallest extension of the US-049 document model; one round-trip on create/update; no second SoT. Edge table with FKs is cleaner for DB integrity but heavier for memory:// parity and US-049 patterns.

**Alternatives:**

| Option | Rejected because |
|--------|------------------|
| Separate edge table only | More schema/API surface for v1; still need cycle checks |
| Free-text dependency notes only | Does not satisfy “identify dependencies” as stable refs |
| Bidirectional required edges | Over-modeling; outbound list is enough for operators |

### D2 — Prioritization: keep `priority` enum + add `queue_rank`

**Choice:**

- Keep existing `priority` enum (`low` | `medium` | `high`) — changing it via PUT is coarse **prioritization / reprioritization**.
- Add server-managed / client-updatable **`queue_rank`**: non-negative integer; **lower = earlier in the operator queue**.
- On create: if omitted, assign `queue_rank = max(existing)+1` (append), or a small default band offset by priority (prefer simple append).
- List default order: `queue_rank ASC`, then priority band (`high` before `medium` before `low`), then `updated_at_utc DESC`.
- **Reprioritize within the queue:** authenticated client updates `queue_rank` on one or more items via existing PUT, and/or a thin authenticated `PUT /editorial/content-backlog/reorder` body `{ "ordered_item_ids": ["…"] }` that reassigns contiguous ranks `0..n-1` for the listed ids (ids not listed keep ranks; missing ids → 4xx). Prefer shipping **PUT field + reorder endpoint** when both are cheap; if one must drop for coherence, keep PUT `queue_rank` + priority (reorder can be UI-computed swaps).

**Why:** US-050 needs both “priority” language (already in Story 1) and explicit reorder so operators can reshuffle the queue without inventing new enum values.

**Alternatives:**

| Option | Rejected because |
|--------|------------------|
| Priority enum only | Weak “reprioritize the queue” UX; ties unresolved |
| Fractional ranks only | Unnecessary complexity vs integer ranks + reorder |
| Drag-only client order without persistence | Violates worker HTTP SoT |

### D3 — HTTP surface (extend US-049; ADR-0001)

**Choice:**

- Extend create/update request/response documents with `depends_on_item_ids` and `queue_rank`.
- List/detail responses include both fields.
- Optional `PUT /editorial/content-backlog/reorder` for bulk rank reassignment (authenticated).
- Unauthenticated → reject. Validation / cycle / dangling → **4xx** with stable codes. Store unavailable → existing **5xx** / unavailable codes. No secrets in bodies.
- MUST NOT introduce n8n Execute Command; MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

**Why:** Same path family operators already use; no Flow B route pollution.

### D4 — Optional enrichment / Flow B independence

**Choice:** Do not import backlog dependency or rank logic into `flow_b_topic_discovery`, `flow_b_blog_draft_generation`, or `flow_b_calendar_gap_trigger`. Spec deltas reaffirm: empty backlog, unused deps, or unused ranks MUST NOT block discover / draft / gap-trigger. Discovery seed/override remains future MAY — not required in this change.

### D5 — Authority Manager thin affordance

**Choice:** Extend `ContentBacklogModal` (and API client/types) only:

- Show each item’s `depends_on_item_ids` (resolve to topic labels when list is loaded).
- Edit dependencies (multi-select / id checklist of other items).
- Change `priority` and move up/down (or explicit rank) to reprioritize; call reorder or PUT.
- Plain-language errors for cycle, missing dependency, validation, auth.
- Copy: optional enrichment; save ≠ Flow B trigger / LinkedIn publish.
- No chrome redesign; no new UI kit.

### D6 — Schema ensure

**Choice:** Idempotent `ALTER TABLE … ADD COLUMN IF NOT EXISTS` (or recreate ensure DDL) for `depends_on_item_ids JSONB NOT NULL DEFAULT '[]'` and `queue_rank INTEGER NOT NULL DEFAULT 0`. Backfill existing rows: `depends_on_item_ids = []`; assign ranks by current list order (`updated_at_utc DESC` or create order). Memory store defaults the same. No Alembic unless project already requires it for these tables (it does not).

### D7 — Tests and docs

**Choice:**

- Pytest: dependency round-trip; dangling rejected; self-dep rejected; cycle rejected; priority + queue_rank update; reorder (if shipped); list sort contract; auth; secret-free; Flow B independence regression (empty backlog / no import into discovery/gap-trigger).
- Vitest: dependency edit + prioritize/reprioritize + error display on Content backlog modal.
- CURRENT-STATE / user-stories / progress-checklist: update only after demonstrated criteria; never mark Story accepted or BL-020 closed by implementation alone.

### D8 — Retire US-049 “dependency UX out of scope” exclusion

**Choice:** Replace / narrow the canonical requirement that excluded US-050 dependency UX so Story 2 deps + prioritization are in scope, while discovery seeding, packaging, and auto-publish remain out of scope.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operators treat dependencies as Flow B gates | Spec + UI copy; no wiring into discover/trigger |
| Cycle detection cost grows | Bound list size; backlog is small hand-curated set |
| JSONB deps without DB FK | Validate existence + cycles at write edge; tests cover dangling |
| Rank collisions after concurrent edits | Optimistic `row_version` on item PUT; reorder can resequence atomically |
| Scope creep into discovery seed | Explicit non-goal; MAY only in prose |

## Migration Plan

1. Schema ensure adds columns with safe defaults; existing items get empty deps and assigned ranks.
2. No Flow B enablement or n8n export changes.
3. Rollback: stop reading new fields in UI/API; columns may remain (harmless) or ignore in a follow-up.
4. Deploy is out of scope for this change’s apply.

## Open Questions

- Whether bulk `PUT …/reorder` ships in the same apply vs UI-only rank swaps via per-item PUT — prefer reorder if both stay thin; otherwise per-item `queue_rank` is sufficient for AC.
- Exact stable error code strings (`dependency_cycle`, `dependency_not_found`, `dependency_self`, `queue_rank_invalid`) — lock in apply to match existing backlog error style.
