# Flow A Incomplete Campaign Recovery (US-031 + US-032)

Operator contract for authenticated incomplete Flow A campaign recovery:
inspect last-valid-stage, resume unfinished worker stages idempotently, repair
allowlisted metadata/filesystem mismatches, classify recovery actions, preserve
attempt history, and safely cancel recovery when it is not appropriate.

## Status

- **Accepted 2026-07-18** against automated fixture evidence.
- **BL-012 closed 2026-07-18.**
- Worker endpoints **deployed** on `192.168.0.194` (`BUILD_REVISION=018aa36`).
- Evidence: [bl-012-incomplete-campaign-recovery-acceptance-2026-07-18.md](bl-012-incomplete-campaign-recovery-acceptance-2026-07-18.md).

This capability covers **BL-012 / US-031 + US-032**. It does **not** implement
LinkedIn API publication recovery (BL-008 / US-021–US-022), production n8n
activation, Git push, live-site confirmation, or LinkedIn API publish.

## Endpoints

All four require the worker Bearer API key (`Depends(require_api_key)`).
Missing/invalid auth returns HTTP 401. Invalid bodies return HTTP 422.
Clients must not supply absolute filesystem paths.

| Operation | Method / path | Mutation |
|-----------|---------------|----------|
| Inspect | `GET /flow-a/incomplete-campaign-recovery/{campaign_id}` | None (read-only; no ledger writes) |
| Resume | `POST /flow-a/incomplete-campaign-recovery/resume` | Yes (optional `dry_run`) |
| Repair | `POST /flow-a/incomplete-campaign-recovery/repair` | Yes (optional `dry_run`) |
| Cancel | `POST /flow-a/incomplete-campaign-recovery/cancel` | Yes (optional `dry_run`) |

### Inspect

```bash
curl -sS \
  -H "Authorization: Bearer ${SILVERMAN_BLOG_LINKEDIN_API_KEY}" \
  "http://localhost:8010/flow-a/incomplete-campaign-recovery/flow-a-2026-07-18-example"
```

Returns `last_valid_stage`, effective `recovery_classification`,
`recommended_recovery_action`, `outcome`, `reason_code`, `summary`,
`recovery_cancel`, recent `recovery_attempts` (≤20), and `next_stage` when
unfinished work remains. Performs zero metadata or filesystem writes.

### Resume

```bash
curl -sS -X POST \
  -H "Authorization: Bearer ${SILVERMAN_BLOG_LINKEDIN_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"campaign_id":"flow-a-2026-07-18-example","dry_run":true}' \
  "http://localhost:8010/flow-a/incomplete-campaign-recovery/resume"
```

Body fields:

- `campaign_id` (required)
- `dry_run` (boolean, default `false`) — plan skips/runs without mutation or ledger append
- `stop_after_stage` (optional durable milestone) — stop after that stage

Default resume advances remaining unfinished worker stages in order:

`publish` → `package` → `schedule` → `source_lifecycle`

Already-confirmed durable milestones are skipped via existing stage
idempotency. Default resume does **not** enable Git publication, live-site
confirmation, or LinkedIn API publish.

Gates:

- Cancelled recovery (`flow_a_recovery.cancelled`) → blocked
  `flow_a_recovery_cancelled` with `recommended_recovery_action=cancel_recovery`
- Non-stale `processing` claim → blocked `manual_intervention_required`
- `location=error` → blocked `requeue_required` (explicit requeue required;
  resume never silent-requeues)
- Ambiguous evidence → blocked `flow_a_recovery_evidence_ambiguous`

### Repair

```bash
curl -sS -X POST \
  -H "Authorization: Bearer ${SILVERMAN_BLOG_LINKEDIN_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"campaign_id":"flow-a-2026-07-18-example","repair_action":"sync_location_from_filesystem","dry_run":true}' \
  "http://localhost:8010/flow-a/incomplete-campaign-recovery/repair"
```

Allowlisted `repair_action` values:

| Action | Purpose |
|--------|---------|
| `sync_location_from_filesystem` | When Markdown identity resolves to exactly one of `ready\|queued\|processed\|error` and metadata `location` disagrees, sync location fields |
| `clear_stale_execution_claim` | Clear a stale processing claim to `idle` without erasing stage evidence |
| `complete_partial_source_move` | Complete an unambiguous remaining sibling image move when `physical_move_state=partial` |

Unknown `repair_action` → HTTP 422. Ambiguous multi-location matches, inventing
publish/package/schedule success, or unsafe `flow_a_complete` marking are
refused with zero mutation. Cancelled recovery blocks repair the same way as
resume.

### Cancel

```bash
curl -sS -X POST \
  -H "Authorization: Bearer ${SILVERMAN_BLOG_LINKEDIN_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"campaign_id":"flow-a-2026-07-18-example","reason_code":"operator_cancelled","summary":"Recovery not appropriate"}' \
  "http://localhost:8010/flow-a/incomplete-campaign-recovery/cancel"
```

Body fields:

- `campaign_id` (required)
- `dry_run` (boolean, default `false`) — describe would-be cancel without writes
- `reason_code` (optional short token; default `operator_cancelled`)
- `summary` (optional short operator text)

Cancel marks incomplete-campaign **recovery eligibility** cancelled
(`flow_a_recovery.cancelled=true`). It does **not** move editorial files, rewrite
pipeline `state` / `state_history`, invent durable stage success, or call
LinkedIn publication cancel endpoints.

Idempotency: already-cancelled → `outcome=noop` with no extra ledger append.
There is no reopen/uncancel endpoint in this change.

## Recovery-action taxonomy (US-032)

`recommended_recovery_action` complements (does not replace)
`recovery_classification`. Closed values:

| Value | Meaning |
|-------|---------|
| `noop_already_complete` | Consistent `flow_a_complete` |
| `resume` | Unfinished eligible worker stages |
| `repair` | Ambiguous / repair_required evidence |
| `requeue` | Error location / requeue_required |
| `manual_intervention` | Active claim or severe block |
| `cancel_recovery` | Recovery cancelled (or cancel is the operator choice when already cancelled) |

Taxonomy strings are never written into `source_file_status.recovery_classification`.

Mutating responses may include `executed_recovery_action`: `resume` | `repair` |
`cancel` | `noop`.

## Attempt history

Applied resume / repair / cancel (first cancel) append one secret-safe entry under
`flow_a_recovery.attempts` (max **50**, oldest trimmed first). Dry-run, HTTP 401,
and HTTP 422 never append. Inspect never appends and returns at most the **20**
most recent attempts.

Ledger writes do not invent stage success or rewrite `state_history`.

## Last-valid-stage rules

`last_valid_stage` is derived (not a new persisted lifecycle state) as the
highest confirmed durable milestone:

`ready` → `validated` → `blog_published` → `derivatives_generated` → `distribution_scheduled` → `flow_a_complete`

Confirmation uses campaign `state`, `state_history`, and durable stage evidence
(`blog_publish`, package/variants, `linkedin_distribution`, processed location).
Pending states (`blog_publish_pending`, `derivatives_pending`) are never
reported as last-valid. Conflicting evidence fails closed with
`flow_a_recovery_evidence_ambiguous`.

Pre-completion durable milestone for catch-up is `distribution_scheduled`
(not `distribution_complete`).

## Operator-visible outcomes

Responses include at least:

- `campaign_id`
- `last_valid_stage` when derivable
- `recovery_classification` (canonical five-value enum)
- `recommended_recovery_action`
- `outcome` (`ok` / `blocked` / `failed` / `noop` / `partial`)
- `reason_code`
- short `summary`
- `recovery_cancel` (`cancelled`, and when cancelled: timestamps/reason/summary)

Mutating responses also include `dry_run`, `executed_recovery_action` when
applicable, optional `attempt` echo, and per-stage or before/after safe
summaries. Payloads never include Markdown/draft bodies, tokens, secrets, or
the absolute editorial base path.

## Suggested operator workflow

1. Inspect the campaign (taxonomy + cancel state + recent attempts).
2. Repair allowlisted inconsistencies if inspect reports `repair` /
   `repair_required` / ambiguity that a listed repair can fix.
3. Resume with `dry_run=true`.
4. Resume for real (optionally with `stop_after_stage`).
5. If `location=error`, requeue via the existing queue helper path before resume.
6. If recovery is not appropriate, cancel (then resume/repair stay blocked).

## Non-goals

- Reopen/uncancel after cancel
- LinkedIn publication cancel via this surface
- BL-013/014/015
- Changing `GET /flow-a/operational-status` or operational-alerts contracts
- Marking US-032 accepted or BL-012 closed from implementation alone
- Deploy, production n8n activation, or live operational validation as part of
  the US-032 implementation change
