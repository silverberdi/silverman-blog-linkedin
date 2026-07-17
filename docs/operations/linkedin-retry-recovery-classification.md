# LinkedIn retry and recovery classification (US-021)

**Scope:** US-021 (BL-008 story 1) — normative classification of LinkedIn publication outcomes (recoverable / non-recoverable / uncertain / blocked) and the safe recovery path per class.
**Status:** Policy defined (docs + canonical spec). Policy defined ≠ operationally validated. No worker code, endpoint, request field, environment variable, `publish_state` value, or evidence field changes.
**Authority:** Canonical spec `openspec/specs/linkedin-retry-recovery-classification/` (after sync). Complements [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md) (US-018/US-019/US-020 contracts, unchanged) and [user-stories.md](../product/user-stories.md) US-021.

## Purpose and scope

US-019 records failure evidence (`last_error_code`, `last_failed_at`, `retryable`, `http_status`) as **descriptive data only** and defers all interpretation to BL-008. This document is the operator source of truth for that interpretation: given a `failed` variant's stored evidence, which class it belongs to and what is safe to do next.

**In scope (US-021):** Classification of every failure and blocked outcome, recovery path per class over existing operations only, token-renewal behavior, and the mandatory duplicate-prevention procedure for uncertain outcomes.

**Out of scope (US-022):** Retry limits, attempt counting, automated retry execution, and evidence preservation across manual re-queue. **No automatic retry exists**; manual re-queue via `POST /queue-linkedin-publication` remains the only retry path for `failed` variants.

## Classification inputs

Classification is a deterministic function of evidence the worker already stores in `linkedin_publication` after a real failed attempt:

- `last_error_code` — stable code (see [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md#publication-evidence-and-failure-taxonomy-us-019))
- `http_status` — numeric when an HTTP response was received; `null` only on transport-level failure (no response); `201` when LinkedIn answered success but returned no usable post URN

The `retryable` boolean is descriptive evidence only and **is not** the classification key: it is `true` for both safe transient errors (429/5xx) and duplicate-risk uncertain outcomes (transport failure, 201 without URN). Classifying on `retryable` alone would conflate them — exactly the duplicate hazard this policy prevents.

## Classification table (failure classes)

Every `failed` variant belongs to exactly one class, keyed on `last_error_code` + `http_status`:

| `last_error_code` | `http_status` | Class | Recovery path |
|---|---|---|---|
| `linkedin_publish_api_error` | `429` or `>= 500` | **Recoverable (transient)** | LinkedIn returned an error response, so no post was created. Wait, then manual re-queue via `POST /queue-linkedin-publication`. No verification step required. |
| `linkedin_publish_token_invalid` | `401` | **Recoverable after remediation** | Token renewal first (see [Token-renewal behavior](#token-renewal-behavior)); only then is manual re-queue meaningful. |
| `linkedin_publish_token_expired` | any | **Recoverable after remediation** | Same as above: token renewal precedes re-queue. |
| `linkedin_publish_insufficient_permission` | `403` | **Recoverable after remediation** | Correct LinkedIn app scopes/products (`w_member_social`, OpenID Connect), then reauthorize, then manual re-queue. |
| `linkedin_publish_content_invalid` | `400` / `422` | **Non-recoverable as-is** | Re-queueing the unchanged variant is expected to fail again — do **not** re-queue. No supported worker path currently corrects the content of a `failed` variant (documented limitation; resolution deferred to US-022). |
| `linkedin_publish_api_error` | `null` (transport failure / timeout) | **Uncertain (duplicate risk)** | The post **may exist** on LinkedIn. Mandatory verification procedure below before any re-queue. |
| `linkedin_publish_api_error` | `201` (success without usable URN) | **Uncertain (duplicate risk)** | The post **very likely exists**. Mandatory verification procedure below before any re-queue. |
| *any combination not listed above* | *any* | **Uncertain (duplicate risk)** | Fail-safe rule: an unlisted code/status combination is treated as uncertain and requires verification before re-queue. Example: `linkedin_publish_api_error` with another numeric 4xx (e.g. `426`) is not listed and therefore falls here. |

## Blocked outcomes (separate non-failure class)

Blocked outcomes are **not failures**: the variant's `publish_state` is unchanged, no LinkedIn post was attempted, and **re-queue is not involved**. Recovery is resolving the named condition and re-running publish-due (`POST /publish-linkedin-due-variants`).

| Stable code | Condition | Recovery |
|---|---|---|
| `linkedin_publish_not_enabled` | `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` not `true` | Enable only within an approved window; the guard remains fail-closed and this policy defines no step that bypasses or weakens it |
| `linkedin_oauth_reauthorization_required` (and related token-provider `action_required`) | OAuth refresh unavailable | Browser reauthorization, then re-run publish-due; variant remains `queued` |
| `linkedin_publish_token_missing` | No token resolvable | Complete OAuth setup, then re-run publish-due |
| `linkedin_publish_member_urn_missing` | No member URN resolvable | Complete OAuth setup (URN from OIDC), then re-run publish-due |
| `linkedin_publish_blocked_sequence` / `linkedin_publish_blocked_cadence` / `linkedin_publish_blocked_evidence_invalid` | US-020 publish-time guard | Wait out the guard (sequence/cadence) or repair invalid `published_at` evidence per US-020 documentation, then re-run publish-due |
| `linkedin_publish_auto_queue_skipped_*` | Auto-queue pre-filter skip | Informational; publish-time guard is the enforcement point |
| dry-run outcomes | `dry_run: true` | Not an error; re-run with `dry_run: false` when intended |

Do not communicate blocked outcomes to operators as failures requiring re-queue.

## Token-renewal behavior

Token renewal follows the existing `linkedin-oauth-token-lifecycle` mechanics as the **only** token recovery paths:

- **Automatic refresh-before-publish** inside the token provider (skew-based, before a real attempt).
- **Operator browser reauthorization** when the provider reports `action_required`.

Two normative rules on top:

1. **Never a reaction.** The worker does not attempt token refresh or reauthorization as a reaction to a failed publish attempt within the same request. The exactly-one-LinkedIn-API-call-per-variant-per-request contract (US-019) is preserved.
2. **Renewal precedes re-queue.** For token-class failures (`linkedin_publish_token_invalid`, `linkedin_publish_token_expired`), confirm token validity via `GET /linkedin/oauth/status` (renewing or reauthorizing if needed) **before** calling `POST /queue-linkedin-publication`. Re-queueing against a known-bad token wastes a real attempt and writes new failure evidence.

Token values, refresh tokens, and client secrets never appear in classification documentation, responses, or evidence.

## Mandatory verification procedure for uncertain outcomes

For a `failed` variant in the **uncertain** class, the operator MUST verify whether the post exists on LinkedIn **before any re-queue**: check the operator profile feed or activity for a post matching the variant within the attempt window (`last_failed_at`).

- **Post exists** → the publication actually succeeded. **Re-queue is forbidden.** Recovery is deliberate manual evidence repair in `metadata/campaigns/<campaign-id>.json`: set the variant's `publish_state` to `published` with the **real** `linkedin_post_urn` and the **real** UTC ISO8601 `Z` `published_at` of the actual publication (cross-checked against LinkedIn). This is the same manual-repair pattern documented for invalid `published_at` evidence under US-020. The worker never guesses or auto-repairs such evidence. Once repaired, the US-020 cadence rule and sequence release apply to that campaign using the repaired evidence.
- **Post does not exist** → manual re-queue via `POST /queue-linkedin-publication` is safe; normal queue → publish-due rules (including the US-020 guard) apply afterward.

**Why blind re-queue is dangerous:** a duplicate created by re-queueing an uncertain outcome would **not** be caught by existing safeguards. Idempotent already-published protection and the US-020 cadence guard both key on stored `published_at`/URN evidence — and an uncertain outcome never wrote any. Verification is operator-executed; no automatic LinkedIn read/query integration exists or is introduced.

## US-022 boundaries and known divergence

- **No automatic retry.** This policy adds no retry execution. Retry limits, attempt counting, and any automated retry mechanics are US-022.
- **Evidence clearing on re-queue (known divergence, recorded for US-022).** Current implementation behavior: `queue_linkedin_publication` clears the stored `linkedin_publication` failure context when re-queueing a `failed` variant, so classification evidence is lost at re-queue time. US-019 explicitly declared this neither authorized nor prohibited; whether attempt history must be preserved is the US-022 "preserve operational evidence" decision. Operators SHOULD note the stored evidence (`last_error_code`, `http_status`, `last_failed_at`) before re-queueing if traceability matters, until US-022 resolves this.
- **Content-correction dead end.** `linkedin_publish_content_invalid` has no supported worker correction path for `failed` variants (`POST /correct-linkedin-variant` requires `publish_state` `pending`). The safe interim answer is: do not re-queue unchanged content. A supported correction or cancel path for `failed` variants is a candidate US-022 concern.

## Preserved behavior (no duplication)

US-021 is documentation/policy + canonical spec only. It does **not** change:

- US-018/US-019/US-020 contracts: queue, publish-due, cancel behavior, stable codes, evidence shapes, blocked-vs-failed taxonomy, idempotent already-published handling, and the publish-time sequence and cadence guard.
- The no-automatic-retry requirement of `linkedin-publication-integration`.
- `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` fail-closed semantics.
- ADR-0001 (n8n → worker HTTP only).

## Related documents

- [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md) — US-019 evidence taxonomy, US-020 guard, and the manual re-queue touchpoint
- [user-stories.md](../product/user-stories.md) — US-021 / US-022 acceptance criteria
- [CURRENT-STATE.md](../CURRENT-STATE.md) — policy-defined status and known divergence record
- Canonical spec: `openspec/specs/linkedin-retry-recovery-classification/` (after sync)
