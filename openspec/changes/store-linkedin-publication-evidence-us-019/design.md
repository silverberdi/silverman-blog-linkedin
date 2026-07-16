# Design: store-linkedin-publication-evidence-us-019

## Context

US-018 (validated 2026-07-16 on `192.168.0.194`, `BUILD_REVISION=c7bce02`) delivered identify-due + auto-queue + publish-once. The worker already writes publication evidence on real success (`published_at`, `linkedin_post_urn`, `linkedin_publication` provider subset) and failure context on real API failure (`last_error_code`, `last_failed_at`, `retryable`, `http_status`), and already preserves URN/`published_at` idempotently on re-run (`linkedin_publish_already_published`, no API call). The archived US-018 design (rule D6, historical reference only) anticipated US-019 as evidence/failure-taxonomy polish **without contract conflict**.

The canonical spec `linkedin-publication-integration`, however, leaves the evidence contract underspecified:

- "`linkedin_post_urn` or `linkedin_post_id`" — no rule for which identifier is mandatory after a real successful publish; `linkedin_post_id` is never written by the current REST Posts provider.
- No normative shape for `linkedin_publication` failure context (field names, when `http_status` may be null, status of `retryable`).
- The failed-vs-not-failed condition taxonomy exists but is distributed across requirements without a single operator-readable rule, and the BL-008 boundary is implicit.
- No US-019-specific idempotency-evidence scenarios (evidence preservation observable in the HTTP response, including under `auto_queue_pending`).

Constraints: ADR-0001 (n8n → worker HTTP only), fail-closed `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, dry-run defaults, no secrets or variant body text in metadata/responses, no state-machine changes, no field renames, no contradiction of the synced US-018 auto-queue contract (additive optional fields on `auto_queue_results` entries are permitted — see D3), no changes to US-017 supervision endpoints or the scheduling model.

## Goals / Non-Goals

**Goals:**

- Normative **minimum complete evidence** rule per variant after a real successful publish, with mandatory vs optional fields.
- Normative, consolidated **failure taxonomy**: which conditions mark `publish_state=failed` and which never do, and the exact failure-context shape.
- US-019 **idempotency evidence** requirements: re-run over `published` preserves URN/`published_at` with zero new API calls, observable in the response (direct and via `auto_queue_pending`).
- **Complete evidence under `auto_queue_pending`:** `auto_queue_results` entries for published / already-published variants carry `linkedin_post_urn` and `published_at`, backed by a small additive code change to `LinkedInAutoQueueVariantResult`.
- Explicit normative **US-019 ↔ BL-008 boundary** in spec text.
- Behavioral tests mirroring each new scenario; operator docs for the evidence fields.

**Non-Goals:**

- BL-008: recoverable/non-recoverable classification rules, retry limits, retry scheduling, token-renewal behavior, duplicate-after-timeout mitigation, attempt-history preservation across re-queues.
- US-020 cadence/sequence; closing BL-007; marking US-019 complete at proposal/apply time.
- New endpoints, request fields, publish states, or renames; changes to queue/cancel/supervision contracts; n8n activation; deployment or live validation.

## Decisions

### D1 — Minimum complete evidence rule (mandatory vs optional)

After a real successful LinkedIn publish, variant metadata MUST contain, at minimum:

| Field | Status | Rule |
|---|---|---|
| `linkedin_post_urn` | **Mandatory** | Non-empty external identifier returned by LinkedIn REST Posts (`X-RestLi-Id`) |
| `published_at` | **Mandatory** | UTC ISO8601 `Z` timestamp written at publish time |
| `linkedin_publication.provider` | **Mandatory** | e.g. `linkedin_rest_posts` |
| `linkedin_publication.post_urn` | **Mandatory** | Equal to `linkedin_post_urn` |
| `linkedin_publication.published_at` | **Mandatory** | Equal to `published_at` |
| `linkedin_publication.http_status` | **Mandatory** | `http_status` is mandatory in `linkedin_publication` for success and failure alike after a real attempt: numeric when an HTTP response was received (success is always `201`), `null` only when none was (transport failure — see D2) |
| `linkedin_post_id` | **Optional** | Permitted additive alias; not written by the current provider — never a substitute for the URN |

- **Why URN-mandatory over the current "URN or post_id":** the implemented and operationally validated provider returns a URN; making the identifier disjunctive leaves "complete evidence" unverifiable. The delta resolves the ambiguity in favor of observed, validated behavior (spec formalization, not behavior change). `linkedin_post_id` remains legal as an optional extra so a future provider change is additive, not breaking.
- A real publish "success" that cannot produce a non-empty URN is already treated as an API failure by the client (`linkedin_publish_api_error` on missing `X-RestLi-Id`) — the spec makes this an explicit evidence-completeness scenario.

### D2 — Failure taxonomy and failure-context shape

Consolidated normative rule (matches implemented behavior; no state-machine change):

**Marks `publish_state=failed` (only after a real LinkedIn API attempt):**

- LinkedIn API error response (mapped by HTTP status: invalid/expired token, insufficient permission, content rejection, API error)
- Transport-level failure while calling the API (no HTTP response)
- Success response without a usable post identifier

**Never marks `failed` (blocked conditions; response fails with stable code, `publish_state` unchanged):**

- `linkedin_publish_not_enabled` (enablement off — fail-closed)
- `linkedin_oauth_reauthorization_required` / OAuth `action_required` from the token provider
- `linkedin_publish_member_urn_missing`, `linkedin_publish_token_missing`
- Dry-run (never attempts, never fails a variant)

Content rejection maps to the dedicated stable code `linkedin_publish_content_invalid` (non-retryable), distinct from the generic `linkedin_publish_api_error` — the taxonomy keeps them separately observable.

Failure context written to `linkedin_publication` after a real failed attempt MUST contain at minimum these fields in a safe shape (no secrets, no variant body text, no raw API response bodies; future additions must remain safe):

- `last_error_code` (stable code from the documented set) — **mandatory**
- `last_failed_at` (UTC ISO8601 `Z`) — **mandatory**
- `retryable` (boolean) — **mandatory as recorded evidence**; its *interpretation* (whether/when to retry) is BL-008 and out of scope
- `http_status` — **mandatory but nullable**: null when no HTTP response was received (transport error)

**Why record `retryable` now if retry rules are BL-008:** it is already written by the implementation and costs nothing to preserve; removing it would destroy evidence BL-008 needs. US-019 freezes it as descriptive evidence only — the spec states explicitly that no retry behavior is derived from it in this change.

### D3 — Idempotency evidence (US-019, not a US-018 re-run)

US-018 proved once-only publication operationally. US-019 makes the *evidence* of that idempotency normative and observable:

- Re-running publish-due (any combination of `dry_run=false`, `publish_now`, `auto_queue_pending`) over a `published` variant MUST: make zero LinkedIn API calls for it, preserve stored `linkedin_post_urn` and `published_at` byte-for-byte, and return the preserved values in the per-variant response with warning `linkedin_publish_already_published` (direct/publish phase) or skip reason `linkedin_publish_auto_queue_skipped_state` (auto-queue phase).
- The response is the operator's evidence surface: for a published or already-published outcome, per-variant results MUST carry `linkedin_post_urn` and `published_at` (already present in the US-018 publish-phase result shape — clarifying MODIFY there).
- **Evidence is also required in the auto-queue phase:** when a variant results `published` or already-published within an `auto_queue_pending` scan — including the cross-campaign scan without `campaign_id` — its `auto_queue_results` entry MUST include `linkedin_post_urn` and `published_at`. A `published` variant encountered by the scan still reports skip reason `linkedin_publish_auto_queue_skipped_state`, but the entry carries the preserved URN and `published_at` so the operator never loses evidence visibility in the combined response.
- **Additive code delta (small):** `LinkedInAutoQueueVariantResult` gains optional `linkedin_post_urn` and `published_at` fields (default `None`), populated when the publish phase confirms a published or already-published outcome for that variant, or from stored metadata for an already-`published` variant skipped by the scan. This only adds fields to `auto_queue_results` entries — no rename, no removal, no shape break of the synced US-018 contract.

### D4 — Gap assessment: spec + tests + docs + one small additive code change

Inspection of `linkedin_publication_flow.py` / `linkedin_client.py` against D1–D2 shows metadata-evidence behavior already satisfies those rules (success evidence at publish, failure context on API failure including `http_status=None` transport case, blocked conditions leaving state untouched, idempotent already-published publish-phase response carrying preserved URN/`published_at`). The gap is therefore **not spec-only**:

- **One real code gap (D3):** `auto_queue_results` entries today carry no `linkedin_post_urn`/`published_at`. Closing it requires the small additive change to `LinkedInAutoQueueVariantResult` described in D3, with a dedicated test asserting both fields present for published and already-published outcomes under `auto_queue_pending`.
- Everything else in the delta converts existing behavior into verifiable requirements/scenarios; no other code work is planned. If a new test falsifies a D1–D2 rule, the fix is the smallest code diff restoring spec conformance — reported before editing, per inspect-before-edit.
- Adjacent behavior deliberately **not** respecified: what happens to stored evidence after a manual re-queue of a `failed` variant (preservation, clearing, or attempt history) is explicitly out of scope of US-019 and is a BL-008 normative decision (US-022 "preserve operational evidence"). US-019 neither authorizes nor prohibits evidence loss in that case — the delta names this exclusion explicitly so current fresh-attempt behavior is not read as a US-019 defect nor as US-019-sanctioned.

### D5 — Normative US-019 ↔ BL-008 boundary

| Concern | US-019 (this change) | BL-008 (excluded) |
|---|---|---|
| Publication identifier + timestamp completeness | Normative | — |
| Failure context shape + failed-vs-blocked taxonomy | Normative | — |
| Observable idempotency of re-runs over `published` | Normative | — |
| `retryable` flag | Recorded as evidence only | Interpretation, classification rules |
| Recoverable vs non-recoverable error classes | — | Normative |
| Token renewal behavior on failure | — | Normative |
| Duplicate prevention after timeouts / uncertain outcomes | — | Normative |
| Retry limits, re-queue attempt history preservation | — | Normative |
| Evidence behavior after manual re-queue of a `failed` variant (preserve / clear / history) | Explicitly out of scope — neither authorized nor prohibited | Normative |

This table's substance is carried into the delta spec so archive/sync preserves the boundary.

## Risks / Trade-offs

- [MODIFIED requirements could drift from the synced US-018 text] → each MODIFIED block copies the full current canonical requirement and only adds; `openspec validate --strict` plus a manual diff of the delta against `openspec/specs/linkedin-publication-integration/spec.md` before approval.
- [Making URN mandatory could break a hypothetical future provider returning only a post id] → `linkedin_post_id` stays as an optional additive field; a provider change would be its own OpenSpec change anyway.
- [Adding fields to `auto_queue_results` could be read as breaking the US-018 contract] → the change is strictly additive (optional fields, default `None`); no existing field is renamed, removed, or retyped, and the delta copies the canonical requirement text before extending it.
- [New tests might reveal a further spec↔behavior gap beyond D3] → smallest conforming diff, reported before editing (D4); no other code work is planned.
- [Freezing `retryable` as evidence could be misread as retry policy] → spec text states no retry behavior derives from it; boundary table in delta.
- [Docs-only completion illusion] → US-019 story checkboxes and progress checklist update only after `/opsx-verify` + demonstrated outcomes; BL-007 stays open regardless.

## Migration Plan

1. Approval → `/opsx-apply`: delta specs authored here become the working contract; the D3 additive change to `LinkedInAutoQueueVariantResult` is implemented with its dedicated test; remaining tests added mirroring scenarios; targeted `pytest tests/test_linkedin_publication.py` plus full suite (executable code changes).
2. `/opsx-verify` → explicit commit approval → implementation commit; then `/opsx-sync` (separate commit) merges MODIFIED/ADDED requirements into `openspec/specs/linkedin-publication-integration/spec.md`; then `/opsx-archive` (separate commit).
3. The change includes executable code, so deploy of the updated worker is a separately approved step with `BUILD_REVISION` confirmation; until deployed, the auto-queue evidence fields exist only in the local build.
4. Rollback: revert the implementation commit; no metadata migrations (evidence fields already exist in production campaign files).

## Open Questions

- None blocking. Cadence/sequence (US-020) and retry/recovery (BL-008) intentionally deferred.
