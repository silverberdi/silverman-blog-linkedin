# LinkedIn retry and recovery classification (US-021 / US-022)

**Scope:** BL-008 — normative classification of LinkedIn publication outcomes (US-021: recoverable / non-recoverable / uncertain / blocked) plus the bounded retry, evidence-preservation, and safe manual-intervention policy (US-022: retry limits, append-only attempt/recovery evidence, class-specific confirmations, failed-state correction and cancellation).
**Status:** US-021 policy defined; US-022 mechanics **operationally validated and operator-accepted**; **BL-008 closed** — see [CURRENT-STATE.md](../CURRENT-STATE.md).
**Authority:** Canonical spec `openspec/specs/linkedin-retry-recovery-classification/` (after sync). Complements [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md) (US-018/US-019/US-020 contracts, unchanged) and [user-stories.md](../product/user-stories.md) US-021/US-022.

## Purpose and scope

US-019 records failure evidence (`last_error_code`, `last_failed_at`, `retryable`, `http_status`) as **descriptive data only** and defers all interpretation to BL-008. This document is the operator source of truth for that interpretation: given a `failed` variant's stored evidence, which class it belongs to, what is safe to do next, how many retries remain, and what evidence the worker keeps.

**In scope (US-021):** Classification of every failure and blocked outcome, recovery path per class, token-renewal behavior, and the mandatory duplicate-prevention procedure for uncertain outcomes.

**In scope (US-022):** The per-variant retry budget and counting rules, the append-only `linkedin_publication_attempts` / `linkedin_recovery_history` evidence contract, class-specific `recovery_confirmation` values on manual re-queue, failed-content correction, failed-state cancellation, exhaustion behavior, and legacy evidence normalization.

**No automatic retry exists** — not within a request, not by background job, not by auto-queue. Manual re-queue via `POST /queue-linkedin-publication` remains the only retry path for `failed` variants.

## Classification inputs

Classification is a deterministic function of evidence the worker already stores in `linkedin_publication` after a real failed attempt:

- `last_error_code` — stable code (see [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md#publication-evidence-and-failure-taxonomy-us-019))
- `http_status` — numeric when an HTTP response was received; `null` only on transport-level failure (no response); `201` when LinkedIn answered success but returned no usable post URN

The `retryable` boolean is descriptive evidence only and **is not** the classification key: it is `true` for both safe transient errors (429/5xx) and duplicate-risk uncertain outcomes (transport failure, 201 without URN). Classifying on `retryable` alone would conflate them — exactly the duplicate hazard this policy prevents.

The worker consumes this table through one shared internal classifier (`classify_linkedin_recovery`); queue and failed-state correction never maintain a second classification table. Machine-readable class tokens in responses and recovery history: `recoverable_transient`, `recoverable_after_remediation`, `non_recoverable_as_is`, `uncertain`.

## Classification table (failure classes)

Every `failed` variant belongs to exactly one class, keyed on `last_error_code` + `http_status`:

| `last_error_code` | `http_status` | Class | Recovery path (below retry limit) |
|---|---|---|---|
| `linkedin_publish_api_error` | `429` or `>= 500` | **Recoverable (transient)** | LinkedIn returned an error response, so no post was created. Wait, then manual re-queue via `POST /queue-linkedin-publication`. No `recovery_confirmation` needed (supplying one is rejected). |
| `linkedin_publish_token_invalid` | `401` | **Recoverable after remediation** | Token renewal first (see [Token-renewal behavior](#token-renewal-behavior)); then re-queue with `recovery_confirmation: "remediation_completed"`. |
| `linkedin_publish_token_expired` | any | **Recoverable after remediation** | Same as above: renewal precedes re-queue; requires `recovery_confirmation: "remediation_completed"`. |
| `linkedin_publish_insufficient_permission` | `403` | **Recoverable after remediation** | Correct LinkedIn app scopes/products (`w_member_social`, OpenID Connect), reauthorize, then re-queue with `recovery_confirmation: "remediation_completed"`. |
| `linkedin_publish_content_invalid` | `400` / `422` | **Non-recoverable as-is** | Unchanged content must not be re-queued (worker rejects it with `linkedin_publish_content_correction_required`). Correct the content via `POST /correct-linkedin-variant` (now supported for this failed class), then explicitly re-queue — no confirmation value applies. |
| `linkedin_publish_api_error` | `null` (transport failure / timeout) | **Uncertain (duplicate risk)** | The post **may exist** on LinkedIn. Mandatory verification procedure below; re-queue requires `recovery_confirmation: "linkedin_post_absence_verified"`. |
| `linkedin_publish_api_error` | `201` (success without usable URN) | **Uncertain (duplicate risk)** | The post **very likely exists**. Mandatory verification procedure below; re-queue requires `recovery_confirmation: "linkedin_post_absence_verified"`. |
| *any combination not listed above* | *any* | **Uncertain (duplicate risk)** | Fail-safe rule: an unlisted code/status combination is treated as uncertain and requires verification plus `recovery_confirmation: "linkedin_post_absence_verified"`. Example: `linkedin_publish_api_error` with another numeric 4xx (e.g. `426`). |

## Retry limits and attempt counting (US-022)

Each variant permits **at most two manual retries after its initial real LinkedIn API attempt** — three real attempts total.

**What counts as a real attempt:** only a call to the LinkedIn publication API. Exact counting rules:

| Operation | Consumes an attempt? |
|---|---|
| Real publish-due reaching the LinkedIn API (success **or** failure, incl. transport failure and 201-without-URN) | **Yes — exactly one** |
| Queue / manual re-queue (`POST /queue-linkedin-publication`) | No |
| Dry-run of any endpoint | No |
| Blocked outcomes before the API call (enablement guard, OAuth/config, missing token/URN, US-020 sequence/cadence/evidence guard, not due) | No |
| Content correction (`POST /correct-linkedin-variant`) | No |
| Cancellation (`POST /cancel-linkedin-publication`) | No |
| Manual evidence repair in campaign metadata | No |

**Per-variant budget, no shared campaign pool:** a campaign with `N` variants has a derived bound of `3N` real attempts, but each variant owns its allowance — one variant exhausting its retries never consumes another variant's recovery path.

**Counters in responses:** queue and per-variant publish results expose additive nullable `publication_attempt_count`, `manual_retries_used`, and `manual_retries_remaining`; failed-state queue, correction, and cancel results also expose `recovery_classification`. The publish result recording the **third failed attempt itself** reports `manual_retries_remaining: 0`, so exhaustion is visible immediately.

**Exhaustion:** after three recorded real attempts, manual re-queue fails with `linkedin_publish_retry_limit_exhausted`, writes no metadata, makes no LinkedIn call, and reports zero retries remaining. An exhausted variant can still be cancelled (below) or repaired manually.

## Append-only evidence (US-022)

**`linkedin_publication_attempts`** — every real LinkedIn API call appends exactly one immutable entry:

- Common fields: consecutive positive `attempt_number`, UTC `attempted_at`, `outcome` (`failed` or `published`), attempted `derivative_content_sha256`.
- Failed entries reuse US-019 fields: `last_error_code`, `last_failed_at`, `retryable`, nullable `http_status`.
- Published entries reuse: `provider`, `post_urn`, `published_at`, numeric `http_status`.

**`linkedin_recovery_history`** — every successful mutating failed-state action appends one immutable event with consecutive `event_number`, `action` (`manual_requeue`, `content_corrected`, `recovery_cancelled`), UTC `recorded_at`, source `attempt_number`, and the US-021 `classification`, plus action-specific safe details (confirmation value, previous/new content hashes, or cancellation reason).

**Latest-evidence compatibility:** the existing `linkedin_publication` object remains the latest-outcome view. **Re-queue no longer removes it** (the previous evidence-clearing behavior is resolved). A later real attempt replaces the latest object only after the prior outcome is retained in attempt history.

Neither collection ever contains secrets, variant body text, or raw LinkedIn response bodies. Dry-run returns planned counters/actions without writing either history.

### Legacy failed-evidence normalization

A `failed` variant written before US-022 has US-019 evidence but no attempt history. On its **first mutating recovery action** (real re-queue, failed correction, or failed cancellation) the worker normalizes that evidence into attempt 1 — `attempted_at` taken from `last_failed_at`, content hash taken from the current verified artifact — before applying the action. If mandatory US-019 evidence is missing or invalid (absent object, missing `last_error_code`/`last_failed_at`/`retryable`/`http_status` key, unparsable timestamp), the recovery action **fails closed** with `linkedin_publish_recovery_evidence_invalid` and changes nothing; the worker never invents evidence. Recovery from that state is deliberate manual metadata repair, then retry of the recovery action.

## Class-specific manual re-queue (US-022)

`POST /queue-linkedin-publication` gains one optional field, `recovery_confirmation`, accepting **only** `remediation_completed` or `linkedin_post_absence_verified` (anything else is HTTP 422). Per class:

| Class | Required `recovery_confirmation` | Notes |
|---|---|---|
| Recoverable (transient) | none — supplying one returns `linkedin_publish_recovery_confirmation_invalid` | Direct re-queue below the limit |
| Recoverable after remediation | `remediation_completed` | Operator attestation that the documented OAuth/scope remediation is done (checked via `GET /linkedin/oauth/status`); missing → `linkedin_publish_recovery_confirmation_required` |
| Uncertain | `linkedin_post_absence_verified` | Operator attestation of the mandatory LinkedIn verification below; missing → `linkedin_publish_recovery_confirmation_required` |
| Non-recoverable as-is (content) | none — a confirmation never substitutes for correction (`linkedin_publish_recovery_confirmation_invalid`) | Requires a recorded `content_corrected` event tied to the latest failed attempt whose `new_content_sha256` matches the current verified artifact hash; otherwise `linkedin_publish_content_correction_required` |

A pending (non-failed) queue request rejects any `recovery_confirmation` with `linkedin_publish_recovery_confirmation_invalid`. A mismatched confirmation value for the variant's class is likewise `linkedin_publish_recovery_confirmation_invalid`. Every successful failed-state re-queue appends a `manual_requeue` recovery event recording the class and the confirmation used.

## Failed-content correction and failed-state cancellation (US-022)

**Correction:** `POST /correct-linkedin-variant` additionally accepts a `failed` variant **only** when its latest evidence is `linkedin_publish_content_invalid` (non-recoverable as-is). It atomically updates the artifact and `derivative_content_sha256`, keeps `publish_state: failed`, retains all publication/attempt evidence, appends both the supervision edit audit (recovery phase) and a `content_corrected` recovery event binding previous/new hashes to the latest failed attempt, and never makes the variant auto-queue eligible. A separate explicit `POST /queue-linkedin-publication` is still required to authorize another attempt. Correction of a failed transient/remediation/uncertain variant is rejected with `linkedin_supervision_action_not_allowed` and no mutation.

**Cancellation:** `POST /cancel-linkedin-publication` additionally accepts `failed -> cancelled`, including retry-exhausted variants. It preserves the latest failure evidence and all attempt/recovery history byte-for-byte, appends a `recovery_cancelled` event (with the operator reason when supplied), makes no LinkedIn call, and uses the existing `cancelled` state, so the US-020 sequence remains released. Pending/queued cancellation behavior is unchanged; `published` variants still cannot be cancelled.

## Blocked outcomes (separate non-failure class)

Blocked outcomes are **not failures**: the variant's `publish_state` is unchanged, no LinkedIn post was attempted, **no attempt is consumed**, and **re-queue is not involved**. Recovery is resolving the named condition and re-running publish-due (`POST /publish-linkedin-due-variants`).

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

## Stable recovery error codes (US-022)

| Code | Meaning | Operator action |
|---|---|---|
| `linkedin_publish_retry_limit_exhausted` | Three real attempts recorded; re-queue refused | Cancel the variant, or repair evidence manually if the outcome was actually successful |
| `linkedin_publish_recovery_confirmation_required` | Class needs a confirmation that was not supplied | Complete the class-specific procedure, then re-queue with the required value |
| `linkedin_publish_recovery_confirmation_invalid` | Confirmation supplied on a pending queue, for the wrong class, or where none applies | Remove or correct the confirmation value |
| `linkedin_publish_content_correction_required` | Content-invalid variant has no matching correction tied to its latest failed attempt | Correct via `POST /correct-linkedin-variant`, then re-queue |
| `linkedin_publish_recovery_evidence_invalid` | Legacy failed variant lacks valid mandatory US-019 evidence | Deliberate manual metadata repair, then retry the recovery action |

## Token-renewal behavior

Token renewal follows the existing `linkedin-oauth-token-lifecycle` mechanics as the **only** token recovery paths:

- **Automatic refresh-before-publish** inside the token provider (skew-based, before a real attempt).
- **Operator browser reauthorization** when the provider reports `action_required`.

Two normative rules on top:

1. **Never a reaction.** The worker does not attempt token refresh or reauthorization as a reaction to a failed publish attempt within the same request. The exactly-one-LinkedIn-API-call-per-variant-per-request contract (US-019) is preserved.
2. **Renewal precedes re-queue.** For token-class failures (`linkedin_publish_token_invalid`, `linkedin_publish_token_expired`), confirm token validity via `GET /linkedin/oauth/status` (renewing or reauthorizing if needed) **before** calling `POST /queue-linkedin-publication` with `recovery_confirmation: "remediation_completed"`. Re-queueing against a known-bad token wastes a real attempt and writes new failure evidence.

Token values, refresh tokens, and client secrets never appear in classification documentation, responses, or evidence. `remediation_completed` is an attestation, not a credential.

## Mandatory verification procedure for uncertain outcomes

For a `failed` variant in the **uncertain** class, the operator MUST verify whether the post exists on LinkedIn **before any re-queue**: check the operator profile feed or activity for a post matching the variant within the attempt window (`last_failed_at`).

- **Post exists** → the publication actually succeeded. **Re-queue is forbidden** (and `linkedin_post_absence_verified` must not be attested). Recovery is deliberate manual evidence repair in `metadata/campaigns/<campaign-id>.json`: set the variant's `publish_state` to `published` with the **real** `linkedin_post_urn` and the **real** UTC ISO8601 `Z` `published_at` of the actual publication (cross-checked against LinkedIn). This is the same manual-repair pattern documented for invalid `published_at` evidence under US-020. The worker never guesses or auto-repairs such evidence. Once repaired, the US-020 cadence rule and sequence release apply to that campaign using the repaired evidence. Manual repair consumes no attempt.
- **Post does not exist** → manual re-queue with `recovery_confirmation: "linkedin_post_absence_verified"` is safe; the attestation is persisted in the `manual_requeue` recovery event; normal queue → publish-due rules (including the US-020 guard) apply afterward.

**Why blind re-queue is dangerous:** a duplicate created by re-queueing an uncertain outcome would **not** be caught by existing safeguards. Idempotent already-published protection and the US-020 cadence guard both key on stored `published_at`/URN evidence — and an uncertain outcome never wrote any. Verification is operator-executed; no automatic LinkedIn read/query integration exists or is introduced.

## Preserved behavior (no duplication)

US-022 changes are additive to the existing worker; they do **not** change:

- US-018/US-019/US-020 contracts: queue-from-pending, publish-due, pending/queued cancel behavior, stable codes, US-019 evidence field names and shapes, blocked-vs-failed taxonomy, idempotent already-published handling, and the publish-time sequence and cadence guard.
- The no-automatic-retry requirement of `linkedin-publication-integration`.
- `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` fail-closed semantics; all endpoints keep API-key auth and `dry_run: true` defaults.
- ADR-0001 (n8n → worker HTTP only).
- No new endpoint, environment variable, or `publish_state` value.

## Related documents

- [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md) — US-019 evidence taxonomy, US-020 guard, and per-class recovery HTTP examples
- [user-stories.md](../product/user-stories.md) — US-021 / US-022 acceptance criteria
- [CURRENT-STATE.md](../CURRENT-STATE.md) — implemented / validated status
- Canonical spec: `openspec/specs/linkedin-retry-recovery-classification/` (after sync)
