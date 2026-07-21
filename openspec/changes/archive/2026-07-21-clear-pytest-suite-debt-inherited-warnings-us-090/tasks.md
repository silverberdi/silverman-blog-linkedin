## 1. Fix suite debt

- [x] 1.1 Fix markdown-only connector `_write_calendar` to seed calendar store (`write_and_seed_calendar`)
- [x] 1.2 Realign compose deployment artifact tests to current mount / avoid `postgres:` URL false positive
- [x] 1.3 Restore normative Flow B MUST NOT enter Flow A automatic publish paths phrase in `#flow-a-vs-flow-b`
- [x] 1.4 Update console static HTML contract assertions to current preview/real copy
- [x] 1.5 Add `httpx2` (dev) and clear Starlette TestClient deprecation warning

## 2. Verify green bar

- [x] 2.1 Full pytest unrestricted: 0 failed, 0 warnings
- [x] 2.2 Vitest green
- [x] 2.3 Refresh baseline evidence + SoT pointers; close US-090 / BL-033 in product docs

## 3. Lifecycle

- [x] 3.1 `git diff --check`; secrets audit; OpenSpec validate
- [x] 3.2 Impl / sync / archive commits
