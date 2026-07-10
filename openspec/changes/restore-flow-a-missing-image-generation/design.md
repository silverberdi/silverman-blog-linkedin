## Context

Flow A business rule (unchanged): ~99% of approved posts arrive in `blog-posts/ready/` as Markdown only. Frontmatter contains canonical `image: /assets/images/<public_slug>.png` or omits `image` entirely. A missing companion PNG must trigger automatic ComfyUI generation (or public-asset reuse/backfill) before full editorial validation blocks publish. Generated images follow the active source through queue processing, public asset handoff, and lifecycle completion.

The archived change `flow-a-operational-queue-lifecycle` correctly introduced `ready/` → `queued/` acceptance and moved sources to `blog-posts/queued/` before execution. Its design stated full `validate_ready_post()` runs after acceptance at processing start before `publish_blog_post`. Implementation placed that call in `editorial_calendar_flow_a_execute._execute_flow_a_item` (line ~358), which runs **before** `publish_blog_post`. Full validation requires companion PNG (`ready_post_image_missing`), so Markdown-only queued sources fail before `publish_blog_post` can invoke image remediation.

Additional gaps predate or compound the regression:

- `blog_image_generation.py` hardcodes `READY_RELATIVE_PREFIX` for PNG detection and output.
- `github_pages_publish.resolve_source_paths` resolves only `blog-posts/ready/<slug>.{md,png}`.
- Current proposed ordering performs public asset handoff inside `ensure_blog_image` before full validation — a durable external side effect that must not precede full validation.
- Pre-generation validation incorrectly requires a canonical non-empty `image` value before remediation, blocking ComfyUI from patching missing frontmatter.
- Connector tests stub `validate_ready_post`, masking the failure.

Constraints: worker owns file I/O over HTTP (ADR-0001); no n8n Execute Command; no real ComfyUI in tests; preserve queue lifecycle, idempotency, and direct ready publish paths.

## Goals / Non-Goals

**Goals:**

- Restore canonical Flow A sequence for Markdown-only sources through queue lifecycle.
- Staged image workflow: editorial remediation and frontmatter patch before full validation; public handoff only after full validation.
- Two-phase validation with explicit responsibilities and stable error codes.
- Authorized source-hash mutation when image remediation patches frontmatter.
- Explicit failure-state and claim-release ownership per failure class.
- Active-source-folder image path derivation for `ready/` and `queued/`.
- Integration tests proving end-to-end connector path without validation stubs.

**Non-Goals:**

- Queue lifecycle redesign, deployment, calendar edits, LinkedIn publication, UI.
- Global suppression of image validation errors.
- Modifying archived OpenSpec changes.

## Decisions

### 1. Canonical publish orchestration ordering (staged image workflow)

**Decision:** Connector sequence for real execution per item:

```
accept_flow_a_source_for_queue (or already-queued resolution)
→ claim_flow_a_execution
→ publish_blog_post(active queued source_relative_path)
    → validate_ready_post_pre_generation()
    → ensure_editorial_blog_image()          # detect, generate/adopt/backfill locally; patch frontmatter; NO public repo write
    → authorized hash reconciliation           # recompute active source_content_sha256; persist on campaign
    → validate_ready_post()                    # full validation against Markdown + local companion PNG
    → handoff_public_blog_image()              # copy/reuse validated PNG into public assets
    → GitHub Pages post publish
→ generate_linkedin_package
→ schedule_linkedin_distribution
→ complete_flow_a_source_lifecycle
→ release_flow_a_execution (only when claim not already closed by terminal/error-move path)
```

`ensure_blog_image()` MAY remain the public compatibility entry point for legacy/direct calls, but `publish_blog_post` orchestration MUST use an internal staged contract (or equivalent option) that defers `handoff_public_blog_image` until after full validation succeeds.

**Rationale:** Public asset handoff writes into the configured GitHub Pages checkout — a durable external side effect. Full-validation failures before handoff are deterministic pre-side-effect failures eligible for queued → `error/`; they must not occur after public writes. Splitting editorial remediation from public handoff preserves the queue lifecycle failure policy.

**Alternative considered:** Keep handoff inside `ensure_blog_image` before validation. Rejected — inconsistent failure classification and violates pre-side-effect deterministic error-move policy.

**Alternative considered:** Connector runs pre-generation validation, then publish without re-validating. Rejected — duplicates validation entry points and risks drift between connector and direct publish paths.

### 2. Two-phase validation model

**Decision:** Split `ready_post_validation` into:

| Phase | Entry point | Validates | Missing/empty frontmatter `image` | Missing companion PNG |
|-------|-------------|-----------|-----------------------------------|----------------------|
| Pre-generation | `validate_ready_post_pre_generation()` | Safe confined path; `.md`; readable non-empty content; frontmatter parse; required editorial fields except generatable `image`; publication-date rules; campaign identity/hash compatibility | **Non-blocking** when image generation enabled, source eligible, no unsafe/conflicting image reference, and ComfyUI may add canonical `image` | **Non-blocking** under same generation-eligibility conditions |
| Full | `validate_ready_post()` | All pre-generation checks **plus** canonical non-empty `image: /assets/images/<public_slug>.png`; companion PNG presence, extension, readability beside active folder | **Blocking** | **Blocking** (`ready_post_image_missing` or `ready_post_image_invalid_extension`) |

Pre-generation MUST still block:

- non-empty non-canonical `image` path;
- conflicting same-basename non-PNG extensions;
- unsafe paths; empty content; campaign mismatch unrelated to authorized image remediation.

When generation is disabled, missing/empty `image` or missing PNG MUST ultimately fail full validation — pre-generation does not waive strict requirements when remediation cannot run.

Full validation runs only after editorial image remediation completes (success, skip with existing PNG, adoption, or public-asset backfill into active folder). Generation failures return specific `blog_image_generation_*` codes — never masked as `ready_post_image_missing`.

**Rationale:** Preserves canonical ComfyUI behavior for missing frontmatter `image` and missing companion PNG; keeps deterministic gates without blocking the generatable path; full validation remains strict post-remediation.

### 3. Staged image responsibilities

**Decision:** One canonical implementation design with two explicit phases:

| Phase | Responsibility | Public repo write |
|-------|----------------|-------------------|
| `ensure_editorial_blog_image` (or internal equivalent) | Detect missing/empty/non-canonical state; ComfyUI generate when eligible; adopt local sibling; backfill active-folder sibling from public asset when readable public asset exists and ComfyUI must not run; patch canonical frontmatter when authorized; record editorial provenance | **No** |
| `handoff_public_blog_image` (or internal equivalent) | Copy or reuse validated active-folder PNG into `assets/images/<public_slug>.png` after full validation | **Yes** |

`ensure_blog_image()` MAY delegate to both phases for non-publish callers, but `publish_blog_post` MUST invoke them in staged order with handoff deferred.

### 4. Active source folder image path strategy

**Decision:** Derive companion image path from the parent folder of `source_relative_path`:

| Active Markdown | Companion PNG |
|-----------------|---------------|
| `blog-posts/ready/<source_slug>.md` | `blog-posts/ready/<source_slug>.png` |
| `blog-posts/queued/<source_slug>.md` | `blog-posts/queued/<source_slug>.png` |

Implementation: extract allowed prefix from `source_relative_path` (`ALLOWED_VALIDATION_PREFIXES`); reject other folders. Editorial image helpers accept `source_relative_path` and derive folder — no hardcoded `READY_RELATIVE_PREFIX` for detection or write.

### 5. Public asset reuse and local backfill

**Decision:** When a readable public asset exists at `assets/images/<public_slug>.png` but the active-folder sibling PNG is missing:

- ComfyUI MUST NOT run.
- The system MAY backfill the active-folder sibling from the public asset during `ensure_editorial_blog_image`.
- Full validation MUST operate on the active local Markdown + companion PNG pair.
- Publish MUST NOT bypass full validation because the public asset exists.
- If local backfill fails, publish MUST fail explicitly; classification is `retryable` or `repair_required` per cause — never silent continuation without local companion when full validation requires it.

This supersedes canonical language suggesting publish may continue without the local sibling when validation requires it.

### 6. Authorized source-hash mutation protocol

**Decision:** Image remediation may add or normalize the canonical `image` frontmatter field. This is an authorized worker mutation, not operator content change.

Protocol:

1. Record or retain queue/intake hash for traceability (`intake_source_content_sha256` when not already present; otherwise preserve existing intake field).
2. Allow only the expected canonical `image` frontmatter mutation by the image-remediation phase.
3. Recompute active `source_content_sha256` from updated Markdown bytes.
4. Persist updated active hash on the same campaign before full validation and publish idempotency checks.
5. Recompute blog publish idempotency key from updated active hash.
6. Preserve `campaign_id`, `source_slug`, `public_slug`, original path chain, queue metadata, attempt metadata, and state history.
7. Do NOT classify authorized remediation as `campaign_content_hash_changed` or `blog_publish_content_hash_changed`.
8. Any unrelated body or frontmatter mutation MUST still fail the existing content-hash guard.
9. Metadata-write failure during authorized hash reconciliation MUST block publish and return a stable explicit error without writing public repo files.

### 7. GitHub Pages source resolution

**Decision:** Refactor `resolve_source_paths(config, source_relative_path)` to parse folder from path (`ready`, `queued`, or `processed` for idempotent reruns), resolve paired `.md`/`.png` under editorial base with confinement, and reject unsupported folders.

`blog_publish_flow` passes active `source_relative_path` from campaign resolution, not assumed `ready/`.

CLI operator helper remains `ready/`-only — out of scope for queued connector path.

### 8. Lifecycle completion

**Decision:** `complete_flow_a_source_lifecycle` discovers companion PNG beside active queued Markdown (including ComfyUI-generated `blog-posts/queued/<slug>.png`). Coordinated move to `processed/` preserves logical slugs, active content hash, generation metadata, handoff metadata, and partial-move recovery semantics.

### 9. Failure behavior and claim-release ownership

| Failure class | ComfyUI | Public handoff | Blog publish | Source location | execution_state | recovery_classification | Claim release |
|---------------|---------|----------------|--------------|-----------------|-----------------|-------------------------|---------------|
| Pre-generation deterministic validation | No | No | No | `error/` when post-acceptance policy applies | `idle` after error move | `requeue_required` / `manual_intervention_required` | Error move owns closure; connector MUST NOT redundantly release |
| Full validation before handoff | N/A | No | No | `error/` when post-acceptance policy applies | `idle` after error move | per editorial policy | Error move owns closure; connector MUST NOT redundantly release |
| ComfyUI unavailable/timeout/transient | Attempted/failed | No | No | `queued/` | `idle` | `retryable` | `release_flow_a_execution` exactly once |
| Local image write/frontmatter patch inconsistency | N/A | No | No | reconcilable `queued/` | `idle` when possible | `repair_required` | `release_flow_a_execution` exactly once when claim remains `processing` |
| Public handoff after successful full validation | N/A | Failed | No | `queued/` | `idle` | `repair_required` | `release_flow_a_execution` exactly once |
| Hash metadata persistence failure during authorized reconciliation | N/A | No | No | `queued/` | `idle` | `repair_required` | `release_flow_a_execution` exactly once when applicable |
| Existing valid companion PNG | Skip | After full validation | Continue | Unchanged | per pipeline | per pipeline | per terminal path |

Persist specific `blog_image_generation_*` codes for ComfyUI failures; `blog_image_public_asset_handoff_failed` for handoff failures; `last_error.category` values: `image_generation` / `transient_runtime` for ComfyUI transient failures; `public_asset_handoff` for post-validation handoff failures.

No package, schedule, or lifecycle completion on any image-related failure path.

### 10. Backward compatibility

**Decision:** Direct `publish_blog_post` with `blog-posts/ready/<slug>.md` unchanged in outcome: pre-generation → editorial remediation → hash reconciliation → full validation → public handoff → publish. Legacy direct-ready behavior that generates and patches missing frontmatter `image` is preserved. Existing ready-path ComfyUI tests remain valid. Queue lifecycle claims, stale detection, retry, processed/error semantics untouched except queued image path support and staged handoff ordering.

### 11. Test strategy

**Decision:** Retain 17-test matrix and add explicit tests for:

- missing frontmatter `image` remediation;
- empty `image` remediation;
- non-canonical non-empty `image` blocking;
- generation-disabled strict validation;
- full-validation failure produces no public asset write;
- authorized frontmatter patch updates campaign hash safely;
- unrelated Markdown mutation rejected;
- ComfyUI transient failure ends queued/idle/retryable with single release;
- handoff failure ends queued/idle/repair_required with single release;
- deterministic validation error move does not cause redundant release;
- public asset reuse backfills queued sibling and passes full validation without ComfyUI;
- public asset reuse with failed queued-sibling backfill does not publish.

Use real validation functions; fake only external boundaries (ComfyUI client, public repo I/O failure injection).

## Risks / Trade-offs

- **[Risk] Staged handoff refactor touches publish and image modules** → Mitigation: keep `ensure_blog_image` facade; staged contract internal to `blog_publish_flow`.
- **[Risk] Hash reconciliation race with validation guard** → Mitigation: persist authorized hash immediately after remediation; validation compares against active hash only for unauthorized changes.
- **[Risk] Connector double-release after error move** → Mitigation: explicit claim-owner matrix in connector spec; integration tests assert release call count.
- **[Risk] Tests still stub validation** → Mitigation: mandatory test matrix in tasks; explicit prohibition in spec scenarios.

## Migration Plan

1. Deploy worker with validation, staged image, and path fixes.
2. Queued Markdown-only sources in production: next connector run proceeds through generation automatically.
3. No data migration; generated PNGs appear beside queued sources on first successful run.
4. **Rollback:** Revert worker; partial generated PNGs in `queued/` remain beside Markdown for operator inspection.

## Open Questions

- None blocking proposal. Apply may name pre-generation entry point `validate_ready_post_pre_generation` or `validate_ready_post(..., phase="pre_generation")` — single canonical name required in implementation.
