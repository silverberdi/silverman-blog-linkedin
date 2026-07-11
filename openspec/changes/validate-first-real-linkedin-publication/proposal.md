## Why

LinkedIn API publication is **implemented and unit-tested** (`linkedin-publication-integration`, `linkedin-oauth-token-lifecycle`) but remains **not operationally validated** — `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` on the production worker at last baseline. Backlog item **BL-002** blocks confidence in the P1 Flow A completion path and all P2 LinkedIn automation work until one real variant is published traceably, with a stored URN, visible on LinkedIn, without duplicate side effects, and with publication safeguards restored afterward. US-001/US-002 established the controlled-validation pattern on `192.168.0.194`; this change applies the same discipline to **US-003**, **US-004**, and **US-005**.

## Goals

- Satisfy **US-003**: validate OAuth credentials and member identity; select one approved variant; move it through `pending` → `queued` → `published`; surface clear outcomes and failures; avoid unintentional changes to unrelated campaigns or variants.
- Satisfy **US-004**: store `linkedin_post_urn` in campaign metadata; confirm the post is visible on LinkedIn; verify idempotent repeat publish-due does not create a duplicate external post.
- Satisfy **US-005**: restore publication safeguards (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false`) after the controlled test; document the validation window and remediation.
- Provide a repeatable server-side validation entry point (mirroring `run-us001-git-publication-smoke.sh` / `run-us002-live-site-confirmation-smoke.sh`) and a Phase 3 evidence report template.
- Update `docs/CURRENT-STATE.md`, `docs/RUNTIME-STATE.md`, and product progress only when acceptance criteria are demonstrated with real LinkedIn evidence.

## Non-Goals

- New LinkedIn publication endpoints, state model changes, or n8n workflow activation (BL-004).
- Publishing multiple variants or full scheduled distribution execution (BL-007).
- LinkedIn article preview validation (BL-009).
- OAuth token lifecycle redesign (BL-024) beyond preflight checks needed for this validation.
- Automatic background publish when `publish_after_utc` elapses.
- Claiming `flow_a_complete` beyond existing campaign lifecycle semantics or fully unattended Flow A (BL-005).
- Deleting or editing the published LinkedIn post after validation (operator may choose to delete manually; out of scope).

## What Changes

- Add `deploy/server/run-us003-linkedin-publication-validation-smoke.sh` — controlled end-to-end validation on the Ubuntu server: OAuth/credential preflight, real queue, real publish-due with `publish_now`, idempotent rerun, variant state snapshots, and safeguard restoration checklist.
- Extend `deploy/server/run-linkedin-publication-smoke.sh` only as needed for US-003/US-004 evidence (e.g. `publish_now`, idempotency rerun flags, member-identity summary without secrets).
- Add operator runbook section and Phase 3 validation report under `docs/operations/` (evidence template; no secrets).
- Document controlled validation prerequisites: valid OAuth token store, member URN resolution, publication flag enablement window, and selection of one approved variant on a `distribution_scheduled` Flow A campaign.
- Record operational validation outcomes in canonical context (`CURRENT-STATE`, `RUNTIME-STATE`, `progress-checklist`) after demonstrated evidence — not at proposal time.
- Fix only validation-blocking gaps discovered during controlled testing (minimal scope; no speculative refactors).
- Document OAuth operator bootstrap as a **blocking prerequisite** before the validation window (token store files, Cloudflare tunnel, browser authorization) — parallel to US-001 deploy-key setup; not assumed complete from prior phases.

Unlike US-001/US-002, there is **no automatic cleanup** of the external artifact: one real LinkedIn post remains visible on the operator profile until manually removed in LinkedIn.

No **BREAKING** changes to existing LinkedIn publication HTTP defaults (`dry_run: true` remains default).

## Capabilities

### New Capabilities

- `linkedin-publication-operational-validation`: Controlled first-real-publish validation playbook — server smoke script, OAuth/credential preflight, state-transition evidence, idempotency check, LinkedIn visibility confirmation checklist, safeguard restoration, and Phase 3 report requirements.

### Modified Capabilities

- `linkedin-publication-integration`: Add normative requirements for US-003/US-004 controlled validation script, idempotent repeat publish-due evidence, and post-validation safeguard restoration documentation.
- `linkedin-oauth-token-lifecycle`: Add preflight validation requirement (member identity and token readiness) before controlled real publish; safe diagnostic output without tokens.
- `flow-a-deployment-readiness-and-smoke-test`: Reference US-003 LinkedIn validation entry point alongside existing Flow A and US-001/US-002 smoke scripts.

## Impact

- **Scripts:** new `run-us003-linkedin-publication-validation-smoke.sh`; possible minor updates to `run-linkedin-publication-smoke.sh` and `collect-flow-a-smoke-evidence.sh`.
- **Documentation:** `docs/operations/phase3-us003-linkedin-publication-validation-*.md`, LinkedIn publication operator docs, `docs/CURRENT-STATE.md`, `docs/RUNTIME-STATE.md`, `docs/product/progress-checklist.md` (after validation).
- **Worker:** changes only if controlled validation exposes blocking defects; default expectation is tooling and docs.
- **Server:** temporary `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` during validation window on `192.168.0.194`; OAuth bootstrap (token store files, tunnel, browser authorization) must be completed and green on `GET /linkedin/oauth/status` before validation — see `docs/deployment/linkedin-publication-prerequisites.md`.
- **External:** one real LinkedIn personal-profile text post (visible on operator profile until manually removed).
- **Tests:** extend smoke-script contract tests if script interfaces change; no real LinkedIn API calls in unit tests.

## Backlog mapping

| ID | Acceptance criteria addressed |
|----|-------------------------------|
| **BL-002** | Completion outcome when US-003, US-004, and US-005 are all demonstrated with real evidence. |
| **US-003** | OAuth/member validation; one approved variant; state transitions; visible outcomes; clear failures; no unintentional side effects. |
| **US-004** | `linkedin_post_urn` stored; LinkedIn visibility confirmed; duplicate publication prevented. |
| **US-005** | Publication safeguards restored after controlled test. |

### Intentionally excluded

- BL-003 calendar status summary correction.
- BL-004 n8n activation and BL-005 fully unattended Flow A.
- BL-006+ LinkedIn review process and scheduled multi-variant execution.
- Marking BL-002 complete before all three user stories have demonstrated acceptance criteria.
