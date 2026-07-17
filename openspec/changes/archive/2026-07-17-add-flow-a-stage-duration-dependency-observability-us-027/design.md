## Context

US-026 already delivers authenticated read-only `GET /flow-a/operational-status` that consolidates persisted run outcomes, campaign lifecycle/blocked/stale/in-progress flags, delayed calendar items, and LinkedIn schedule/publication evidence from confined on-disk sources. Canonical contract: `openspec/specs/flow-a-operational-status/spec.md`. Implementation: `src/silverman_blog_linkedin/flow_a_operational_status.py`. US-026 business acceptance remains pending and is not reopened by this change.

US-027 (BL-010 slice 2) requires the same operator view to also capture stage duration and surface failures by external dependency. Existing persisted evidence already includes:

- Run records: `started_at`, `completed_at`, and machine-readable `errors[]`.
- Campaign documents: `state_history[]` with `at` / `from_state` / `to_state` / `error_code`; top-level `errors[]`; `source_file_status` clocks (`processing_started_at`, `last_progress_at`, `last_transition_at`); LinkedIn variant failure codes under publication evidence.

The worker remains the HTTP boundary (ADR-0001). Observation must stay read-only and must not call ComfyUI, DeepSeek, LinkedIn, OAuth, Git, or live-site endpoints.

## Goals / Non-Goals

**Goals:**

- Extend `GET /flow-a/operational-status` so one response includes stage durations and dependency-failure aggregation without a parallel status surface.
- Derive stage durations from existing persisted timestamps; do not invent history.
- Classify existing failure error codes into ComfyUI, DeepSeek, LinkedIn, and GitHub Pages checkout buckets, plus an explicit unclassified bucket.
- Preserve US-026 auth, confinement, partial results, safe output, deterministic ordering, and zero mutation.
- Keep n8n HTTP-only: it may consume the endpoint but never reads files or shells into the worker mount.

**Non-Goals:**

- Re-implementing or changing US-026 execution/campaign/calendar classification semantics.
- BL-011 alerts, BL-015 UI, deployment, n8n workflow edits, background monitors.
- New persisted stage-timing schema fields (see Decision 2).
- Live dependency health probes or re-running pipeline eligibility checks.
- Claiming lifecycle stage duration equals live-site deploy latency or LinkedIn API RTT.

## Decisions

### 1. Extend the existing endpoint response, do not add a second route

Add stage-duration and dependency-failure fields to the existing authenticated `GET /flow-a/operational-status` JSON contract:

- Top-level `dependency_failures`: one entry per dependency bucket with failure counts, sorted validated error codes, and safe artifact identifiers (`campaign_id` / `run_id`) when available.
- `summary.dependency_failures`: counts by bucket, including `unclassified`.
- `summary.stage_durations`: compact counts of campaigns/executions that contributed duration evidence and total stage intervals reported.
- Per-execution optional `duration_seconds` when both `started_at` and `completed_at` are valid.
- Per-campaign optional `stage_durations[]` derived from `state_history`.
- Per-campaign optional `dependency_failures[]` listing buckets and safe error codes attributed to that campaign.

No new path, request body, dry-run flag, or user-supplied filesystem path.

Alternatives considered:

- Separate `GET /flow-a/operational-timings` route: rejected; criterion 3 requires one consolidated view.
- Emit durations only in operator docs/scripts: rejected; US-027 is an observability capability of the worker status contract.

### 2. Derive stage durations from existing evidence; do not add persisted timing fields

**Decision:** Existing evidence is sufficient for US-027. This change MUST NOT add new campaign or run timestamp fields.

Duration sources and rules:

1. **Worker execution duration**  
   For each valid run summary, when both `started_at` and `completed_at` parse as canonical UTC and `completed_at >= started_at`, set `duration_seconds` to the integer whole-second difference. Otherwise omit `duration_seconds` and emit a stable data issue when timestamps are present but invalid or inverted.

2. **Campaign lifecycle stage intervals**  
   Treat each consecutive pair of valid `state_history` entries as one completed stage interval:
   - `stage` = the entered state (`to_state` of the earlier entry / equivalently the state occupied until the next transition).
   - `started_at` = earlier entry `at`.
   - `ended_at` = later entry `at`.
   - `duration_seconds` = whole seconds between them when `ended_at >= started_at`.
   - `from_state` / `to_state` retained from the transition that *ended* the interval (the later entry), so operators see which transition closed the stage.
   - `open` = `false` for completed intervals.

   For the current open stage after the last valid history entry:
   - `stage` = campaign `state` when it matches the last `to_state`; otherwise report the last `to_state` and add a stable inconsistency data issue.
   - `started_at` = last valid history `at`.
   - `ended_at` = null.
   - `duration_seconds` = whole seconds from `started_at` to `observed_at_utc` when `observed_at_utc >= started_at`.
   - `open` = `true`.

3. **Current attempt clock (supplemental, not a lifecycle stage)**  
   When both `processing_started_at` and `last_progress_at` are valid and ordered, include `attempt_duration_seconds` on the campaign summary as attempt-progress evidence. This MUST NOT replace lifecycle stage intervals and MUST NOT invent missing `state_history`.

Malformed or non-chronological history entries produce data issues and omit only the affected intervals; valid intervals from the same campaign still appear.

Alternatives considered:

- Persist per-stage start/end clocks on every transition: rejected for US-027 because `state_history[].at` already provides enter/leave evidence without schema migration.
- Use only run `started_at`/`completed_at` as “stage” duration: rejected because runs are endpoint executions, not Flow A lifecycle stages; both are exposed with distinct labels.
- Approximate stages from folder mtimes: rejected as non-authoritative and outside confined metadata sources.

### 3. Classify failures by external dependency from error-code families

**Decision:** Classify only validated machine-readable error codes already accepted by the US-026 safe-code whitelist. Never call external systems. Never use raw exception text.

Canonical dependency buckets:

| Bucket | Error-code families (prefix / pattern) |
|--------|----------------------------------------|
| `comfyui` | `comfyui_*`, `blog_image_generation_*` |
| `deepseek` | `deepseek_*` |
| `linkedin` | `linkedin_*` |
| `github_pages_checkout` | `blog_publish_*`, `blog_git_publication_*`, `checkout_*`, plus LinkedIn preview codes that name checkout (`linkedin_preview_validation_checkout_*`, `linkedin_article_preview_public_repo_not_configured`) |
| `unclassified` | any other validated failure code that appears in failure evidence |

Classification is by the **persisted error code’s family**, not by inferred causal root (for example `linkedin_package_generation_failed` remains `linkedin` even when DeepSeek was involved upstream). DeepSeek-specific codes remain `deepseek` when those codes are what was persisted.

Evidence sources scanned (read-only):

- Failed run summaries: validated `errors[]` / `error_codes`.
- Failed or blocked campaigns: top-level validated `errors[]`, `source_file_status.last_error` / last error code already exposed, and `state_history[].error_code` when present and valid.
- LinkedIn variant publication failure codes already collected as safe LinkedIn evidence.

Each distinct `(dependency, error_code, artifact_id)` contributes at most once to bucket counts for a given response so repeated identical codes on one artifact do not inflate counts. Summary counts are totals of classified failure attributions after that dedupe.

Unclassified codes remain visible: they increment `unclassified` and appear in the dependency-failure list so operators are not left with silent gaps.

Alternatives considered:

- Probe ComfyUI/DeepSeek/LinkedIn/Git health live: rejected; violates read-only zero side-effect guarantee and US-027 scope.
- Collapse LinkedIn package and DeepSeek into one “generation” bucket: rejected; US-027 names distinct external dependencies.
- Omit unclassified codes: rejected; would hide failures and violate clear communication of blocked/failed states.

### 4. Preserve US-026 contract invariants while updating scope language

Keep unchanged:

- API-key auth via `Depends(require_api_key)`.
- Optional canonical `now_utc`; one observation instant for all derivations including open-stage durations.
- Confined sources only under the editorial base.
- `status` `ok`/`partial` and `data_issues` semantics.
- Safe-output whitelist; no secrets, bodies, absolute base path, or raw provider payloads.
- Deterministic ordering of existing collections; new collections MUST also sort deterministically:
  - `stage_durations` by `started_at` then `stage` ascending within a campaign;
  - `dependency_failures` by dependency name then error code ascending;
  - top-level dependency entries by dependency name ascending.
- Structural zero mutation: no writers, mutators, Git, or external clients.

Update the US-026 “out of scope” requirement that forbade stage durations and dependency-failure aggregation so US-027 is in scope for this capability, while BL-011 and BL-015 remain out of scope.

### 5. Implementation shape

Extend `flow_a_operational_status.py` with pure helpers for:

- duration arithmetic (whole seconds, reject inverted clocks);
- `state_history` stage-interval derivation;
- error-code → dependency bucket mapping;
- aggregation into summary + top-level dependency lists.

Keep FastAPI route wiring thin. Prefer extending existing dataclasses/response builders over a parallel service module. Tests extend `tests/test_flow_a_operational_status.py` with fixtures covering:

- completed and open stage intervals;
- execution `duration_seconds`;
- each dependency bucket and unclassified codes;
- inverted/missing timestamps as data issues;
- US-026 regression (auth, classifications, ordering, safe output, byte-for-byte zero mutation).

### 6. Documentation and progress discipline

After implementation verification:

- Update `docs/operations/flow-a-operational-status.md` with stage-duration and dependency-failure contract language.
- Update `docs/CURRENT-STATE.md` to the demonstrated level only.
- Update product progress for US-027 only when acceptance criteria are demonstrated; do not mark US-026 accepted or BL-010 closed solely because US-027 code lands.

## Risks / Trade-offs

- **[Risk] Sparse or irregular `state_history` yields incomplete stage timelines.** → Report only derived intervals; emit data issues for invalid timestamps or inconsistent last-state; never fabricate missing transitions.
- **[Risk] Operators confuse endpoint execution duration with lifecycle stage duration.** → Keep separate fields (`duration_seconds` on executions vs `stage_durations` on campaigns) and document both.
- **[Risk] Error-code family mapping mis-buckets some historical codes.** → Prefer explicit prefix tables; keep `unclassified` visible; document the mapping in operator docs; adjust only via later approved change if new families appear.
- **[Risk] `linkedin_package_*` failures hide DeepSeek outages when only package codes were persisted.** → Accept honest classification of persisted codes; DeepSeek appears when `deepseek_*` codes exist. Do not invent DeepSeek attribution from package failures.
- **[Trade-off] Whole-second durations lose sub-second precision.** → Acceptable for operator triage; timestamps remain available for exact clocks.
- **[Trade-off] Open-stage duration grows with `observed_at_utc`.** → Deterministic for a supplied `now_utc`; document that open stages are observation-relative.

## Migration Plan

1. Approve this change, then implement behind the existing route and API-key boundary.
2. Add focused tests and run US-026 regression coverage for the operational-status module.
3. Update operator docs and CURRENT-STATE after verification; update US-027 progress only to the demonstrated level.
4. Deploy only after separate explicit approval; no schema migration or data backfill is required.

Rollback removes the new response fields / helper logic. No persisted-state rollback is needed because the change writes nothing and adds no on-disk schema.

## Open Questions

None blocking proposal approval. If implementation discovers a class of failures stored only as free-text (not machine-readable codes), they remain excluded under the existing safe-code rules and surface via `unclassified` only when a validated code exists—or as a data issue when failure evidence is present but not safely classifiable.
