## Why

US-009 and US-010 are done: canonical Flow A n8n is identified and activated on `192.168.0.194` with Schedule 09:00 UTC and single-flight. BL-004 still needs **US-011** — prove LinkedIn API publication stays independently gated (fail-closed until separately approved) so scheduled Flow A cannot cause unintended LinkedIn posts. Closing US-011 closes BL-004; BL-005 remains open.

## Goals

- Satisfy **US-011** under backlog **BL-004**: keep LinkedIn publication disabled until separately approved; operator-visible outcomes; clear blocked/failure communication; no unintended change to completed US-009/US-010 work.
- Make the separation operator-clear: Flow A activation/schedule ≠ LinkedIn enablement; `distribution_scheduled` ≠ LinkedIn API published.
- Reuse the existing fail-closed path (`linkedin_publish_not_enabled`) with evidence + docs + light assertions — no new LinkedIn endpoints.
- Allow a controlled evidence window that may set `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` to prove fail-closed, then restore the prior operator-approved value (US-009 pattern). US-011 is **not** “leave LinkedIn permanently false forever.”
- Update CURRENT-STATE / RUNTIME-STATE / product progress only after demonstrated evidence; close BL-004 when US-011 ACs are demonstrated; leave BL-005 open.

## Non-Goals

- **BL-005** — Fully unattended end-to-end Flow A test.
- **BL-007 / auto_queue_pending / publish-pending WIP** — Ignore unstaged LinkedIn publication automation WIP and any publish-pending workflow.
- Flow B draft-generation workflow changes.
- Calendar rewrite to `POST /editorial-calendar/execute-flow-a-due` as Flow A body.
- New LinkedIn publication endpoints, queue/publish/cancel contract redesign, or OAuth lifecycle changes.
- Flipping LinkedIn enablement as a side effect of Flow A activation (activation already happened under US-010; this change owns the publication-guard acceptance only).
- Permanently forcing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` after validation (restore prior operator-approved value unless operator decides otherwise and records it).
- n8n Execute Command or any non-HTTP worker integration (ADR-0001).

## What Changes

- Document and prove that scheduled/activated Flow A orchestration does not call LinkedIn publication APIs and does not imply LinkedIn enablement.
- Define an operator evidence procedure (prefer empty ready / non-mutating probes) that demonstrates fail-closed LinkedIn publication when the flag is `false` via existing `linkedin_publish_not_enabled` (or equivalent stable blocked response), then restores the prior RUNTIME-STATE / `.env` operator-approved flag value.
- Add light assertions/docs/scripts as needed so outcomes are PASS/PENDING/FAIL with remediation — without duplicating US-010 activation work or inventing endpoints.
- Clarify glossary/CURRENT-STATE language: activation ≠ LinkedIn published; flag restore after a verify window is allowed and must be recorded.
- Update product progress for US-011 and close BL-004 only when evidence demonstrates all US-011 ACs; leave BL-005 incomplete.

## Capabilities

### New Capabilities

- `flow-a-linkedin-publication-guard`: Operator and system requirements for keeping LinkedIn API publication independently gated from Flow A n8n activation/schedule — fail-closed evidence via existing publication guards, controlled temporary disable/restore window, operator-visible pass/fail/pending outcomes, and BL-004 closure without claiming BL-005 or permanent LinkedIn-off policy (US-011).

### Modified Capabilities

- `flow-a-n8n-workflow-activation`: Evolve the “US-011 remains out of scope / must not close US-011” framing so activation remains non-owner of LinkedIn enablement, while US-011 closure is owned by `flow-a-linkedin-publication-guard` after demonstrated evidence; reaffirm activation MUST NOT flip LinkedIn as a side effect.
- `n8n-flow-a-blog-publish-orchestration`: Cross-reference the publication-guard capability; reaffirm the workflow MUST NOT publish to LinkedIn via API and MUST NOT depend on `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` for Flow A success through schedule.

## Impact

- **Docs/ops evidence:** New `docs/operations/us-011-*-validation-YYYY-MM-DD.md` (or equivalent); CURRENT-STATE; RUNTIME-STATE (flag before/during/after window); deployment/README notes separating Flow A schedule from LinkedIn enablement; product `user-stories.md` / `progress-checklist.md` / backlog closure for BL-004 when demonstrated.
- **Scripts/tests (light):** Optional thin verifier or assertions that Flow A export has no LinkedIn publish calls and/or that worker fail-closed `linkedin_publish_not_enabled` remains covered; reuse existing LinkedIn publication tests — no new publish endpoints.
- **Worker:** Reuse existing guarded LinkedIn publication integration; no contract expansion expected.
- **n8n:** No Schedule/activation redesign; confirm canonical Flow A workflow still excludes LinkedIn API/nodes.
- **Live ops:** Controlled temporary `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` + worker recreate for evidence, then restore prior value — explicit operator approval for live mutation.
- **Backlog:** Completes US-011 and closes BL-004; leaves BL-005, BL-007, and Flow B open.

## Acceptance criteria addressed (US-011)

| AC | How this change addresses it |
|----|------------------------------|
| Keep LinkedIn publication disabled until separately approved | Fail-closed guard remains authoritative; Flow A schedule does not enable or invoke LinkedIn API; controlled evidence may prove disabled behavior then restore prior operator-approved flag |
| Outcome visible to intended user | Pass/fail/pending evidence report + remediation; CURRENT-STATE/RUNTIME-STATE updates after demonstration |
| Failures or blocked states clearly communicated | Stable `linkedin_publish_not_enabled` (and related blocked codes); operator remediation for flag/env mismatch |
| Existing completed work not duplicated/unintentionally changed | No rework of US-009/US-010 activation; no BL-007 WIP; no new LinkedIn endpoints; no calendar rewrite |

## Acceptance criteria intentionally excluded

- BL-005 unattended full-path success criteria.
- Permanent LinkedIn-off policy after US-011 (enablement remains a separate operator/backlog decision).
- BL-007 scheduled multi-variant LinkedIn execution.
