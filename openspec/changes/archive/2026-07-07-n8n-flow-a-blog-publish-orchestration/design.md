## Context

### Umbrella and sequencing

This is **child change 7** under the active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`. Completed siblings:

| Slice | Change | Delivers |
|-------|--------|----------|
| 1 | `editorial-canon-and-linkedin-distribution-strategy` | `content-strategy/silverman-editorial-system.md`, spec `editorial-canon` |
| 2 | `flow-a-lifecycle-and-duplicate-prevention` | `campaign_lifecycle.py`, spec `flow-a-lifecycle` |
| 3 | `ready-post-editorial-validation` | `ready_post_validation.py`, spec `ready-post-editorial-validation` |
| 4 | `worker-blog-publishing-endpoint` | `POST /publish-blog-post`, `blog_publish_flow.py` |
| 5 | `linkedin-derivative-package-generation` | `POST /generate-linkedin-package`, `linkedin_package_flow.py` |
| 6 | `linkedin-distribution-scheduling-model` | `POST /schedule-linkedin-distribution`, `linkedin_distribution_schedule.py` |
| 7 | `n8n-flow-a-blog-publish-orchestration` (this change) | Flow A n8n workflow JSON + validation tests |

Slice 7 wires n8n HTTP orchestration across slices 3–6. Validation runs inside `POST /publish-blog-post` via `validate_ready_post()` (slice 3 HTTP exposure deferred; no separate validation endpoint in this slice).

### Existing n8n workflow baseline

The repository has one importable workflow today:

| Artifact | Purpose | Scope |
|----------|---------|-------|
| `n8n/workflows/silverman-blog-linkedin-draft-generation.json` | Manual-trigger draft generation for human review | Flow B–adjacent / operator smoke; `process-ready` → `process-file` → compute expected URL → `generate-linkedin-draft` (single variant) |
| `tests/test_n8n_workflow.py` | Lightweight JSON structure validation | Forbidden nodes, secrets, endpoint fragments, inactive export |

That workflow:

- Uses **Set Configuration** with `worker_base_url`, `worker_api_key` placeholder `CHANGE_ME_WORKER_API_KEY`, `site_base_url`, editorial hints (`tone`, `audience`, `variant`), optional `topic_theme`.
- Calls `GET /health`, `POST /process-ready`, `POST /process-file`, `POST /generate-linkedin-draft`.
- Keeps `"active": false`; Manual Trigger only.
- Does **not** call publish, package, or schedule endpoints.
- Writes drafts to `linkedin-posts/review/` (human review path).

**Decision:** Add a **separate** Flow A workflow file. Do **not** modify `silverman-blog-linkedin-draft-generation.json` — preserves Flow B separation and avoids breaking existing draft-generation tests and operator workflows.

### Current worker endpoints (orchestration targets)

| Endpoint | Auth | Key request fields | Key response fields for chaining |
|----------|------|-------------------|--------------------------------|
| `GET /health` | None | — | `status`, `folders_ready` |
| `POST /process-ready` | Bearer API key | `{}` | `status`, `valid_files[]` with `relative_path` |
| `POST /publish-blog-post` | Bearer API key | `source_relative_path`, optional `site_url` | `status`, `campaign_id`, `source_relative_path`, `source_public_url`, `errors[]`, `blog_publish` |
| `POST /generate-linkedin-package` | Bearer API key | `campaign_id` **or** `source_relative_path`, optional `variants`, `topic_theme`, `site_url` | `status`, `campaign_id`, `source_relative_path`, `source_public_url`, `variants[]`, `errors[]` |
| `POST /schedule-linkedin-distribution` | Bearer API key | `campaign_id` **or** `source_relative_path`, optional `strategy`, `start_at_utc`, `timezone` | `status`, `campaign_id`, `variant_schedules[]`, `errors[]` |

All three Flow A worker steps return `status` `completed` | `failed` and `errors[]` suitable for n8n IF branching.

### Policy references

- Umbrella: `flow-a-automatic-blog-linkedin-publishing-roadmap` — Flow A automatic after validation; no human approval gate.
- ADR-0001: n8n HTTP only; no Execute Command, SSH, filesystem, or direct LLM nodes.
- Lifecycle: worker owns metadata; orchestration does not move `blog-posts/ready/` sources.

## Goals / Non-Goals

**Goals:**

- Add `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` orchestrating Flow A end-to-end over HTTP.
- Reuse proven patterns from draft-generation workflow: Set Configuration, health gate, process-ready scan, Split Out, per-item HTTP chain, IF branches on `status`.
- Flow `campaign_id` and `source_relative_path` from publish → package → schedule responses.
- Support idempotent worker reruns (`already_published`, package/schedule idempotent `completed`).
- API key via configuration placeholder + Bearer expression (no production secrets in git).
- Export `"active": false`; Manual Trigger only.
- Document end-to-end smoke test procedure for Ubuntu server.
- Add lightweight tests mirroring `test_n8n_workflow.py` guardrails.

**Non-Goals:**

- LinkedIn API publication.
- Cron, webhook, or schedule trigger activation in export.
- Modifying `silverman-blog-linkedin-draft-generation.json`.
- New worker endpoints or contract changes.
- Source file moves (`ready` / `processed` / `error`).
- Git commit/push from n8n or worker orchestration.
- Archiving umbrella or this child.

## Decisions

### 1. Separate workflow artifact (not extend draft-generation)

**Decision:** Create `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` with workflow name identifying Flow A automatic publishing (for example `Silverman Blog LinkedIn Flow A Publish`).

**Rationale:** Flow A policy (no review gate, package + schedule chain) differs from single-draft review workflow. Separate files prevent Flow B/regression risk and keep existing tests stable.

**Alternatives considered:** Extend draft-generation JSON with a mode flag — rejected; mixes concerns and complicates validation.

### 2. Proposed workflow node sequence

```
Manual Trigger
    → Set Configuration
    → Health Check (GET /health)
    → IF Health Ready
        ├─ false → Stop Health Failed (No Op)
        └─ true → Process Ready (POST /process-ready)
            → IF Process Ready Failed
                ├─ true → Stop Process Ready Failed
                └─ false → IF Has Valid Candidates (valid_count > 0)
                    ├─ false → Stop No Candidates (clean exit)
                    └─ true → Split Out Valid Files
                        → [per item] Publish Blog Post (POST /publish-blog-post)
                        → IF Publish Completed (status === completed)
                            ├─ false → Set Publish Failed (errors from response)
                            └─ true → Generate LinkedIn Package (POST /generate-linkedin-package)
                                → IF Package Completed
                                    ├─ false → Set Package Failed
                                    └─ true → Schedule LinkedIn Distribution (POST /schedule-linkedin-distribution)
                                        → IF Schedule Completed
                                            ├─ false → Set Schedule Failed
                                            └─ true → Set Flow A Success (expose campaign_id, URLs, schedules)
```

**Notes:**

- **Process Ready** replaces a standalone validation HTTP call; `publish-blog-post` invokes `validate_ready_post()` unless idempotent `already_published` short-circuit applies.
- **Per-item loop** uses `relative_path` from `valid_files[]` as `source_relative_path` for publish.
- No `process-file` or `generate-linkedin-draft` nodes in Flow A workflow.
- No Code node for URL derivation; publish returns publish-confirmed `source_public_url`.
- Error branches use Set nodes (or No Op + Set) exposing `errors[]`, `campaign_id`, and step name for operator visibility.

### 3. HTTP calls and payloads

#### `POST /publish-blog-post`

**URL:** `={{ $('Set Configuration').first().json.worker_base_url }}/publish-blog-post`

**Headers:** `Authorization: Bearer {{ $('Set Configuration').first().json.worker_api_key }}`

**JSON body (per candidate):**

```json
{
  "source_relative_path": "<from valid_files[].relative_path or $json.relative_path>",
  "site_url": "<from Set Configuration site_url when non-empty; omit key when empty>"
}
```

**Success branch:** `status` equals `completed` (includes `blog_publish.status` `already_published` idempotent case).

**Failure branch:** `status` equals `failed`; expose `errors[]` and optional `validation` summary.

**Fields to carry forward:** `campaign_id`, `source_relative_path`, `source_public_url`, `state`, `public_slug`, `publication_date`.

#### `POST /generate-linkedin-package`

**URL:** `={{ $('Set Configuration').first().json.worker_base_url }}/generate-linkedin-package`

**Headers:** Same Bearer pattern.

**JSON body (prefer campaign_id from publish response):**

```json
{
  "campaign_id": "<from Publish Blog Post response>",
  "source_relative_path": "<fallback from publish response when campaign_id absent>",
  "topic_theme": "<optional; include only when Set Configuration topic_theme non-empty>",
  "site_url": "<optional; include only when Set Configuration site_url non-empty>"
}
```

Use n8n `jsonBody` JavaScript pattern (as in draft workflow) to conditionally omit empty optional keys.

**Success branch:** `status` equals `completed`.

**Fields to carry forward:** `campaign_id`, `source_relative_path`, `package_id`, `variants[]`.

#### `POST /schedule-linkedin-distribution`

**URL:** `={{ $('Set Configuration').first().json.worker_base_url }}/schedule-linkedin-distribution`

**Headers:** Same Bearer pattern.

**JSON body:**

```json
{
  "campaign_id": "<from Generate LinkedIn Package response>",
  "strategy": "<optional; default flow_a_staggered via worker when omitted>",
  "start_at_utc": "<optional; include only when Set Configuration start_at_utc non-empty>",
  "timezone": "<optional informational>"
}
```

**Success branch:** `status` equals `completed`; `variant_schedules[]` with `publish_state` `pending`.

**No LinkedIn API call** at any step.

### 4. campaign_id / source_relative_path flow between nodes

| Step | Primary identifier passed | Fallback |
|------|---------------------------|----------|
| Process Ready → Publish | `valid_files[].relative_path` → `source_relative_path` | — |
| Publish → Package | `campaign_id` from publish response | `source_relative_path` from publish response |
| Package → Schedule | `campaign_id` from package response | `source_relative_path` from package response |

n8n Set success nodes SHOULD merge prior step outputs so downstream HTTP `jsonBody` expressions can read `$json.campaign_id` from the immediate prior worker response item.

Worker resolves campaign from either identifier consistently across slices 4–6.

### 5. Error branching for each worker response

Each worker HTTP step is followed by an IF node checking `$json.status === 'completed'` (string equals).

| Step | On failure | Behavior |
|------|------------|----------|
| Health | `status !== 'healthy'` or `folders_ready !== true` | Stop; no further worker calls |
| Process Ready | `status === 'failed'` | Stop; expose `errors[]` |
| Publish | `status === 'failed'` | Per-item failure branch; do not call package/schedule for that item |
| Package | `status === 'failed'` | Do not call schedule |
| Schedule | `status === 'failed'` | Terminal failure for that item |

Validation failures surface as publish `errors[]` containing `blog_publish_validation_failed` with embedded `validation` object — no separate validation branch required.

### 6. Idempotent rerun behavior

Worker endpoints support safe re-runs; n8n does not need special deduplication logic:

| Step | Idempotent signal | n8n behavior |
|------|-------------------|--------------|
| Publish | `status: completed`, `blog_publish.status: already_published` | Treat as success; proceed to package |
| Package | `status: completed` with existing package metadata | Proceed to schedule |
| Schedule | `status: completed` with matching schedule idempotency proof | Terminal success |

Re-running the full workflow on the same ready post MUST NOT create duplicate blog writes or duplicate schedule slots when worker idempotency keys match.

### 7. Worker API key handling

**Decision:** Mirror draft-generation workflow:

- **Set Configuration** assigns `worker_api_key` placeholder `CHANGE_ME_WORKER_API_KEY` (safe for git).
- Authenticated HTTP nodes use header expression: `Bearer {{ $('Set Configuration').first().json.worker_api_key }}` — **not** a hardcoded literal token in `Authorization` value.
- README documents post-import replacement via Set node edit or n8n credentials (Header Auth) without committing real keys.
- Lightweight tests assert: no `sk-` patterns, no real Bearer literals, `CHANGE_ME_WORKER_API_KEY` present in config, authenticated nodes reference `worker_api_key` expression.

### 8. Environment / configuration fields (Set Configuration)

| Field | Default | Purpose |
|-------|---------|---------|
| `worker_base_url` | `http://192.168.0.194:8010` | Worker HTTP base (document local vs Docker override) |
| `worker_api_key` | `CHANGE_ME_WORKER_API_KEY` | Bearer token placeholder |
| `site_url` | `https://silverman.pro` | Passed to publish/package when non-empty |
| `topic_theme` | `""` | Optional package generation hint |
| `schedule_strategy` | `""` | Optional; omit from schedule request when empty (worker default `flow_a_staggered`) |
| `start_at_utc` | `""` | Optional deterministic schedule anchor for smoke tests |

Do **not** include Flow B editorial hints (`tone`, `audience`, `variant`) — package generation uses canonical variant set internally.

### 9. Manual execution / inactive export

- Top-level `"active": false` in workflow JSON.
- **Manual Trigger** only — no Cron, Webhook, or Schedule Trigger nodes.
- No production activation in this change.

### 10. No LinkedIn API, no git from n8n, no source file moves

- Forbidden node types: `linkedIn`, `github`, `executeCommand`, `ssh`, filesystem read/write, direct LLM providers (same set as `test_n8n_workflow.py`).
- Workflow MUST NOT invoke worker endpoints that move source files; publish/package/schedule already avoid moves per canonical specs.
- Lifecycle file moves remain deferred to a future operations slice if needed; this child does not propose n8n-triggered moves.

### 11. End-to-end smoke test preparation

After `/opsx-apply`, operators can:

1. Place canonical test post (+ PNG) in `blog-posts/ready/` on server mount.
2. Import `silverman-blog-linkedin-flow-a-publish.json` into n8n; set `worker_api_key`.
3. Confirm worker healthy (`GET /health` via workflow or curl).
4. Execute workflow manually (inactive export).
5. Verify: campaign metadata progresses `validated` → `blog_published` → `derivatives_generated` → `distribution_scheduled`; artifacts under `linkedin-posts/generated/<campaign_id>/`; `publish_state` `pending` on variants.
6. Re-run workflow; confirm idempotent `completed` responses without duplicate artifacts.

README section documents these steps; tasks include server manual verification.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operator runs Flow A on invalid ready post | Publish returns `failed` with validation errors; workflow stops at publish branch |
| Accidental workflow activation | Export `active: false`; no cron in this change; README warning |
| API key committed to git | Placeholder only; tests scan for secret patterns |
| Confusion with draft-generation workflow | Separate file name; README distinguishes Flow A vs review workflow |
| Package called before publish completes | Strict IF chain; schedule only after package `completed` |
| Git push not automated after blog publish | Documented open question from umbrella; out of scope for n8n slice |

## Migration Plan

1. Apply this child change: add workflow JSON, tests, README.
2. Operator imports new workflow alongside existing draft-generation workflow (both may coexist).
3. Manual smoke test on Ubuntu server before any future cron activation change.
4. Slice 8 may add LinkedIn API publish step after schedule matures.
5. Rollback: stop using Flow A workflow; worker endpoints remain backward-compatible.

## Open Questions

1. Should Flow A workflow support a single hardcoded `source_relative_path` in Set Configuration for one-shot smoke tests without `process-ready`? (Optional enhancement at apply time.)
2. Should success branch write a run summary to `metadata/runs/` via a future worker endpoint, or is n8n execution log sufficient for slice 7?
3. When should a separate change enable cron polling of `ready/`?

## Implementation Note (apply)

During `/opsx-apply`, inspect:

- `n8n/workflows/silverman-blog-linkedin-draft-generation.json` — copy HTTP auth and branching patterns only.
- `tests/test_n8n_workflow.py` — extend or add parallel test module for Flow A workflow.
- `src/silverman_blog_linkedin/main.py` — confirm request/response field names before wiring `jsonBody` expressions.

Do not invent worker API fields; use actual `to_dict()` shapes from `blog_publish_flow.py`, `linkedin_package_flow.py`, and `linkedin_distribution_schedule.py`.
