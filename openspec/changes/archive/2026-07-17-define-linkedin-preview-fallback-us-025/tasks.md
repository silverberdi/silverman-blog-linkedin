# Tasks: define-linkedin-preview-fallback-us-025

Docs/spec-only change: no code under `src/`, `tests/`, `n8n/`, or `deploy/` may change. Full pytest is not required (no executable code changes); spec validation and repository hygiene checks are.

## 1. Pre-apply verification

- [x] 1.1 Re-read `docs/product/backlog.md` (BL-009), `docs/product/user-stories.md` (US-023–US-025), and `docs/product/progress-checklist.md`; confirm the proposal's scope still matches US-025 acceptance criteria and no acceptance criteria are missing or contradictory
- [x] 1.2 Re-read canonical specs `linkedin-article-preview-verification`, `linkedin-article-preview-rendering-confirmation`, `linkedin-publication-integration`, `linkedin-retry-recovery-classification`, `linkedin-distribution-scheduling-model`, and `linkedin-article-preview-image-support`; confirm the delta spec introduces no MODIFIED requirement and no contradiction with their contracts (US-024 outcome vocabulary, US-020 guard semantics, US-022 evidence rules, defer/cancel mechanics)

## 2. Fallback policy document

- [x] 2.1 Create `docs/operations/linkedin-preview-fallback-policy.md` implementing every requirement of the delta spec: purpose/boundaries (US-023 input truth, US-024 observation source, no LinkedIn API/UI automation), fallback triggers table (triggering US-024 outcomes only; `preview_inputs_incorrect` routed to the US-023 remediation loop), pre-publish decision procedure (accept / delay via defer with US-020 follower-blocking note and queued-variant honesty / correct-and-reverify with ADR-0002 and Git-push approval note / cancel with irreversibility note), post-publish recovery procedure (accept-and-record default; no evidence mutation with stated rationale; re-scrape never a post-publish remedy)
- [x] 2.2 Add the supported / approval-gated / forbidden action classification table with the delete/re-post safety analysis, the approval-gated manual post-removal rules (prior recorded approval; variant stays `published`; cadence unchanged), the forbidden list (cache-busting, test posts, metadata falsification, UI scraping, undocumented behavior, automatic execution), and the two named deferred future-change candidates (`content.article` post format; worker-supported deletion/re-publication) with their preconditions
- [x] 2.3 Add the fixed fallback outcome vocabulary (`fallback_accept_rendering`, `fallback_delay_publication`, `fallback_correct_inputs_reverify`, `fallback_cancel_variant`, `fallback_post_removal_approved`, `fallback_format_change_deferred`, `fallback_blocked`), the per-decision evidence-record template (campaign id, variants + `publish_state`, US-024 and US-023 references, action + classification + approval reference, endpoint calls dry-run/real, resulting state, outcome label, operator + UTC timestamp; no secrets/body text/image bytes; campaign metadata never edited), and the blocked-state table with named next actions
- [x] 2.4 Verify the policy document safeguards section states: no retry-budget consumption, no `recovery_confirmation` use for non-`failed` variants, defer-blocks/cancel-releases sequence effects, cadence anchored to stored `published_at` (including after approved removal), scheduling idempotency untouched, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` fail-closed and never bypassed

## 3. Cross-references and product docs (qualified status language throughout)

- [x] 3.1 Update `docs/operations/linkedin-preview-rendering-confirmation.md`: replace the "US-025 territory / not defined here" placeholders (purpose boundary, decision-matrix next actions, safe re-scrape honest limit) with links to the fallback policy — without changing any US-024 procedure step, outcome label, or rule
- [x] 3.2 Update `docs/deployment/linkedin-publication-prerequisites.md`: add a pointer from the "Post format (v1)" and US-023/US-024 sections to the fallback policy for wrong/missing preview reactions
- [x] 3.3 Update `docs/product/user-stories.md` US-025: status line "Policy defined — not operationally validated, story not accepted; BL-009 remains open", policy artifact link, and per-criterion mechanism mapping at policy-definition scope with checkboxes left unchecked
- [x] 3.4 Update `docs/product/progress-checklist.md` US-025: mark story reviewed / acceptance criteria agreed / work started; leave business outcome demonstrated, acceptance criteria validated, and story accepted unchecked
- [x] 3.5 Update `docs/CURRENT-STATE.md`: add US-025 entry under "Implemented but not operationally validated" (policy defined; docs + canonical procedure-spec only; no worker code; acceptance requires operator demonstration; BL-009 remains open pending US-023 deploy/validation, US-024 demonstration, and US-025 demonstration)

## 4. Verification and hygiene

- [x] 4.1 Run `openspec validate define-linkedin-preview-fallback-us-025 --strict` (and `openspec validate --all`) and fix any findings
- [x] 4.2 Confirm `git status` shows changes only under `openspec/changes/define-linkedin-preview-fallback-us-025/`, `docs/`, and no changes under `src/`, `tests/`, `n8n/`, `deploy/`
- [x] 4.3 Run `git diff --check` (whitespace) and a secrets audit over new/modified files (no tokens, URNs are non-secret identifiers and allowed, no session data, no variant body text)
- [ ] 4.4 Run `/opsx-verify`; obtain explicit commit approval; implementation commit, then `/opsx-sync` (canonical spec `linkedin-article-preview-fallback` lands) and `/opsx-archive` as separate approved commits per the OpenSpec lifecycle

## 5. Operational demonstration and business validation (approval-gated — separate from apply)

Do not start section 5 without explicit operator approval. It depends on the pending US-023 deploy + operational validation on `192.168.0.194` and on a US-024 confirmation producing a fallback-triggering outcome (or `preview_confirmed`, in which case the demonstration uses a controlled decision walkthrough agreed with the operator).

- [ ] 5.1 With explicit operator approval, demonstrate the fallback policy end-to-end on a real campaign: a recorded triggering US-024 evidence record → decision per the policy → supported action executed dry-run then real over existing endpoints (or accept-and-record with no calls) → completed fallback evidence record with a fixed outcome label; verify zero changes to campaign publication evidence and zero retry-budget consumption
- [ ] 5.2 Record the demonstration evidence report under `docs/operations/` following the evidence-record template; confirm blocked states (if encountered) were recorded as `fallback_blocked` with named conditions
- [ ] 5.3 Business validation review: only after the demonstrated outcome satisfies US-025 acceptance criteria, update `docs/product/user-stories.md` US-025 checkboxes and `docs/product/progress-checklist.md` (business outcome demonstrated → acceptance criteria validated → story accepted), and update `docs/CURRENT-STATE.md`; evaluate BL-009 closure only when US-023, US-024, and US-025 are all demonstrated and accepted — partial outcomes remain explicitly in progress
