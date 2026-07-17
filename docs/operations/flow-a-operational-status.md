# Flow A Operational Status

Operator contract for the read-only US-026 status view. This capability is
implemented and tested locally. It is not deployed or operationally validated,
does not provide alerts, and does not close US-027 or BL-010.

## Request

`GET /flow-a/operational-status` requires the worker Bearer API key. It accepts
one optional query parameter, `now_utc`, in canonical
`YYYY-MM-DDTHH:MM:SSZ` form. An invalid value returns HTTP 422. When omitted,
the worker captures current UTC once for the complete response.

Example:

```bash
curl -sS \
  -H "Authorization: Bearer ${SILVERMAN_BLOG_LINKEDIN_API_KEY}" \
  "http://localhost:8010/flow-a/operational-status?now_utc=2026-07-17T12:00:00Z"
```

The endpoint has no request body, path parameter, or `dry_run` mode. It is
intrinsically read-only.

## Response

- `status`: `ok` when every fixed source is present and valid; `partial` when
  any source or classification evidence is rejected. Empty valid sources are
  `ok`.
- `observed_at_utc`: the one request-level classification instant.
- `read_only`: always `true`.
- `stale_after_seconds`: validated
  `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` value.
- `summary`: successful/failed execution counts; total, successful, failed,
  blocked, stale, and in-progress campaign counts; delayed calendar count;
  LinkedIn counts by persisted `publish_state`; and data-issue count.
- `executions`: safe persisted run records partitioned into `successful` and
  `failed`.
- `campaigns`: lifecycle, operational, current-attempt, health-reason, and
  LinkedIn schedule/publication summaries.
- `delayed_calendar_items`: safe summaries of non-terminal past-due items.
- `data_issues`: stable source, safe identifier when available, and
  machine-readable reason. Raw documents and exception text are not returned.

Results are deterministic for unchanged files and the same `now_utc`.
Executions sort by available completion/start time then run ID descending;
campaigns by valid `updated_at` then campaign ID descending; delayed items by
`due_at_utc` then item ID ascending; issues by source, identifier, and reason
ascending.

## Classification rules

Persisted worker executions are the valid direct JSON records under
`metadata/runs/`:

- `status=completed` is `outcome=successful`.
- `status=failed` is `outcome=failed`.
- Missing or unsupported status is a data issue and is not counted.

Only whitelisted fields are returned: run ID, validated trigger, persisted
status, derived outcome, valid start/completion timestamps, and validated error
codes. Existing run records do not consistently contain campaign linkage and
are not complete Flow A attempt history. The view never infers that linkage or
synthesizes runs from campaign `attempt_count` or `state_history`.

Campaign flags are independent:

- `successful`: `state=flow_a_complete`, source `location=processed`, and
  `execution_state=idle`.
- `failed`: lifecycle `state` is `validation_failed` or `error`, or source
  `location=error`.
- `blocked`: failed, or recovery classification is `repair_required`,
  `requeue_required`, or `manual_intervention_required`. `retryable` alone is
  not blocked.
- `stale`: persisted `execution_state=stale`, or a processing campaign is
  observed at or after `last_progress_at + stale_after_seconds`. Missing or
  invalid `last_progress_at` on processing fails safe to stale.
- `in_progress`: neither successful nor failed. It may also be blocked or
  stale.

Staleness always uses `last_progress_at`.
`processing_lease_expires_at` is display evidence only and cannot override the
threshold. Observation never invokes stale detection or persists a transition.

LinkedIn summaries preserve campaign lifecycle and API publication as separate
outcomes. They count persisted `pending`, `queued`, `published`, `failed`, and
`cancelled` variants; show distribution strategy and anchor; report the
earliest valid pending schedule, earliest valid queue time, and latest valid
publication; and count elapsed pending/queued windows relative to
`observed_at_utc`. Elapsed windows are descriptive only. The endpoint does not
re-run publication eligibility, sequence, cadence, enablement, OAuth, or
dependency checks.

A calendar item is delayed only when its status is `planned`, `scheduled`,
`due`, or `in_progress` and `due_at_utc` is strictly earlier than
`observed_at_utc`. Equality is due now, not delayed. `completed`, `skipped`, and
`failed` items are excluded. LinkedIn timing is never a calendar-delay anchor.

## Sources and safety

The worker reads only:

- direct `.json` entries in `metadata/runs/`;
- direct `.json` entries in `metadata/campaigns/`;
- `editorial-calendar/calendar.json`.

All paths are fixed under the configured editorial base. Escaping symlinks and
resolved files outside their approved directory are rejected. A campaign
contributes only when its canonical ID is valid, its filename matches the
persisted ID, and `flow=flow_a`.

Partial results preserve valid evidence from unaffected sources. The response
never returns the absolute editorial base, Markdown or draft bodies, API keys,
tokens, client secrets, authorization values, arbitrary environment values,
raw provider responses, or raw exception text.

Observation performs no writes, file moves, stale marking, reconciliation,
queueing, publication, Git operation, or external call.

## Controlled fixture demonstration

Local verification on 2026-07-17 exercised one consolidated response containing
successful and failed persisted runs, blocked and stale campaigns, delayed
calendar items, and separate LinkedIn lifecycle/publication evidence. The
response exposed counts plus stable reasons without requiring raw-file
inspection. Repeated service and authenticated HTTP calls with the same
`now_utc` produced identical responses, while complete fixture inventory,
bytes, and modification timestamps remained unchanged.

This demonstrates US-026 at controlled-fixture and automated-test scope only.
Business acceptance, deployment, and live operational validation remain
pending.
