## Why

Flow A calendar completion writes `flow_a_completion.linkedin_package_status` and `flow_a_completion.linkedin_distribution_status` from campaign metadata fields that do not exist (`linkedin_package.status`, `linkedin_distribution.status`). Completed campaigns therefore persist `null` LinkedIn summary values in `editorial-calendar/calendar.json`, making the editorial calendar unreliable for operators reviewing package and scheduling outcomes (BL-003).

## What Changes

- Fix `_build_completion_facts_from_campaign` to derive LinkedIn summary statuses from the canonical campaign metadata shape and lifecycle evidence.
- Map package generation evidence from `linkedin_package.package_status` (and related lifecycle state) to calendar summary `linkedin_package_status`.
- Map distribution scheduling evidence from `linkedin_distribution` presence, top-level `variants[]` schedule metadata, and campaign lifecycle state to calendar summary `linkedin_distribution_status`.
- Preserve idempotent reconciliation: equivalent derived facts MUST NOT trigger calendar rewrites; conflicting facts MUST still fail with `calendar_completion_facts_conflict`.
- Extend `complete_flow_a_calendar_item` equivalence so `null` or missing LinkedIn summary fields on an already-`completed` item can be repaired when derived facts supply non-null values and other fields match (planner contract; supports reconcile close paths).
- Add behavioral tests covering completion and reconciliation paths with **realistic** campaign metadata shapes (`package_status: generated`, not fictional `linkedin_package.status`).
- **Forward-only operator repair:** `POST /editorial-calendar/execute-flow-a-due` repairs LinkedIn summaries when a **`scheduled` or `due`** calendar item reconciles to `completed` against an existing `flow_a_complete` campaign.

## Goals

- Calendar `flow_a_completion` accurately reflects package generation and distribution scheduling for completed Flow A campaigns (US-006).
- Completed campaign terminal facts remain immutable unless an operator resolves a documented conflict (US-007).
- No duplicate publish/package/schedule/lifecycle side effects during reconciliation (US-007, US-008).

## Non-Goals

- LinkedIn API publication status (`pending`, `queued`, `published`) — out of scope; summary fields describe package/scheduling only.
- Changing campaign metadata schema (`linkedin_package`, `linkedin_distribution` objects).
- New HTTP endpoints or n8n workflow changes.
- Rewriting operator `notes` or unrelated calendar item fields.
- **Automatic HTTP repair for calendar items already `status=completed` with null LinkedIn summaries.** `find_due_items` excludes `completed` items; extending the planner is out of scope for this change.
- Bulk migration scripts.

## Capabilities

### New Capabilities

_(none — bug fix within existing calendar completion behavior)_

### Modified Capabilities

- `editorial-calendar-flow-a-execution-connector`: Clarify how `flow_a_completion` LinkedIn summary fields are derived from campaign metadata when completing or reconciling calendar items.
- `editorial-calendar-orchestration`: Clarify allowed values and derivation rules for `flow_a_completion.linkedin_package_status` and `flow_a_completion.linkedin_distribution_status`, and null-summary repair semantics in `complete_flow_a_calendar_item`.

## Impact

**Backlog / user stories:** BL-003; US-006 (show actual package and distribution status), US-007 (immutable completed facts, reconciliation idempotency), US-008 (no unrelated data changes).

**Acceptance criteria addressed:**
- US-006: show actual package-generation and distribution-scheduling status in calendar summaries on **new** completions and on **reconcile-close** of `scheduled`/`due` items.
- US-007: preserve idempotent reconciliation and immutability for already-correct completion facts.
- US-008: limit changes to LinkedIn summary derivation; no republish/repackage/reschedule.

**Acceptance criteria excluded:**
- Live operational validation on production server.
- n8n activation; LinkedIn API publication proof.
- Automatic repair of historical `completed` items via `execute-flow-a-due` (operator may edit `calendar.json` manually for a small number of legacy rows).

**Code:** `src/silverman_blog_linkedin/editorial_calendar_flow_a_execute.py` (`_build_completion_facts_from_campaign`), `src/silverman_blog_linkedin/editorial_calendar_plan.py` (derivation helper + repair equivalence).

**Tests:** `tests/test_editorial_calendar_flow_a_execute.py`, `tests/test_editorial_calendar_completion.py`.

**Docs/examples:** `docs/examples/editorial-calendar/calendar.example.json` only if example values need alignment with derivation rules.

**APIs:** No new routes. Existing `POST /editorial-calendar/execute-flow-a-due` populates corrected summaries when reconciling **`scheduled`/`due`** items to `completed`.

**Historical data (operator, out of band):** If legacy calendar rows are already `completed` with null LinkedIn summaries, patch those fields manually in `editorial-calendar/calendar.json` once after deploy, or leave them as-is until a future change extends planner repair discovery.
