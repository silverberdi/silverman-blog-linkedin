# Tasks: define-linkedin-retry-recovery-classification-us-021

## 1. Pre-implementation verification

- [x] 1.1 Re-verify the current failure/blocked taxonomy against code before writing policy text: `linkedin_client._map_http_status` mappings, `retryable` assignments, transport-failure `http_status: null` path, and 201-without-URN path (`src/silverman_blog_linkedin/linkedin_client.py`)
- [x] 1.2 Re-verify manual re-queue behavior for `failed` variants in `queue_linkedin_publication` (`QUEUE_ELIGIBLE_PUBLISH_STATES`, `linkedin_publication` cleared on re-queue) so the documented divergence statement matches actual behavior
- [x] 1.3 Confirm no US-018/US-019/US-020 requirement in `openspec/specs/linkedin-publication-integration/spec.md` or `openspec/specs/linkedin-oauth-token-lifecycle/spec.md` needs modification (additive references only; BL-007 closed)

## 2. Operator policy documentation

- [x] 2.1 Create `docs/operations/linkedin-retry-recovery-classification.md` with: the complete classification table (recoverable transient / recoverable after remediation / non-recoverable as-is / uncertain, keyed on `last_error_code` + `http_status` including `null` and `201` cases; unlisted combinations fail safe to uncertain), recovery path per class over existing operations only, the blocked class with its stable codes and no-`publish_state`-change statement, the mandatory uncertain-outcome verification procedure (post exists → manual evidence repair to `published` with real URN/`published_at`, re-queue forbidden; post absent → manual re-queue safe), token-renewal-precedes-re-queue rule for token-class failures, and explicit US-022 boundary statements (no automatic retry; evidence-clearing-on-re-queue divergence recorded for US-022)
- [x] 2.2 Extend `docs/deployment/linkedin-publication-prerequisites.md`: add a US-021 classification-and-recovery section (or extend the US-019 failure-taxonomy section additively) linking the policy document, with the classification table summary and the mandatory verification step at the manual re-queue touchpoint; keep all existing US-018/US-019/US-020 text intact
- [x] 2.3 Audit both documents: no secrets, no variant body text, qualified status language only (policy defined ≠ operationally validated), no bare "Flow A complete"

## 3. Canonical context updates

- [x] 3.1 Update `docs/CURRENT-STATE.md`: add BL-008 / US-021 "policy defined" entry (mirroring the US-015/US-016 pattern), and record the known divergence that manual re-queue of a `failed` variant clears stored `linkedin_publication` failure evidence (US-022 input)
- [x] 3.2 Verify `docs/RUNTIME-STATE.md` needs no change (no live flags touched; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` untouched and fail-closed)

## 4. Verification

- [x] 4.1 Run `openspec validate --change define-linkedin-retry-recovery-classification-us-021 --strict` (or current equivalent) and fix any artifact issues
- [x] 4.2 Confirm zero changes under `src/`, `tests/`, `n8n/`, and `deploy/` (`git status` / `git diff --stat`); docs-only change, full pytest not required — record that rationale
- [x] 4.3 Run `git diff --check`; stage-time secrets audit on new/modified files

## 5. Business validation and tracking

- [x] 5.1 Demonstrate US-021 acceptance criteria against the artifacts: each criterion mapped to the spec requirement and the operator documentation section that satisfies it; record any criterion not fully demonstrated as in progress
- [x] 5.2 Update `docs/product/user-stories.md` (US-021) and `docs/product/progress-checklist.md` only for criteria actually demonstrated; do not close BL-008 (US-022 remains open); do not mark US-021 complete beyond demonstrated policy-definition scope
