## Context

### Umbrella and sequencing

This is **child change 2** under the active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`. Child change 1 (`editorial-canon-and-linkedin-distribution-strategy`, archived) established `content-strategy/silverman-editorial-system.md` and canonical spec `editorial-canon`. The umbrella defines Flow A lifecycle states, slug terminology, derivative package model, idempotency expectations, and dependency order for slices 3–8.

This child implements the **foundational metadata and duplicate-prevention layer** the umbrella defers to slice 2. Future endpoints MUST NOT invent alternate campaign schemas.

### Current state

| Component | Lifecycle behavior today |
|-----------|-------------------------|
| `run_metadata.py` | Per-request run traces under `metadata/runs/`; no campaign-level lifecycle |
| `paths.py` | Expects `metadata/campaigns/` folder; no campaign writers |
| `github_pages_publish.py` | Idempotent blog publish at CLI level via target existence; not tied to campaign metadata |
| `POST /generate-linkedin-draft` | Single-variant generation; no campaign linkage or derivative idempotency |
| Flow A policy | Documented in umbrella and editorial canon; not persisted in campaign metadata |

The worker remains the filesystem and metadata boundary (ADR-0001). n8n orchestrates over HTTP only.

### Policy references (not parsed at runtime in this change)

- Umbrella: `flow-a-automatic-blog-linkedin-publishing-roadmap`
- Canonical spec: `openspec/specs/editorial-canon/spec.md`
- Canonical artifact: `content-strategy/silverman-editorial-system.md` (`#flow-a-vs-flow-b`)

## Goals / Non-Goals

**Goals:**

- Define `metadata/campaigns/<campaign-id>.json` JSON schema with required fields and nested structures.
- Implement lifecycle state machine with enforced valid transitions for Flow A.
- Define and implement idempotency key builders for blog publish, derivative variants, and LinkedIn schedule slots.
- Record state history with timestamps, from/to states, reason, actor, and error codes on failure transitions.
- Reserve `flow_b` in the `flow` enum with guardrails preventing automatic Flow A transitions.
- Implement metadata persistence helpers consistent with `run_metadata.py` patterns.
- Exclude `markdown_content` and `generated_draft_content` from campaign metadata serialization.

**Non-Goals:**

- HTTP endpoints for validation, publish, package generation, or scheduling.
- Physical file movement helpers (policy documented; implementation deferred to orchestration children).
- n8n workflow JSON, LinkedIn API integration, Flow B workflow.
- Runtime editorial canon loading.
- Archiving umbrella or this child change.

## Campaign metadata schema

### Storage path

```
metadata/campaigns/<campaign-id>.json
```

`metadata/campaigns/` MUST exist and be writable before persistence (same readiness pattern as `metadata/runs/`).

### Campaign ID format

**Pattern:** `flow-a-<publication-date>-<public-slug>` or `flow-b-<publication-date>-<public-slug>`

- `publication-date`: `YYYY-MM-DD` from frontmatter `date` (ISO date portion); MUST be a valid calendar date.
- `public-slug`: derived public slug after numeric prefix strip (aligned with `github_pages_publish.derive_public_slug`).
- Characters: lowercase letters, digits, hyphens only; no path separators, `..`, spaces, or uppercase.
- Slug segment MUST match `^[a-z0-9]+(?:-[a-z0-9]+)*$`.
- Example: `flow-a-2026-07-06-why-i-did-not-start-with-the-database`

Persisted campaign IDs MUST be validated by `validate_campaign_id()` before path resolution. Invalid IDs raise `CampaignLifecycleError` with error code `invalid_campaign_id` in path helpers, or return structured write failure / `None` on read.

Flow B campaigns (future) MAY use `flow-b-<publication-date>-<public-slug>`; this change reserves the prefix but does not implement Flow B creation paths beyond enum/guard validation.

### Top-level document shape

```json
{
  "campaign_id": "flow-a-2026-07-06-why-i-did-not-start-with-the-database",
  "flow": "flow_a",
  "state": "ready",
  "created_at": "2026-07-06T14:30:00Z",
  "updated_at": "2026-07-06T14:30:00Z",
  "source_slug": "01-why-i-did-not-start-with-the-database",
  "public_slug": "why-i-did-not-start-with-the-database",
  "source_relative_path": "blog-posts/ready/01-why-i-did-not-start-with-the-database.md",
  "image_relative_path": "blog-posts/ready/01-why-i-did-not-start-with-the-database.png",
  "source_content_sha256": "<hex-sha256-of-markdown-bytes>",
  "publication_date": "2026-07-06",
  "source_public_url": null,
  "blog_publish": {
    "idempotency_key": "blog:01-why-i-did-not-start-with-the-database:why-i-did-not-start-with-the-database:2026-07-06:<sha256-prefix>",
    "status": "pending",
    "published_at": null,
    "error_code": null
  },
  "variants": [],
  "state_history": [],
  "errors": [],
  "warnings": [],
  "source_file_status": {
    "location": "ready",
    "marked_processed_at": null,
    "marked_error_at": null
  }
}
```

**Forbidden fields** (MUST NOT appear in persisted campaign JSON): `markdown_content`, `generated_draft_content`, `draft_content`, `api_key`, or any secret.

### Nested: `blog_publish`

| Field | Type | Purpose |
|-------|------|---------|
| `idempotency_key` | string | Stable blog publish intent key |
| `status` | enum | `pending`, `published`, `already_published`, `failed` |
| `published_at` | ISO8601 or null | When publish confirmed |
| `error_code` | string or null | Machine-readable failure |

### Canonical LinkedIn variant IDs

The `variant` field MUST use a canonical variant ID from `content-strategy/silverman-editorial-system.md` (`#linkedin-derivative-package`):

| Canonical variant ID | Audience lens |
|----------------------|---------------|
| `executive-recruiter` | Recruiters + C-level |
| `technical-architect` | Software architects |
| `engineering-leadership` | Engineering managers |
| `short-provocative` | Senior ICs + enthusiasts |

**Rules:**

- Variant IDs are hyphenated lowercase strings; snake_case aliases (e.g. `short_provocative`) MUST NOT be used.
- New variant IDs MAY be added only by updating the editorial canon first; lifecycle metadata does not define its own variant vocabulary.
- Default Flow A package trio per canon: `executive-recruiter`, `technical-architect`, `short-provocative`; optional fourth: `engineering-leadership`.

### Nested: `variants[]`

Each derivative variant entry:

| Field | Type | Purpose |
|-------|------|---------|
| `variant` | string | Canonical variant ID from editorial canon (e.g. `executive-recruiter`, `technical-architect`, `engineering-leadership`, `short-provocative`) |
| `idempotency_key` | string | Derivative generation key |
| `draft_relative_path` | string or null | Path to draft file when generated |
| `draft_content_sha256` | string or null | Fingerprint of draft file |
| `schedule_at` | ISO8601 or null | Scheduled publication time |
| `publish_state` | enum | `pending`, `scheduled`, `published`, `skipped`, `failed` |
| `schedule_idempotency_key` | string or null | LinkedIn slot key when scheduled |
| `error_code` | string or null | Variant-level failure |

### Nested: `state_history[]`

| Field | Type | Purpose |
|-------|------|---------|
| `at` | ISO8601 UTC | Transition timestamp |
| `from_state` | string or null | Prior state (`null` on create) |
| `to_state` | string | New state |
| `reason` | string | Human-readable transition reason |
| `actor` | enum | `worker`, `n8n`, `manual` |
| `error_code` | string or null | Required on failure transitions to `validation_failed` or `error` |

### Nested: `source_file_status`

Tracks metadata-only marking until orchestration children perform physical moves.

| Field | Type | Purpose |
|-------|------|---------|
| `location` | enum | `ready`, `processed`, `error` |
| `marked_processed_at` | ISO8601 or null | When lifecycle closed or source marked processed |
| `marked_error_at` | ISO8601 or null | When validation/unrecoverable error recorded |

## Lifecycle state machine

### States

| State | Meaning |
|-------|---------|
| `ready` | Campaign created; source in `blog-posts/ready/`; not yet validated |
| `validation_failed` | Automated validation failed |
| `validated` | Passed Flow A validation; eligible for publish |
| `blog_publish_pending` | Blog publish requested or in progress |
| `blog_published` | GitHub Pages assets written; URL confirmed in metadata |
| `derivatives_pending` | Blog live; package generation not started or in progress |
| `derivatives_generated` | LinkedIn package created; scheduling may be pending |
| `distribution_scheduled` | Each derivative has schedule slot per strategy |
| `distribution_complete` | All scheduled derivatives published or terminal |
| `flow_a_complete` | Lifecycle closed; source marked processed per policy |
| `error` | Unrecoverable failure |

### Valid transitions (Flow A)

Enforced by `transition_state()` helper; invalid transitions raise `InvalidStateTransition`.

```
ready → validation_failed | validated | error
validation_failed → error (terminal for auto-retry without re-ready)
validated → blog_publish_pending | error
blog_publish_pending → blog_published | error
blog_published → derivatives_pending | error
derivatives_pending → derivatives_generated | error
derivatives_generated → distribution_scheduled | error
distribution_scheduled → distribution_complete | error
distribution_complete → flow_a_complete | error
flow_a_complete → (terminal)
error → (terminal unless manual reset — not implemented in this change)
```

Failure transitions to `validation_failed` or `error` MUST include `error_code` in the history entry and append to top-level `errors[]`.

### Flow B guardrail

- `flow` MUST be `flow_a` or `flow_b`.
- Automatic Flow A transition helpers MUST reject campaigns where `flow == flow_b` with error code `flow_b_not_eligible_for_flow_a`.
- Flow B campaign creation MAY be stubbed for tests only; no Flow B workflow implementation.

## Idempotency keys

### Blog publish

**Key format:**

```
blog:{source_slug}:{public_slug}:{publication_date}:{source_content_sha256}
```

**Expected behavior (future `POST /publish-blog-post`):**

- First publish: `blog_publish.status` → `published`; write targets via GitHub Pages bridge.
- Re-run when targets exist: `blog_publish.status` → `already_published`; no overwrite.

### LinkedIn derivative variant

**Key format:**

```
derivative:{campaign_id}:{source_content_sha256}:{variant}:{flow}
```

`{variant}` MUST be a canonical hyphenated variant ID (e.g. `executive-recruiter`, not `executive`).

**Examples** (campaign `flow-a-2026-07-06-why-i-did-not-start-with-the-database`, hash `abc123…`, flow `flow_a`):

```
derivative:flow-a-2026-07-06-why-i-did-not-start-with-the-database:abc123…:executive-recruiter:flow_a
derivative:flow-a-2026-07-06-why-i-did-not-start-with-the-database:abc123…:technical-architect:flow_a
derivative:flow-a-2026-07-06-why-i-did-not-start-with-the-database:abc123…:short-provocative:flow_a
```

**Expected behavior (future package generation):**

- If key matches existing variant with same `draft_relative_path` and unchanged hash: skip write; return existing path.
- If `source_content_sha256` changes: new generation allowed (new draft path).

### LinkedIn publication schedule slot

**Key format:**

```
schedule:{campaign_id}:{variant}:{scheduled_at}
```

`{variant}` MUST be a canonical hyphenated variant ID (e.g. `engineering-leadership`).

**Example:**

```
schedule:flow-a-2026-07-06-why-i-did-not-start-with-the-database:executive-recruiter:2026-07-08T14:00:00Z
```

`scheduled_at` MUST be normalized UTC ISO8601 (`YYYY-MM-DDTHH:MM:SSZ`).

**Expected behavior (future LinkedIn API integration):**

- Duplicate schedule slot for same campaign/variant/time MUST NOT create a second API publish intent.

## File movement vs metadata marking

**Decision (D1):** This change implements **metadata-only** `source_file_status` updates. Physical moves between `blog-posts/ready/`, `blog-posts/processed/`, and `blog-posts/error/` are **policy-defined but deferred** to `ready-post-editorial-validation` and `n8n-flow-a-blog-publish-orchestration`.

| Event | Metadata action (this change) | Physical move (future children) |
|-------|------------------------------|--------------------------------|
| Validation failure | `state` → `validation_failed`; `source_file_status.location` → `error` | Move to `blog-posts/error/` |
| Flow A complete | `state` → `flow_a_complete`; `source_file_status.location` → `processed` | Move to `blog-posts/processed/` |
| Unrecoverable error | `state` → `error`; `source_file_status.location` → `error` | Move or leave per orchestration policy |

Helpers MAY expose `mark_source_processed()` and `mark_source_error()` that update metadata timestamps only.

## Implementation layout

### Module: `campaign_lifecycle.py`

Located alongside `run_metadata.py` under `src/silverman_blog_linkedin/`.

**Constants:**

- `METADATA_CAMPAIGNS_RELATIVE = "metadata/campaigns"`
- `FLOW_A = "flow_a"`, `FLOW_B = "flow_b"`
- Lifecycle state enum strings
- `FORBIDDEN_METADATA_FIELDS` frozenset

**Functions (minimum):**

| Function | Purpose |
|----------|---------|
| `validate_campaign_id(campaign_id)` | Validate persisted campaign ID format and path safety |
| `generate_campaign_id(flow, publication_date, public_slug)` | Build safe campaign ID |
| `build_blog_publish_idempotency_key(...)` | Blog publish key |
| `build_derivative_idempotency_key(...)` | Variant generation key |
| `build_schedule_idempotency_key(...)` | LinkedIn slot key |
| `compute_source_content_sha256(content: bytes \| str)` | SHA-256 hex digest |
| `build_initial_campaign_metadata(...)` | Create new campaign document |
| `transition_state(campaign, to_state, *, reason, actor, error_code=None)` | Enforce transitions + history |
| `sanitize_campaign_metadata(payload)` | Strip forbidden fields before write |
| `check_metadata_campaigns_ready(base_path)` | Readiness check |
| `write_campaign_metadata(base_path, campaign_id, payload)` | Persist JSON; returns `CampaignMetadataWriteResult` with `written` and `error_code` |
| `read_campaign_metadata(base_path, campaign_id)` | Load JSON; returns `None` for invalid campaign ID |
| `campaign_metadata_relative_path(campaign_id)` | Relative path helper; validates campaign ID before resolving path |

Reuse `utc_now_iso()` from `run_metadata` or duplicate minimally to avoid circular imports.

### Tests: `test_campaign_lifecycle.py`

Cover:

- Campaign ID generation (canonical example slug/date)
- Unsafe slug rejection in campaign ID
- Initial metadata shape and required fields
- State transitions along happy path
- Invalid transition rejection
- Failure transitions require `error_code`
- Idempotency key stability and format
- `sanitize_campaign_metadata` removes forbidden fields
- Flow B campaign rejected by Flow A transition helper
- Serialization round-trip without content bodies

## Decisions

### D1: Metadata-first; defer file moves

**Decision:** Record `source_file_status` in campaign JSON; do not implement `shutil.move` helpers in this change.

**Rationale:** Umbrella open question on when to move sources; validation child owns failure moves; orchestration owns completion moves.

**Alternatives:** Implement moves now — rejected; couples lifecycle foundation to orchestration timing.

### D2: Campaign ID includes flow prefix and publication date

**Decision:** `flow-a-YYYY-MM-DD-<public-slug>` format.

**Rationale:** Stable across reruns; human-readable; avoids collisions when same slug republished on different dates.

**Alternatives:** UUID-only — rejected; poor operator traceability.

### D3: Enforce state machine in helper layer

**Decision:** `transition_state()` validates allowed edges; callers (future endpoints) cannot set `state` directly without helper.

**Rationale:** Prevents orphan states when multiple endpoints update the same campaign.

**Alternatives:** Document-only state machine — rejected; too easy to drift at implementation time.

### D4: Idempotency keys as namespaced strings

**Decision:** Prefix keys with `blog:`, `derivative:`, `schedule:` for log grep and future index.

**Rationale:** Single string field per idempotency domain; no separate hash table service.

### D5: Reuse `metadata/campaigns` from `paths.py`

**Decision:** Align with existing `EXPECTED_FOLDERS`; same readiness pattern as `metadata/runs`.

**Rationale:** Consistent deployment validation; no new folder layout.

### D6: Hyphenated canonical variant IDs from editorial canon

**Decision:** `variants[].variant` and all idempotency keys use hyphenated canonical IDs from `content-strategy/silverman-editorial-system.md` (`executive-recruiter`, `technical-architect`, `engineering-leadership`, `short-provocative`). No snake_case aliases.

**Rationale:** Single vocabulary across canon, campaign metadata, prompts, and scheduling; avoids drift between `executive` and `executive-recruiter`.

**Alternatives:** Accept legacy short names in lifecycle layer — rejected; would fork vocabulary from canon.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Campaign JSON schema drift in future children | Single spec `flow-a-lifecycle`; helpers centralize shape |
| Same slug republished on same date with different content | `source_content_sha256` in blog and derivative keys detects change |
| Flow B accidentally enters Flow A path | `flow` guard on transition helpers; spec scenario |
| Metadata grows large | No content bodies; variants array bounded by canon max variants |
| State machine too rigid for edge cases | `error` terminal state + manual intervention documented; manual actor in history |

## Migration Plan

1. Apply this change: add `campaign_lifecycle.py` and tests; no endpoint behavior change.
2. Future validation child creates/updates campaign on first touch of a ready post.
3. Future publish child reads `blog_publish.idempotency_key` before CLI apply.
4. Existing `metadata/runs/` traces remain; campaigns are orthogonal long-lived documents.

Rollback: remove module; no production campaigns until slice 3+; zero impact on current endpoints.

## Open Questions

1. Should `flow_a_complete` allow re-open for derivative-only retries, or require new campaign ID?
2. When source content hash changes mid-campaign, auto-reset state or create new campaign?
3. Should campaign metadata include `run_id` cross-references to `metadata/runs/` entries?
