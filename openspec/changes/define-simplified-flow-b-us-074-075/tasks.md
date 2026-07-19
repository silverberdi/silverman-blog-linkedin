## 1. Normative operations policy

- [x] 1.1 Create `docs/operations/flow-b-simplified-policy.md` covering process boundary, Authority Manager, `pending-approval/` eligibility, weekly gap defaults, n8n→HTTP intent, ISO-week idempotency, spill algorithm A, DeepSeek v1 + pluggable note, discovery non-news posture, and cross-links to US-082+ and planning notes
- [x] 1.2 Cross-link the new policy from `docs/product/planning-notes-flow-b-simplification.md` and `docs/workflows/linkedin-draft-review-flow.md`

## 2. Glossary and editorial alignment

- [x] 2.1 Verify `docs/GLOSSARY.md` Flow B / Silverman Authority Manager / `pending-approval` / `ready` / Mandatory review entries match the policy (complete any missing wording)
- [x] 2.2 Verify `content-strategy/silverman-editorial-system.md` `#flow-a-vs-flow-b` matches the policy (complete any missing wording)
- [x] 2.3 Grep touched docs for obsolete Flow B gap language (daily-only gap, mandatory LinkedIn review for Flow B after blog OK) and fix remaining hits in scope

## 3. Product progress and CURRENT-STATE

- [x] 3.1 Update `docs/CURRENT-STATE.md` to note Flow B simplified **policy defined** (US-074/US-075 docs) and runtime still not implemented (US-076+)
- [x] 3.2 Mark US-074/US-075 Work started in `docs/product/progress-checklist.md` after policy artifacts exist; leave Story accepted unchecked pending operator review
- [x] 3.3 Confirm no `src/` / route / n8n Execute Command changes were introduced by this change

## 4. Verification

- [x] 4.1 Walk US-074 and US-075 acceptance criteria against the committed docs and record any gap
- [x] 4.2 Run `git diff --check` on changed files
