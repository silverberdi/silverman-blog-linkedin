# Flow A Operational Status

Operator contract for the read-only status view covering US-026
(execution/campaign/calendar classifications) and US-027 (stage durations and
dependency-failure aggregation). Both slices are implemented and tested
locally. The capability is not deployed or operationally validated, does not
send notifications or write alert ledgers, and does not by itself close BL-010.
BL-011 / US-028, US-029, and US-030 alerting is owned by the separate
[`POST /flow-a/operational-alerts/evaluate`](flow-a-operational-alerts.md)
contract (plus US-030 report ingest).

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
  LinkedIn counts by persisted `publish_state`; `stage_durations` evidence
  counts (`campaigns_with_stage_durations`, `executions_with_duration`,
  `stage_intervals_reported`); `dependency_failures` counts for `comfyui`,
  `deepseek`, `github_pages_checkout`, `linkedin`, and `unclassified`; and
  data-issue count.
- `executions`: safe persisted run records partitioned into `successful` and
  `failed`, each with `duration_seconds` when both run clocks are valid.
- `campaigns`: lifecycle, operational, current-attempt, health-reason, and
  LinkedIn schedule/publication summaries, plus `stage_durations`, optional
  `attempt_duration_seconds`, and per-campaign `dependency_failures`.
- `delayed_calendar_items`: safe summaries of non-terminal past-due items.
- `dependency_failures`: top-level aggregation of validated failure codes by
  external dependency, with counts, safe codes, and contributing
  `campaign_ids` / `run_ids`.
- `data_issues`: stable source, safe identifier when available, and
  machine-readable reason. Raw documents and exception text are not returned.

Results are deterministic for unchanged files and the same `now_utc`.
Executions sort by available completion/start time then run ID descending;
campaigns by valid `updated_at` then campaign ID descending; delayed items by
`due_at_utc` then item ID ascending; per-campaign `stage_durations` by
`started_at` then `stage` ascending; dependency entries by dependency name
ascending with error codes ascending; issues by source, identifier, and
reason ascending.

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

## Stage durations (US-027)

All durations are derived read-only from existing persisted timestamps and
reported in whole seconds. No new timing field is persisted.

Execution duration and lifecycle stage duration are distinct measurements:

- Execution `duration_seconds` measures one worker HTTP run
  (`started_at` to `completed_at` on a `metadata/runs` record). It is not a
  Flow A lifecycle stage. Missing clocks omit the field silently; present but
  invalid or inverted clocks omit it with a stable data issue
  (`run_timestamp_invalid` / `run_clock_inverted`).
- Campaign `stage_durations` measure lifecycle stages derived from
  `state_history`. Each consecutive pair of valid entries yields one closed
  interval: `stage` is the state entered by the earlier entry, `started_at` /
  `ended_at` are the two `at` clocks, and `from_state` / `to_state` record the
  transition that closed the stage. After the last valid entry, exactly one
  open interval is reported with `open=true` and `ended_at=null`; its
  `duration_seconds` is measured to `observed_at_utc`, so open-stage durations
  are observation-relative and grow between requests unless a fixed `now_utc`
  is supplied.

Malformed history entries produce `campaign_stage_history_invalid`;
non-chronological pairs (or a future-dated open stage) produce
`campaign_stage_clock_inverted` and omit only the affected interval. When the
campaign `state` disagrees with the last history `to_state`, the open stage
reports the last `to_state` and adds
`campaign_stage_history_state_inconsistent`. Missing history is never
fabricated.

`attempt_duration_seconds` is supplemental current-attempt evidence
(`processing_started_at` to `last_progress_at`) and never replaces lifecycle
stage intervals. Inverted attempt clocks produce
`campaign_attempt_clock_inverted`.

Lifecycle stage durations are campaign metadata clocks. They are not
live-site deploy latency and not LinkedIn API network round-trip time.

## Dependency-failure buckets (US-027)

Validated machine-readable failure codes are classified by their persisted
code family, without calling any integration:

| Bucket | Code families |
|--------|---------------|
| `comfyui` | `comfyui_*`, `blog_image_generation_*` |
| `deepseek` | `deepseek_*` |
| `github_pages_checkout` | `blog_publish_*`, `blog_git_publication_*`, `checkout_*`, `linkedin_preview_validation_checkout_*`, exactly `linkedin_article_preview_public_repo_not_configured` |
| `linkedin` | remaining `linkedin_*` |
| `unclassified` | any other validated failure code |

Checkout-named patterns are evaluated before the general `linkedin_*` family.
Classification follows the persisted code as written; causal roots are never
inferred (`linkedin_package_generation_failed` stays `linkedin` even when
DeepSeek failed upstream).

Evidence sources are limited to validated codes from failed run records,
failed or blocked campaigns (top-level `errors`, last-error evidence, and
`state_history[].error_code`), and LinkedIn variant publication failure codes.
Repeated identical codes on one artifact count once per response. Unclassified
codes stay visible in the `unclassified` bucket and are never silently
dropped.

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

US-027 controlled-fixture verification on the same date exercised closed and
open lifecycle stage intervals, execution durations, every dependency bucket
(including checkout-named LinkedIn preview codes and unclassified codes),
inverted and missing clocks as stable data issues, and byte-for-byte zero
mutation with no external client invocation.

This demonstrates US-026 and US-027 at controlled-fixture and automated-test
scope only. Business acceptance, deployment, and live operational validation
remain pending.
