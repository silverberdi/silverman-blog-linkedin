## 1. Recovery Model and Evidence Helpers

- [x] 1.1 Add the shared US-021 classifier helper and constants for two manual retries, supported confirmations, and stable US-022 errors; cover every existing code/status class and unlisted-to-uncertain fallback.
- [x] 1.2 Implement validated attempt-count/counter helpers plus append-only `linkedin_publication_attempts` and `linkedin_recovery_history` builders with no secrets, variant body text, or raw response bodies.
- [x] 1.3 Implement lazy normalization of valid legacy failed evidence before mutation and fail closed with `linkedin_publish_recovery_evidence_invalid` when mandatory US-019 evidence is invalid.

## 2. Publication Attempt Recording

- [x] 2.1 Update every real LinkedIn API outcome path (success, API/content/token/permission failure, transport failure, and success without URN) to append exactly one numbered attempt while retaining the latest `linkedin_publication` compatibility view.
- [x] 2.2 Add attempt/retry counters to per-variant publication results and prove blocked, dry-run, OAuth/configuration, and guard paths do not append or consume attempts.

## 3. Bounded Manual Re-queue

- [x] 3.1 Extend the queue service with class-aware `recovery_confirmation`, two-retry enforcement, content-correction evidence validation, recovery-event append, and preservation of latest failure evidence.
- [x] 3.2 Extend `QueueLinkedInPublicationRequest` and route wiring with the constrained optional confirmation field while preserving API-key auth, strict extra-field rejection, and dry-run defaults.
- [x] 3.3 Add queue response fields for attempt count, retries used/remaining, and recovery classification; return stable errors for exhaustion, missing/mismatched confirmation, missing correction, and invalid legacy evidence.

## 4. Safe Failed-state Intervention

- [x] 4.1 Extend `correct_linkedin_variant` only for failed `linkedin_publish_content_invalid`: atomically update artifact/hash, retain failed state and evidence, append supervision/recovery audit, and require separate manual queue.
- [x] 4.2 Extend failed-state correction request/response tests for dry-run, idempotency, changed-content proof, ineligible failure classes, write failure, and absence of automatic queue/publication.
- [x] 4.3 Extend `cancel_linkedin_publication` for `failed -> cancelled`, including exhausted variants, while preserving evidence, appending recovery cancellation audit, making no LinkedIn call, and leaving existing pending/queued/published behavior unchanged.

## 5. Behavioral and Regression Tests

- [x] 5.1 Add publication tests for append-only attempts across all outcome shapes, evidence preservation over re-queue and later outcomes, counter accuracy, and valid/invalid legacy normalization.
- [x] 5.2 Add tests allowing exactly two manual retries, blocking the third re-queue, proving only real API calls count, proving variants do not share a campaign retry pool, and proving no automatic retry exists.
- [x] 5.3 Add class-specific queue tests for transient, remediation, uncertain (including unlisted fallback), content-invalid correction, wrong/inapplicable confirmation, dry-run zero mutation, auth, and HTTP 422 validation.
- [x] 5.4 Add failed correction/cancellation tests that preserve attempts/recovery history and verify responses/metadata contain no secrets or variant body text.
- [x] 5.5 Run focused `tests/test_linkedin_publication.py` and `tests/test_linkedin_supervision_flow.py`, then the full pytest suite; fix root causes without weakening existing US-018/US-019/US-020 assertions and confirm zero new warnings.

## 6. Operator Documentation and Product Traceability

- [x] 6.1 Update `docs/operations/linkedin-retry-recovery-classification.md` with the two-retry policy, counting table, evidence schema, class-specific confirmations, content correction, failed cancellation, exhaustion, and legacy normalization procedure.
- [x] 6.2 Update `docs/deployment/linkedin-publication-prerequisites.md` with exact HTTP examples and operator steps for each recovery class, preserving the fail-closed publication guard and ADR-0001 HTTP-only boundary.
- [x] 6.3 Update `docs/CURRENT-STATE.md` to replace the evidence-clearing divergence with qualified implemented/tested status; do not claim deployment or operational validation and do not change RUNTIME-STATE because no live flag changes.
- [x] 6.4 Map demonstrated evidence to all US-022 criteria in `docs/product/user-stories.md` and update `docs/product/progress-checklist.md` only to the demonstrated/reviewed level; keep US-022 unaccepted and BL-008 open unless the business outcome is explicitly reviewed and accepted.

## 7. Verification and Business Validation

- [x] 7.1 Run strict OpenSpec validation, `git diff --check`, and a focused secrets audit over every modified/new file.
- [x] 7.2 Run `/opsx-verify` after all edits and re-run it if any post-verification edit occurs.
- [ ] 7.3 Conduct the final intended-user review: demonstrate visible limits, retained evidence, safe correction/cancellation, clear blocked/exhausted states, and no duplicate/unintended BL-007 changes; record whether US-022 is accepted and close BL-008 only if every backlog outcome is demonstrated.
