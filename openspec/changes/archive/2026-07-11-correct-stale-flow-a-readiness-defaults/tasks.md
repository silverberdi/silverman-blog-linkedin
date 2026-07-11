## 1. Readiness script defaults

- [x] 1.1 Replace `DEFAULT_EXPECTED_COMMITS` in `scripts/flow_a_readiness.py` with `("88cd5bc", "96519c3", "9dba064")` per design D1
- [x] 1.2 Add module-level comment documenting each milestone SHA and purpose (design D2)
- [x] 1.3 Confirm `--expected-commit` override still replaces defaults entirely (no merge with defaults)

## 2. Tests

- [x] 2.1 Update `tests/test_flow_a_readiness.py` assertions that reference old default SHAs
- [x] 2.2 Add test verifying `DEFAULT_EXPECTED_COMMITS` equals the three documented operational milestones
- [x] 2.3 Run `pytest tests/test_flow_a_readiness.py` and confirm pass

## 3. Operator documentation

- [x] 3.1 Update `docs/deployment/ubuntu-server-worker-deployment.md` Phase 0 expected-commit list to new defaults with brief meanings
- [x] 3.2 Update `README.md` Flow A readiness section: remove or revise "defaults may lag" caveat; document capability milestones and clarify they differ from `last_verified_baseline` in CURRENT-STATE (not "permanent expected commit")

## 4. Canonical context

- [x] 4.1 Remove the `DEFAULT_EXPECTED_COMMITS` known-divergence row from `docs/CURRENT-STATE.md`
- [x] 4.2 Add a brief CURRENT-STATE note (e.g. under deployment/readiness pointers or a short “Flow A readiness defaults” bullet) distinguishing `last_verified_baseline` (`615091c` @ `2026-07-11T07:45:00Z`, point-in-time) from `DEFAULT_EXPECTED_COMMITS` (`88cd5bc`, `96519c3`, `9dba064` — capability milestones, not permanent runtime requirements)

## 5. Verification and product tracking

- [x] 5.1 Run `/opsx-verify` for change `correct-stale-flow-a-readiness-defaults`
- [x] 5.2 Run `git diff --check` and secrets audit on touched files
- [x] 5.3 Business validation: run `python scripts/flow_a_readiness.py --repo-path . --phase 0` locally and confirm `expected_commits` check passes on current HEAD
- [ ] 5.4 After explicit approval and validation: update `docs/product/progress-checklist.md` BL-026 and user-story US-061–US-063 only if acceptance criteria are demonstrated (defer if not approved yet)
