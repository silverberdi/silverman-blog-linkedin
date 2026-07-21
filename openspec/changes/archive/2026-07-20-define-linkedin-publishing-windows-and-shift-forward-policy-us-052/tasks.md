## 1. Normative operations policy

- [x] 1.1 Create `docs/operations/linkedin-publishing-windows-and-shift-forward-policy.md` covering: preferred windows (Tue–Thu; 08:00–10:00 or 16:00–18:00 America/Bogota) with cross-link to editorial `#linkedin-distribution-strategy`; audience balancing at strategy level (packaging remains Flow A); shift-forward when cadence-infeasible (reuse US-051 cadence-conflict meaning; also US-040K max 2 + existing strategy constraints; MUST NOT silently keep infeasible time); feasible-slot definition; fail-closed 28 operator-local-day horizon and no-feasible-slot error obligation for US-088; residual cadence-conflict still requires US-087 warning; blocked-state vocabulary (cadence vs density vs no-feasible-slot; sequence/enablement/OAuth by reference to US-051); explicit non-goals (no US-087/US-088/US-089 implementation; no second cadence engine; no US-020 weaken)
- [x] 1.2 Update `docs/operations/linkedin-cadence-spacing-policy.md` to replace “preferred windows deferred to US-052” with a pointer to the new US-052 policy; keep US-020 spacing / cadence-conflict / density-gap coexistence unchanged
- [x] 1.3 Add a brief cross-link from `content-strategy/silverman-editorial-system.md` `#linkedin-distribution-strategy` (preferred windows table) to the new ops policy without changing spacing math or inventing a second 72h constant

## 2. Glossary and status pointers

- [x] 2.1 Add or update concise `docs/GLOSSARY.md` entries as needed for **preferred publishing window**, **shift-forward** (schedule placement), and/or **feasible slot** matching the policy — do not redefine cadence conflict (US-051 remains authoritative)
- [x] 2.2 Update `docs/CURRENT-STATE.md` to note LinkedIn publishing windows + shift-forward **policy defined** (US-052 docs) and that console warning / schedule-time shift-forward / replan remain not implemented (US-087–US-089); do not claim Story accepted
- [x] 2.3 Optionally add a one-line pointer from `docs/deployment/linkedin-publication-prerequisites.md` US-020 section only if needed to prevent drift (windows/shift-forward → US-052 policy); do not rewrite the publish-time guard contract

## 3. Product progress (post-doc, not Story accepted)

- [x] 3.1 Mark US-052 Work started in `docs/product/progress-checklist.md` after policy artifacts exist; leave Story accepted / BL-021 unchecked
- [x] 3.2 Do **not** check off US-052 acceptance criteria in `docs/product/user-stories.md` as Story accepted; leave checkboxes for operator review after apply
- [x] 3.3 Confirm no `src/`, route, n8n, cron, env-default, console UI, or LinkedIn enablement changes were introduced by this change

## 4. Verification

- [x] 4.1 Walk US-052 acceptance criteria against the committed docs and record any gap (docs-only; full pytest not required)
- [x] 4.2 Run `git diff --check` on changed files
- [x] 4.3 Business validation: operator can open the US-052 ops policy and CURRENT-STATE pointer and recognize preferred windows + shift-forward / fail-closed bounds for US-088 without treating infeasible Scheduled times as guaranteed sends — Story accepted remains an explicit operator gate after review

### Verification notes (2026-07-20 apply)

**4.1 US-052 AC walk (no gaps):**

| AC | Evidence |
|----|----------|
| Preferred publishing windows (local-day / clock) at strategy level | Policy §1; editorial `#linkedin-distribution-strategy` cross-link; GLOSSARY **preferred publishing window** |
| Balance audience segments at strategy level; packaging stays Flow A | Policy §2; editorial `#audience-map` / sequencing citations |
| Shift-forward when cadence-infeasible; density + strategy; no silent keep | Policy §3 (feasible slot + shift-forward rules) |
| Residual cadence-conflict still shows US-087 warning | Policy §5 |
| Outcome visible to operators | Policy path + CURRENT-STATE **policy defined** bullet + US-051 / editorial / prerequisites pointers |
| Failures / blocked states clearly communicated | Policy §6 vocabulary (cadence vs density vs no-feasible-slot; sequence/enablement/OAuth by US-051 ref) |
| No duplicate / weaken of existing completed work | Docs-only; §7–8 non-goals; US-020 guard untouched; no second 72h engine |

**4.2** `git diff --check` clean.
**4.3** Operator entry points: [linkedin-publishing-windows-and-shift-forward-policy.md](../../../docs/operations/linkedin-publishing-windows-and-shift-forward-policy.md) and CURRENT-STATE US-052 bullet. Story accepted / BL-021 remain operator gates.
**3.2** US-052 AC checkboxes in `user-stories.md` left unchecked.
**3.3** Diff touches docs + content-strategy + OpenSpec change only — no `src/`, `n8n/`, `deploy/`, console app sources, cron, env-default, or enablement edits.
