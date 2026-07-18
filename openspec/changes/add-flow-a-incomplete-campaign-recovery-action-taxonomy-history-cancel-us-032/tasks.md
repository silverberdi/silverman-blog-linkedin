## 1. Recovery Metadata and Taxonomy Foundation

- [x] 1.1 Extend incomplete-campaign recovery models with closed `recommended_recovery_action` / `executed_recovery_action` enums, `flow_a_recovery` cancel-state helpers, and secret-safe attempt record builders (`attempt_id`, UTC `recorded_at`, operation, outcome, reason_code, summary, optional stage/classification/repair fields).
- [x] 1.2 Implement deterministic `recommended_recovery_action` mapping from cancel state, `last_valid_stage`, `recovery_classification`, location/claim gates, and ambiguity blocks per design (complementary to the five-value classification; never write taxonomy strings into `recovery_classification`).
- [x] 1.3 Implement bounded append-only ledger helpers on campaign metadata (`flow_a_recovery.attempts`, max 50 with oldest-first trim; treat missing `flow_a_recovery` as empty/not cancelled) without rewriting `state_history` or inventing durable stage success.

## 2. Cancel, History Wiring, and Gate Resume/Repair

- [x] 2.1 Implement applied cancel: set `flow_a_recovery.cancelled` + timestamps/reason/summary; append one cancel attempt; leave pipeline `state`, confirmed stage evidence, and editorial files unchanged; do not call LinkedIn publication cancel.
- [x] 2.2 Implement cancel idempotency and dry-run: already-cancelled → `outcome=noop` without extra ledger append; `dry_run=true` returns would-be cancel without writes.
- [x] 2.3 Gate applied and dry-run resume/repair when cancelled with `reason_code=flow_a_recovery_cancelled`, `recommended_recovery_action=cancel_recovery`, and zero mutations.
- [x] 2.4 Wire applied resume/repair control-path completions to append one secret-safe attempt each; ensure dry-run, HTTP 401, and HTTP 422 paths never append; leave `recovery_classification` unchanged on cancel by default.

## 3. HTTP Contract Enrichment

- [x] 3.1 Add `POST /flow-a/incomplete-campaign-recovery/cancel` with `Depends(require_api_key)`, validated body (`campaign_id`, optional `dry_run`/`reason_code`/`summary`), no client absolute paths, and structured secret-safe JSON outcomes.
- [x] 3.2 Enrich inspect/resume/repair responses with additive fields only: `recommended_recovery_action`, `recovery_cancel`, recent `recovery_attempts` (inspect ≤20), and mutating `executed_recovery_action` / attempt echo — without breaking existing US-031 fields.
- [x] 3.3 Keep operational-status, operational-alerts, and LinkedIn publication recovery routes/contracts untouched.

## 4. Behavioral Tests

- [x] 4.1 Add taxonomy mapping tests for `noop_already_complete`, `resume`, `repair`, `requeue`, `manual_intervention`, and `cancel_recovery`, proving classification enum members are never replaced by taxonomy strings.
- [x] 4.2 Add attempt-history tests: applied resume/repair append; dry-run/401/422 do not append; inspect returns recent attempts; FIFO trim at 50; secret/body exclusion in ledger and responses.
- [x] 4.3 Add cancel tests: first cancel persists state + attempt; idempotent noop; dry-run zero writes; post-cancel resume/repair blocked; durable stage evidence and `state_history` unchanged; LinkedIn cancel not invoked.
- [x] 4.4 Add regression coverage that existing US-031 inspect/resume/repair happy paths, short-circuits, and repair allowlist still pass with additive fields present.

## 5. Documentation and Status

- [x] 5.1 Update operator docs for action taxonomy, attempt history bounds, cancel semantics/idempotency, and non-goals (no reopen, no LinkedIn cancel, no BL-012 closure).
- [x] 5.2 Update `docs/CURRENT-STATE.md` after implementation verification to record US-032 taxonomy/history/cancel as implemented/tested without claiming deployment, operator acceptance, or BL-012 closure.
- [x] 5.3 Update `docs/product/progress-checklist.md` and US-032 status only to the demonstrated business-validation level; do not mark US-032 accepted or BL-012 closed from code alone; leave US-031 status unchanged unless newly demonstrated.

## 6. Verification and Business Validation

- [x] 6.1 Run targeted incomplete-campaign recovery tests plus affected Flow A lifecycle / operational-queue regression coverage.
- [x] 6.2 Run the full pytest suite because executable worker code changes; resolve any new warnings attributable to this change; run strict OpenSpec validation.
- [x] 6.3 Run `git diff --check` and a secrets/content-body audit over modified files and representative inspect/resume/repair/cancel responses and ledger entries.
- [x] 6.4 Demonstrate US-032 against controlled fixtures: classify recovery actions; preserve attempt history across calls; safely cancel and block further recovery; show understandable outcomes; communicate blocks/failures; prove completed work is not duplicated or unintentionally changed.
- [ ] 6.5 Obtain business review of every US-032 acceptance criterion before marking the story accepted; keep BL-012 open until both US-031 and US-032 are accepted.
