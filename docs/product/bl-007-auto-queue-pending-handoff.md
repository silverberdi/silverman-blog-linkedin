# BL-007 handoff — `auto_queue_pending` WIP (2026-07-11)

**Status:** Deferred construction WIP — **not** on `main`, **not** an approved OpenSpec change, **not** part of BL-003.  
**Target backlog:** [BL-007 — Implement Scheduled LinkedIn Publication Execution](backlog.md#bl-007--implement-scheduled-linkedin-publication-execution) (US-018 / US-019 / US-020).  
**Origin:** Operator request during BL-003 planning (*“haz que los post pendientes se puedan enviar”*) after BL-002 published only `executive-recruiter` and left sibling variants `pending`. Explicitly excluded from BL-003 OpenSpec scope.

## Intent

Provide a single worker call that, when opted in:

1. Finds Flow A variants still in `pending` (and re-queue-eligible `failed` where queue rules already allow).
2. Enqueues them (`pending` → `queued`) via the existing queue path.
3. Publishes eligible `queued` variants via the existing publish-due path.

Canonical v1 contract today (on `main` / specs) is still **two steps**: `POST /queue-linkedin-publication` then `POST /publish-linkedin-due-variants`. This WIP adds an **opt-in combine** (`auto_queue_pending=true`) for construction and scheduled-execution convenience — it must be formalized under BL-007 before merge.

## Local uncommitted artifacts (handoff inventory)

Do **not** mix these into unrelated commits (BL-004, calendar, etc.). Treat as one future OpenSpec apply.

| Path | Role |
|------|------|
| `src/silverman_blog_linkedin/linkedin_publication_flow.py` | `auto_queue_pending` on publish-due; `_collect_pending_targets`, `_auto_queue_pending_variants`, due/scheduled helpers |
| `src/silverman_blog_linkedin/main.py` | Request field `auto_queue_pending` on `POST /publish-linkedin-due-variants` + logging |
| `tests/test_linkedin_publication.py` | Unit/HTTP coverage for auto-queue path |
| `deploy/server/run-publish-pending-linkedin-variants.sh` | Operator script: dry-run default; `--real`, `--respect-schedule`, optional campaign/variant |
| `deploy/server/finish-pending-linkedin-publication.sh` | Mac → server scp + run helper |
| `n8n/workflows/silverman-blog-linkedin-publish-pending.json` | Manual inactive workflow calling publish-due with `auto_queue_pending: true` |

**Git note (2026-07-15):** These files may appear modified/untracked in the working tree. They are **not** committed on `main` as of `ffa3101`. A server image may have been rebuilt with this WIP during construction smoke — do not treat server presence as product completion.

## Proposed HTTP contract (from WIP)

```json
{
  "dry_run": true,
  "publish_now": false,
  "auto_queue_pending": true,
  "campaign_id": null,
  "variant": null
}
```

- Default fail-closed: `auto_queue_pending=false` preserves current two-step behavior.
- Real LinkedIn API still requires `dry_run=false` and `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`.
- `--respect-schedule` / `publish_now=false` should honor `scheduled_at_utc` (cadence — US-020).

## Mapping to BL-007 acceptance criteria

| Story | Criterion | WIP contribution | Still required in BL-007 OpenSpec |
|-------|-----------|------------------|-----------------------------------|
| US-018 | Identify due variants | Helpers scan pending/due by schedule | Spec scenarios; planner vs publication due semantics; cross-campaign scan rules |
| US-018 | Move only eligible variants to queued | Reuses queue eligibility | Formalize “auto-queue then publish” vs separate endpoints; no double-queue |
| US-018 / US-019 | Publish once / store URN / failures clear | Reuses publish-due + existing metadata | Idempotency with auto-queue; warning codes; operator-visible results |
| US-019 | Avoid duplicate retries | Existing published skip | Spec + tests for auto-queue + already-published / already-queued |
| US-020 | Respect cadence and sequence | `publish_now` / schedule gating in WIP | Normative ordering across variants/audiences; stagger rules |

## Relationship to prior items

| Item | Relationship |
|------|----------------|
| **BL-002** | Closed with one controlled real publish (`executive-recruiter`). Remaining `pending` variants are expected leftovers, not a BL-002 defect. See [phase3-us003 report](../operations/phase3-us003-linkedin-publication-validation-2026-07-11.md). |
| **BL-003** | Unrelated (calendar LinkedIn **package/schedule summary** fields). Design/tasks of that change list `auto_queue_pending` as **out of scope**. |
| **BL-004 / BL-005** | n8n activation / unattended Flow A — do not activate `publish-pending` workflow as a substitute for scheduled publication design. |
| **BL-006** | Variant review before queue — may constrain which states auto-queue may touch. |
| **Canonical specs** | `openspec/specs/linkedin-publication-integration/spec.md` documents separate queue and publish-due; BL-007 delta MUST modify those requirements if auto-queue is retained. |

## How to start BL-007 (OpenSpec)

1. `/opsx-propose` a change scoped to BL-007 (suggested name pattern: `implement-scheduled-linkedin-publication-execution` or narrower `add-auto-queue-pending-to-publish-due` if slicing).
2. In proposal/design:
   - Decide keep **opt-in `auto_queue_pending`** vs keep strict two-step only + n8n/orchestration composing calls.
   - Require ADR-0001 (HTTP only); no Execute Command.
   - Keep publication enablement fail-closed.
   - Define due window, ordering, and interaction with review (BL-006) if any.
3. `/opsx-apply` should **absorb or rewrite** this WIP under the approved change — not land as an undocumented drive-by.
4. Sync specs → verify → commit implementation separately from unrelated WIP → archive.
5. Update [progress-checklist.md](progress-checklist.md) / [user-stories.md](user-stories.md) only with demonstrated evidence; close BL-007 only after controlled operational validation.

## Explicit non-goals for this handoff

- Committing the WIP without an approved OpenSpec change.
- Marking US-018–US-020 complete based on construction smoke alone.
- Activating n8n unattended scheduling as part of documenting this WIP.
- Changing calendar `flow_a_completion` LinkedIn summary fields (BL-003 — already closed).

## Operator smoke (when BL-007 apply is active)

After approved implementation is committed and deployed:

```bash
# Dry-run (safe)
./deploy/server/run-publish-pending-linkedin-variants.sh

# Real + schedule respect (requires publication enabled)
./deploy/server/run-publish-pending-linkedin-variants.sh --real --respect-schedule
```

Prefer campaign/variant filters during controlled windows. Restore `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` after validation unless a later backlog item keeps it enabled.

## Related links

- Backlog: [backlog.md](backlog.md) § BL-007  
- Stories: [user-stories.md](user-stories.md) § US-018–US-020  
- Specs: `openspec/specs/linkedin-publication-integration/spec.md`  
- Prerequisites: [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md)  
- BL-002 evidence: [phase3-us003-linkedin-publication-validation-2026-07-11.md](../operations/phase3-us003-linkedin-publication-validation-2026-07-11.md)  
