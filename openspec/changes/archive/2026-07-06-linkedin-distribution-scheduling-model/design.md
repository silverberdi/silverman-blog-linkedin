## Context

### Umbrella and sequencing

This is **child change 6** under the active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`. Completed siblings:

| Slice | Change | Delivers |
|-------|--------|----------|
| 1 | `editorial-canon-and-linkedin-distribution-strategy` | `content-strategy/silverman-editorial-system.md`, spec `editorial-canon` |
| 2 | `flow-a-lifecycle-and-duplicate-prevention` | `campaign_lifecycle.py`, spec `flow-a-lifecycle` |
| 3 | `ready-post-editorial-validation` | `ready_post_validation.py`, spec `ready-post-editorial-validation` |
| 4 | `worker-blog-publishing-endpoint` | `POST /publish-blog-post`, `blog_publish_flow.py`, spec `worker-blog-publishing-endpoint` |
| 5 | `linkedin-derivative-package-generation` | `POST /generate-linkedin-package`, `linkedin_package_flow.py`, spec `linkedin-derivative-package-generation` |
| 6 | `linkedin-distribution-scheduling-model` (this change) | `POST /schedule-linkedin-distribution`, `linkedin_distribution_schedule.py` |

The umbrella lifecycle diagram places **SCHEDULE DISTRIBUTION** after **GENERATE DERIVATIVE PACKAGE**. Slice 5 leaves campaigns in `derivatives_generated` with package artifacts and metadata; slice 6 computes staggered per-variant schedule slots and transitions to `distribution_scheduled`.

### Current state

| Component | Distribution scheduling behavior today |
|-----------|--------------------------------------|
| `linkedin_package_flow.py` | Generates variants; writes `linkedin_package` and `variants[]` metadata; transitions to `derivatives_generated`; explicitly does NOT create scheduling metadata |
| `campaign_lifecycle.py` | States through `distribution_scheduled`; `CANONICAL_VARIANT_IDS`; `transition_state()`; `write_campaign_metadata()` |
| `content-strategy/silverman-editorial-system.md` | `#linkedin-distribution-strategy`: ≥3 calendar days between variants, max 1 per day, audience sequencing, anti-simultaneous publish |
| `main.py` | No distribution scheduling route |

Gaps for Flow A distribution scheduling:

- No worker service to compute and persist per-variant `scheduled_at_utc`.
- No `publish_state` `pending` metadata for downstream publication slice.
- No campaign lifecycle transition from `derivatives_generated` to `distribution_scheduled`.
- No schedule-level idempotency in campaign metadata.
- No HTTP endpoint for n8n to invoke scheduling after package generation.

### Policy references

- Umbrella: `flow-a-automatic-blog-linkedin-publishing-roadmap`
- Editorial canon: `openspec/specs/editorial-canon/spec.md`, `content-strategy/silverman-editorial-system.md` (`#linkedin-distribution-strategy`, `#no-redundancy-rules`)
- Lifecycle: `openspec/specs/flow-a-lifecycle/spec.md`, `campaign_lifecycle.py`
- Package generation: `openspec/specs/linkedin-derivative-package-generation/spec.md`, `linkedin_package_flow.py`

## Goals / Non-Goals

**Goals:**

- Implement `schedule_linkedin_distribution(base_path, *, campaign_id=None, source_relative_path=None, strategy=None, start_at_utc=None, timezone=None)` as the single service entry point for Flow A distribution scheduling.
- Add `POST /schedule-linkedin-distribution` with API-key auth consistent with existing worker endpoints.
- Require campaign `flow_a`, state `derivatives_generated` (or `distribution_scheduled` for idempotent re-run), `linkedin_package` metadata, matching `variants[]`, and on-disk artifacts with hash verification.
- Apply default staggered strategy: variants scheduled on separate calendar days with ≥3-day spacing per editorial canon.
- Persist per-variant scheduling metadata (`scheduled_at_utc`, `publish_state` `pending`, schedule idempotency key, artifact path/hash).
- Transition `derivatives_generated` → `distribution_scheduled` on first success.
- Support idempotent re-run when `distribution_scheduled` and schedule idempotency proof matches.
- Return `LinkedInDistributionScheduleResult` dataclass with fields required for n8n branching.
- Add `tests/test_linkedin_distribution_scheduling.py` with deterministic schedule anchors.

**Non-Goals:**

- LinkedIn API publication or `publish_state` transitions beyond `pending`.
- n8n workflow JSON changes.
- Source blog file moves.
- Derivative package regeneration.
- Flow B scheduling.
- Git commit or git push.
- Archiving umbrella or this child.

## Decisions

### 1. Service module + thin HTTP route

**Decision:** Implement `linkedin_distribution_schedule.py` with `schedule_linkedin_distribution()` orchestrating campaign reads, eligibility checks, artifact verification, schedule computation, metadata persistence, and lifecycle transitions; wire `POST /schedule-linkedin-distribution` in `main.py` as a thin adapter.

**Rationale:** Matches slices 4–5 pattern (module-first, testable without HTTP).

**Alternatives considered:** Extend `POST /generate-linkedin-package` with a `schedule_mode` flag — rejected; mixes unrelated contracts and lifecycle boundaries.

### 2. Default strategy: `flow_a_staggered`

**Decision:** Define a built-in default strategy name `flow_a_staggered` implementing editorial canon `#linkedin-distribution-strategy`:

| Parameter | Value |
|-----------|-------|
| Minimum spacing | 3 calendar days between variants |
| Max variants per calendar day | 1 |
| Simultaneous publish | Prohibited |
| Preferred publish window | 14:00 UTC (10:00 America/Bogota) unless overridden |

**Audience sequencing** for the four canonical variants (when all present):

1. `executive-recruiter` — day 0 (anchor)
2. `engineering-leadership` — day 3
3. `technical-architect` — day 6
4. `short-provocative` — day 9

When the package contains a subset of variants, preserve relative order from the full sequence and apply the same spacing from the anchor. Request MAY supply an alternate `strategy` name; unknown strategies fail with `linkedin_schedule_invalid_strategy`.

**Rationale:** Operationalizes editorial canon without parsing the artifact at runtime (consistent with slice 5 posture). Deterministic spacing enables idempotency and testability.

**Alternatives considered:** Parse `silverman-editorial-system.md` at runtime — deferred; static map aligned with canon is sufficient for slice 6.

### 3. Schedule anchor and timezone

**Decision:**

- Request MAY supply `start_at_utc` (ISO 8601 UTC, e.g. `2026-07-07T14:00:00Z`) as the deterministic scheduling anchor for the first variant.
- When omitted, default anchor is the next eligible Tuesday/Wednesday/Thursday at 14:00 UTC from current UTC time (editorial preferred days).
- All `scheduled_at_utc` values are stored and returned in UTC. Request `timezone` is accepted for documentation/future use but scheduling computation uses UTC internally for determinism and idempotency.
- Invalid anchor format fails with `linkedin_schedule_invalid_anchor`.

**Rationale:** UTC-only storage avoids DST ambiguity in metadata and idempotency proofs. Optional anchor enables deterministic tests and operator override.

**Alternatives considered:** America/Bogota-local storage — rejected for idempotency complexity; UTC is simpler and safer.

### 4. Distribution scheduling flow sequence

**Decision:** `schedule_linkedin_distribution()` executes in this order:

1. **Resolve campaign** — from `campaign_id` or derive from `source_relative_path`.
2. **Eligibility** — reject: no campaign, `flow_b`, state before `derivatives_generated`, regressive states (`distribution_complete`, `flow_a_complete`), missing `linkedin_package`, missing or mismatched `variants[]`, missing artifacts, artifact hash mismatch.
3. **Variant resolution** — derive variant list from `linkedin_package.variant_ids` (sorted); MUST match `variants[]` entries; fail on empty with `linkedin_schedule_no_variants`.
4. **Idempotent short-circuit** — if state is `distribution_scheduled` and stored schedule idempotency proof matches expected key and per-variant `scheduled_at_utc` values: return `status: completed` without rewriting schedules or appending `state_history`.
5. **Metadata mismatch guard** — if `distribution_scheduled` but stored schedule proof does not match: fail with `linkedin_schedule_metadata_mismatch`.
6. **Compute schedules** — apply strategy to produce per-variant `scheduled_at_utc` (staggered, not simultaneous).
7. **Persist** — update `variants[]` with scheduling fields, write `linkedin_distribution` object, transition `derivatives_generated` → `distribution_scheduled`.

**Rationale:** Aligns with package generation idempotency patterns. Fail-safe on mismatch prevents silent schedule drift.

### 5. Distribution scheduling idempotency key

**Decision:** Define schedule-level idempotency key:

```
schedule:{campaign_id}:{source_content_sha256}:{package_idempotency_key}:{variant_list}:{strategy}:{anchor_utc}:{flow}
```

Where:

- `{package_idempotency_key}` is `campaign.linkedin_package.idempotency_key`
- `{variant_list}` is comma-separated sorted canonical variant IDs present in the package
- `{anchor_utc}` is the normalized UTC ISO anchor used for computation (e.g. `2026-07-07T14:00:00Z`)
- `{flow}` is `flow_a`

Store in campaign metadata as `linkedin_distribution.idempotency_key`. Per-variant schedule keys:

```
schedule-variant:{campaign_id}:{variant}:{derivative_content_sha256}:{scheduled_at_utc}:{flow}
```

**Rationale:** Re-scheduling with different anchor, strategy, or package content produces a different key; idempotent re-run with same inputs returns completed without mutation.

### 6. Campaign metadata shape extensions

**Decision:** Extend campaign JSON with:

```json
{
  "linkedin_distribution": {
    "distribution_id": "<campaign_id>-dist",
    "idempotency_key": "schedule:...",
    "strategy": "flow_a_staggered",
    "anchor_utc": "2026-07-07T14:00:00Z",
    "variant_ids": ["executive-recruiter", "..."]
  },
  "variants": [
    {
      "variant": "executive-recruiter",
      "artifact_relative_path": "linkedin-posts/generated/<campaign_id>/executive-recruiter.md",
      "derivative_content_sha256": "<hex>",
      "scheduled_at_utc": "2026-07-07T14:00:00Z",
      "publish_state": "pending",
      "schedule_idempotency_key": "schedule-variant:..."
    }
  ]
}
```

Existing variant fields from package generation (`audience`, `tone`, `idempotency_key`, `generated_at`, etc.) MUST be preserved. Scheduling fields are additive.

Per-variant schedule timestamps use `scheduled_at_utc` as the canonical stored field (umbrella target spec legacy name: `schedule_at`).

No `markdown_content`, `generated_draft_content`, or variant body text in campaign metadata or HTTP responses.

**Rationale:** Publication slice reads `scheduled_at_utc` and `publish_state`; metadata remains traceable without body storage.

### 7. HTTP request/response contract

**Decision:**

**Request** (`POST /schedule-linkedin-distribution`):

- Exactly one of `campaign_id` or `source_relative_path` (required).
- Optional `strategy` (string; default `flow_a_staggered`).
- Optional `start_at_utc` (UTC ISO 8601 anchor).
- Optional `timezone` (string; informational; scheduling stored in UTC).
- `extra="forbid"` on Pydantic model.

**Response** (`LinkedInDistributionScheduleResult`):

- `status`: `completed` | `failed`
- `campaign_id`, `state`
- `distribution_id` (or `schedule_id`)
- `variant_schedules`: array of per-variant summaries (`variant`, `artifact_relative_path`, `derivative_content_sha256`, `scheduled_at_utc`, `publish_state`, `schedule_idempotency_key` — not body text)
- `distribution`: distribution metadata object
- `errors`, `warnings`
- `metadata_written`, `metadata_error_code`

Auth: `Depends(require_api_key)` consistent with `POST /generate-linkedin-package` and `POST /publish-blog-post`.

**Rationale:** n8n branches on `status`; mirrors package generation response patterns.

### 8. State machine integration

**Decision:**

| Step | Campaign state | Action |
|------|----------------|--------|
| Eligibility fail | any | Return `status: failed` with stable error code; no state change |
| Idempotent hit | `distribution_scheduled` + matching schedule key | Return `completed`; no schedule rewrite |
| Metadata mismatch | `distribution_scheduled` + mismatched proof | Fail `linkedin_schedule_metadata_mismatch` |
| Success (first run) | `derivatives_generated` | Transition → `distribution_scheduled` |
| Regressive attempt | `distribution_complete`, `flow_a_complete` | Fail `linkedin_schedule_invalid_campaign_state` |
| Before derivatives | `blog_published`, `derivatives_pending`, etc. | Fail `linkedin_schedule_invalid_campaign_state` |

Use `transition_state(..., actor="worker")` from `campaign_lifecycle.py`.

Do NOT transition beyond `distribution_scheduled` in this slice.

### 9. Artifact verification

**Decision:** Before scheduling, for each variant in `linkedin_package.variant_ids`:

1. Resolve `artifact_relative_path` from matching `variants[]` entry.
2. Confirm file exists at `base_path / artifact_relative_path`.
3. Compute SHA-256 of file contents; MUST match `derivative_content_sha256` in metadata.

Failures: `linkedin_schedule_artifact_missing`, `linkedin_schedule_artifact_hash_changed`.

**Rationale:** Scheduling must not proceed on stale or missing artifacts; publication slice depends on hash integrity.

### 10. No LinkedIn API or publication

**Decision:** This slice MUST NOT import or call any LinkedIn API client. Every scheduled variant MUST have `publish_state` `pending`. No immediate publication.

**Rationale:** Publication is deferred to `linkedin-publication-integration` (slice 8).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Anchor default drifts between runs | Idempotent key includes anchor; explicit `start_at_utc` in n8n for production |
| Timezone operator expectations | Document UTC storage; optional `timezone` field for display context |
| Variant subset ordering edge cases | Static full-sequence map; tests for 3- and 4-variant packages |
| Metadata write failure mid-transition | Structured `linkedin_schedule_metadata_write_failed`; no partial state beyond lifecycle rules |
| Editorial canon drift from static map | Map aligned with `#linkedin-distribution-strategy`; runtime parsing deferred |

## Migration Plan

1. Apply this child change: add module, endpoint, tests.
2. n8n orchestration (slice 7) will call `POST /schedule-linkedin-distribution` after `POST /generate-linkedin-package` succeeds.
3. Publication slice (8) reads `scheduled_at_utc` and `publish_state` when API integration exists.
4. Rollback: endpoint remains optional; package generation unaffected.

## Resolved Decisions

### 1. Endpoint path

**Decision:** `POST /schedule-linkedin-distribution` (not `/schedule-linkedin-package`). Name reflects lifecycle stage (distribution scheduling) distinct from package generation.

### 2. Editorial canon runtime loading

**Decision:** Static `DEFAULT_STAGGER_STRATEGY` map aligned with `#linkedin-distribution-strategy`. Do not parse `content-strategy/silverman-editorial-system.md` at runtime in this slice.

## Implementation Note (apply)

During `/opsx-apply`, inspect the real signatures and existing contracts of:

- `src/silverman_blog_linkedin/campaign_lifecycle.py`
- `src/silverman_blog_linkedin/linkedin_package_flow.py`
- `src/silverman_blog_linkedin/main.py`
- `tests/test_linkedin_package_generation.py`

Use the actual signatures. Do not invent APIs.

Especially verify:

- `CANONICAL_VARIANT_IDS`
- `transition_state`
- `write_campaign_metadata`
- `read_campaign_metadata`
- `build_package_idempotency_key` (from `linkedin_package_flow.py`)
- `LinkedInPackageResult` / campaign metadata shapes from slice 5 tests
