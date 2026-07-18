# Flow A concurrency and duplicate-execution protection (US-033)

Operator-facing outcomes for **BL-013 / US-033** only: concurrent or repeated
triggers must not duplicate **post processing**, **image generation**, or
**blog publication** (checkout handoff). Worker HTTP remains the safety net
(ADR-0001); n8n single-flight is complementary defense-in-depth.

## Status

- **Implemented, automated-tested, and acceptance criteria validated** against fixture evidence (2026-07-18).
- **Not** deployed or operationally validated on the live worker by this document alone.
- US-034 accepted (fixture evidence). US-035 and BL-013 remain open.

## In scope (US-033)

| Surface | Protection | Operator-visible outcome |
|---------|------------|--------------------------|
| Post processing (claim) | Atomic campaign-metadata CAS (+ flock) so only one non-stale `execution_state=processing` claim wins | Loser: `flow_a_execution_already_claimed`, `already_claimed=true`, `recovery_classification=manual_intervention_required` |
| Queue acceptance | Same-identity already-queued is idempotent | `skipped_already_queued` / completed accept; no second campaign JSON |
| Image generation | Re-check active sibling PNG and public `assets/images/<public_slug>.png` immediately before ComfyUI; claim losers never reach ComfyUI | `blog_image_generation.status=skipped` with `skip_reason` (`public_asset_reuse`, `already_valid`, …); existing public assets not overwritten |
| Blog publication | `already_published` short-circuit; fail-closed when public targets exist without matching identity proof; concurrent first publish leaves one artifact set | `blog_publish.status=already_published` or `blog_publish_target_exists` |

## Out of scope (do not expect from US-033)

| Story | Not delivered here |
|-------|--------------------|
| **US-034** | Delivered separately — see [flow-a-concurrency-duplicate-execution-protection-us-034.md](flow-a-concurrency-duplicate-execution-protection-us-034.md) |
| **US-035** | Restart validation evidence |
| Ops | Git push, live-site mutation, LinkedIn API publish, deploy, production n8n activation |

US-034 covers duplicate scheduling, LinkedIn once-only publish under contention,
and abandoned-claim reclaim as a story deliverable.

## How to read blocked / skip outcomes

### Already claimed

Calendar connector item `errors` include `flow_a_execution_already_claimed`.
Publish and ComfyUI are not invoked for that losing attempt. Treat as
`manual_intervention_required` until the active claim completes, is released,
or (later story) is reclaimed when stale.

### Already queued

Repeated queue acceptance for the same campaign identity and matching
`source_content_sha256` returns idempotent already-queued / completed without a
second campaign document.

### Already published

Matching blog publish identity returns `status=completed` with
`blog_publish.status=already_published` and does not rewrite public `_posts/` or
`assets/images/` targets.

### Image skip / reuse

When a reusable public or active-folder PNG already exists, generation is
skipped. Responses expose skip reason fields; they must not contain secrets,
tokens, absolute base paths, or Markdown bodies.

### Target exists (unproven identity)

Public targets present without matching stored blog publish idempotency proof
fail with `blog_publish_target_exists` and do not overwrite.

## Secret-safe responses

Contention and idempotent paths return structured codes and recovery
classification only. Do not expect content bodies, API keys, or absolute
editorial/public paths in these outcomes.

## Related

- Change proposal: `openspec/changes/add-flow-a-concurrency-duplicate-execution-protection-post-image-blog-us-033/`
- Connector notes: [editorial-calendar-flow-a-execution-connector.md](../workflows/editorial-calendar-flow-a-execution-connector.md)
- Incomplete-campaign recovery (BL-012): [flow-a-incomplete-campaign-recovery.md](flow-a-incomplete-campaign-recovery.md)
- Status authority: [CURRENT-STATE.md](../CURRENT-STATE.md)
