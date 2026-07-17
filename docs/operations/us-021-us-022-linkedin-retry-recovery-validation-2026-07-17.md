# US-021 / US-022 — LinkedIn retry and recovery: operational validation (2026-07-17)

**Host:** `192.168.0.194`
**Deployed revision:** `BUILD_REVISION=d15d85b0c5827cc8d0a4fdb5038b01530a009f87`
**Worker:** `http://192.168.0.194:8010`
**Operator approval:** BL-008 demonstration explicitly approved in session 2026-07-17; controlled failure injection and real publication approved per step.

## Scope

End-to-end operational demonstration of the BL-008 recovery chain on a real, calendar-due variant: controlled real failure → US-021 classification → class-aware re-queue guardrails → mandatory uncertain-class operator verification → attested re-queue → successful real retry → append-only evidence and idempotency verification.

## Subject

`flow-a-2026-07-10-a-bounded-context-is-not-a-folder :: engineering-leadership` — due per calendar (`scheduled_at_utc` 2026-07-17T14:00:00Z), sequence released (campaign's `executive-recruiter` published 2026-07-11), cadence free (>72h).

## Controlled failure method

Transport-level block injected in the running worker container only: `127.0.0.1 api.linkedin.com` appended to the container `/etc/hosts` (backup taken), removed immediately after the failed attempt. No code, config, token, or flag changes; guard `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` untouched. This produces a genuine `POST /rest/posts` connection failure — the exact transport-failure shape the uncertain class models.

## Timeline and results

| Step | Result |
|---|---|
| Queue dry-run (pending variant) | counters exposed: `publication_attempt_count 0`, `manual_retries_remaining 2` |
| Queue real | `pending → queued`, no LinkedIn call |
| Real publish-due attempt 1 (hosts block active) | `publish_state: failed`, `linkedin_publish_api_error`, `http_status: null`, attempt #1 appended (`attempted_at 2026-07-17T19:54:55Z`), `manual_retries_remaining 2` |
| Hosts restored | container `/etc/hosts` back to original (0 `api.linkedin.com` entries) |
| Classification surfaced | queue responses report `recovery_classification: "uncertain"` (transport failure = duplicate risk; matches the US-021 table) |
| Re-queue without confirmation (real) | rejected `linkedin_publish_recovery_confirmation_required`, `metadata_written: false` |
| Re-queue with wrong class confirmation (`remediation_completed`) | rejected `linkedin_publish_recovery_confirmation_invalid`, `metadata_written: false` |
| Mandatory uncertain-class verification | operator checked LinkedIn profile/activity: **no post exists** in the `last_failed_at` window (attested in session, 2026-07-17 ~19:58Z) |
| Attested re-queue (`linkedin_post_absence_verified`) | `failed → queued`, recovery event #1 appended (`manual_requeue`, class `uncertain`, confirmation persisted, tied to attempt 1) |
| Real publish-due attempt 2 | `published`, URN `urn:li:share:7483974070842241024`, `published_at 2026-07-17T20:01:04Z`, `http_status 201`, `publication_attempt_count 2`, `manual_retries_used 1` |
| Replay (real, same request) | idempotent `linkedin_publish_already_published`, same URN, attempts stay 2 — no duplicate |

## Final stored evidence (campaign metadata)

- `publish_state: published`; latest `linkedin_publication` complete per US-019 (`provider linkedin_rest_posts`, URN, `published_at`, `http_status 201`).
- `linkedin_publication_attempts`: `#1 failed` (transport, `http_status null`) and `#2 published` (`201`) — the failed attempt **retained** after re-queue and success (US-021 evidence-clearing divergence confirmed resolved in operation).
- `linkedin_recovery_history`: one `manual_requeue` event, classification `uncertain`, confirmation `linkedin_post_absence_verified`, source attempt 1.

## Acceptance-criteria demonstration mapping

| Criterion (US-021/US-022) | Operational evidence |
|---|---|
| Classify recoverable/non-recoverable errors | Real transport failure classified `uncertain` per the deterministic table; class exposed in queue responses |
| Prevent duplicate posts after timeouts | Blind re-queue impossible (`confirmation_required`); mandatory operator verification executed before attestation; replay idempotent after success |
| Set retry limits | Budget counters correct at every step (0→1→2 attempts; 2→2→1 retries remaining); queue/correction/cancel operations consumed nothing |
| Preserve operational evidence | Append-only attempt history retained the failure after recovery; recovery event recorded; latest evidence complete |
| Support safe manual intervention | Class-specific confirmations enforced (missing → required; wrong class → invalid; correct → accepted and persisted) |
| Failures/blocked clearly communicated | Stable codes `linkedin_publish_recovery_confirmation_required` / `_invalid` observed with zero mutation |
| Token-renewal behavior | Not exercised in this window (no token-class failure occurred); mechanics remain per `linkedin-oauth-token-lifecycle`; policy-defined scope unchanged |

Not exercised operationally (unit-tested only): content-invalid correction path (`POST /correct-linkedin-variant`), `failed → cancelled`, retry exhaustion (third attempt), legacy evidence normalization. These paths require failure shapes that did not occur and were not worth forcing with additional real posts.

## Qualified status

- US-022 mechanics **operationally validated** on the transport-failure/uncertain recovery chain; remaining paths covered at unit-test scope.
- US-021 classification **operationally exercised** for the uncertain class; the classification policy itself was already accepted at policy-definition scope.
- BL-008 closure is a business decision: the demonstrated outcome (recover a real failure without losing traceability or duplicating content) is satisfied on the primary path.
