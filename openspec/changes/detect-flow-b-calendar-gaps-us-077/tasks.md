## 1. Gap detect core

- [x] 1.1 Add `flow_b_calendar_gap_detect` module with `detect_next_week_calendar_gaps(...)` that loads settings via `load_gap_operator_settings()`, resolves next operator-local Mon–Sun week + ISO week id, and buckets LinkedIn coverage (`pending`/`queued`/`published`) by local day using existing schedule-visibility / local-day helpers
- [x] 1.2 Apply `gap_posts_threshold` (default 0) and `min_lead_days` (default 5) so only actionable empty days appear in `gaps[]`; days with ≥1 covering posts are not gaps; do not redefine gap as density capacity under max-2
- [x] 1.3 Ensure detect-only path never mutates campaigns, calendar rows, or draft folders and never calls LinkedIn/DeepSeek/ComfyUI/Git; allow detect when `gap_trigger_enabled=false` (echo flag; no trigger side effects)

## 2. Authenticated HTTP API

- [x] 2.1 Add authenticated non-mutating gap-detect endpoint (prefer `GET /flow-b/calendar-gaps`) returning `status` (gaps_found/no_gap), `gaps[]`, target ISO week, `operator_timezone`, settings source, effective knobs, `read_only=true`, `observed_at_utc`; reject unauthenticated callers; secret-safe errors
- [x] 2.2 Confirm no US-082 trigger, US-078/079 discovery/draft, or US-080/081 approve/promote routes are added; no n8n Execute Command; LinkedIn publish enablement untouched

## 3. Tests

- [x] 3.1 Unit/API tests: empty next week → gaps (subject to lead); day with one pending → not a gap; `min_lead_days` filters near days; defaults when settings row missing; DB `min_lead_days` honored; detect allowed with `gap_trigger_enabled=false`; auth required; repeated calls non-mutating; ready-folder alone does not clear gaps
- [x] 3.2 Run targeted pytest for the new module/route; fix warnings attributable to this change; `git diff --check` clean

## 4. Docs and product status

- [x] 4.1 Update `docs/operations/flow-b-simplified-policy.md` (and glossary/planning notes if needed) so US-077 detect is the runtime sensor, distinguish detect vs trigger, and note empty coverage is a proxy not a filesystem inventory — without claiming trigger/discovery/draft implemented
- [x] 4.2 Update `docs/CURRENT-STATE.md` to record gap detect **implemented** (not Story accepted / not deployed unless separately approved)
- [x] 4.3 After demonstrated automated AC, update `docs/product/user-stories.md` US-077 and `docs/product/progress-checklist.md` only to the validated state — do not mark Story accepted without operator walkthrough; do not close BL-019

## 5. Business validation gate

- [x] 5.1 Walk US-077 acceptance criteria against local worker evidence (next-week scan, gap=0, min_lead_days, settings load, clear result shape, non-mutation, auth inspect endpoint)
- [x] 5.2 Record any remaining gaps explicitly; leave US-078–US-082 and BL-019 close unchecked
