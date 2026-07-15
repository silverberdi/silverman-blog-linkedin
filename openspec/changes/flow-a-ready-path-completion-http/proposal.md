## Why

BL-005 Manual evidence (`05-keep-contracts-boring`) proved ready-path n8n can reach `distribution_scheduled` with package + staggered schedule, but **cannot** meet US-012–US-014 full-path ACs: publish omits `git_publication` / `live_site_confirmation` opt-in (handoff-only despite env flags `true`), there is **no** authenticated HTTP route for `complete_flow_a_source_lifecycle` (source stuck in `blog-posts/ready/`), and calendar terminal records are owned only by `execute-flow-a-due`. Without closing that orchestration gap, unattended Flow A validation stays FAIL. Evidence: [bl-005-unattended-flow-a-validation-2026-07-15.md](../../../docs/operations/bl-005-unattended-flow-a-validation-2026-07-15.md).

## What Changes

- Expose authenticated worker HTTP for Flow A source lifecycle completion after successful distribution scheduling (wrapping existing `complete_flow_a_source_lifecycle`), including legacy ready→processed support used by current ready-path campaigns.
- Define ready-path calendar completion: when `editorial-calendar/calendar.json` is present, upsert or reconcile a completed calendar item from campaign facts after lifecycle success (no inventing due-planner semantics; no rewrite of Flow A n8n onto `execute-flow-a-due`).
- Update Flow A n8n export (`silverman-blog-linkedin-flow-a-publish.json`) so **Set Configuration** can opt into `git_publication` and `live_site_confirmation` on `POST /publish-blog-post`, and so the shared path calls lifecycle (+ calendar completion) HTTP after successful schedule — still HTTP-only (ADR-0001).
- Keep LinkedIn API publication out of Flow A; do not change LinkedIn enablement policy.
- Unblock resumption of BL-005 Manual revalidation (and then Schedule) after deploy/import — BL-005 product close remains gated on demonstrated dual evidence, not on this change alone.

## Goals

- Ready-path n8n can drive: publish (with optional git/live) → package → schedule → source lifecycle → calendar record when calendar is configured.
- Worker contracts remain fail-closed on git/live flags; opt-in fields default false.
- BL-005 (`run-fully-unattended-flow-a-test-bl-005`) can re-run Manual/Schedule against the remediated path without mid-run operator Git or filesystem moves.

## Non-Goals

- Rewriting Flow A n8n body to `POST /editorial-calendar/execute-flow-a-due` (calendar due connector remains separate).
- Mandatory queue-accept `ready`→`queued` for already-scheduled legacy ready campaigns (lifecycle already supports ready legacy fallback; optional queue wiring is deferred unless required by tests).
- BL-006 LinkedIn variant review process; BL-007 LinkedIn API scheduled publication / `auto_queue_pending`.
- Permanent changes to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Closing BL-005 / US-012–US-014 without new Manual+Schedule evidence after this change is deployed.
- n8n Execute Command; hidden Git from n8n.

## Capabilities

### New Capabilities

- `flow-a-ready-path-completion`: Authenticated HTTP completion for ready-path Flow A after schedule — source lifecycle completion endpoint and calendar upsert/reconcile from campaign when editorial calendar is configured; idempotent/safe failure shapes for n8n branching.

### Modified Capabilities

- `n8n-flow-a-blog-publish-orchestration`: Require configurable `git_publication` / `live_site_confirmation` on publish; after schedule success call ready-path completion HTTP (lifecycle + calendar); still no LinkedIn publication endpoints; repo export remains `active: false`.
- `flow-a-source-lifecycle-completion`: Cross-reference HTTP exposure used by ready-path orchestration (Python entry point behavior unchanged except as needed for HTTP result mapping).

## Impact

- **Worker:** New route(s) under `main.py` + thin service wrapper; tests for auth, eligibility, idempotency, calendar upsert; reuse `complete_flow_a_source_lifecycle` and calendar persistence helpers.
- **n8n:** Update `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` (and server re-import/activation with operator approval).
- **Ops:** After deploy, re-run BL-005 Manual (Post A hygiene) then Schedule (Post B); update CURRENT-STATE when capability is implemented/validated.
- **Product:** Does not close BL-005 by itself; enables US-012–US-014 demonstration via existing BL-005 change.

## Acceptance criteria addressed

| Story | How this change helps |
|-------|------------------------|
| **US-012** | Opt-in git + live-site confirmation from n8n when env flags enabled |
| **US-013** | Source lifecycle completable via HTTP after schedule |
| **US-014** | Campaign already produced by current path; calendar record via ready-path completion |

## Acceptance criteria intentionally excluded

- LinkedIn API real publish (BL-007).
- Variant review policy (BL-006).
- Demonstrating BL-005 PASS in this change’s apply (owned by `run-fully-unattended-flow-a-test-bl-005` after this is live).
