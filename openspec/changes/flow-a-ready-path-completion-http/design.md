## Context

BL-005 Manual run on `192.168.0.194` completed ready-path n8n through publish → package → schedule (`campaign_id=flow-a-2026-07-15-keep-contracts-boring`, `state=distribution_scheduled`), but:

- `POST /publish-blog-post` body omitted `git_publication` / `live_site_confirmation` → handoff-only; public post left untracked in checkout; no `blog_git_publication` / `blog_live_site_publication`.
- No HTTP route wraps `complete_flow_a_source_lifecycle` → source Markdown+PNG remain in `blog-posts/ready/` (legacy ready location; lifecycle Python already supports ready→processed fallback).
- Calendar terminal updates live only inside `POST /editorial-calendar/execute-flow-a-due` → ready-path campaigns never get a calendar row.

Canonical n8n spec today **forbids** invoking lifecycle moves from Flow A orchestration (“source remains in ready”). That contract conflicts with BL-005 / US-013 ACs and GLOSSARY “fully unattended Flow A”. This change intentionally supersedes that orchestration rule for a dedicated post-schedule completion HTTP step (worker still owns filesystem moves; n8n remains HTTP-only — ADR-0001).

Active change `run-fully-unattended-flow-a-test-bl-005` stays open for dual Manual+Schedule evidence after this ships.

## Goals / Non-Goals

**Goals:**

- Authenticated HTTP completion after schedule: lifecycle → `flow_a_complete` + processed files; optional calendar upsert/reconcile when `editorial-calendar/calendar.json` exists.
- n8n export: configurable git/live opt-in on publish; post-schedule call to completion endpoint; IF branching; no LinkedIn publication nodes.
- Preserve fail-closed git/live env flags; opt-in request fields default false in worker API.
- Enable BL-005 revalidation without mid-run operator Git or manual `mv` to processed.

**Non-Goals:**

- Replacing ready-path with calendar `execute-flow-a-due` as the n8n body.
- Mandatory queue-accept for every ready-path run (lifecycle legacy ready path is sufficient for current campaigns).
- BL-006 / BL-007 / LinkedIn API publish.
- Closing BL-005 product stories in this change’s apply/verify alone.

## Decisions

### D1 — Single completion endpoint after schedule

**Decision:** Add `POST /complete-flow-a-ready-path` that (1) runs `complete_flow_a_source_lifecycle`, then (2) when `update_calendar` is true (default), upserts/reconciles a calendar item from campaign facts.

**Alternatives:** Separate lifecycle + calendar routes (more n8n nodes); call lifecycle only and leave calendar to operators (fails US-014).

**Rationale:** One authenticated step matches n8n IF-branch style used for publish/package/schedule; calendar is optional-fail-partial so lifecycle success is not rolled back.

### D2 — Calendar upsert for ad-hoc ready campaigns

**Decision:** Resolve by `campaign_id` then by normalized `source_relative_path` / original ready path. If a matching item exists → `complete_flow_a_calendar_item` + atomic save. If none → insert a new `completed` item populated from campaign public slug, URLs, LinkedIn summary statuses, and `flow_a_completion` facts (same shape as connector completion). If calendar file absent → `calendar_update_status=skipped_calendar_absent` without failing the HTTP overall status when lifecycle succeeded.

**Alternatives:** Require pre-planned calendar rows only; fail when no match.

**Rationale:** BL-005 posts are operator-dropped ready files without prior calendar planning; calendar is configured (existing completed items) so “when configured” implies write a record, not skip forever.

### D3 — n8n git/live opt-in via Set Configuration

**Decision:** Extend Publish Blog Post JSON body builder to include `git_publication` and `live_site_confirmation` when Set Configuration booleans are true. Repository export defaults both to `false` (safe); server BL-005 / unattended ops set both `true` while env flags remain authoritative fail-closed.

**Alternatives:** Hardcode `true` in export (unsafe surprise side effects on import).

### D4 — Supersede “no lifecycle from n8n” requirement

**Decision:** MODIFIED requirement: orchestration MUST call ready-path completion HTTP after successful schedule; MUST NOT move files via Execute Command / filesystem nodes; worker endpoint performs moves. Idempotent re-runs return skipped/completed without duplicating damage.

**Rationale:** Required to meet source lifecycle ACs without switching to calendar-due connector.

### D5 — No new LinkedIn publication coupling

**Decision:** Completion endpoint MUST NOT queue or publish LinkedIn variants. Variants remain `pending` until BL-007.

### D6 — Existing Manual campaign remediation

**Decision:** Implementation may be revalidated against a fresh serialized post or by re-invoking publish (idempotent git/live) + new completion endpoint for `flow-a-2026-07-15-keep-contracts-boring` during controlled ops — owned by BL-005 apply after deploy, not by inventing special repair APIs.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Calendar insert creates duplicate items if matching logic weak | Match campaign_id and normalized ready/processed/original paths; tests for match-before-insert |
| Partial calendar failure after lifecycle | Overall `partial` + structured `calendar_update_status` / errors; do not undo processed move |
| Git push while remote diverged | Existing git publication codes; n8n publish IF already treats non-completed as failure |
| Live probe 403/CDN false fail | Existing live-site confirmation contract (`partial`); document probe evidence in BL-005 ops |
| Spec ↔ old “source remains ready” docs drift | Update README / CURRENT-STATE after sync; BL-005 evidence language uses GLOSSARY layers |
| Mixing BL-007 WIP in worker tree | Keep apply scoped; do not commit unrelated LinkedIn publication WIP |

## Migration Plan

1. Implement worker endpoint + tests locally; update n8n export + lightweight workflow tests.
2. `/opsx-verify` → commit (exclude unrelated WIP) → sync → archive this change.
3. Deploy worker on `192.168.0.194`; re-import Flow A n8n (inactive then activate per existing US-010 pattern); set Set Configuration git/live `true` on server.
4. Resume `run-fully-unattended-flow-a-test-bl-005`: clear/hold Post A ready residue; revalidate Manual (or completion-only if handoff already present + republish for git); then Post B Schedule.

**Rollback:** Re-import prior Flow A export; leave new endpoint unused (harmless); calendar inserts are additive — reverse only with operator approval.

## Open Questions

- None blocking propose: live probe soft-fail remains `partial` per existing live-site specs; BL-005 operators accept that vs declaring site published/live only on `confirmed`.
