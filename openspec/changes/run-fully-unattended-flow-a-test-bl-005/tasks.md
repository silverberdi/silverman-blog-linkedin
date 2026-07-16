## 1. Ready-gate preparation (US-012 prerequisites)

- [x] 1.1 Remove AppleDouble `._*` files from `blog-posts/ready/`
- [x] 1.2 Remediate front matter for `05-keep-contracts-boring.md` and `06-search-is-not-one-model.md` (required fields including `layout`, `date`, `categories`, `tags`, `description`, `image`)
- [x] 1.3 Stage serialization: keep only Post A (`05-...`) in ready; hold Post B (`06-...`) outside ready until Manual completes
- [x] 1.4 Confirm ComfyUI enablement / image remediation path or companion PNG readiness for both posts

## 2. Manual unattended run — Post A (US-012 / US-013 / US-014)

- [x] 2.1 Verify `ready_count=1` for Post A and Flow A workflow `silvermanFlowAPublish01` active
- [x] 2.2 Execute Manual Trigger / CLI execute; do not intervene mid-run
- [x] 2.3 Verify publish → live-site confirmation (when enabled), LinkedIn package, distribution schedule, source lifecycle / `flow_a_complete` — **PASS**
- [x] 2.4 Verify campaign + calendar records; confirm no LinkedIn publication API calls — **PASS**
- [x] 2.5 Record Manual section in `docs/operations/bl-005-unattended-flow-a-validation-2026-07-15.md`

## 3. Schedule unattended run — Post B (US-012 / US-013 / US-014)

- [x] 3.1 After Manual PASS, place only Post B in ready (`ready_count=1`)
- [x] 3.2 Wait for Schedule Trigger `0 9 * * *` UTC (record PENDING if waiting); no mid-run intervention — Schedule fired `2026-07-16T09:01Z`
- [x] 3.3 Verify same full-path outcomes as Manual for Post B campaign — **PASS** after post-lag resume (`flow_a_complete`)
- [x] 3.4 Confirm no LinkedIn publication API calls; Flow A still active / single-flight intact — **PASS**
- [x] 3.5 Record Schedule section + overall PASS/PENDING/FAIL in the same ops evidence file — overall **PASS**

## 4. Product and context updates (demonstrated only)

- [x] 4.1 Update `docs/CURRENT-STATE.md`: BL-005 / US-012–US-014 status with qualified language
- [x] 4.2 Update `docs/RUNTIME-STATE.md` if live flags/revision materially change
- [x] 4.3 Update `docs/product/user-stories.md` ACs for US-012–US-014 when demonstrated
- [x] 4.4 Update `docs/product/progress-checklist.md` and backlog: close BL-005; leave BL-006/BL-007 open

## 5. Business validation and verify prep

- [x] 5.1 Map evidence to every US-012 / US-013 / US-014 AC across Manual + Schedule
- [x] 5.2 Confirm out of scope remains open: BL-006, BL-007, LinkedIn API publish, permanent flag policy
- [x] 5.3 Run `openspec validate run-fully-unattended-flow-a-test-bl-005 --strict`; prepare `/opsx-verify` before any commit request
