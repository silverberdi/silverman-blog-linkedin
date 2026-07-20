## 1. Normative operations policy

- [x] 1.1 Create `docs/operations/linkedin-cadence-spacing-policy.md` covering: US-020 72h same-campaign spacing ratification; cross-campaign independence; LinkedIn frequency ≈ ~2/local day via US-040K; blog frequency strategy-level (no automation); US-040K density + BL-019 gap as interim coexisting controls (density ≠ cadence; gap does not bypass cadence); cadence conflict definition for US-087/US-088/US-089; blocked-state vocabulary (cadence vs sequence vs density vs enablement vs OAuth); explicit non-goals (no second cadence engine; no US-087–US-089 implementation in this change)
- [x] 1.2 Cross-link the new policy from `docs/deployment/linkedin-publication-prerequisites.md` (US-020 publish-time sequence and cadence guard section) without rewriting the guard contract

## 2. Glossary and status pointers

- [x] 2.1 Add or update a concise `docs/GLOSSARY.md` entry for **cadence conflict** (and, if needed, clarify density ≠ cadence) matching the policy
- [x] 2.2 Update `docs/CURRENT-STATE.md` to note LinkedIn cadence spacing **policy defined** (US-051 docs) and that console warning / shift-forward / replan remain not implemented (US-087–US-089); do not claim Story accepted
- [x] 2.3 Optionally note in `content-strategy/silverman-editorial-system.md` distribution stagger language that publish-time cadence (US-020 / this policy) is authoritative at send — only if needed to prevent drift; do not change spacing math

## 3. Product progress (post-doc, not Story accepted)

- [x] 3.1 Mark US-051 Work started in `docs/product/progress-checklist.md` after policy artifacts exist; leave Story accepted / BL-021 unchecked
- [x] 3.2 Do **not** check off US-051 acceptance criteria in `docs/product/user-stories.md` as Story accepted; leave checkboxes for operator review after apply (may note “policy artifacts present — pending operator Story accepted” only if the product trio convention requires it)
- [x] 3.3 Confirm no `src/`, route, n8n, cron, env-default, or LinkedIn enablement changes were introduced by this change

## 4. Verification

- [x] 4.1 Walk US-051 acceptance criteria against the committed docs and record any gap (docs-only; full pytest not required)
- [x] 4.2 Run `git diff --check` on changed files
- [x] 4.3 Business validation: operator can open the ops policy and CURRENT-STATE pointer and recognize one shared cadence meaning aligned with live `linkedin_publish_blocked_cadence` — Story accepted remains an explicit operator gate after review

### Verification notes (2026-07-20 apply)

**4.1 US-051 AC walk (no gaps):**

| AC | Evidence |
|----|----------|
| Ratify US-020 72h same-campaign; cross-campaign independence | Policy §1; prerequisites US-020 section unchanged + pointer |
| LinkedIn frequency ≈ ~2/local day via US-040K | Policy §2 |
| Blog frequency strategy-level | Policy §2 |
| Density + gap interim coexistence; density ≠ cadence; gap does not bypass | Policy §3 |
| Cadence conflict = publish-time cadence gate at slot | Policy §4; GLOSSARY |
| Outcome visible | Policy path + CURRENT-STATE **policy defined** bullet + prerequisites pointer |
| Blocked states clear | Policy §5 vocabulary table |
| No weaken/duplicate US-020 | Docs-only; §6–7 non-goals; no `src/` |

**4.2** `git diff --check` clean.
**4.3** Operator entry points: [linkedin-cadence-spacing-policy.md](../../../docs/operations/linkedin-cadence-spacing-policy.md) and CURRENT-STATE US-051 bullet. Story accepted / BL-021 remain operator gates.
**3.2** US-051 AC checkboxes in `user-stories.md` left unchecked (no Story accepted note required by trio convention).
**3.3** Diff touches docs + content-strategy + OpenSpec change only — no `src/`, `n8n/`, `deploy/`, or enablement edits.
