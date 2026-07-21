## 1. Normative SoT + suite baseline run

- [x] 1.1 Create `docs/operations/warning-and-test-quality-baseline.md` (US-067+US-068; how to run suites; inventory; inherited vs new; zero new warnings; independence from BL-029)
- [x] 1.2 Run full pytest via `.venv`; inventory warnings; fix cheap root causes where safe
- [x] 1.3 Run frontend Vitest if practical; include summary in evidence
- [x] 1.4 Write dated baseline evidence under `docs/operations/` (counts + warning classes; no secrets)

## 2. Glossary and status

- [x] 2.1 GLOSSARY entries for warning/test quality baseline (BL-028)
- [x] 2.2 CURRENT-STATE: SoT + baseline run; BL-028 closed when stories accepted
- [x] 2.3 Product backlog / user-stories pointers

## 3. Product progress

- [x] 3.1 Mark US-067 + US-068 Story accepted; close BL-028
- [x] 3.2 Check ACs in user-stories.md
- [x] 3.3 Confirm BL-029 CI left open; no enablement mutation

## 4. Verification

- [x] 4.1 Walk ACs; `git diff --check`; secrets audit
- [x] 4.2 Business validation: baseline document makes inherited vs new distinguishable
