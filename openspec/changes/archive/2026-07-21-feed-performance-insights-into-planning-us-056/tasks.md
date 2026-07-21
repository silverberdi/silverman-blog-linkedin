## 1. Normative planning-feedback procedure definition

- [x] 1.1 Extend `docs/operations/business-and-content-metrics.md` (preferred single SoT; or a clearly linked sibling under `docs/operations/`) to cover US-056 Story 2: feed insights into future planning (allowed inputs = recorded US-053 / US-054 / US-055 period evidence; where planning-insight notes go; how planning decisions are recorded for the next horizon; default calendar-month / America/Bogota alignment); reduce repetition of low-performing content (documented criteria as inverse/complement of US-054 §8 high-performing / US-055 §16 effective-format language; signal or blocked state required; forbid ranks from schedule/pending/package-complete); keep human oversight (MUST NOT auto-mutate strategy docs, editorial backlog, or Flow B discovery/draft/gap-trigger without explicit operator action; metrics-log notes ≠ backlog mutation); reuse BL-022 blocked-state vocabulary with incomplete-insight ≠ actionable-rank guidance; update scope banner / §12 non-goals / §13 preserved behavior so US-056 procedure is in scope while analytics platforms, auto-apply planning mutation, Flow A/B gating, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` mutation, US-053/US-054/US-055 Story accepted, BL-022 close, BL-023 close, and BL-020 close remain non-goals — do **not** redefine US-055 §§14–16 collection consistency
- [x] 1.2 Extend `docs/operations/business-and-content-metrics-log-TEMPLATE.md` with durable US-056 sections for planning-insight notes (inputs cited), low-performing labels (signal or blocked state), planning decisions for next horizon, and human-applied confirmation that backlog / Flow B / strategy were not auto-mutated (keep secrets/PII out of git)
- [x] 1.3 Cross-link from product backlog / user-stories BL-023 section (pointer only for US-056 procedure) without rewriting Flow A/B specs or marking US-053 / US-054 / US-055 Story accepted or closing BL-022 / BL-023

## 2. Glossary and status pointers

- [x] 2.1 Update `docs/GLOSSARY.md` **business and content metrics** entry (or add a concise US-056 planning-feedback sub-note) so feed-into-planning / low-performing reduction / human oversight are named without conflating them with operational metric chips, inventing ranks from schedule metadata, redefining US-055 collection, or claiming Story accepted
- [x] 2.2 Update `docs/CURRENT-STATE.md` to note US-056 planning-feedback procedure **published** (docs) and that Story accepted / BL-023 close remain not done; do not claim US-053 / US-054 / US-055 Story accepted; do not close BL-022, BL-023, or BL-020
- [x] 2.3 Optionally add a one-line help pointer in Authority Manager only if visibility AC still needs it after docs + CURRENT-STATE; default is docs-only (no metrics dashboard or planning UI) — **skipped** (docs + CURRENT-STATE + GLOSSARY satisfy visibility)

## 3. Product progress (post-doc, not Story accepted)

- [x] 3.1 Mark US-056 Work started in `docs/product/progress-checklist.md` after procedure artifacts exist; leave Story accepted / BL-023 / US-053 / US-054 / US-055 Story accepted / BL-022 unchecked
- [x] 3.2 Do **not** check off US-056 (or US-053 / US-054 / US-055) acceptance criteria in `docs/product/user-stories.md` as Story accepted; leave checkboxes for operator review after apply; add a status note pointing at the extended ops definition when useful
- [x] 3.3 Confirm no Flow A/B pipeline gating, no required analytics auto-fetch routes, no LinkedIn enablement mutation, no auto-mutation of strategy / editorial backlog / Flow B, no US-055 collection redefinition, no US-053/US-054/US-055 Story accepted, no BL-022 close, no BL-023 close, and no BL-020 Story accepted / close were introduced by this change

## 4. Verification

- [x] 4.1 Walk US-056 acceptance criteria against the committed docs and record any gap (docs/contract-first; full pytest not required unless optional console pointer ships) — see [us-056-planning-feedback-doc-walk-2026-07-21.md](../../../docs/operations/us-056-planning-feedback-doc-walk-2026-07-21.md)
- [x] 4.2 Run `git diff --check` on changed files
- [x] 4.3 Business validation: business owner can open the extended ops definition and CURRENT-STATE pointer and recognize planning-feedback inputs and recording, low-performing criteria aligned with high-performing / effective-format language, human-oversight fail-closed rules, and blocked-state vocabulary consistent with BL-022 — Story accepted remains an explicit operator gate after review
