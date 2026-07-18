# Flow A Incomplete Campaign Recovery (US-031)

Operator contract for authenticated incomplete Flow A campaign recovery:
inspect last-valid-stage, resume unfinished worker stages idempotently, and
repair allowlisted metadata/filesystem mismatches.

This capability covers **BL-012 / US-031 only**. It does **not** implement
US-032 (recovery-action taxonomy, attempt history ledger, or safe cancellation),
LinkedIn API publication recovery (BL-008 / US-021–US-022), production n8n
activation, Git push, live-site confirmation, or LinkedIn API publish.

## Endpoints

All three require the worker Bearer API key (`Depends(require_api_key)`).
Missing/invalid auth returns HTTP 401. Invalid bodies return HTTP 422.
Clients must not supply absolute filesystem paths.

| Operation | Method / path | Mutation |
|-----------|---------------|----------|
| Inspect | `GET /flow-a/incomplete-campaign-recovery/{campaign_id}` | None (read-only) |
| Resume | `POST /flow-a/incomplete-campaign-recovery/resume` | Yes (optional `dry_run`) |
| Repair | `POST /flow-a/incomplete-campaign-recovery/repair` | Yes (optional `dry_run`) |

### Inspect

```bash
curl -sS \
  -H "Authorization: Bearer ${SILVERMAN_BLOG_LINKEDIN_API_KEY}" \
  "http://localhost:8010/flow-a/incomplete-campaign-recovery/flow-a-2026-07-18-example"
```

Returns `last_valid_stage`, effective `recovery_classification`, `outcome`,
`reason_code`, `summary`, and `next_stage` when unfinished work remains.
Performs zero metadata or filesystem writes.

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
- `dry_run` (boolean, default `false`) — plan skips/runs without mutation
- `stop_after_stage` (optional durable milestone) — stop after that stage

Default resume advances remaining unfinished worker stages in order:

`publish` → `package` → `schedule` → `source_lifecycle`

Already-confirmed durable milestones are skipped via existing stage
idempotency. Default resume does **not** enable Git publication, live-site
confirmation, or LinkedIn API publish.

Gates:

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
refused with zero mutation.

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
- `outcome` (`ok` / `blocked` / `failed` / `noop` / `partial`)
- `reason_code`
- short `summary`

Mutating responses also include `dry_run` and per-stage or before/after safe
summaries. Payloads never include Markdown/draft bodies, tokens, secrets, or
the absolute editorial base path.

Recovery outcomes are **response-only** for US-031 (no dedicated recovery
attempt history — that is US-032).

## Suggested operator workflow

1. Inspect the campaign.
2. Repair allowlisted inconsistencies if inspect reports `repair_required` /
   ambiguity that a listed repair can fix.
3. Resume with `dry_run=true`.
4. Resume for real (optionally with `stop_after_stage`).
5. If `location=error`, requeue via the existing queue helper path before resume.

## Non-goals

- US-032 action taxonomy / attempt ledger / safe cancellation
- BL-013/014/015
- LinkedIn publication recovery surface (`/queue-linkedin-publication`, etc.)
- Changing `GET /flow-a/operational-status` or operational-alerts contracts
- Deploy, production n8n activation, or live operational validation as part of
  the US-031 implementation change
