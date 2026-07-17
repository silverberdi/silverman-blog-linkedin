## Why

BL-008 / US-022 requires bounded recovery after LinkedIn publication failures, but the worker currently permits unlimited manual re-queue and deletes the latest `linkedin_publication` failure evidence when a failed variant is queued again. Operators also lack a supported way to correct a content-rejected failed variant or deliberately stop retrying it, so recovery is neither fully traceable nor safely actionable.

## Goals

- Set and enforce a clear manual retry limit per variant while retaining the US-021 classification and no-automatic-retry boundary.
- Preserve an append-only record of real LinkedIn attempts and operator recovery actions across re-queue, correction, success, and cancellation.
- Require class-appropriate operator confirmation before risky re-queue and provide safe correction or cancellation paths for failed variants.
- Communicate attempt counts, remaining retries, exhausted limits, and required remediation through stable worker responses and operator documentation.
- Demonstrate every US-022 acceptance criterion without reopening completed BL-007 behavior.

## Non-goals

- Automatic retries, background retry jobs, n8n activation, deployment, or live LinkedIn publication.
- Reclassification of US-021 outcomes or changes to token-renewal ordering and uncertain-outcome verification.
- New `publish_state` values, a broad redesign of US-019 evidence fields, or changes to the fail-closed LinkedIn publication guard.
- BL-009 article-preview validation, BL-015 supervision console work, or general campaign recovery under BL-012.
- Marking US-022 accepted or BL-008 complete from proposal or implementation alone.

## What Changes

- Define a maximum of two manual retries after the initial real LinkedIn attempt for each variant (three real attempts total). There is no separate shared campaign quota; a campaign's bound is the sum of its per-variant bounds, so one variant cannot consume another's recovery allowance.
- Count only real LinkedIn API calls as attempts; blocked outcomes, dry-runs, queue operations, corrections, cancellations, and manual evidence repair do not consume the limit.
- Preserve US-019 evidence in append-only per-attempt history and stop clearing the latest failure context on re-queue. Legacy failed variants without history are normalized from their current US-019 failure evidence before recovery.
- Add one optional, constrained recovery-confirmation field to `POST /queue-linkedin-publication`: remediation confirmation for US-021 “recoverable after remediation” outcomes, or LinkedIn-absence confirmation for “uncertain” outcomes. Transient recovery needs no confirmation; unchanged non-recoverable content remains blocked.
- Extend existing worker mechanics minimally: permit `POST /correct-linkedin-variant` to correct a `failed` `linkedin_publish_content_invalid` variant while it remains failed, and permit `POST /cancel-linkedin-publication` to move a failed or retry-exhausted variant to existing state `cancelled`.
- Persist class, confirmation, correction, re-queue, exhaustion, and cancellation evidence without secrets, variant body text, or raw LinkedIn responses.
- Add stable operator-visible retry-limit and recovery-action errors plus additive attempt/retry counters in relevant responses.
- Update operator policy, CURRENT-STATE, US-022 traceability, and tests. Product completion remains pending until the business outcome is demonstrated and accepted.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `linkedin-retry-recovery-classification`: Define the US-022 retry budget, attempt-counting rules, evidence-retention contract, class-specific confirmations, exhaustion behavior, and safe manual intervention policy while consuming the existing US-021 classification unchanged.
- `linkedin-publication-integration`: Enforce the retry budget in the existing queue path, preserve append-only attempt/recovery evidence, add the minimal queue confirmation field and response counters, and extend existing correction/cancel services to supported failed-state recovery actions.

## Impact

- Worker code: `linkedin_publication_flow.py`, `linkedin_supervision_flow.py`, and the existing FastAPI request models/route wiring in `main.py`.
- Tests: focused additions to `tests/test_linkedin_publication.py`, `tests/test_linkedin_supervision_flow.py`, and API validation coverage; existing US-018/US-019/US-020 tests must remain unchanged and pass.
- Documentation: the US-021 recovery policy, LinkedIn publication prerequisites, CURRENT-STATE, user-story traceability, and progress checklist after demonstrated outcomes.
- API compatibility: no endpoint removal or `publish_state` change. Existing pending-queue callers remain valid; failed re-queue gains class-aware validation, one optional request field, stable errors, and additive response fields.
- Operations: no n8n activation, deployment, environment-variable change, or real LinkedIn call is part of this change. ADR-0001 remains binding: any orchestration continues to use worker HTTP endpoints only.
