## 1. Normative collection procedure definition

- [x] 1.1 Extend `docs/operations/business-and-content-metrics.md` (preferred single SoT; or a clearly linked sibling under `docs/operations/`) to cover US-055 Story 1: consistent collection procedure (cadence after period close; period identity fields; eligibility context as supporting only; completeness rules requiring value-or-blocked-state per US-053 / US-054 family; forbid filler zeros); theme/variant comparison (thin operator notes; signal documented; forbid ranks from schedule/pending/package-complete); effective-format identification (reuse US-054 §8 high-performing criteria; no second contradictory table; no Flow A/B duplication); reuse BL-022 measurement period and blocked-state vocabulary with incomplete-collection ≠ measured-zero guidance; update scope banner so US-055 procedure is in scope while US-056, analytics platforms, Flow A/B gating, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` mutation, US-053/US-054 Story accepted, BL-022 close, and BL-020 close remain non-goals
- [x] 1.2 Extend `docs/operations/business-and-content-metrics-log-TEMPLATE.md` with durable US-055 sections for collection completeness, theme/variant comparison notes, and effective-format labels (keep secrets/PII out of git)
- [x] 1.3 Cross-link from product backlog / user-stories BL-023 section (pointer only for US-055 procedure) without rewriting Flow A/B specs or marking US-053 / US-054 Story accepted or closing BL-022

## 2. Glossary and status pointers

- [x] 2.1 Update `docs/GLOSSARY.md` **business and content metrics** entry (or add a concise US-055 collection sub-note) so consistent collection / theme-variant comparison / effective formats are named without conflating them with operational metric chips, inventing ranks from schedule metadata, or claiming US-056 planning feed
- [x] 2.2 Update `docs/CURRENT-STATE.md` to note US-055 collection procedure **published** (docs) and that US-056 / Story accepted / BL-023 close remain not done; do not claim US-053 or US-054 Story accepted; do not close BL-022 or BL-020
- [x] 2.3 Optionally add a one-line help pointer in Authority Manager only if visibility AC still needs it after docs + CURRENT-STATE; default is docs-only (no metrics dashboard)

## 3. Product progress (post-doc, not Story accepted)

- [x] 3.1 Mark US-055 Work started in `docs/product/progress-checklist.md` after procedure artifacts exist; leave Story accepted / BL-023 / US-053 / US-054 Story accepted / BL-022 unchecked
- [x] 3.2 Do **not** check off US-055 (or US-053 / US-054) acceptance criteria in `docs/product/user-stories.md` as Story accepted; leave checkboxes for operator review after apply; add a status note pointing at the extended ops definition when useful
- [x] 3.3 Confirm no Flow A/B pipeline gating, no required analytics auto-fetch routes, no LinkedIn enablement mutation, no US-056 planning feed, no US-053/US-054 Story accepted, no BL-022 close, and no BL-020 Story accepted / close were introduced by this change

## 4. Verification

- [x] 4.1 Walk US-055 acceptance criteria against the committed docs and record any gap (docs/contract-first; full pytest not required unless optional console pointer ships)
- [x] 4.2 Run `git diff --check` on changed files
- [x] 4.3 Business validation: business owner can open the extended ops definition and CURRENT-STATE pointer and recognize consistent collection completeness rules, theme/variant comparison guidance, effective-format identification aligned with US-054, and blocked-state vocabulary consistent with BL-022 — Story accepted remains an explicit operator gate after review
